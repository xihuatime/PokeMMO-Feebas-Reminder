#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
丑丑鱼点提醒器 —— 常驻托盘的周期提醒小工具

规则：
    锚点 22:15，周期 45 分钟，全天 24 小时循环。
    因为 1440 / 45 = 32 整除，45 分钟周期在一天里正好走满 32 格，
    所以「与当日 22:15 相差 45 分钟整数倍」等价于「距锚点绝对分钟数是 45 的整数倍」，
    跨天、跨月、跨年都自动延续，不需要任何重置逻辑。

用法：
    python reminder.py            正常启动（带控制台）
    pythonw reminder.py           静默启动（无控制台窗口，推荐）
    python reminder.py --selfcheck  只跑时刻算法的自检，不启动界面

依赖：pystray、Pillow（tkinter / winsound 是标准库自带的）
"""

import ctypes
import sys

# Windows 高分缩放（125% / 150%）下 tkinter 界面发虚，是因为进程默认按 96 DPI 绘制再被系统位图拉伸。
# 这段必须在 import tkinter 之前执行，否则 Tk 已按旧 DPI 初始化，再声明就无效了。
if sys.platform == "win32":
    _ok = False
    try:
        # 优先 Per-Monitor v2：连标题栏、菜单等非客户区也按显示器缩放正确绘制。
        # 必须显式声明 argtypes：DPI_AWARENESS_CONTEXT 是 64 位句柄，直接传 -4 会被截断成 32 位导致调用失败。
        _user32 = ctypes.windll.user32
        _user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        _user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
        _ok = bool(_user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)))
    except Exception:
        _ok = False
    if not _ok:
        try:
            # 降级一：shcore 的 Per-Monitor（Win8.1+），客户区不再被位图拉伸
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                # 降级二：系统级 DPI 感知（Vista+）
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass  # 全都不可用就按系统默认走，不影响程序运行

import math
import queue
import threading
import tkinter as tk
import webbrowser
from datetime import datetime, timedelta

import pystray
from PIL import Image, ImageDraw

try:  # winsound 只有 Windows 有，其它平台静默降级为无声
    import winsound
except ImportError:
    winsound = None

ANCHOR = datetime(2020, 1, 1, 22, 15)  # 相位锚点：某个普通日期的 22:15
PERIOD_MIN = 45                        # 固定周期（分钟）
MESSAGE = "丑丑鱼点已刷新"                  # 固定提醒内容
POPUP_SECONDS = 8                      # 弹窗自动关闭秒数
BG = "#009688"                         # 主题色（弹窗底色 / 托盘图标）

APP_VERSION = "1.3.1"                  # 发版时与 git tag 保持一致
APP_REPO = "https://github.com/xihuatime/PokeMMO-Feebas-Reminder"
APP_CONTACT = "1371365690@qq.com"

WIN_W, WIN_H = 440, 360                # 主窗口尺寸
TEXT = "#1f2328"                       # 主文字色
MUTED = "#6e7781"                      # 次要文字色
WEEKDAYS = "一二三四五六日"


def next_fire_time(now=None):
    """返回 now 之后的下一个提醒时刻（严格大于 now）。"""
    now = now or datetime.now()
    elapsed = (now - ANCHOR).total_seconds() / 60.0
    step = math.floor(elapsed / PERIOD_MIN) + 1
    return ANCHOR + timedelta(minutes=step * PERIOD_MIN)


def selfcheck():
    """时刻算法自检：边界、跨天、跨年、整日循环。"""
    d = datetime
    assert next_fire_time(d(2026, 10, 26, 22, 15)) == d(2026, 10, 26, 23, 0)
    assert next_fire_time(d(2026, 10, 26, 22, 14)) == d(2026, 10, 26, 22, 15)
    assert next_fire_time(d(2026, 10, 26, 22, 15, 0, 1)) == d(2026, 10, 26, 23, 0)
    assert next_fire_time(d(2026, 10, 26, 23, 59)) == d(2026, 10, 27, 0, 30)   # 跨天
    assert next_fire_time(d(2026, 12, 31, 23, 59)) == d(2027, 1, 1, 0, 30)     # 跨年
    # 连跑 32 个点正好一天，之后完全重复
    t = d(2026, 10, 26, 22, 15)
    marks = [t]
    for _ in range(32):
        t = next_fire_time(t)
        marks.append(t)
    assert marks[32] == marks[0] + timedelta(days=1)
    print("selfcheck ok: 32 个提醒点覆盖 24 小时，跨天不重置")


def play_sound():
    if winsound is None:
        return
    try:
        winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
    except RuntimeError:
        winsound.MessageBeep()


class ReminderThread(threading.Thread):
    """后台调度线程：到点回调 on_fire()，换下一个目标时回调 on_schedule(target)。"""

    def __init__(self, on_fire, on_schedule):
        super().__init__(daemon=True)
        self.on_fire = on_fire
        self.on_schedule = on_schedule
        self.enabled = True
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            if not self.enabled:
                self._stop_event.wait(1.0)
                continue
            target = next_fire_time()
            self.on_schedule(target)
            # 分段等待：随时响应暂停/退出；系统休眠唤醒后也能立刻发现已过期
            while not self._stop_event.is_set() and self.enabled:
                remain = (target - datetime.now()).total_seconds()
                if remain <= 0:
                    break
                self._stop_event.wait(min(remain, 1.0))
            if self._stop_event.is_set() or not self.enabled:
                continue
            self.on_fire()


class TrayUI:
    """tkinter 主线程：提醒弹窗 + 跨线程消息队列。其它线程只往队列投递，不直接操作 Tk。"""

    def __init__(self, root):
        self.root = root
        self.queue = queue.Queue()
        self.popup = None
        root.after(200, self._poll)

    def post(self, kind, value=None):
        self.queue.put((kind, value))

    def _poll(self):
        while True:
            try:
                kind, value = self.queue.get_nowait()
            except queue.Empty:
                break
            if kind == "quit":
                self.root.destroy()
                return
            self._show_popup(value)
        self.root.after(200, self._poll)

    def _show_popup(self, text):
        if self.popup is not None and self.popup.winfo_exists():
            self.popup.destroy()

        win = tk.Toplevel(self.root)
        self.popup = win
        win.title("丑丑鱼点提醒")
        win.configure(bg=BG)
        win.attributes("-topmost", True)  # 置顶但不抢焦点，避免打断正在输入的内容
        win.resizable(False, False)
        w, h = 340, 130
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry("%dx%d+%d+%d" % (w, h, (sw - w) // 2, sh // 3))
        tk.Label(win, text=text, font=("Microsoft YaHei UI", 20, "bold"),
                 fg="white", bg=BG).pack(expand=True)
        tk.Label(win, text="点击窗口关闭 · %d 秒后自动消失" % POPUP_SECONDS,
                 font=("Microsoft YaHei UI", 9), fg="#c8e6e2", bg=BG).pack(pady=(0, 10))
        win.bind("<Button-1>", lambda e: win.destroy())
        win.after(POPUP_SECONDS * 1000, lambda: win.winfo_exists() and win.destroy())
        win.lift()


class MainWindow:
    """主窗口：白底，中间大字显示当前时间，下方显示距离下次刷新的倒计时。

    关闭按钮不退出程序，只是收回托盘；要真正退出请用托盘菜单。
    """

    def __init__(self, root, is_enabled):
        self.root = root
        self.is_enabled = is_enabled

        root.title("丑丑鱼点刷新提醒")
        root.configure(bg="white")
        root.resizable(False, False)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry("%dx%d+%d+%d" % (WIN_W, WIN_H, (sw - WIN_W) // 2, (sh - WIN_H) // 3))
        try:  # 有 tkinter 才有 ImageTk，失败就用默认图标，不影响主功能
            from PIL import ImageTk
            self._icon = ImageTk.PhotoImage(make_icon_image().resize((64, 64)))
            root.iconphoto(True, self._icon)
        except Exception:
            pass

        self.clock = tk.Label(root, font=("Microsoft YaHei UI", 54, "bold"), fg=TEXT, bg="white")
        self.clock.pack(pady=(56, 0))
        self.date = tk.Label(root, font=("Microsoft YaHei UI", 10), fg=MUTED, bg="white")
        self.date.pack(pady=(2, 0))
        self.countdown = tk.Label(root, font=("Microsoft YaHei UI", 15), fg=BG, bg="white")
        self.countdown.pack(pady=(34, 0))
        self.next_label = tk.Label(root, font=("Microsoft YaHei UI", 10), fg=MUTED, bg="white")
        self.next_label.pack(pady=(6, 0))

        about = tk.Label(root, text="关于", font=("Microsoft YaHei UI", 9), fg=MUTED,
                         bg="white", cursor="hand2")
        about.place(relx=1.0, rely=1.0, x=-16, y=-12, anchor="se")
        about.bind("<Button-1>", lambda e: self._about())

        root.protocol("WM_DELETE_WINDOW", self.hide)  # 关闭 = 收回托盘，不退出
        self._tick()

    def _tick(self):
        now = datetime.now()
        self.clock.config(text=now.strftime("%H:%M:%S"))
        self.date.config(text=now.strftime("%Y年%m月%d日 星期") + WEEKDAYS[now.weekday()])
        if self.is_enabled():
            target = next_fire_time(now)
            left = max(0, int((target - now).total_seconds()))
            self.countdown.config(text="距离下次刷新 %02d:%02d" % (left // 60, left % 60), fg=BG)
            self.next_label.config(text="下次提醒 %s" % target.strftime("%H:%M"))
        else:
            self.countdown.config(text="提醒已暂停", fg=MUTED)
            self.next_label.config(text="右键托盘图标可恢复")
        self.root.after(500, self._tick)

    def hide(self):
        self.root.withdraw()

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _about(self):
        win = tk.Toplevel(self.root)
        win.title("关于")
        win.configure(bg="white")
        win.resizable(False, False)
        win.transient(self.root)
        w, h = 320, 200
        x = self.root.winfo_rootx() + (WIN_W - w) // 2
        y = self.root.winfo_rooty() + (WIN_H - h) // 2
        win.geometry("%dx%d+%d+%d" % (w, h, x, y))

        tk.Label(win, text="丑丑鱼点刷新提醒工具", font=("Microsoft YaHei UI", 13, "bold"),
                 fg=TEXT, bg="white").pack(pady=(24, 6))
        tk.Label(win, text="版本 %s" % APP_VERSION, font=("Microsoft YaHei UI", 10),
                 fg=MUTED, bg="white").pack()
        tk.Label(win, text="联系作者：%s" % APP_CONTACT, font=("Microsoft YaHei UI", 10),
                 fg=TEXT, bg="white").pack(pady=(16, 4))
        link = tk.Label(win, text=APP_REPO, font=("Microsoft YaHei UI", 9),
                        fg=BG, bg="white", cursor="hand2")
        link.pack()
        link.bind("<Button-1>", lambda e: webbrowser.open(APP_REPO))
        tk.Button(win, text="关闭", command=win.destroy, width=8,
                  font=("Microsoft YaHei UI", 9)).pack(pady=(18, 0))


def make_icon_image():
    """托盘图标：绿圆底 + 白色小鱼（纯图形，不依赖字体）。"""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 61, 61), fill=(0, 150, 136, 255))
    d.ellipse((20, 24, 50, 42), fill=(255, 255, 255, 255))
    d.polygon([(16, 33), (6, 21), (6, 45)], fill=(255, 255, 255, 255))
    d.ellipse((42, 29, 47, 34), fill=(0, 150, 136, 255))
    return img


def main():
    root = tk.Tk()
    state = {"enabled": True, "sound": True}
    window = MainWindow(root, lambda: state["enabled"])
    ui = TrayUI(root)
    icon_ref = {}  # 托盘图标晚于回调创建，用字典占位

    def fire():
        ui.post("popup", MESSAGE)
        if state["sound"]:
            play_sound()
        icon = icon_ref.get("icon")
        if icon is not None:
            try:
                icon.notify(MESSAGE, "丑丑鱼点提醒")  # Windows 系统通知
            except Exception:
                pass  # 通知失败不影响弹窗和声音

    def on_schedule(target):
        icon = icon_ref.get("icon")
        if icon is not None:
            icon.title = "丑丑鱼点提醒器 · 下次 %s" % target.strftime("%H:%M")

    reminder = ReminderThread(fire, on_schedule)

    def toggle_enabled(icon, item):
        state["enabled"] = not state["enabled"]
        reminder.enabled = state["enabled"]
        icon.title = "丑丑鱼点提醒器 · " + ("已开启" if state["enabled"] else "已暂停")

    def toggle_sound(icon, item):
        state["sound"] = not state["sound"]

    def show_window(icon, item):
        window.show()

    def quit_app(icon, item):
        reminder.stop()
        icon.stop()
        ui.post("quit")

    menu = pystray.Menu(
        pystray.MenuItem("显示主窗口", show_window, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("开启提醒", toggle_enabled, checked=lambda i: state["enabled"]),
        pystray.MenuItem("提示音", toggle_sound, checked=lambda i: state["sound"]),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", quit_app),
    )
    icon = pystray.Icon("fish_reminder", make_icon_image(), "丑丑鱼点提醒器", menu)
    icon_ref["icon"] = icon

    reminder.start()
    threading.Thread(target=icon.run, daemon=True).start()
    try:
        root.mainloop()
    finally:
        reminder.stop()


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        selfcheck()
    else:
        main()

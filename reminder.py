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

import math
import queue
import sys
import threading
import tkinter as tk
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
BG = "#009688"                         # 弹窗底色


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
    """tkinter 主线程：隐藏的主窗口 + 提醒弹窗。跨线程通过队列投递，避免直接操作 Tk。"""

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
    root.withdraw()  # 隐藏主窗口，只留托盘图标
    ui = TrayUI(root)

    state = {"enabled": True, "sound": True}
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

    def test_now(icon, item):
        fire()

    def quit_app(icon, item):
        reminder.stop()
        icon.stop()
        ui.post("quit")

    menu = pystray.Menu(
        pystray.MenuItem("开启提醒", toggle_enabled, checked=lambda i: state["enabled"]),
        pystray.MenuItem("提示音", toggle_sound, checked=lambda i: state["sound"]),
        pystray.MenuItem("立即提醒一次", test_now, default=True),
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

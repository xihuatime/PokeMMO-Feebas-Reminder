#!/usr/bin/env python3

import ctypes
import sys

if sys.platform == "win32":
    _ok = False
    try:
        _user32 = ctypes.windll.user32
        _user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        _user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
        _ok = bool(_user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)))
    except Exception:
        _ok = False
    if not _ok:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

import base64
import io
import math
import queue
import threading
import tkinter as tk
import webbrowser
from datetime import datetime, timedelta

import pystray
from PIL import Image

try:
    import winsound
except ImportError:
    winsound = None

ANCHOR = datetime(2020, 1, 1, 22, 15)
PERIOD_MIN = 45
MESSAGE = "丑丑鱼点已刷新"
POPUP_SECONDS = 8
BG = "#009688"

APP_VERSION = "1.3.2"
APP_REPO = "https://github.com/xihuatime/PokeMMO-Feebas-Reminder"
APP_CONTACT = "1371365690@qq.com"

WIN_W, WIN_H = 440, 360
TEXT = "#1f2328"
MUTED = "#6e7781"
WEEKDAYS = "一二三四五六日"

ICON_B64 = (
    "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"
)


def next_fire_time(now=None):
    now = now or datetime.now()
    elapsed = (now - ANCHOR).total_seconds() / 60.0
    step = math.floor(elapsed / PERIOD_MIN) + 1
    return ANCHOR + timedelta(minutes=step * PERIOD_MIN)


def selfcheck():
    d = datetime
    assert next_fire_time(d(2026, 10, 26, 22, 15)) == d(2026, 10, 26, 23, 0)
    assert next_fire_time(d(2026, 10, 26, 22, 14)) == d(2026, 10, 26, 22, 15)
    assert next_fire_time(d(2026, 10, 26, 22, 15, 0, 1)) == d(2026, 10, 26, 23, 0)
    assert next_fire_time(d(2026, 10, 26, 23, 59)) == d(2026, 10, 27, 0, 30)
    assert next_fire_time(d(2026, 12, 31, 23, 59)) == d(2027, 1, 1, 0, 30)
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
            while not self._stop_event.is_set() and self.enabled:
                remain = (target - datetime.now()).total_seconds()
                if remain <= 0:
                    break
                self._stop_event.wait(min(remain, 1.0))
            if self._stop_event.is_set() or not self.enabled:
                continue
            self.on_fire()


class TrayUI:
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
        win.attributes("-topmost", True)
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
    def __init__(self, root, is_enabled):
        self.root = root
        self.is_enabled = is_enabled

        root.title("丑丑鱼点刷新提醒")
        root.configure(bg="white")
        root.resizable(False, False)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry("%dx%d+%d+%d" % (WIN_W, WIN_H, (sw - WIN_W) // 2, (sh - WIN_H) // 3))
        try:
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

        root.protocol("WM_DELETE_WINDOW", self.hide)
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
    return Image.open(io.BytesIO(base64.b64decode(ICON_B64))).convert("RGBA")


def main():
    root = tk.Tk()
    try:
        _dpi = root.winfo_fpixels("1i")
        if _dpi > 0:
            root.tk.call("tk", "scaling", _dpi / 72.0)
    except Exception:
        pass
    state = {"enabled": True, "sound": True}
    window = MainWindow(root, lambda: state["enabled"])
    ui = TrayUI(root)
    icon_ref = {}

    def fire():
        ui.post("popup", MESSAGE)
        if state["sound"]:
            play_sound()
        icon = icon_ref.get("icon")
        if icon is not None:
            try:
                icon.notify(MESSAGE, "丑丑鱼点提醒")
            except Exception:
                pass

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

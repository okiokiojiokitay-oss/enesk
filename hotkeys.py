"""Windows-wide Ctrl+Shift+F10 (save) and Ctrl+Shift+F9 (start/stop)."""

from __future__ import annotations
import ctypes
import queue
import sys
import threading


class Hotkeys:
    def __init__(self, events: queue.Queue):
        self.events = events
        self.thread_id = 0
        self.thread: threading.Thread | None = None
        self.registered: list[int] = []

    def start(self) -> None:
        if sys.platform != "win32":
            return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self) -> None:
        from ctypes import wintypes

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND), ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM), ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD), ("pt", POINT),
                ("lPrivate", wintypes.DWORD),
            ]

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user32.GetMessageW.restype = ctypes.c_int
        user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        self.thread_id = kernel32.GetCurrentThreadId()
        modifiers = 0x0002 | 0x0004  # CTRL + SHIFT
        for hotkey_id, vk in ((1, 0x79), (2, 0x78)):  # F10, F9
            if user32.RegisterHotKey(None, hotkey_id, modifiers, vk):
                self.registered.append(hotkey_id)
        if len(self.registered) != 2:
            self.events.put(("hotkey_info", "Bazi genel kisayollar baska uygulama tarafindan kullaniliyor."))
        msg = MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                if msg.wParam == 1:
                    self.events.put(("shortcut_save", None))
                elif msg.wParam == 2:
                    self.events.put(("shortcut_toggle", None))
        for hotkey_id in self.registered:
            user32.UnregisterHotKey(None, hotkey_id)

    def stop(self) -> None:
        if sys.platform == "win32" and self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)

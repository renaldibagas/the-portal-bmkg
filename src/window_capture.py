import ctypes
from ctypes import wintypes
import os
import time
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image
import mss
import win32gui
import win32ui
import win32con
import win32api
import win32process
import psutil
import pygetwindow as gw

try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

ASFW_ANY = -1

PUL = ctypes.POINTER(ctypes.c_ulong)

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL)
    ]

class INPUT_I(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ii", INPUT_I)
    ]

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

SCANCODE_TAB = 0x0F    # Tab
SCANCODE_SPACE = 0x39  # Spacebar

EXCLUDED_STRINGS = [
    "visual studio", "code", "antigravity", "calibration", "monitor",
    "the-portal", "portal-bmkg", "cmd", "powershell", "python",
    "task manager", "discord", "chrome", "firefox", "edge", "notepad"
]

class WindowCapture:
    def __init__(self, target_title: str = "Roblox"):
        self.target_title = target_title
        self.hwnd: Optional[int] = None
        self.sct = mss.mss()

    def get_all_game_windows(self) -> List[Dict[str, Any]]:
        my_pid = os.getpid()
        windows = []

        try:
            all_wins = gw.getAllWindows()
            for w in all_wins:
                hwnd = w._hWnd
                title = w.title.strip()
                if not title or not w.visible or w.width < 300 or w.height < 300:
                    continue

                title_lower = title.lower()
                if any(ex in title_lower for ex in EXCLUDED_STRINGS):
                    continue

                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid == my_pid:
                        continue
                    pname = psutil.Process(pid).name()
                except Exception:
                    pname = ""

                pname_lower = pname.lower()
                if any(ex in pname_lower for ex in ["code.exe", "python.exe", "cmd.exe", "powershell.exe"]):
                    continue

                is_real_roblox = (
                    "robloxplayer" in pname_lower or
                    title == "Roblox"
                )

                windows.append({
                    "hwnd": hwnd,
                    "title": title,
                    "process": pname,
                    "rect": (w.left, w.top, w.right, w.bottom),
                    "width": w.width,
                    "height": w.height,
                    "is_roblox": is_real_roblox
                })
        except Exception as e:
            print(f"[WindowCapture] Window scan error: {e}")

        windows.sort(key=lambda x: (not x["is_roblox"], x["title"]))
        return windows

    def find_roblox_hwnd(self) -> Optional[int]:
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if "robloxplayer" in proc.info['name'].lower():
                    pid = proc.info['pid']
                    def enum_windows_callback(hwnd, extra):
                        if win32gui.IsWindowVisible(hwnd):
                            _, w_pid = win32process.GetWindowThreadProcessId(hwnd)
                            if w_pid == pid:
                                extra.append(hwnd)
                    hwnds = []
                    win32gui.EnumWindows(enum_windows_callback, hwnds)
                    if hwnds:
                        self.hwnd = hwnds[0]
                        return self.hwnd
        except Exception:
            pass

        wins = self.get_all_game_windows()
        for w in wins:
            if w["is_roblox"] or w["title"] == "Roblox":
                self.hwnd = w["hwnd"]
                return self.hwnd

        self.hwnd = wins[0]["hwnd"] if wins else None
        return self.hwnd

    def get_client_rect(self) -> Optional[Tuple[int, int, int, int]]:
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            if not self.find_roblox_hwnd():
                return None

        try:
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            width = right - left
            height = bottom - top
            return (left, top, width, height)
        except Exception:
            return None

    def _focus_window(self, target_hwnd: int) -> bool:
        try:
            ctypes.windll.user32.AllowSetForegroundWindow(ASFW_ANY)
            cur_thread = win32api.GetCurrentThreadId()
            target_thread, _ = win32process.GetWindowThreadProcessId(target_hwnd)
            
            ctypes.windll.user32.AttachThreadInput(cur_thread, target_thread, True)
            win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(target_hwnd)
            ctypes.windll.user32.AttachThreadInput(cur_thread, target_thread, False)
            return True
        except Exception:
            try:
                win32gui.SetForegroundWindow(target_hwnd)
                return True
            except Exception:
                return False

    def _send_directx_key(self, scancode: int):
        extra = ctypes.c_ulong(0)
        ii_down = INPUT_I()
        ii_down.ki = KEYBDINPUT(0, scancode, KEYEVENTF_SCANCODE, 0, ctypes.pointer(extra))
        input_down = INPUT(INPUT_KEYBOARD, ii_down)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(input_down), ctypes.sizeof(INPUT))
        
        time.sleep(0.04)
        
        ii_up = INPUT_I()
        ii_up.ki = KEYBDINPUT(0, scancode, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
        input_up = INPUT(INPUT_KEYBOARD, ii_up)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(input_up), ctypes.sizeof(INPUT))

    def hover_and_capture_live_roi(
        self,
        hover_rel_x: float,
        hover_rel_y: float,
        crop_rel_x: float,
        crop_rel_y: float,
        crop_rel_w: float,
        crop_rel_h: float,
        do_anti_afk: bool = True,
        hover_delay: float = 0.85
    ) -> Optional[Image.Image]:
        """
        1. Focuses Roblox window.
        2. Sets physical cursor to weather bar with micro-jiggle to trigger Roblox hover event.
        3. Sends Anti-AFK Spacebar jump.
        4. Waits hover_delay (default 0.85s) for UI animations to fully load even under lag.
        5. Snaps the cropped ROI.
        6. Restores original window & mouse.
        """
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            if not self.find_roblox_hwnd():
                return None

        rect_info = self.get_client_rect()
        if not rect_info:
            return None

        s_left, s_top, width, height = rect_info
        screen_target_x = int(s_left + width * hover_rel_x)
        screen_target_y = int(s_top + height * hover_rel_y)

        prev_hwnd = win32gui.GetForegroundWindow()
        prev_pos = win32api.GetCursorPos()

        try:
            # 1. Bring Roblox to active foreground
            self._focus_window(self.hwnd)
            time.sleep(0.05)

            # 2. Position cursor on weather bar
            ctypes.windll.user32.SetCursorPos(screen_target_x, screen_target_y)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 1, 0, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -1, 0, 0, 0)

            # 3. Anti-AFK jump
            if do_anti_afk:
                self._send_directx_key(SCANCODE_SPACE)

            # 4. Generous delay (0.85s) for the weather tooltip to visibly and completely render
            time.sleep(hover_delay)

            # 5. Capture the cropped ROI WHILE cursor is actively on the weather bar!
            roi_image = self.capture_roi(crop_rel_x, crop_rel_y, crop_rel_w, crop_rel_h)

            # 6. Restore previous window and cursor
            if prev_hwnd and win32gui.IsWindow(prev_hwnd) and prev_hwnd != self.hwnd:
                self._focus_window(prev_hwnd)

            ctypes.windll.user32.SetCursorPos(prev_pos[0], prev_pos[1])
            return roi_image

        except Exception as e:
            print(f"[WindowCapture] Hover & Capture error: {e}")
            try:
                if prev_hwnd and win32gui.IsWindow(prev_hwnd):
                    self._focus_window(prev_hwnd)
                ctypes.windll.user32.SetCursorPos(prev_pos[0], prev_pos[1])
            except:
                pass
            return None

    def send_tab_key(self) -> bool:
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            if not self.find_roblox_hwnd():
                return False

        prev_hwnd = win32gui.GetForegroundWindow()
        prev_pos = win32api.GetCursorPos()

        try:
            self._focus_window(self.hwnd)
            time.sleep(0.05)

            self._send_directx_key(SCANCODE_TAB)
            time.sleep(0.05)

            if prev_hwnd and win32gui.IsWindow(prev_hwnd) and prev_hwnd != self.hwnd:
                self._focus_window(prev_hwnd)

            ctypes.windll.user32.SetCursorPos(prev_pos[0], prev_pos[1])
            print("[WindowCapture] Sent hardware TAB to Roblox successfully!")
            return True
        except Exception as e:
            print(f"[WindowCapture] Error sending Tab key: {e}")
            return False

    def capture_client_area(self) -> Optional[Image.Image]:
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            if not self.find_roblox_hwnd():
                return None

        try:
            rect = win32gui.GetWindowRect(self.hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if w <= 0 or h <= 0:
                return None

            bbox = {
                "left": rect[0],
                "top": rect[1],
                "width": w,
                "height": h
            }
            sct_img = self.sct.grab(bbox)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception:
            try:
                sct_img = self.sct.grab(self.sct.monitors[1])
                return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception:
                return None

    def capture_roi(
        self,
        rel_x: float,
        rel_y: float,
        rel_w: float,
        rel_h: float
    ) -> Optional[Image.Image]:
        full_img = self.capture_client_area()
        if not full_img:
            return None

        img_w, img_h = full_img.size
        x1 = max(0, int(img_w * rel_x))
        y1 = max(0, int(img_h * rel_y))
        x2 = min(img_w, int(img_w * (rel_x + rel_w)))
        y2 = min(img_h, int(img_h * (rel_y + rel_h)))

        if x2 <= x1 or y2 <= y1:
            return None

        return full_img.crop((x1, y1, x2, y2))

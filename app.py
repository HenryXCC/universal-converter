"""
Main application lifecycle and layout management.
"""
import json
import os
import re
import sys
import threading

import customtkinter as ctk
from PIL import Image
from tkinter import messagebox

from config import (
    BG, PANEL, CARD, SURFACE, BORDER, SIDEBAR,
    ACCENT, ACCENT2, ACCENT_DIM, ACCENT_GLOW, MUTED, TEXT, SUBTLE,
    ACCENT_GRADIENT_L, ACCENT_GRADIENT_R,
    FONT_FAMILY,
    DND_OK, TkinterDnD, DND_FILES,
)
from i18n import get_lang, set_lang, t
from utils import _reg, apply_font_scale, SMALL, SUB, BODY
from widgets import GhostButton
from tabs.image_tab   import ImageTab
from tabs.video_tab   import VideoTab
from tabs.youtube_tab import YouTubeTab

_AppBases = (
    (ctk.CTk, TkinterDnD.DnDWrapper)
    if DND_OK and TkinterDnD is not None
    else (ctk.CTk,)
)

class App(*_AppBases):

    _NAV_ITEMS = [
        ("image",   "tab_image"),
        ("video",   "tab_video"),
        ("youtube", "tab_youtube"),
    ]

    def __init__(self):
        super().__init__()
        self.configure(fg_color=BG)
        if DND_OK and TkinterDnD is not None:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception:
                pass

        self._font_delta = 0
        self.config_file = "config.json"
        self._load_config()

        self._current_tab = "image"
        self._nav_btns = {}
        self._tab_frames = {}
        self._tab_instances = {}

        self._build()
        self._set_icon()

        if DND_OK:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind("<<Drop>>", self._on_drop)
                self.dnd_bind("<<DropEnter>>", self._on_drop_enter)
                self.dnd_bind("<<DropLeave>>", self._on_drop_leave)
            except Exception:
                pass

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        if sys.platform == "win32":
            self.after(100, self._install_custom_frame)
            self.bind("<Map>", lambda _e: self.after(50, self._install_custom_frame), add=True)
            self.bind("<FocusIn>", lambda _e: self.after(10, self._install_custom_frame), add=True)

        self._prev_wm_state = self.wm_state()
        self._btn_maximize_text = None
        self.bind("<Configure>", self._on_configure_evt, add=True)

        if sys.platform == "win32":
            self.after(250, self._setup_resize_bindings)


    def _get_hwnd(self):
        import ctypes
        if getattr(self, "_hwnd_cache", None):
            return self._hwnd_cache
        self.update_idletasks()
        raw  = self.winfo_id()
        hwnd = ctypes.windll.user32.GetParent(raw)
        if not hwnd:
            hwnd = ctypes.windll.user32.GetAncestor(raw, 2)
        result = hwnd or raw
        if result:
            self._hwnd_cache = result
        return result

    def _install_custom_frame(self):
        if sys.platform != "win32":
            return
        if getattr(self, "_frame_fully_installed", False):
            return
        try:
            import ctypes
            from ctypes import wintypes

            hwnd = self._get_hwnd()
            if not hwnd:
                return

            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000

            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)

            if (style & WS_CAPTION) or not (style & WS_THICKFRAME):
                new_style = (style & ~WS_CAPTION) | WS_THICKFRAME
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
                ctypes.windll.user32.SetWindowPos(
                    hwnd, 0, 0, 0, 0, 0,
                    0x0027,  
                )

            try:
                _dwm = ctypes.windll.dwmapi.DwmSetWindowAttribute
                _sz = ctypes.sizeof(wintypes.DWORD)
                dark = wintypes.DWORD(1)
                _dwm(hwnd, 19, ctypes.byref(dark), _sz)
                _dwm(hwnd, 20, ctypes.byref(dark), _sz)
            except Exception:
                pass

            if not getattr(self, "_nccalcsize_installed", False):
                self._install_nccalcsize_fix(hwnd)
                self._nccalcsize_installed = True
                self._frame_fully_installed = True
                ctypes.windll.user32.SetWindowPos(
                    hwnd, 0, 0, 0, 0, 0,
                    0x0027,
                )
                self.update_idletasks()
                try:
                    ctypes.windll.dwmapi.DwmFlush()
                except Exception:
                    pass

        except Exception:
            pass

    def _install_nccalcsize_fix(self, hwnd):
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes

            WM_SIZE             = 0x0005
            WM_WINDOWPOSCHANGED = 0x0047
            WM_NCCALCSIZE       = 0x0083
            WM_NCHITTEST        = 0x0084
            WM_NCPAINT          = 0x0085
            WM_NCACTIVATE       = 0x0086
            GWLP_WNDPROC        = -4

            HTLEFT, HTRIGHT, HTTOP      = 10, 11, 12
            HTTOPLEFT, HTTOPRIGHT       = 13, 14
            HTBOTTOM                    = 15
            HTBOTTOMLEFT, HTBOTTOMRIGHT = 16, 17
            WM_SETCURSOR                = 0x0020

            class RECT(ctypes.Structure):
                _fields_ = [("left",   ctypes.c_long), ("top",    ctypes.c_long),
                             ("right",  ctypes.c_long), ("bottom", ctypes.c_long)]

            user32 = ctypes.windll.user32

            user32.GetWindowRect.argtypes   = [ctypes.c_void_p, ctypes.POINTER(RECT)]
            user32.GetWindowRect.restype    = wintypes.BOOL
            user32.IsZoomed.argtypes        = [ctypes.c_void_p]
            user32.IsZoomed.restype         = wintypes.BOOL
            user32.CallWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                               wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user32.CallWindowProcW.restype    = ctypes.c_longlong
            user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_longlong]
            user32.SetWindowLongPtrW.restype  = ctypes.c_longlong
            user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
            user32.GetWindowLongPtrW.restype  = ctypes.c_longlong
            user32.LoadCursorW.argtypes       = [ctypes.c_void_p, ctypes.c_void_p]
            user32.LoadCursorW.restype        = ctypes.c_void_p
            user32.SetCursor.argtypes         = [ctypes.c_void_p]
            user32.SetCursor.restype          = ctypes.c_void_p

            def _lc(n): return user32.LoadCursorW(None, ctypes.c_void_p(n))
            _resize_cur = {
                HTLEFT: _lc(32644), HTRIGHT:      _lc(32644),   # IDC_SIZEWE  ↔
                HTTOP:  _lc(32645), HTBOTTOM:     _lc(32645),   # IDC_SIZENS  ↕
                HTTOPLEFT:  _lc(32642), HTBOTTOMRIGHT: _lc(32642),  # IDC_SIZENWSE ↖↘
                HTTOPRIGHT: _lc(32643), HTBOTTOMLEFT:  _lc(32643),  # IDC_SIZENESW ↗↙
            }

            bx = max(user32.GetSystemMetrics(32) + user32.GetSystemMetrics(92), 8)
            by = max(user32.GetSystemMetrics(33) + user32.GetSystemMetrics(92), 8)
            inner_x = max(user32.GetSystemMetrics(92), 8)
            inner_y = max(user32.GetSystemMetrics(92), 8)

            WndProcType = ctypes.WINFUNCTYPE(
                ctypes.c_longlong, ctypes.c_void_p, wintypes.UINT,
                wintypes.WPARAM, wintypes.LPARAM,
            )
            old_proc = user32.GetWindowLongPtrW(ctypes.c_void_p(hwnd), GWLP_WNDPROC)

            hwnd_ptr0 = ctypes.c_void_p(hwnd)
            _zoom  = [bool(user32.IsZoomed(hwnd_ptr0))]
            _rc    = RECT()
            _rc_ok = [False]
            user32.GetWindowRect(hwnd_ptr0, ctypes.byref(_rc))
            _rc_ok[0] = True

            def _wndproc(hwnd_w, msg, wparam, lparam):
                hwnd_ptr = ctypes.c_void_p(hwnd_w)

                if msg == WM_NCCALCSIZE and wparam:
                    try:
                        if user32.IsZoomed(hwnd_ptr):
                            r = ctypes.cast(lparam, ctypes.POINTER(RECT))
                            r[0].left   += bx
                            r[0].top    += by
                            r[0].right  -= bx
                            r[0].bottom -= by
                    except Exception:
                        pass
                    return 0

                if msg == WM_NCACTIVATE:
                    return 1

                if msg == WM_NCPAINT:
                    return 0

                if msg == WM_SIZE:
                    _zoom[0] = bool(user32.IsZoomed(hwnd_ptr))
                    _rc_ok[0] = False   
                if msg == WM_WINDOWPOSCHANGED:
                    _rc_ok[0] = False

                if msg == WM_SETCURSOR and not _zoom[0]:
                    ht = lparam & 0xFFFF
                    if ht in _resize_cur:
                        try:
                            user32.SetCursor(_resize_cur[ht])
                        except Exception:
                            pass
                        return 1  
                if msg == WM_NCHITTEST:
                    if not _zoom[0]:
                        try:
                            x = ctypes.c_short(lparam & 0xFFFF).value
                            y = ctypes.c_short((lparam >> 16) & 0xFFFF).value

                            if not _rc_ok[0]:
                                user32.GetWindowRect(hwnd_ptr, ctypes.byref(_rc))
                                _rc_ok[0] = True

                            on_l = x  <  (_rc.left   + bx + inner_x)
                            on_t = y  <  (_rc.top    + by + inner_y)
                            on_r = x  >= (_rc.right  - bx - inner_x)
                            on_b = y  >= (_rc.bottom - by - inner_y)

                            if on_t and on_l: return HTTOPLEFT
                            if on_t and on_r: return HTTOPRIGHT
                            if on_b and on_l: return HTBOTTOMLEFT
                            if on_b and on_r: return HTBOTTOMRIGHT
                            if on_t: return HTTOP
                            if on_l: return HTLEFT
                            if on_r: return HTRIGHT
                            if on_b: return HTBOTTOM
                        except Exception:
                            pass

                return user32.CallWindowProcW(old_proc, hwnd_ptr, msg, wparam, lparam)

            self._wndproc_cb = WndProcType(_wndproc)
            cb_addr = ctypes.cast(self._wndproc_cb, ctypes.c_void_p).value
            user32.SetWindowLongPtrW(ctypes.c_void_p(hwnd), GWLP_WNDPROC, cb_addr)

        except Exception:
            pass

    def _on_configure_evt(self, event):
        if event.widget is not self:
            return

        curr = self.wm_state()
        if curr == self._prev_wm_state:
            return

        self._prev_wm_state = curr
        self._update_maximize_btn()

    def _unlock_redraw(self, hwnd):
        """Compatibilidad: ya no se usa."""
        return

    def _update_maximize_btn(self):
        if hasattr(self, "_btn_maximize"):
            is_max = self.wm_state() == "zoomed"
            new_text = "❐" if is_max else "□"
            if getattr(self, "_btn_maximize_text", None) != new_text:
                self._btn_maximize_text = new_text
                self._btn_maximize.configure(text=new_text)

    def _toggle_maximize(self, event=None):
        if event is not None:
            w = event.widget
            while w is not None and w is not self:
                if "Button" in type(w).__name__:
                    return
                try:
                    w = w.master
                except Exception:
                    break
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.c_void_p(self._get_hwnd())
                SW_MAXIMIZE = 3
                SW_RESTORE  = 9
                is_max = bool(ctypes.windll.user32.IsZoomed(hwnd))
                ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE if is_max else SW_MAXIMIZE)
            except Exception:
                if self.wm_state() == "zoomed":
                    self.wm_state("normal")
                else:
                    self.wm_state("zoomed")
        else:
            if self.wm_state() == "zoomed":
                self.wm_state("normal")
            else:
                self.wm_state("zoomed")
        self.after(60, self._update_maximize_btn)

    def _header_drag_start(self, event):
        if hasattr(self, "_resize_margin") and self._hit_test_resize(event) is not None:
            return
        w = event.widget
        while w is not None and w is not self:
            if "Button" in type(w).__name__:
                return
            try:
                w = w.master
            except Exception:
                break
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = self._get_hwnd()
                ctypes.windll.user32.ReleaseCapture()
                ctypes.windll.user32.PostMessageW(hwnd, 0xA1, 2, 0)
            except Exception:
                pass


    _RESIZE_CURSORS = {
        10: "size_we",    # HTLEFT
        11: "size_we",    # HTRIGHT
        12: "size_ns",    # HTTOP
        15: "size_ns",    # HTBOTTOM
        13: "size_nw_se", # HTTOPLEFT
        17: "size_nw_se", # HTBOTTOMRIGHT
        14: "size_ne_sw", # HTTOPRIGHT
        16: "size_ne_sw", # HTBOTTOMLEFT
    }

    def _setup_resize_bindings(self):
        self._resize_margin = 8
        self.bind_all("<Motion>",       self._on_resize_cursor, add=True)
        self.bind_all("<ButtonPress-1>", self._on_resize_press,  add=True)

    def _hit_test_resize(self, event):
        if self.wm_state() == "zoomed":
            return None
        try:
            rx = self.winfo_rootx()
            ry = self.winfo_rooty()
            rw = self.winfo_width()
            rh = self.winfo_height()
            x  = event.x_root - rx
            y  = event.y_root - ry
            m  = self._resize_margin
            on_l = 0 <= x < m
            on_r = rw - m <= x < rw
            on_t = 0 <= y < m
            on_b = rh - m <= y < rh
            if on_t and on_l: return 13   # HTTOPLEFT
            if on_t and on_r: return 14   # HTTOPRIGHT
            if on_b and on_l: return 16   # HTBOTTOMLEFT
            if on_b and on_r: return 17   # HTBOTTOMRIGHT
            if on_t:          return 12   # HTTOP
            if on_b:          return 15   # HTBOTTOM
            if on_l:          return 10   # HTLEFT
            if on_r:          return 11   # HTRIGHT
        except Exception:
            pass
        return None

    def _on_resize_cursor(self, event):
        hit = self._hit_test_resize(event)
        cur = self._RESIZE_CURSORS.get(hit, "")
        try:
            event.widget.configure(cursor=cur)
        except Exception:
            pass
        try:
            self.configure(cursor=cur)
        except Exception:
            pass

    def _on_resize_press(self, event):
        hit = self._hit_test_resize(event)
        if hit is None or sys.platform != "win32":
            return
        _wmsz = {10: 1, 11: 2, 12: 3, 15: 6, 13: 4, 14: 5, 16: 7, 17: 8}
        direction = _wmsz.get(hit)
        if direction:
            try:
                import ctypes
                hwnd = self._get_hwnd()
                ctypes.windll.user32.ReleaseCapture()
                ctypes.windll.user32.PostMessageW(
                    hwnd, 0x0112, 0xF000 | direction, 0
                )
            except Exception:
                pass
            return "break"

    def _set_icon(self):
        candidates = [
            os.path.join(os.path.dirname(sys.argv[0]), "assets", "icon.ico"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico"),
        ]
        for icon_ico in candidates:
            if os.path.exists(icon_ico):
                try:
                    self.iconbitmap(icon_ico)
                    try:
                        from PIL import ImageTk
                        img = Image.open(icon_ico)
                        photo = ImageTk.PhotoImage(img)
                        self.iconphoto(True, photo)
                    except Exception:
                        pass
                    return
                except Exception:
                    pass

    def _load_config(self):
        self._saved_out_dir = None
        self._font_delta = 0
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._saved_out_dir = cfg.get("out_dir")
                self._font_delta = cfg.get("font_delta", 0)
                set_lang(cfg.get("lang", "es"))
        except Exception:
            pass

    def _save_config(self):
        try:
            out_dir = os.path.expanduser("~/Desktop")
            for instance in self._tab_instances.values():
                if hasattr(instance, "out_dir"):
                    out_dir = instance.out_dir.get()
                    break
            cfg = {
                "out_dir":    out_dir,
                "font_delta": self._font_delta,
                "lang":       get_lang(),
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def _on_closing(self):
        self._save_config()
        self.destroy()

    def _build(self):
        self.title(t("app_title"))
        self.geometry("980x800")
        self.minsize(860, 660)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_separator()
        self._build_main()
        self._build_footer()

        if self._font_delta != 0:
            apply_font_scale(self._font_delta)
            self._fvl.configure(text=f"{int(100 + self._font_delta * 10)}%")

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, height=80)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        logo = ctk.CTkFrame(header, fg_color="transparent")
        logo.pack(side="left", padx=24, fill="y")

        ctk.CTkLabel(
            logo, text="◆",
            font=(FONT_FAMILY, 16),
            text_color=ACCENT,
        ).pack(side="left", padx=(0, 12))

        titles = ctk.CTkFrame(logo, fg_color="transparent")
        titles.pack(side="left", fill="y", pady=16)

        title_row = ctk.CTkFrame(titles, fg_color="transparent")
        title_row.pack(anchor="w")

        ctk.CTkLabel(
            title_row, text=t("app_header_part1"),
            font=(FONT_FAMILY, 22, "bold"), text_color=TEXT,
        ).pack(side="left")

        self._lbl_header_accent = ctk.CTkLabel(
            title_row, text=" " + t("app_header_part2"),
            font=(FONT_FAMILY, 22, "bold"), text_color=ACCENT,
        )
        self._lbl_header_accent.pack(side="left")

        self._lbl_app_subtitle = _reg(
            ctk.CTkLabel(titles, text=t("app_subtitle"),
                         font=SMALL(), text_color=MUTED),
            "small",
        )
        self._lbl_app_subtitle.pack(anchor="w", pady=(2, 0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=(6, 146), fill="y")

        self._btn_lang = GhostButton(
            right, text=t("lang_btn"), width=76, height=30,
            command=self._change_lang,
        )
        self._btn_lang.pack(side="right", padx=(6, 0))

        _reg(ctk.CTkLabel(right, text="v1.4", font=SMALL(),
                           text_color=MUTED), "small").pack(side="right", padx=10)

        fc = ctk.CTkFrame(right, fg_color=CARD, corner_radius=14,
                          border_width=1, border_color=BORDER)
        fc.pack(side="right", padx=(0, 14))

        self._lbl_text_size = _reg(
            ctk.CTkLabel(fc, text=t("text_size_label"),
                         font=SMALL(), text_color=MUTED),
            "small",
        )
        self._lbl_text_size.pack(side="left", padx=(12, 6), pady=8)

        GhostButton(fc, text="A-", width=34, height=28,
                    command=self._font_down).pack(side="left", padx=2, pady=4)

        self._fvl = _reg(
            ctk.CTkLabel(fc, text="100%", font=SMALL(),
                         text_color=ACCENT, width=46),
            "small",
        )
        self._fvl.pack(side="left", padx=2)

        GhostButton(fc, text="A+", width=34, height=28,
                    command=self._font_up).pack(side="left", padx=2, pady=4)

        GhostButton(fc, text="R", width=28, height=28,
                    command=self._font_reset).pack(side="left", padx=(2, 12), pady=4)

        wc = ctk.CTkFrame(header, fg_color="transparent", corner_radius=0,
                          width=138, height=30)
        wc.place(relx=1.0, y=0, anchor="ne")

        ctk.CTkButton(
            wc, text="─", width=46, height=30, corner_radius=0,
            fg_color="transparent", hover_color=ACCENT_DIM,
            text_color=TEXT, font=(FONT_FAMILY, 13), border_width=0,
            command=self.iconify,
        ).pack(side="left")

        self._btn_maximize = ctk.CTkButton(
            wc, text="□", width=46, height=30, corner_radius=0,
            fg_color="transparent", hover_color=ACCENT_DIM,
            text_color=TEXT, font=(FONT_FAMILY, 17), border_width=0,
            command=self._toggle_maximize,
        )
        self._btn_maximize.pack(side="left")

        ctk.CTkButton(
            wc, text="✕", width=46, height=30, corner_radius=0,
            fg_color="transparent", hover_color="#C42B1C",
            text_color=TEXT, font=(FONT_FAMILY, 14), border_width=0,
            command=self._on_closing,
        ).pack(side="left")

        for _w in (header, logo, titles, title_row):
            _w.bind("<Button-1>",        self._header_drag_start,  add=True)
            _w.bind("<Double-Button-1>", self._toggle_maximize,     add=True)

    def _build_separator(self):
        import tkinter as _tk
        sep = _tk.Canvas(self, height=3, bd=0, highlightthickness=0, bg=BORDER)
        sep.grid(row=1, column=0, sticky="ew")
        self._sep_canvas = sep
        self._sep_photo  = None
        self._sep_after  = None
        sep.bind("<Configure>", self._on_sep_configure)

    def _on_sep_configure(self, event):
        if self._sep_after is not None:
            self.after_cancel(self._sep_after)
        self._sep_after = self.after(40, lambda: self._draw_sep_gradient(event.width, event.height))

    def _draw_sep_gradient(self, w, h):
        self._sep_after = None
        if w < 2 or h < 1:
            return
        try:
            from PIL import Image as _Img, ImageTk as _ITk

            def _hex2rgb(hx):
                hx = hx.lstrip("#")
                return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

            r0, g0, b0 = _hex2rgb(ACCENT_GRADIENT_L)
            r1, g1, b1 = _hex2rgb(ACCENT_GRADIENT_R)
            w1 = max(w - 1, 1)
            row = [
                (int(r0 + (r1 - r0) * x / w1),
                 int(g0 + (g1 - g0) * x / w1),
                 int(b0 + (b1 - b0) * x / w1))
                for x in range(w)
            ]
            img = _Img.new("RGB", (w, h))
            img.putdata(row * h)
            photo = _ITk.PhotoImage(img)
            self._sep_photo = photo
            self._sep_canvas.delete("all")
            self._sep_canvas.create_image(0, 0, anchor="nw", image=photo)
        except Exception:
            pass

    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        main.grid(row=2, column=0, sticky="nsew")
        main.grid_columnconfigure(2, weight=1)
        main.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(
            main, fg_color=SIDEBAR, corner_radius=0,
            width=180, border_width=0,
        )
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        self._build_sidebar_nav(sidebar)

        ctk.CTkFrame(
            main, fg_color=BORDER, width=1, corner_radius=0,
        ).grid(row=0, column=1, sticky="ns")

        self._content = ctk.CTkFrame(main, fg_color=BG, corner_radius=0)
        self._content.grid(row=0, column=2, sticky="nsew")

        tab_classes = {
            "image":   ImageTab,
            "video":   VideoTab,
            "youtube": YouTubeTab,
        }

        for key, label_key in self._NAV_ITEMS:
            scroll = ctk.CTkScrollableFrame(
                self._content,
                fg_color="transparent",
                scrollbar_button_color=BORDER,
                scrollbar_button_hover_color=ACCENT,
            )
            self._tab_frames[key] = scroll

            instance = tab_classes[key](scroll)
            instance.pack(fill="both", expand=True)
            self._tab_instances[key] = instance

            if (hasattr(self, "_saved_out_dir") and self._saved_out_dir
                    and hasattr(instance, "out_dir")):
                instance.out_dir.set(self._saved_out_dir)

            scroll.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)

        self._switch_to("image")

    def _build_sidebar_nav(self, sidebar):
        ctk.CTkFrame(sidebar, fg_color="transparent", height=16).pack(fill="x")

        for key, label_key in self._NAV_ITEMS:
            self._make_nav_slot(sidebar, key, label_key)

        spacer = ctk.CTkFrame(sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

    def _make_nav_slot(self, sidebar, key: str, label_key: str):
        btn = ctk.CTkButton(
            sidebar,
            text="  " + t(label_key),
            anchor="w",
            width=160, height=38,
            corner_radius=8,
            fg_color="transparent",
            hover_color=ACCENT_DIM,
            text_color=MUTED,
            font=(FONT_FAMILY, 12, "bold"),
            border_width=0,
            command=lambda k=key: self._switch_to(k),
        )
        btn.pack(fill="x", padx=10, pady=4)
        self._nav_btns[key] = (btn, label_key)

    def _switch_to(self, key: str):
        self._current_tab = key

        for k, (btn, label_key) in self._nav_btns.items():
            if k == key:
                btn.configure(
                    fg_color=ACCENT_DIM,
                    text_color=ACCENT,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=MUTED,
                )

        active_frame = self._tab_frames.get(key)
        if active_frame:
            active_frame.lift()

    def _build_footer(self):
        ctk.CTkFrame(self, fg_color=ACCENT_DIM, height=1, corner_radius=0).grid(
            row=3, column=0, sticky="ew",
        )

        footer = ctk.CTkFrame(self, fg_color=PANEL, height=34, corner_radius=0)
        footer.grid(row=4, column=0, sticky="ew")
        footer.grid_propagate(False)

        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.place(relx=0.0, rely=0.5, x=20, anchor="w")

        self._lbl_footer_deps = _reg(
            ctk.CTkLabel(inner, text=t("footer_deps"),
                         font=SMALL(), text_color=MUTED),
            "small",
        )
        self._lbl_footer_deps.pack(side="left")

        ctk.CTkLabel(inner, text="  |  ", font=SMALL(),
                     text_color=SUBTLE).pack(side="left")

        ctk.CTkFrame(
            inner, width=8, height=8,
            fg_color="#4ADE80", corner_radius=4,
        ).pack(side="left", padx=(0, 5))

        self._lbl_local_proc = _reg(
            ctk.CTkLabel(inner, text=t("local_proc"),
                         font=SMALL(), text_color=MUTED),
            "small",
        )
        self._lbl_local_proc.pack(side="left")

        self._btn_about = GhostButton(
            footer, text=t("about_btn"),
            width=116, height=24,
            command=self._show_about,
        )
        self._btn_about.place(relx=1.0, rely=0.5, x=-20, anchor="e")

    def _show_about(self):
        messagebox.showinfo(t("about_title"), t("about_text"))

    def _on_drop(self, event):
        self._on_drop_leave(event)
        raw_paths = re.findall(r'\{[^}]+\}|\S+', event.data)
        files = [p.strip("{}") for p in raw_paths if os.path.isfile(p.strip("{}"))]
        if not files:
            return

        current = self._current_tab

        if current == "image":
            image_tab = self._tab_instances.get("image")
            if image_tab:
                for p in files:
                    if (p.lower().endswith(
                            (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".gif", ".webp"))
                            and p not in image_tab._files):
                        image_tab._files.append(p)
                        image_tab._load_thumb(p)
                image_tab._refresh_normal_list()
                if image_tab.fmt_var.get() == "GIF":
                    image_tab._refresh_gif_list()
                    image_tab._restart_preview()

        elif current == "video":
            video_tab = self._tab_instances.get("video")
            if video_tab:
                src_ext = video_tab._src_ext()
                for p in files:
                    if p.lower().endswith(f".{src_ext}") and p not in video_tab._files:
                        video_tab._files.append(p)
                video_tab._refresh_file_list()
                if len(video_tab._files) == 1:
                    threading.Thread(
                        target=video_tab._probe_file,
                        args=(video_tab._files[0],),
                        daemon=True,
                    ).start()

    def _on_drop_enter(self, event):
        tab = self._tab_instances.get(self._current_tab)
        if tab and hasattr(tab, "highlight_drop_zone"):
            tab.highlight_drop_zone(True)

    def _on_drop_leave(self, event):
        tab = self._tab_instances.get(self._current_tab)
        if tab and hasattr(tab, "highlight_drop_zone"):
            tab.highlight_drop_zone(False)

    def _font_up(self):
        if self._font_delta < 8:
            self._font_delta += 1
            self._apply_font()

    def _font_down(self):
        if self._font_delta > -3:
            self._font_delta -= 1
            self._apply_font()

    def _font_reset(self):
        self._font_delta = 0
        self._apply_font()

    def _apply_font(self):
        apply_font_scale(self._font_delta)
        self._fvl.configure(text=f"{int(100 + self._font_delta * 10)}%")

    def _change_lang(self) -> None:
        new_lang = "en" if get_lang() == "es" else "es"
        set_lang(new_lang)

        self.title(t("app_title"))
        self._lbl_header_accent.configure(text=" " + t("app_header_part2"))
        self._lbl_app_subtitle.configure(text=t("app_subtitle"))
        self._lbl_text_size.configure(text=t("text_size_label"))
        self._btn_lang.configure(text=t("lang_btn"))

        self._lbl_footer_deps.configure(text=t("footer_deps"))
        self._lbl_local_proc.configure(text=t("local_proc"))
        self._btn_about.configure(text=t("about_btn"))

        for key, (btn, label_key) in self._nav_btns.items():
            btn.configure(text="  " + t(label_key))

        for instance in self._tab_instances.values():
            instance.refresh_lang()

        self._save_config()
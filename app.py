"""
Main class of the application.
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
    BG, PANEL, CARD, BORDER, ACCENT, ACCENT2, MUTED, TEXT,
    DND_OK, TkinterDnD, DND_FILES,
)
from i18n import get_lang, set_lang, t
from utils import _reg, apply_font_scale, SMALL
from widgets import GhostButton
from tabs.image_tab   import ImageTab
from tabs.video_tab   import VideoTab
from tabs.youtube_tab import YouTubeTab

# Dynamic base class (with or without Drag & Drop)
_AppBases = (
    (ctk.CTk, TkinterDnD.DnDWrapper)
    if (DND_OK and TkinterDnD is not None)
    else (ctk.CTk,)
)


class App(*_AppBases):
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

        self._build()
        self._set_icon()

        if DND_OK:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # Icon
    def _set_icon(self):
        icon_ico = os.path.join(os.path.dirname(sys.argv[0]), "icon.ico")
        icon_png = os.path.join(os.path.dirname(sys.argv[0]), "icon.png")
        try:
            if os.path.exists(icon_ico):
                self.iconbitmap(icon_ico)
            elif os.path.exists(icon_png):
                icon  = Image.open(icon_png)
                photo = ctk.CTkImage(light_image=icon, dark_image=icon, size=(32, 32))
                self.iconphoto(True, photo)
        except Exception:
            pass

    # Config 
    def _load_config(self):
        # Initialize both attributes before try block to avoid AttributeError if exception occurs
        self._saved_out_dir = None
        self._font_delta = 0
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._saved_out_dir = cfg.get("out_dir")
                self._font_delta    = cfg.get("font_delta", 0)
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

    # Build 
    def _build(self):
        self.title(t("app_title"))
        self.geometry("900x760")
        self.minsize(820, 640)

        # Header 
        header = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0)
        header.pack(fill="x")
        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="x", padx=30, pady=14)

        # Logo / Title
        logo = ctk.CTkFrame(inner, fg_color="transparent")
        logo.pack(side="left")
        ctk.CTkLabel(logo, text="◈", font=("Courier New", 28, "bold"),
                     text_color=ACCENT).pack(side="left", padx=(0, 10))
        titles = ctk.CTkFrame(logo, fg_color="transparent")
        titles.pack(side="left")
        self._lbl_header = ctk.CTkLabel(
            titles, text=t("app_header"),
            font=("Courier New", 17, "bold"), text_color="#FFFFFF",
        )
        self._lbl_header.pack(anchor="w")
        self._lbl_app_subtitle = _reg(
            ctk.CTkLabel(titles, text=t("app_subtitle"), font=SMALL(), text_color=MUTED),
            "small",
        )
        self._lbl_app_subtitle.pack(anchor="w")

        # Rights controls
        right_frame = ctk.CTkFrame(inner, fg_color="transparent")
        right_frame.pack(side="right")

        # Language button
        self._btn_lang = GhostButton(
            right_frame, text=t("lang_btn"), width=70, height=26,
            command=self._change_lang,
        )
        self._btn_lang.pack(side="right", padx=(4, 0))

        _reg(ctk.CTkLabel(right_frame, text="v1.4", font=SMALL(),
                           text_color=MUTED), "small").pack(side="right", padx=8)

        # Text size control
        fc2 = ctk.CTkFrame(right_frame, fg_color=CARD, corner_radius=8)
        fc2.pack(side="right", padx=(0, 12))
        self._lbl_text_size = _reg(
            ctk.CTkLabel(fc2, text=t("text_size_label"), font=SMALL(), text_color=MUTED),
            "small",
        )
        self._lbl_text_size.pack(side="left", padx=(8, 4), pady=6)
        GhostButton(fc2, text="A−", width=36, height=26,
                    command=self._font_down).pack(side="left", padx=2, pady=4)
        self._fvl = _reg(
            ctk.CTkLabel(fc2, text="100%", font=SMALL(), text_color=ACCENT, width=44), "small"
        )
        self._fvl.pack(side="left", padx=2)
        GhostButton(fc2, text="A+", width=36, height=26,
                    command=self._font_up).pack(side="left", padx=2, pady=4)
        GhostButton(fc2, text="↺", width=30, height=26,
                    command=self._font_reset).pack(side="left", padx=(2, 8), pady=4)

        # accent separator lines
        ctk.CTkFrame(self, fg_color=ACCENT, height=2, corner_radius=0).pack(fill="x")

        # tabs
        self._tabview = ctk.CTkTabview(
            self, fg_color=BG,
            segmented_button_fg_color=PANEL,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT2,
            segmented_button_unselected_color=PANEL,
            segmented_button_unselected_hover_color=BORDER,
            text_color=TEXT, text_color_disabled=MUTED,
            corner_radius=0, border_width=0,
        )
        self._tabview.pack(fill="both", expand=True)

        self._tab_keys   = ["image", "video", "youtube"]
        self._tab_instances: dict[str, ImageTab | VideoTab | YouTubeTab] = {}

        tab_classes = {
            "image":   ImageTab,
            "video":   VideoTab,
            "youtube": YouTubeTab,
        }
        # Fixed tab names — not translated, so CTkTabview never needs to rename them.
        # Content inside each tab is translated via refresh_lang().
        tab_fixed_names = {
            "image":   "🖼 Image",
            "video":   "🎬 Video",
            "youtube": "▶ YouTube",
        }

        for key in self._tab_keys:
            name = tab_fixed_names[key]
            self._tabview.add(name)
            self._tabview.tab(name).configure(fg_color=BG)
            scroll = ctk.CTkScrollableFrame(
                self._tabview.tab(name), fg_color="transparent",

                scrollbar_button_color=BORDER,
                scrollbar_button_hover_color=ACCENT,
            )
            scroll.pack(fill="both", expand=True)
            instance = tab_classes[key](scroll)
            instance.pack(fill="both", expand=True)
            self._tab_instances[key] = instance

            if (hasattr(self, "_saved_out_dir") and self._saved_out_dir
                    and hasattr(instance, "out_dir")):
                instance.out_dir.set(self._saved_out_dir)

        # Apply saved font scale
        if self._font_delta != 0:
            apply_font_scale(self._font_delta)
            self._fvl.configure(text=f"{int(100 + self._font_delta * 10)}%")

        # Footer 
        self._footer = ctk.CTkFrame(self, fg_color=PANEL, height=28, corner_radius=0)
        self._footer.pack(fill="x", side="bottom")
        self._footer.pack_propagate(False)
        self._lbl_footer_deps = _reg(
            ctk.CTkLabel(self._footer, text=t("footer_deps"), font=SMALL(), text_color=MUTED),
            "small",
        )
        self._lbl_footer_deps.pack(side="left", padx=20)
        self._lbl_local_proc = _reg(
            ctk.CTkLabel(self._footer, text=t("local_proc"), font=SMALL(), text_color=MUTED),
            "small",
        )
        self._lbl_local_proc.pack(side="right", padx=20)
        self._btn_about = GhostButton(
            self._footer, text=t("about_btn"), width=100, command=self._show_about,
        )
        self._btn_about.pack(side="right", padx=20)

    # About dialog 
    def _show_about(self):
        messagebox.showinfo(t("about_title"), t("about_text"))

    # Drag & Drop
    def _on_drop(self, event):
        raw_paths = re.findall(r'\{[^}]+\}|\S+', event.data)
        files = [p.strip("{}") for p in raw_paths if os.path.isfile(p.strip("{}"))]
        if not files:
            return

        current = self._tabview.get()

        if current == "🖼 Image":
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

        elif current == "🎬 Video":
            video_tab = self._tab_instances.get("video")
            if video_tab:
                for p in files:
                    if (p.lower().endswith(
                            (".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"))
                            and p not in video_tab._files):
                        video_tab._files.append(p)
                video_tab._refresh_file_list()
                if len(video_tab._files) == 1:
                    threading.Thread(
                        target=video_tab._probe_file,
                        args=(video_tab._files[0],),
                        daemon=True,
                    ).start()

    # Font scale
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

    # Live language change
    def _change_lang(self) -> None:
        """Cambia el idioma al instante sin cerrar ni reiniciar la app."""
        new_lang = "en" if get_lang() == "es" else "es"
        set_lang(new_lang)

        # 1. Window title
        self.title(t("app_title"))

        # 2. Header
        self._lbl_header.configure(text=t("app_header"))
        self._lbl_app_subtitle.configure(text=t("app_subtitle"))
        self._lbl_text_size.configure(text=t("text_size_label"))
        self._btn_lang.configure(text=t("lang_btn"))

        # 3. Footer
        self._lbl_footer_deps.configure(text=t("footer_deps"))
        self._lbl_local_proc.configure(text=t("local_proc"))
        self._btn_about.configure(text=t("about_btn"))

        # 4. Tabs — names are fixed (not translated), so no rename needed.
        # Content inside each tab is updated via refresh_lang() in step 5.

        # 5. Content of each tab
        for instance in self._tab_instances.values():
            instance.refresh_lang()

        # 6. Persist the new language
        self._save_config()
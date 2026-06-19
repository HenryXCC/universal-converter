"""
Image conversion UI panel.
"""
import os
import threading

import customtkinter as ctk
from PIL import Image
from tkinter import filedialog, messagebox

from config import ACCENT, ACCENT2, BORDER, MUTED, TEXT, CARD, SURFACE
from i18n import t
from utils import _reg, BODY, SMALL, HEAD
from widgets import (
    AccentButton, Card, GhostButton, GifThumbItem,
    LogBox, ProgressCard, SectionLabel, DropZoneCard,
)

class ImageTab(ctk.CTkFrame):
    FORMATS = {
        "WebP": "WEBP", "PNG": "PNG", "JPEG": "JPEG",
        "BMP": "BMP", "TIFF": "TIFF", "GIF": "GIF", "ICO": "ICO",
    }
    EXT = {
        "WEBP": ".webp", "PNG": ".png", "JPEG": ".jpg",
        "BMP": ".bmp", "TIFF": ".tif", "GIF": ".gif", "ICO": ".ico",
    }

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._files = []
        self._thumb_refs = []
        # PIL sources for the GIF preview. Keep originals so the preview can
        # be re-rendered crisply when the window is resized/maximized.
        self._prev_pils = []
        self._preview_job = None
        self._preview_resize_job = None
        self._preview_idx = 0
        self._preview_img_ref = None
        self._blank_prev_img = None
        self._build()

    def _log(self, msg: str) -> None:
        self.after(0, lambda: self.log.append(msg))

    def _set_progress(self, value: float, text: str = "") -> None:
        self.after(0, lambda: self.progress.set(value, text))

    def _done_progress(self, ok: bool) -> None:
        self.after(0, lambda: self.progress.done(ok))

    def highlight_drop_zone(self, active: bool):
        if hasattr(self, "drop_zone"):
            self.drop_zone.set_active(active)

    def _build(self):
        self._lbl_title = _reg(
            ctk.CTkLabel(self, text=t("img_title"), font=HEAD(), text_color=ACCENT), "head"
        )
        self._lbl_title.pack(pady=(32, 2))
        self._lbl_subtitle = _reg(
            ctk.CTkLabel(self, text=t("img_subtitle"), font=SMALL(), text_color=MUTED), "small"
        )
        self._lbl_subtitle.pack(pady=(0, 24))

        oc = Card(self)
        oc.pack(fill="x", padx=100, pady=8)
        
        self._lbl_options = SectionLabel(oc, text=t("options_section"))
        self._lbl_options.pack(anchor="w", padx=20, pady=(16, 4))

        rf = ctk.CTkFrame(oc, fg_color="transparent")
        rf.pack(fill="x", padx=20, pady=4)
        
        self._lbl_fmt = _reg(
            ctk.CTkLabel(rf, text=t("img_format_label"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_fmt.pack(side="left")
        
        self.fmt_var = ctk.StringVar(value="WebP")
        self.fmt_selector = ctk.CTkSegmentedButton(
            rf, variable=self.fmt_var, values=list(self.FORMATS),
            fg_color=SURFACE, selected_color=ACCENT, unselected_color=SURFACE,
            text_color=TEXT, font=SMALL(), height=34
        )
        self.fmt_selector.pack(side="left", padx=12, fill="x", expand=True)

        self._lbl_quality = _reg(
            ctk.CTkLabel(rf, text=t("img_quality_label"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_quality.pack(side="left", padx=(12, 8))
        
        self.quality_var = ctk.IntVar(value=85)
        ctk.CTkSlider(
            rf, from_=1, to=100, variable=self.quality_var, width=120,
            button_color=ACCENT, button_hover_color=ACCENT2, progress_color=ACCENT,
            fg_color=SURFACE,
        ).pack(side="left", padx=4)
        
        self.qlabel = _reg(
            ctk.CTkLabel(rf, text="85", font=BODY(), text_color=ACCENT, width=30), "body"
        )
        self.qlabel.pack(side="left", padx=4)
        self.quality_var.trace_add(
            "write", lambda *_: self.qlabel.configure(text=str(self.quality_var.get()))
        )

        or2 = ctk.CTkFrame(oc, fg_color="transparent")
        or2.pack(fill="x", padx=20, pady=(8, 16))
        
        self._lbl_outdir = _reg(
            ctk.CTkLabel(or2, text=t("out_dir_label"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_outdir.pack(side="left")
        
        self.out_dir = ctk.StringVar(value=os.path.expanduser("~/Desktop"))
        ctk.CTkEntry(or2, textvariable=self.out_dir, font=SMALL(),
                     fg_color=SURFACE, border_color=BORDER, height=36).pack(side="left", fill="x", expand=True, padx=10)
        
        self._btn_browse = GhostButton(or2, text=t("browse"), width=90, height=36, command=self._pick_outdir)
        self._btn_browse.pack(side="right")

        self._input_container = ctk.CTkFrame(self, fg_color="transparent")
        self._input_container.pack(fill="both", expand=True, pady=4)
        
        self._normal_section = self._build_normal_section()
        self._gif_section = self._build_gif_section()
        self._normal_section.pack(fill="x", padx=100, pady=6)
        self.fmt_var.trace_add("write", self._on_fmt_change)

        self.progress = ProgressCard(self)
        self.progress.pack(fill="x", padx=100, pady=6)
        
        self.log = LogBox(self, height=110)
        self.log.pack(fill="x", padx=100, pady=6)
        
        self._btn_convert = AccentButton(self, text=t("img_convert_btn"),
                                         command=self._start, height=44)
        self._btn_convert.pack(fill="x", padx=100, pady=18)

    def _build_normal_section(self) -> ctk.CTkFrame:
        container = ctk.CTkFrame(self._input_container, fg_color="transparent")
        
        self.drop_zone = DropZoneCard(container)
        self.drop_zone.pack(fill="x", pady=(0, 8))

        fc = Card(container)
        fc.pack(fill="x")
        self._lbl_input_section = SectionLabel(fc, text=t("img_input_section"))
        self._lbl_input_section.pack(anchor="w", padx=16, pady=(14, 6))
        row = ctk.CTkFrame(fc, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 8))
        self._btn_add_normal = AccentButton(row, text=t("img_add_btn"),
                                            command=self._pick_files, width=160, height=34)
        self._btn_add_normal.pack(side="left")
        self._btn_clear_normal = GhostButton(row, text=t("img_clear_btn"),
                                             command=self._clear_files, width=120, height=34)
        self._btn_clear_normal.pack(side="left", padx=8)
        self.file_list = _reg(
            ctk.CTkTextbox(fc, height=100, font=SMALL(), fg_color="#050403",
                           text_color=MUTED, border_width=1, border_color=BORDER,
                           corner_radius=8),
            "small",
        )
        self.file_list.pack(fill="x", padx=16, pady=(0, 14))
        self.file_list.insert("0.0", t("img_no_files"))
        self.file_list.configure(state="disabled")
        return container

    def _build_gif_section(self) -> Card:
        gc = Card(self._input_container)
        self._lbl_gif_section = SectionLabel(gc, text=t("img_gif_section"))
        self._lbl_gif_section.pack(anchor="w", padx=16, pady=(14, 6))
        br = ctk.CTkFrame(gc, fg_color="transparent")
        br.pack(fill="x", padx=16, pady=(0, 8))
        self._btn_add_gif = AccentButton(br, text=t("img_add_btn"),
                                         command=self._pick_files, width=160, height=34)
        self._btn_add_gif.pack(side="left")
        self._btn_clear_gif = GhostButton(br, text=t("img_clear_all_btn"),
                                          command=self._clear_files, width=120, height=34)
        self._btn_clear_gif.pack(side="left", padx=8)

        content = ctk.CTkFrame(gc, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)
        self._gif_scroll = ctk.CTkScrollableFrame(
            left, height=260, fg_color="#050403",
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=ACCENT,
            corner_radius=8, border_width=1, border_color=BORDER,
        )
        self._gif_scroll.pack(fill="both", expand=True)
        _reg(ctk.CTkLabel(self._gif_scroll, text=t("img_gif_hint"),
                           font=SMALL(), text_color=MUTED, justify="center"),
             "small").pack(pady=30)

        right = ctk.CTkFrame(content, fg_color=SURFACE, corner_radius=10, width=320)
        right.pack(side="right", fill="both", padx=(10, 0))
        right.pack_propagate(False)
        self._lbl_preview_header = _reg(
            ctk.CTkLabel(right, text=t("img_preview_label"), font=SMALL(), text_color=MUTED),
            "small",
        )
        self._lbl_preview_header.pack(pady=(8, 4))
        self._preview_lbl = ctk.CTkLabel(
            right, text=t("img_no_images"), width=300, height=210,
            fg_color="#050403", corner_radius=8, font=SMALL(), text_color=MUTED,
        )
        self._preview_lbl.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self._preview_lbl.bind("<Configure>", self._on_preview_resize)
        self._set_empty_preview()
        self._preview_stats = _reg(
            ctk.CTkLabel(right, text="0 frames", font=SMALL(),
                          text_color=MUTED, justify="center"), "small"
        )
        self._preview_stats.pack(pady=(0, 8))

        dr = ctk.CTkFrame(gc, fg_color="transparent")
        dr.pack(fill="x", padx=16, pady=(0, 4))
        self._lbl_frame_dur = _reg(
            ctk.CTkLabel(dr, text=t("img_frame_dur"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_frame_dur.pack(side="left")
        self._frame_dur_var = ctk.IntVar(value=100)
        ctk.CTkSlider(
            dr, from_=50, to=1000, variable=self._frame_dur_var, width=160,
            button_color=ACCENT, button_hover_color=ACCENT2, progress_color=ACCENT,
            fg_color=SURFACE,
        ).pack(side="left", padx=10)
        self._dur_lbl = _reg(
            ctk.CTkLabel(dr, text="100 ms", font=BODY(), text_color=ACCENT, width=60), "body"
        )
        self._dur_lbl.pack(side="left")
        self._frame_dur_var.trace_add(
            "write",
            lambda *_: self._dur_lbl.configure(text=f"{self._frame_dur_var.get()} ms"),
        )

        lr = ctk.CTkFrame(gc, fg_color="transparent")
        lr.pack(fill="x", padx=16, pady=(0, 14))
        self._loop_var = ctk.BooleanVar(value=True)
        self._chk_loop = ctk.CTkCheckBox(
            lr, text=t("img_loop_check"), variable=self._loop_var, font=BODY(),
            text_color=TEXT, fg_color=ACCENT, hover_color=ACCENT2, checkmark_color="#000",
        )
        self._chk_loop.pack(side="left")
        return gc

    def refresh_lang(self) -> None:
        self._lbl_title.configure(text=t("img_title"))
        self._lbl_subtitle.configure(text=t("img_subtitle"))
        self._lbl_options.configure(text=t("options_section"))
        self._lbl_fmt.configure(text=t("img_format_label"))
        self._lbl_quality.configure(text=t("img_quality_label"))
        self._lbl_outdir.configure(text=t("out_dir_label"))
        self._btn_browse.configure(text=t("browse"))
        self._lbl_input_section.configure(text=t("img_input_section"))
        self._btn_add_normal.configure(text=t("img_add_btn"))
        self._btn_clear_normal.configure(text=t("img_clear_btn"))
        self._lbl_gif_section.configure(text=t("img_gif_section"))
        self._btn_add_gif.configure(text=t("img_add_btn"))
        self._btn_clear_gif.configure(text=t("img_clear_all_btn"))
        self._lbl_preview_header.configure(text=t("img_preview_label"))
        self._lbl_frame_dur.configure(text=t("img_frame_dur"))
        self._chk_loop.configure(text=t("img_loop_check"))
        self._btn_convert.configure(text=t("img_convert_btn"))
        self.progress.refresh_lang()
        if hasattr(self, "drop_zone"):
            self.drop_zone.refresh_lang()
        if not self._files:
            self.file_list.configure(state="normal")
            self.file_list.delete("0.0", "end")
            self.file_list.insert("0.0", t("img_no_files"))
            self.file_list.configure(state="disabled")
        if self.fmt_var.get() == "GIF":
            self._refresh_gif_list()
            if not self._files:
                self._set_empty_preview()

    def _on_fmt_change(self, *_):
        allowed = self._allowed_exts()
        wrong = [p for p in self._files if not p.lower().endswith(allowed)]
        if wrong:
            keep_files = [p for p in self._files if p.lower().endswith(allowed)]
            keep_thumbs = [t for p, t in zip(self._files, self._thumb_refs)
                           if p.lower().endswith(allowed)]
            keep_prevs  = [pr for p, pr in zip(self._files, self._prev_pils)
                           if p.lower().endswith(allowed)]
            self._files       = keep_files
            self._thumb_refs  = keep_thumbs
            self._prev_pils   = keep_prevs

        if self.fmt_var.get() == "GIF":
            self._normal_section.pack_forget()
            self._gif_section.pack(fill="both", expand=True, padx=100, pady=6)
            self._refresh_gif_list()
            if self._files:
                self._restart_preview()
            else:
                self._stop_preview()
                self._set_empty_preview()
                self._preview_stats.configure(text=t("img_frames_zero"))
        else:
            self._stop_preview()
            self._gif_section.pack_forget()
            self._normal_section.pack(fill="x", padx=100, pady=6)
            self._refresh_normal_list()

    _FMT_EXTS = {
        "WEBP": (".webp",),
        "PNG":  (".png",),
        "JPEG": (".jpg", ".jpeg"),
        "BMP":  (".bmp",),
        "TIFF": (".tif", ".tiff"),
        "GIF":  (".gif",),
        "ICO":  (".ico",),
    }

    def _allowed_exts(self) -> tuple[str, ...]:
        dest_fmt = self.FORMATS[self.fmt_var.get()]
        exts = []
        for fmt, ext_tuple in self._FMT_EXTS.items():
            if fmt != dest_fmt:
                exts.extend(ext_tuple)
        return tuple(exts)

    def _pick_files(self):
        allowed = self._allowed_exts()
        glob_pattern = " ".join(f"*{e}" for e in allowed)
        dest_label = self.fmt_var.get()
        paths = filedialog.askopenfilenames(
            title=t("img_pick_title"),
            filetypes=[
                (t("img_filetypes_excl", fmt=dest_label), glob_pattern),
                ("All", "*.*"),
            ],
        )
        if not paths:
            return
        rejected = []
        for p in paths:
            if not p.lower().endswith(allowed):
                rejected.append(os.path.basename(p))
                continue
            if p not in self._files:
                self._files.append(p)
                self._load_thumb(p)
        if rejected:
            messagebox.showwarning(
                t("img_wrong_fmt_title"),
                t("img_wrong_fmt_msg", fmt=dest_label, files=", ".join(rejected)),
            )
        self._refresh_normal_list()
        if self.fmt_var.get() == "GIF":
            self._refresh_gif_list()
            self._restart_preview()

    def _load_thumb(self, path: str):
        try:
            img = Image.open(path).convert("RGB")
            t_img = img.copy(); t_img.thumbnail((80, 55), Image.LANCZOS)
            ct  = ctk.CTkImage(light_image=t_img, dark_image=t_img,
                                 size=(t_img.width, t_img.height))
            cp = img.copy()
        except Exception:
            ct = cp = None
        self._thumb_refs.append(ct)
        self._prev_pils.append(cp)

    def _clear_files(self):
        self._stop_preview()
        self._files.clear()
        self._thumb_refs.clear()
        self._prev_pils.clear()
        self._refresh_normal_list()
        if self.fmt_var.get() == "GIF":
            self._refresh_gif_list()
            self._set_empty_preview()
            self._preview_stats.configure(text=t("img_frames_zero"))

    def _move(self, idx: int, d: int):
        target = idx + d
        if 0 <= target < len(self._files):
            for lst in (self._files, self._thumb_refs, self._prev_pils):
                lst.insert(target, lst.pop(idx))
            self._refresh_gif_list()
            self._preview_idx = 0
            self._start_preview()

    def _remove(self, idx: int):
        for lst in (self._files, self._thumb_refs, self._prev_pils):
            lst.pop(idx)
        self._refresh_gif_list()
        if not self._files:
            self._stop_preview()
            self._set_empty_preview()
            self._preview_stats.configure(text=t("img_frames_zero"))
        else:
            self._preview_idx = 0
            self._start_preview()

    def _refresh_normal_list(self):
        self.file_list.configure(state="normal")
        self.file_list.delete("0.0", "end")
        if self._files:
            for f in self._files:
                self.file_list.insert("end", f"• {os.path.basename(f)}\n")
        else:
            self.file_list.insert("0.0", t("img_no_files"))
        self.file_list.configure(state="disabled")

    def _refresh_gif_list(self):
        for w in self._gif_scroll.winfo_children():
            w.destroy()
        if not self._files:
            _reg(ctk.CTkLabel(self._gif_scroll, text=t("img_gif_hint"),
                               font=SMALL(), text_color=MUTED, justify="center"),
                 "small").pack(pady=30)
        else:
            for i, (path, thumb) in enumerate(zip(self._files, self._thumb_refs)):
                GifThumbItem(
                    self._gif_scroll, i + 1, path, thumb,
                    on_up=lambda i=i: self._move(i, -1),
                    on_down=lambda i=i: self._move(i, +1),
                    on_remove=lambda i=i: self._remove(i),
                ).pack(fill="x", pady=2, padx=4)
        n = len(self._files)
        self._preview_stats.configure(
            text=t("img_frames_total", n=n, secs=n * self._frame_dur_var.get() / 1000)
        )

    def _restart_preview(self):
        self._preview_idx = 0
        self._start_preview()

    def _preview_box_size(self) -> tuple[int, int]:
        w = max(1, self._preview_lbl.winfo_width())
        h = max(1, self._preview_lbl.winfo_height())
        if w <= 1 or h <= 1:
            return 300, 210
        return w, h

    def _fit_preview_image(self, img: Image.Image) -> ctk.CTkImage:
        box_w, box_h = self._preview_box_size()
        preview = img.copy()
        preview.thumbnail((box_w, box_h), Image.LANCZOS)
        return ctk.CTkImage(
            light_image=preview,
            dark_image=preview,
            size=(preview.width, preview.height),
        )

    def _show_preview_frame(self, idx: int) -> None:
        if not self._prev_pils:
            self._set_empty_preview()
            return
        img = self._prev_pils[idx % len(self._prev_pils)]
        if img is None:
            self._preview_lbl.configure(image="", text=t("img_no_images"))
            return
        self._preview_img_ref = self._fit_preview_image(img)
        self._preview_lbl.configure(image=self._preview_img_ref, text="")

    def _set_empty_preview(self) -> None:
        # Keep the empty preview visually consistent with the current widget size.
        w, h = self._preview_box_size() if hasattr(self, "_preview_lbl") else (300, 210)
        blank = Image.new("RGB", (w, h), color=(5, 4, 3))
        self._blank_prev_img = ctk.CTkImage(
            light_image=blank, dark_image=blank, size=(w, h)
        )
        self._preview_lbl.configure(image=self._blank_prev_img, text=t("img_no_images"))

    def _on_preview_resize(self, event=None) -> None:
        if self._preview_resize_job:
            self.after_cancel(self._preview_resize_job)
        self._preview_resize_job = self.after(80, self._redraw_preview)

    def _redraw_preview(self) -> None:
        self._preview_resize_job = None
        if self._prev_pils:
            self._show_preview_frame((self._preview_idx - 1) % len(self._prev_pils))
        else:
            self._set_empty_preview()

    def _start_preview(self):
        self._stop_preview()
        if self._prev_pils:
            self._tick_preview()

    def _tick_preview(self):
        if not self._prev_pils:
            return
        self._show_preview_frame(self._preview_idx)
        self._preview_idx = (self._preview_idx + 1) % max(1, len(self._prev_pils))
        self._preview_job = self.after(
            max(50, self._frame_dur_var.get()), self._tick_preview
        )

    def _stop_preview(self):
        if self._preview_job:
            self.after_cancel(self._preview_job)
            self._preview_job = None
        if self._preview_resize_job:
            self.after_cancel(self._preview_resize_job)
            self._preview_resize_job = None

    def _pick_outdir(self):
        d = filedialog.askdirectory()
        if d:
            self.out_dir.set(d)

    def _start(self):
        if not self._files:
            messagebox.showwarning(t("img_warn_title"), t("img_warn_msg"))
            return
        self.log.clear()
        self.progress.reset()
        threading.Thread(target=self._convert, daemon=True).start()

    def _convert(self):
        fmt     = self.FORMATS[self.fmt_var.get()]
        out_dir = self.out_dir.get()
        os.makedirs(out_dir, exist_ok=True)

        if fmt == "GIF":
            self._convert_animated_gif(out_dir)
            return

        quality = self.quality_var.get()
        errors  = 0
        files = list(self._files)
        total = len(files)
        for i, path in enumerate(files):
            stem = os.path.splitext(os.path.basename(path))[0]
            dest = os.path.join(out_dir, stem + self.EXT[fmt])
            try:
                img = Image.open(path)
                if fmt == "JPEG" and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                kw = {"quality": quality} if fmt in ("WEBP", "JPEG") else {}
                img.save(dest, fmt, **kw)
                _stem, _ext = stem, self.EXT[fmt]
                self._log(f"✓  {_stem}{_ext}")
            except Exception as e:
                _stem, _e = stem, e
                self._log(f"✗  {_stem}  →  {_e}")
                errors += 1
            self._set_progress(
                (i + 1) / total,
                t("img_processing", cur=i + 1, total=total, stem=stem),
            )

        self._done_progress(errors == 0)
        ok  = total - errors
        key = "img_summary_ok" if errors == 0 else "img_summary_warn"
        self._log(t(key, ok=ok, total=total, out_dir=out_dir))

    def _convert_animated_gif(self, out_dir: str):
        files = list(self._files)
        self._log(t("img_gif_building", n=len(files)))
        imgs  = []
        total = len(files)
        for i, path in enumerate(files):
            self._set_progress(
                (i + 1) / total,
                t("img_gif_loading", cur=i + 1, total=total),
            )
            try:
                src = Image.open(path)
                if src.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", src.size, (255, 255, 255))
                    bg.paste(src.convert("RGBA"), mask=src.convert("RGBA").split()[-1])
                    src = bg
                else:
                    src = src.convert("RGB")
                try:
                    img_p = src.quantize(
                        colors=256,
                        method=Image.Quantize.MEDIANCUT,
                        dither=Image.Dither.FLOYDSTEINBERG,
                    )
                except (AttributeError, TypeError):
                    img_p = src.convert("P", palette=Image.ADAPTIVE)
                imgs.append(img_p)
            except Exception as e:
                _i, _e = i, e
                self._log(t("img_gif_frame_err", i=_i + 1, e=_e))

        if not imgs:
            self._done_progress(False)
            self._log(t("img_gif_no_imgs"))
            return

        dest = os.path.join(out_dir, "animacion.gif")
        try:
            self._set_progress(0.95, t("img_gif_saving"))
            imgs[0].save(
                dest, format="GIF", save_all=True, append_images=imgs[1:],
                loop=0 if self._loop_var.get() else 1,
                duration=self._frame_dur_var.get(), optimize=True, disposal=2,
            )
            size_mb  = os.path.getsize(dest) / (1024 * 1024)
            _n       = len(imgs)
            _ms      = self._frame_dur_var.get()
            _dest    = dest
            _mb      = size_mb
            self._done_progress(True)
            self._log(t("img_gif_done", n=_n, ms=_ms, dest=_dest, mb=_mb))
        except Exception as e:
            _e = e
            self._done_progress(False)
            self._log(f"\n✗ {_e}")
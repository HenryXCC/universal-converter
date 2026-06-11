"""
Video conversion UI panel.
"""
import os
import re
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

from config import ACCENT, ACCENT2, BORDER, ERR, MUTED, SURFACE, TEXT, _VIDEO_CODEC
from i18n import t, translate_ffmpeg_error
from utils import (
    _reg, BODY, SMALL, HEAD,
    FFmpegNotFoundError, probe_video, run_ffmpeg, smart_gif_fps,
)
from widgets import (
    AccentButton, Card, GhostButton,
    LogBox, ProgressCard, SectionLabel, DropZoneCard,
)

class VideoTab(ctk.CTkFrame):
    CONVERSIONS = {
        "MP4  →  GIF":  ("mp4",  "gif"),
        "MP4  →  AVI":  ("mp4",  "avi"),
        "MP4  →  MKV":  ("mp4",  "mkv"),
        "MP4  →  MOV":  ("mp4",  "mov"),
        "MP4  →  WMV":  ("mp4",  "wmv"),
        "MP4  → WebM":  ("mp4",  "webm"),
        "MP4  →  MP3":  ("mp4",  "mp3"),
        "MP4  →  WAV":  ("mp4",  "wav"),
        "AVI  →  MP4":  ("avi",  "mp4"),
        "MKV  →  MP4":  ("mkv",  "mp4"),
        "MOV  →  MP4":  ("mov",  "mp4"),
        "WMV  →  MP4":  ("wmv",  "mp4"),
        "WebM →  MP4":  ("webm", "mp4"),
    }

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._files = []
        self._src_fps = 0.0
        self._duration = 0.0
        self._has_probe = False
        self._cancel_flag = threading.Event()
        self._running = False
        self._build()

    def _log(self, msg: str) -> None:
        self.after(0, lambda m=msg: self.log.append(m))

    def _set_progress(self, value: float, text: str = "") -> None:
        self.after(0, lambda v=value, tx=text: self.progress.set(v, tx))

    def _done_progress(self, ok: bool) -> None:
        self.after(0, lambda o=ok: self.progress.done(o))

    def highlight_drop_zone(self, active: bool):
        if hasattr(self, "drop_zone"):
            self.drop_zone.set_active(active)

    def _build(self):
        self._lbl_title = _reg(
            ctk.CTkLabel(self, text=t("vid_title"), font=HEAD(), text_color=ACCENT), "head"
        )
        self._lbl_title.pack(pady=(32, 2))
        self._lbl_subtitle = _reg(
            ctk.CTkLabel(self, text=t("vid_subtitle"), font=SMALL(), text_color=MUTED), "small"
        )
        self._lbl_subtitle.pack(pady=(0, 24))

        self.drop_zone = DropZoneCard(self, command=self._pick_files)
        self.drop_zone.pack(fill="x", padx=100, pady=(0, 8))

        fc = Card(self)
        fc.pack(fill="x", padx=100, pady=6)
        self._lbl_input_section = SectionLabel(fc, text=t("vid_input_section"))
        self._lbl_input_section.pack(anchor="w", padx=16, pady=(14, 6))
        row = ctk.CTkFrame(fc, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 14))
        self._btn_add = AccentButton(row, text=t("vid_add_btn"),
                                     command=self._pick_files, width=150, height=34)
        self._btn_add.pack(side="left")
        self.file_label = _reg(
            ctk.CTkLabel(row, text=t("vid_no_file"), font=SMALL(),
                          text_color=MUTED, wraplength=450, anchor="w"), "small"
        )
        self.file_label.pack(side="left", padx=14)

        ic = Card(self)
        ic.pack(fill="x", padx=100, pady=6)
        self._lbl_info_section = SectionLabel(ic, text=t("vid_info_section"))
        self._lbl_info_section.pack(anchor="w", padx=16, pady=(14, 6))
        self.info_lbl = _reg(
            ctk.CTkLabel(ic, text=t("vid_info_hint"), font=SMALL(),
                          text_color=MUTED, justify="left", anchor="w"), "small"
        )
        self.info_lbl.pack(anchor="w", padx=16, pady=(0, 14))

        oc = Card(self)
        oc.pack(fill="x", padx=100, pady=6)
        self._lbl_options = SectionLabel(oc, text=t("options_section"))
        self._lbl_options.pack(anchor="w", padx=16, pady=(14, 6))
        row2 = ctk.CTkFrame(oc, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(0, 12))
        self.conv_var = ctk.StringVar(value=list(self.CONVERSIONS)[0])
        ctk.CTkOptionMenu(
            row2, variable=self.conv_var, values=list(self.CONVERSIONS),
            fg_color=SURFACE, button_color=ACCENT, button_hover_color=ACCENT2,
            text_color=TEXT, font=BODY(), width=220, height=34
        ).pack(side="left")

        self._fps_wrapper = ctk.CTkFrame(oc, fg_color="transparent")
        self._fps_wrapper.pack(fill="x", padx=16, pady=(0, 4))
        fpr = ctk.CTkFrame(self._fps_wrapper, fg_color="transparent")
        fpr.pack(fill="x")
        self._lbl_gif_fps = _reg(
            ctk.CTkLabel(fpr, text=t("vid_gif_fps_label"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_gif_fps.pack(side="left")
        self.fps_var = ctk.IntVar(value=12)
        ctk.CTkSlider(
            fpr, from_=5, to=30, variable=self.fps_var, width=140,
            button_color=ACCENT, button_hover_color=ACCENT2, progress_color=ACCENT,
            fg_color=SURFACE,
        ).pack(side="left", padx=8)
        self.fps_lbl = _reg(
            ctk.CTkLabel(fpr, text="12", font=BODY(), text_color=ACCENT, width=28), "body"
        )
        self.fps_lbl.pack(side="left", padx=4)
        self.fps_var.trace_add("write", lambda *_: (
            self.fps_lbl.configure(text=str(self.fps_var.get())),
            self._update_fps_hint(),
        ))
        self.fps_hint = _reg(
            ctk.CTkLabel(self._fps_wrapper, text=t("vid_fps_auto_hint"),
                          font=SMALL(), text_color=MUTED,
                          justify="left", anchor="w", wraplength=600), "small"
        )
        self.fps_hint.pack(anchor="w", pady=(4, 8))

        self._crf_wrapper = ctk.CTkFrame(oc, fg_color="transparent")
        crf_row = ctk.CTkFrame(self._crf_wrapper, fg_color="transparent")
        crf_row.pack(fill="x")
        self._lbl_crf = _reg(
            ctk.CTkLabel(crf_row, text=t("vid_crf_label"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_crf.pack(side="left")
        self.crf_var = ctk.IntVar(value=18)
        ctk.CTkSlider(
            crf_row, from_=0, to=51, variable=self.crf_var, width=140,
            button_color=ACCENT, button_hover_color=ACCENT2, progress_color=ACCENT,
            fg_color=SURFACE,
        ).pack(side="left", padx=8)
        self.crf_lbl = _reg(
            ctk.CTkLabel(crf_row, text="18", font=BODY(), text_color=ACCENT, width=28), "body"
        )
        self.crf_lbl.pack(side="left", padx=4)
        self.crf_var.trace_add("write", lambda *_: (
            self.crf_lbl.configure(text=str(self.crf_var.get())),
            self._update_crf_hint(),
        ))
        self.crf_hint = _reg(
            ctk.CTkLabel(self._crf_wrapper, text=t("vid_crf_hint_high"),
                          font=SMALL(), text_color=MUTED,
                          justify="left", anchor="w"), "small"
        )
        self.crf_hint.pack(anchor="w", pady=(4, 8))
        self._crf_wrapper.pack(fill="x", padx=16, pady=(0, 4))

        or3 = ctk.CTkFrame(oc, fg_color="transparent")
        or3.pack(fill="x", padx=16, pady=(4, 16))
        self._lbl_outdir = _reg(
            ctk.CTkLabel(or3, text=t("out_dir_label"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_outdir.pack(side="left")
        self.out_dir = ctk.StringVar(value=os.path.expanduser("~/Desktop"))
        ctk.CTkEntry(
            or3, textvariable=self.out_dir, font=SMALL(),
            fg_color=SURFACE, border_color=BORDER, height=36
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._btn_browse = GhostButton(or3, text=t("browse"), width=90, height=36,
                                       command=self._pick_outdir)
        self._btn_browse.pack(side="right")
        self.conv_var.trace_add("write", self._on_conv_change)

        self.progress = ProgressCard(self)
        self.progress.pack(fill="x", padx=100, pady=6)
        self.log = LogBox(self, height=130)
        self.log.pack(fill="x", padx=100, pady=6)
        
        br = ctk.CTkFrame(self, fg_color="transparent")
        br.pack(fill="x", padx=100, pady=12)
        self._btn_convert = AccentButton(br, text=t("vid_convert_btn"),
                                         command=self._start, height=46)
        self._btn_convert.pack(side="left", fill="x", expand=True)
        self._btn_cancel = GhostButton(br, text=t("cancel_btn"),
                                       command=self._cancel, height=46, width=120)
        self._btn_cancel.configure(state="disabled")
        self._btn_cancel.pack(side="left", padx=(12, 0))

    def refresh_lang(self) -> None:
        self._lbl_title.configure(text=t("vid_title"))
        self._lbl_subtitle.configure(text=t("vid_subtitle"))
        self._lbl_input_section.configure(text=t("vid_input_section"))
        self._btn_add.configure(text=t("vid_add_btn"))
        if not self._files:
            self.file_label.configure(text=t("vid_no_file"), text_color=MUTED)
        self._lbl_info_section.configure(text=t("vid_info_section"))
        if not self._has_probe:
            self.info_lbl.configure(text=t("vid_info_hint"), text_color=MUTED)
        self._lbl_options.configure(text=t("options_section"))
        self._lbl_gif_fps.configure(text=t("vid_gif_fps_label"))
        self._lbl_crf.configure(text=t("vid_crf_label"))
        self._lbl_outdir.configure(text=t("out_dir_label"))
        self._btn_browse.configure(text=t("browse"))
        self._update_fps_hint()
        self._update_crf_hint()
        self._btn_convert.configure(text=t("vid_convert_btn"))
        self._btn_cancel.configure(text=t("cancel_btn"))
        self.progress.refresh_lang()
        if hasattr(self, "drop_zone"):
            self.drop_zone.refresh_lang()

    def _on_conv_change(self, *_):
        src_ext, ext = self.CONVERSIONS[self.conv_var.get()]
        if ext == "gif":
            self._fps_wrapper.pack(fill="x", padx=16, pady=(0, 4))
            self._crf_wrapper.pack_forget()
            self._update_fps_hint()
        elif ext in ("mp3", "wav"):
            self._fps_wrapper.pack_forget()
            self._crf_wrapper.pack_forget()
        else:
            self._fps_wrapper.pack_forget()
            self._crf_wrapper.pack(fill="x", padx=16, pady=(0, 4))
            self._update_crf_hint()

        wrong = [p for p in self._files if not p.lower().endswith(f".{src_ext}")]
        if wrong:
            self._files = [p for p in self._files if p.lower().endswith(f".{src_ext}")]
            self._src_fps  = 0.0
            self._duration = 0.0
            self._has_probe = False
            self._refresh_file_list()
            if not self._files:
                self.file_label.configure(text=t("vid_no_file"), text_color=MUTED)
                self.info_lbl.configure(text=t("vid_info_hint"), text_color=MUTED)

    def _update_fps_hint(self):
        fps = self.fps_var.get()
        if self._src_fps > 0:
            rec = smart_gif_fps(self._src_fps)
            fl  = (t("vid_fps_fluency_high") if fps >= 20
                   else (t("vid_fps_fluency_mid") if fps >= 12
                         else t("vid_fps_fluency_low")))
            sz  = (t("vid_fps_size_high") if fps >= 20
                   else (t("vid_fps_size_mid") if fps >= 12
                         else t("vid_fps_size_low")))
            self.fps_hint.configure(
                text=t("vid_fps_hint_src",
                        src_fps=self._src_fps, rec=rec, fps=fps, fl=fl, sz=sz),
                text_color=MUTED,
            )
        else:
            self.fps_hint.configure(text=t("vid_fps_hint_general"), text_color=MUTED)

    def _update_crf_hint(self):
        crf = self.crf_var.get()
        if crf <= 10:
            label = t("vid_crf_hint_lossless")
        elif crf <= 18:
            label = t("vid_crf_hint_high")
        elif crf <= 28:
            label = t("vid_crf_hint_mid")
        else:
            label = t("vid_crf_hint_low")
        self.crf_hint.configure(text=f"CRF {crf}  —  {label}")

    def _src_ext(self) -> str:
        src, _ = self.CONVERSIONS[self.conv_var.get()]
        return src

    def _pick_files(self):
        src = self._src_ext()
        ext_pattern = f"*.{src}"
        paths = filedialog.askopenfilenames(
            title=t("vid_pick_title"),
            filetypes=[
                (f"{src.upper()} {t('vid_filetypes')}", ext_pattern),
                ("All", "*.*"),
            ],
        )
        if not paths:
            return
        rejected = []
        for p in paths:
            if not p.lower().endswith(f".{src}"):
                rejected.append(os.path.basename(p))
                continue
            if p not in self._files:
                self._files.append(p)
        if rejected:
            messagebox.showwarning(
                t("vid_wrong_fmt_title"),
                t("vid_wrong_fmt_msg", ext=src.upper(), files=", ".join(rejected)),
            )
        self._refresh_file_list()
        if len(self._files) == 1:
            threading.Thread(
                target=self._probe_file, args=(self._files[0],), daemon=True
            ).start()

    def _refresh_file_list(self):
        if len(self._files) == 1:
            self.file_label.configure(text=os.path.basename(self._files[0]),
                                       text_color=TEXT)
        else:
            self.file_label.configure(
                text=t("vid_files_selected", n=len(self._files)), text_color=TEXT
            )

    def _probe_file(self, path: str):
        try:
            info           = probe_video(path)
            self._src_fps  = info["fps"]
            self._duration = info["duration"]
            self._has_probe = True
            rec             = smart_gif_fps(self._src_fps)
            self.after(0, lambda: self.fps_var.set(rec))
            size_mb         = os.path.getsize(path) / (1024 * 1024)
            mins, secs      = divmod(int(self._duration), 60)
            _name  = os.path.basename(path)
            _mb    = size_mb
            _mins  = mins
            _secs  = secs
            _fps   = self._src_fps
            _path  = path
            self.after(0, self._update_fps_hint)
            self.after(0, lambda: self.info_lbl.configure(
                text=(
                    f"{_name}\n"
                    f"{_mb:.2f} MB   {_mins}:{_secs:02d}"
                    f"   {_fps:.3f} FPS\n"
                    f"{_path}"
                ),
                text_color=TEXT,
            ))
        except FFmpegNotFoundError as e:
            _e = str(e)
            self.after(0, lambda: self.info_lbl.configure(
                text=f"! {_e}", text_color=ERR
            ))
        except Exception as e:
            _e = str(e)
            self.after(0, lambda: self.info_lbl.configure(
                text=t("vid_probe_err", e=_e), text_color=ERR
            ))

    def _pick_outdir(self):
        d = filedialog.askdirectory()
        if d:
            self.out_dir.set(d)

    def _clean_ffmpeg_error(self, raw: str) -> str:
        lines = raw.split("\n")
        clean = []
        seen_hints = set()
        for line in lines:
            cleaned = re.sub(r'@ [0-9a-fA-Fx]+', '', line).strip()
            if not cleaned:
                continue
            if any(kw in cleaned.lower() for kw in
                   ["error", "cannot", "failed", "nothing"]):
                clean.append(cleaned)
                hint = translate_ffmpeg_error(cleaned)
                if hint and hint not in seen_hints:
                    seen_hints.add(hint)
                    clean.append(f"  → {hint}")
            elif "Conversion failed" in cleaned:
                clean.append(cleaned)
                hint = translate_ffmpeg_error(cleaned)
                if hint and hint not in seen_hints:
                    seen_hints.add(hint)
                    clean.append(f"  → {hint}")
        return "\n".join(clean) if clean else "\n".join(
            [l for l in lines if l.strip()][-3:]
        )

    def _start(self):
        if not self._files:
            messagebox.showwarning(t("vid_warn_title"), t("vid_warn_msg"))
            return
        if self._running:
            return
        self._cancel_flag.clear()
        self.log.clear()
        self.progress.reset()
        self._running = True
        self._btn_cancel.configure(state="normal")
        _, ext  = self.CONVERSIONS[self.conv_var.get()]
        out_dir = self.out_dir.get()
        threading.Thread(target=self._convert, args=(ext, out_dir), daemon=True).start()

    def _cancel(self):
        if not self._running:
            return
        self._cancel_flag.set()
        self._btn_cancel.configure(state="disabled")
        self._log(t("vid_cancelling"))

    def _convert(self, ext: str, out_dir: str):
        os.makedirs(out_dir, exist_ok=True)
        files = list(self._files)
        success = True

        for idx, file_path in enumerate(files):
            if self._cancel_flag.is_set():
                break

            stem = os.path.splitext(os.path.basename(file_path))[0]
            dest = os.path.join(out_dir, f"{stem}.{ext}")

            _stem = stem
            _ext  = ext
            _idx  = idx
            _tot  = len(files)

            self._log(f"▶ {_stem} → .{_ext}  ({_idx + 1}/{_tot})")
            self._set_progress(0.05, t("vid_processing", cur=_idx + 1, total=_tot))

            try:
                src_fps  = self._src_fps
                duration = self._duration
                if src_fps <= 0 or duration <= 0:
                    info     = probe_video(file_path)
                    src_fps  = info["fps"] or src_fps
                    duration = info["duration"] or duration

                def prog(pct, label, _self=self):
                    _self.after(0, lambda p=pct, l=label:
                                _self.progress.set(0.10 + 0.87 * p, l))

                if ext == "gif":
                    import tempfile
                    fps          = self.fps_var.get()
                    palette_path = os.path.join(
                        tempfile.gettempdir(), f"{stem}_gif_palette.png"
                    )

                    self._log(t("vid_gif_pass1"))
                    vf1 = f"fps={fps},palettegen=max_colors=256:stats_mode=diff"
                    ok, err_tail = run_ffmpeg(
                        ["-i", file_path, "-vf", vf1, "-y", palette_path],
                        duration, None, self._cancel_flag,
                    )

                    if ok and not self._cancel_flag.is_set():
                        self._log(t("vid_gif_pass2"))
                        vf2 = (
                            f"fps={fps}[v];"
                            "[v][1:v]paletteuse=dither=floyd_steinberg"
                        )
                        ok, err_tail = run_ffmpeg(
                            ["-i", file_path, "-i", palette_path,
                             "-lavfi", vf2, "-loop", "0", dest],
                            duration, prog, self._cancel_flag,
                        )

                    try:
                        os.remove(palette_path)
                    except OSError:
                        pass

                elif ext in ("mp3", "wav"):
                    acodec   = "libmp3lame" if ext == "mp3" else "pcm_s16le"
                    ok, err_tail = run_ffmpeg(
                        ["-i", file_path, "-vn", "-acodec", acodec, dest],
                        duration, prog, self._cancel_flag,
                    )
                elif ext == "webm":
                    crf = self.crf_var.get()
                    ok, err_tail = run_ffmpeg(
                        ["-i", file_path, "-c:v", "libvpx-vp9",
                         "-crf", str(crf), "-b:v", "0",
                         "-c:a", "libopus", dest],
                        duration, prog, self._cancel_flag,
                    )
                else:
                    codec  = _VIDEO_CODEC.get(ext, "libx264")
                    crf    = self.crf_var.get()
                    q_args = (["-q:v", str(max(1, crf // 6 + 1))] if ext == "avi"
                               else ["-crf", str(crf), "-preset", "fast"])
                    ok, err_tail = run_ffmpeg(
                        ["-i", file_path, "-c:v", codec, "-r", f"{src_fps}"]
                        + q_args + ["-c:a", "copy", dest],
                        duration, prog, self._cancel_flag,
                    )

                if self._cancel_flag.is_set():
                    self._log(t("vid_cancelled"))
                    break

                if ok:
                    _dest   = dest
                    _size   = os.path.getsize(dest) / (1024 * 1024)
                    self._log(f"✓ {_dest} ({_size:.2f} MB)")
                else:
                    _tail = err_tail
                    self._log(f"✗ Error:\n{self._clean_ffmpeg_error(_tail)}")
                    success = False

            except FFmpegNotFoundError as e:
                _e = str(e)
                self._log(f"✗ {_e}")
                success = False
                break
            except Exception as e:
                _e = str(e)
                self._log(f"✗ {_e}")
                success = False

        self._done_progress(success and not self._cancel_flag.is_set())
        self.after(0, lambda: self._btn_cancel.configure(state="disabled"))
        self._running = False
        _out = out_dir
        if success and not self._cancel_flag.is_set():
            self._log(t("vid_done", out_dir=_out))
        else:
            self._log(t("vid_failed"))
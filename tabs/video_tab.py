"""
Pestaña de conversión de video.

Correcciones aplicadas:
  - Lambda capture bug en bucle: dest/size_mb/err_tail/e se capturan
    con variables locales antes de pasar al after(), no por referencia.
  - FFmpegNotFoundError se maneja explícitamente y muestra mensaje claro.
  - progress.set() desde el hilo de trabajo usa after() via helpers.
"""
import os
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

from config import ACCENT, ACCENT2, BORDER, ERR, MUTED, TEXT, _VIDEO_CODEC
from i18n import t
from utils import (
    _reg, BODY, SMALL, HEAD,
    FFmpegNotFoundError, probe_video, run_ffmpeg, smart_gif_fps,
)
from widgets import (
    AccentButton, Card, GhostButton,
    LogBox, ProgressCard, SectionLabel,
)


class VideoTab(ctk.CTkFrame):
    CONVERSIONS = {
        "MP4  →  GIF": ("mp4", "gif"),
        "MP4  →  AVI": ("mp4", "avi"),
        "MP4  →  MKV": ("mp4", "mkv"),
        "AVI  →  MP4": ("avi", "mp4"),
        "MKV  →  MP4": ("mkv", "mp4"),
        "MP4  →  MP3": ("mp4", "mp3"),
        "MP4  →  WAV": ("mp4", "wav"),
    }

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._files:       list[str] = []
        self._src_fps      = 0.0
        self._duration     = 0.0
        self._has_probe    = False
        self._cancel_flag  = threading.Event()
        self._build()

    # ── UI helpers (siempre hilo principal) ───────────────────────────────────
    def _log(self, msg: str) -> None:
        self.after(0, lambda m=msg: self.log.append(m))

    def _set_progress(self, value: float, text: str = "") -> None:
        self.after(0, lambda v=value, tx=text: self.progress.set(v, tx))

    def _done_progress(self, ok: bool) -> None:
        self.after(0, lambda o=ok: self.progress.done(o))

    # ── Construcción de la UI ─────────────────────────────────────────────────
    def _build(self):
        self._lbl_title = _reg(
            ctk.CTkLabel(self, text=t("vid_title"), font=HEAD(), text_color=ACCENT), "head"
        )
        self._lbl_title.pack(pady=(24, 2))
        self._lbl_subtitle = _reg(
            ctk.CTkLabel(self, text=t("vid_subtitle"), font=SMALL(), text_color=MUTED), "small"
        )
        self._lbl_subtitle.pack(pady=(0, 20))

        # Entrada
        fc = Card(self)
        fc.pack(fill="x", padx=30, pady=6)
        self._lbl_input_section = SectionLabel(fc, text=t("vid_input_section"))
        self._lbl_input_section.pack(anchor="w", padx=16, pady=(14, 6))
        row = ctk.CTkFrame(fc, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 14))
        self._btn_add = AccentButton(row, text=t("vid_add_btn"),
                                     command=self._pick_files, width=180)
        self._btn_add.pack(side="left")
        self.file_label = _reg(
            ctk.CTkLabel(row, text=t("vid_no_file"), font=SMALL(),
                          text_color=MUTED, wraplength=400, anchor="w"), "small"
        )
        self.file_label.pack(side="left", padx=14)

        # Información
        ic = Card(self)
        ic.pack(fill="x", padx=30, pady=6)
        self._lbl_info_section = SectionLabel(ic, text=t("vid_info_section"))
        self._lbl_info_section.pack(anchor="w", padx=16, pady=(14, 6))
        self.info_lbl = _reg(
            ctk.CTkLabel(ic, text=t("vid_info_hint"), font=SMALL(),
                          text_color=MUTED, justify="left", anchor="w"), "small"
        )
        self.info_lbl.pack(anchor="w", padx=16, pady=(0, 14))

        # Opciones
        oc = Card(self)
        oc.pack(fill="x", padx=30, pady=6)
        self._lbl_options = SectionLabel(oc, text=t("options_section"))
        self._lbl_options.pack(anchor="w", padx=16, pady=(14, 6))
        row2 = ctk.CTkFrame(oc, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(0, 8))
        self.conv_var = ctk.StringVar(value=list(self.CONVERSIONS)[0])
        ctk.CTkOptionMenu(
            row2, variable=self.conv_var, values=list(self.CONVERSIONS),
            fg_color=BORDER, button_color=ACCENT, button_hover_color=ACCENT2,
            text_color=TEXT, font=BODY(), width=200,
        ).pack(side="left")

        # Control FPS para GIF
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
            fpr, from_=5, to=30, variable=self.fps_var, width=120,
            button_color=ACCENT, button_hover_color=ACCENT2, progress_color=ACCENT,
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
                          justify="left", anchor="w", wraplength=820), "small"
        )
        self.fps_hint.pack(anchor="w", pady=(4, 0))

        # Carpeta de salida
        or3 = ctk.CTkFrame(oc, fg_color="transparent")
        or3.pack(fill="x", padx=16, pady=(8, 14))
        self._lbl_outdir = _reg(
            ctk.CTkLabel(or3, text=t("out_dir_label"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_outdir.pack(side="left")
        self.out_dir = ctk.StringVar(value=os.path.expanduser("~/Desktop"))
        ctk.CTkEntry(or3, textvariable=self.out_dir, font=BODY(),
                     fg_color=BORDER, border_color=ACCENT, width=280).pack(side="left", padx=10)
        self._btn_browse = GhostButton(or3, text=t("browse"), width=110,
                                       command=self._pick_outdir)
        self._btn_browse.pack(side="left")
        self.conv_var.trace_add("write", self._on_conv_change)

        # Progreso, log, botones
        self.progress = ProgressCard(self)
        self.progress.pack(fill="x", padx=30, pady=6)
        self.log = LogBox(self, height=130)
        self.log.pack(fill="x", padx=30, pady=6)
        br = ctk.CTkFrame(self, fg_color="transparent")
        br.pack(pady=18)
        self._btn_convert = AccentButton(br, text=t("vid_convert_btn"),
                                         command=self._start, height=44, width=220)
        self._btn_convert.pack(side="left")
        self._btn_cancel = GhostButton(br, text=t("cancel_btn"),
                                       command=self._cancel, height=44, width=120)
        self._btn_cancel.pack(side="left", padx=12)

    # ── Actualización de idioma en vivo ───────────────────────────────────────
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
        self._lbl_outdir.configure(text=t("out_dir_label"))
        self._btn_browse.configure(text=t("browse"))
        self._update_fps_hint()
        self._btn_convert.configure(text=t("vid_convert_btn"))
        self._btn_cancel.configure(text=t("cancel_btn"))
        self.progress.refresh_lang()

    # ── Cambio de conversión ──────────────────────────────────────────────────
    def _on_conv_change(self, *_):
        src_ext, ext = self.CONVERSIONS[self.conv_var.get()]
        if ext == "gif":
            self._fps_wrapper.pack(fill="x", padx=16, pady=(0, 4))
            self._update_fps_hint()
        else:
            self._fps_wrapper.pack_forget()

        # Drop any loaded files that don't match the new source format
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

    # ── Hint de FPS ───────────────────────────────────────────────────────────
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

    # ── Gestión de archivos ───────────────────────────────────────────────────
    def _src_ext(self) -> str:
        """Returns the expected source extension for the current conversion."""
        src, _ = self.CONVERSIONS[self.conv_var.get()]
        return src  # e.g. "mp4", "avi", "mkv"

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
                    f"📄 {_name}\n"
                    f"📦 {_mb:.2f} MB   ⏱ {_mins}:{_secs:02d}"
                    f"   🎞 {_fps:.3f} FPS\n"
                    f"📂 {_path}"
                ),
                text_color=TEXT,
            ))
        except FFmpegNotFoundError as e:
            _e = str(e)
            self.after(0, lambda: self.info_lbl.configure(
                text=f"⚠ {_e}", text_color=ERR
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

    # ── Conversión ────────────────────────────────────────────────────────────
    def _start(self):
        if not self._files:
            messagebox.showwarning(t("vid_warn_title"), t("vid_warn_msg"))
            return
        self._cancel_flag.clear()
        self.log.clear()
        self.progress.reset()
        threading.Thread(target=self._convert, daemon=True).start()

    def _cancel(self):
        self._cancel_flag.set()
        self._log(t("vid_cancelling"))

    def _convert(self):
        _, ext  = self.CONVERSIONS[self.conv_var.get()]
        out_dir = self.out_dir.get()
        os.makedirs(out_dir, exist_ok=True)

        # Snapshot the files list to prevent race condition if user modifies it during conversion
        files = list(self._files)
        
        # Track conversion success to report correct status
        success = True

        for idx, file_path in enumerate(files):
            if self._cancel_flag.is_set():
                break

            stem = os.path.splitext(os.path.basename(file_path))[0]
            dest = os.path.join(out_dir, f"{stem}.{ext}")

            # Capture loop variables before lambda (safe outside loop)
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
                    fps    = self.fps_var.get()
                    vf     = (
                        f"fps={fps},split[s0][s1];"
                        "[s0]palettegen=max_colors=256:stats_mode=full[p];"
                        "[s1][p]paletteuse=dither=floyd_steinberg"
                    )
                    ffargs = ["-i", file_path, "-vf", vf, "-loop", "0", dest]
                elif ext in ("mp3", "wav"):
                    acodec = "libmp3lame" if ext == "mp3" else "pcm_s16le"
                    ffargs = ["-i", file_path, "-vn", "-acodec", acodec, dest]
                else:
                    codec  = _VIDEO_CODEC.get(ext, "libx264")
                    q_args = (["-q:v", "4"] if ext == "avi"
                               else ["-crf", "18", "-preset", "fast"])
                    ffargs = (["-i", file_path, "-c:v", codec,
                                "-r", f"{src_fps}"] + q_args + ["-c:a", "copy", dest])

                ok, err_tail = run_ffmpeg(ffargs, duration, prog, self._cancel_flag)

                if self._cancel_flag.is_set():
                    self._log(t("vid_cancelled"))
                    break

                # FIX: captura de variables de bucle ANTES del after()
                if ok:
                    _dest   = dest
                    _size   = os.path.getsize(dest) / (1024 * 1024)
                    self._log(f"✓ {_dest} ({_size:.2f} MB)")
                else:
                    _tail = err_tail
                    self._log(f"✗ Error: {_tail}")

            except FFmpegNotFoundError as e:
                _e = str(e)
                self._log(f"✗ {_e}")
                success = False
                break   # Without FFmpeg it doesn't make sense to continue
            except Exception as e:
                _e = str(e)
                self._log(f"✗ {_e}")
                success = False

        self._done_progress(success and not self._cancel_flag.is_set())
        _out = out_dir
        self._log(t("vid_done", out_dir=_out))
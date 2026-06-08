"""
Reusable UI components — modern layout definitions.
"""
import customtkinter as ctk

from config import (
    CARD, PANEL, SURFACE, BORDER, SUBTLE,
    ACCENT, ACCENT2, ACCENT_DIM,
    OK, ERR, TEXT, MUTED, FONT_FAMILY,
)
from i18n import t
from utils import _reg, SUB, BODY, SMALL, MONO


class SectionLabel(ctk.CTkFrame):
    """Etiqueta de sección minimalista con jerarquía tipográfica moderna."""

    def __init__(self, master, text: str, **kw):
        kw.pop("text_color", None)
        kw.pop("font", None)
        super().__init__(master, fg_color="transparent", **kw)

        self._indicator = ctk.CTkFrame(
            self, width=3, height=14, fg_color=ACCENT, corner_radius=1
        )
        self._indicator.pack(side="left", padx=(0, 8))

        self._lbl = ctk.CTkLabel(
            self, text=text.upper().replace("▸ ", ""), 
            font=(FONT_FAMILY, 11, "bold"), text_color=MUTED
        )
        _reg(self._lbl, "small")
        self._lbl.pack(side="left")

    def configure(self, **kw):
        if "text" in kw:
            self._lbl.configure(text=kw.pop("text").upper().replace("▸ ", ""))
        if kw:
            super().configure(**kw)


class GhostButton(ctk.CTkButton):
    """Botón secundario delineado con micro-borde plano."""

    def __init__(self, master, **kw):
        h = kw.pop("height", 36)
        super().__init__(
            master,
            fg_color="transparent",
            hover_color=ACCENT_DIM,
            text_color=TEXT,
            border_width=1,
            border_color=BORDER,
            font=(FONT_FAMILY, 13),
            corner_radius=8,
            height=h,
            **kw,
        )
        _reg(self, "body")


class AccentButton(ctk.CTkButton):
    """Botón de acción principal plano con tipografía sólida semi-bold."""

    def __init__(self, master, **kw):
        h = kw.pop("height", 44)
        super().__init__(
            master,
            fg_color=ACCENT,
            hover_color=ACCENT2,
            text_color="#090605",
            font=(FONT_FAMILY, 13, "bold"),
            corner_radius=8,
            height=h,
            border_width=0,
            **kw,
        )
        _reg(self, "sub")


class LogBox(ctk.CTkFrame):
    """Consola de salida de texto compacta."""

    def __init__(self, master, height: int = 140, **kw):
        super().__init__(
            master,
            fg_color=BORDER,
            corner_radius=12,
            height=height,
            **kw,
        )
        self.pack_propagate(False)

        hdr = ctk.CTkFrame(self, fg_color=SURFACE, height=28, corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        dots = ctk.CTkFrame(hdr, fg_color="transparent")
        dots.pack(side="left", padx=(12, 6), pady=0)
        dot_colors = [("#FF5F57", "#3D1818"), ("#FEBC2E", "#3D3010"), ("#28C840", "#103D18")]
        for color, halo in dot_colors:
            pair = ctk.CTkFrame(dots, fg_color="transparent", width=16, height=16)
            pair.pack(side="left", padx=2)
            ctk.CTkLabel(
                pair, text="", font=(FONT_FAMILY, 7),
                fg_color=halo, width=14, height=14,
                corner_radius=7,
            ).place(relx=0.5, rely=0.5, anchor="center")
            ctk.CTkLabel(
                pair, text="\u25cf", font=(FONT_FAMILY, 8),
                text_color=color, width=14,
            ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            hdr, text="OUTPUT",
            font=("Cascadia Code", 9, "bold"), text_color=MUTED,
        ).pack(side="left", padx=(14, 0))

        self._tb = ctk.CTkTextbox(
            self,
            font=MONO(),
            fg_color="#050403",
            text_color=TEXT,
            border_width=0,
            corner_radius=0,
            activate_scrollbars=True,
        )
        _reg(self._tb, "mono")
        self._tb.configure(state="disabled")
        self._tb.pack(fill="both", expand=True, padx=1, pady=(0, 1))

    def append(self, msg: str) -> None:
        self._tb.configure(state="normal")
        self._tb.insert("end", msg + "\n")
        self._tb.see("end")
        self._tb.configure(state="disabled")

    def clear(self) -> None:
        self._tb.configure(state="normal")
        self._tb.delete("1.0", "end")
        self._tb.configure(state="disabled")


class Card(ctk.CTkFrame):
    """Contenedor Bento con bordes finos de 1px."""

    def __init__(self, master, accent_left: bool = False, **kw):
        super().__init__(
            master,
            fg_color=CARD,
            corner_radius=12,
            border_width=1,
            border_color=BORDER,
            **kw,
        )
        if accent_left:
            self._accent_bar = ctk.CTkFrame(
                self, width=2, fg_color=ACCENT, corner_radius=0
            )
            self._accent_bar.place(x=0, y=10, relheight=0.8)


class ProgressCard(Card):
    """Barra de progreso integrada."""

    _PULSE_ON  = "#A6988B"
    _PULSE_OFF = MUTED
    _PULSE_MS  = 1400

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self._state = "ready"
        self._pulse_on = False
        self._pulse_after = None

        self.label = _reg(
            ctk.CTkLabel(self, text=t("progress_ready"),
                         font=(FONT_FAMILY, 12), text_color=MUTED),
            "body",
        )
        self.label.pack(pady=(12, 4), padx=16, anchor="w")

        self.bar = ctk.CTkProgressBar(
            self,
            fg_color=SURFACE,
            progress_color=ACCENT,
            corner_radius=4,
            height=6,
        )
        self.bar.set(0)
        self.bar.pack(fill="x", padx=16, pady=(0, 12))

        self._schedule_pulse()

    def _schedule_pulse(self):
        if self._pulse_after is not None:
            try:
                self.after_cancel(self._pulse_after)
            except Exception:
                pass
        self._pulse_after = self.after(self._PULSE_MS, self._tick_pulse)

    def _tick_pulse(self):
        self._pulse_after = None
        if self._state != "ready":
            return
        self._pulse_on = not self._pulse_on
        try:
            self.label.configure(
                text_color=self._PULSE_ON if self._pulse_on else self._PULSE_OFF
            )
        except Exception:
            pass
        self._schedule_pulse()

    def set(self, value: float, text: str = "") -> None:
        self._state = "running"
        self.bar.set(value)
        if text:
            self.label.configure(text=text, text_color=MUTED)

    def done(self, ok: bool = True) -> None:
        self._state = "done_ok" if ok else "done_err"
        self.bar.set(1.0)
        color = OK if ok else ERR
        self.bar.configure(progress_color=color)
        self.label.configure(
            text=t("progress_completed") if ok else t("progress_error"),
            text_color=color,
        )

    def reset(self) -> None:
        self._state = "ready"
        self.bar.set(0)
        self.bar.configure(progress_color=ACCENT)
        self.label.configure(text=t("progress_ready"), text_color=MUTED)
        self._schedule_pulse()

    def refresh_lang(self) -> None:
        if self._state == "ready":
            self.label.configure(text=t("progress_ready"))
        elif self._state == "done_ok":
            self.label.configure(text=t("progress_completed"))
        elif self._state == "done_err":
            self.label.configure(text=t("progress_error"))


class DropZoneCard(Card):
    """Manejador de selección visual interactiva."""

    def __init__(self, master, command=None, **kw):
        super().__init__(master, **kw)
        self.configure(border_width=1, border_color=BORDER, fg_color="#050403")
        self._command = command
        self._active = False

        self.inner_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.inner_frame.pack(expand=True, pady=20, padx=20)

        self.icon_lbl = ctk.CTkLabel(
            self.inner_frame, text="📥", font=(FONT_FAMILY, 28), text_color=MUTED
        )
        self.icon_lbl.pack(pady=(0, 4))

        self.text_lbl = ctk.CTkLabel(
            self.inner_frame,
            text=t("drop_zone_text"),
            font=(FONT_FAMILY, 12),
            text_color=MUTED,
            justify="center",
        )
        _reg(self.text_lbl, "body")
        self.text_lbl.pack()

        if command:
            for widget in [self, self.inner_frame, self.icon_lbl, self.text_lbl]:
                widget.bind("<Button-1>", lambda _: command())
                widget.configure(cursor="hand2")

    def set_active(self, active: bool):
        self._active = active
        if active:
            self.configure(border_color=ACCENT, fg_color=ACCENT_DIM)
            self.icon_lbl.configure(text_color=ACCENT2)
            self.text_lbl.configure(text=t("drop_zone_active"), text_color=TEXT)
        else:
            self.configure(border_color=BORDER, fg_color="#050403")
            self.icon_lbl.configure(text_color=MUTED)
            self.text_lbl.configure(text=t("drop_zone_text"), text_color=MUTED)

    def refresh_lang(self):
        if not self._active:
            self.text_lbl.configure(text=t("drop_zone_text"))
        else:
            self.text_lbl.configure(text=t("drop_zone_active"))


class GifThumbItem(ctk.CTkFrame):
    HEIGHT = 64

    def __init__(self, master, number, path, thumb_img,
                 on_up, on_down, on_remove, **kw):
        import os
        super().__init__(
            master,
            fg_color=SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=BORDER,
            height=self.HEIGHT, **kw,
        )
        self.pack_propagate(False)
        self._img_ref = thumb_img

        _reg(ctk.CTkLabel(self, text=f"{number:02d}", font=(FONT_FAMILY, 11, "bold"),
                           text_color=ACCENT, width=24), "small").pack(side="left", padx=(10, 2))

        if thumb_img:
            ctk.CTkLabel(self, image=thumb_img, text="").pack(side="left", padx=4)
        else:
            ctk.CTkLabel(self, text="?", width=64, height=44, fg_color=PANEL,
                          corner_radius=6, font=SMALL(), text_color=MUTED).pack(side="left", padx=4)

        name = os.path.basename(path)
        if len(name) > 34:
            name = name[:31] + "..."
        _reg(ctk.CTkLabel(self, text=name, font=(FONT_FAMILY, 12), text_color=TEXT,
                           anchor="w"), "small").pack(side="left", padx=8, fill="x", expand=True)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(side="right", padx=8)
        GhostButton(bf, text="^", width=28, height=28, command=on_up).pack(side="left", padx=1)
        GhostButton(bf, text="v", width=28, height=28, command=on_down).pack(side="left", padx=1)
        GhostButton(bf, text="✕", width=28, height=28, command=on_remove).pack(side="left", padx=(1, 0))
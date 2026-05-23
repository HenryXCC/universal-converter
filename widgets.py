"""
Reusable UI components.
"""
import customtkinter as ctk

from config import (
    CARD, BORDER, ACCENT, ACCENT2, OK, ERR, TEXT, MUTED,
)
from i18n import t
from utils import _reg, SUB, BODY, SMALL


# Section label
class SectionLabel(ctk.CTkLabel):
    def __init__(self, master, text: str, **kw):
        super().__init__(master, text=text, font=SUB(), text_color=ACCENT, **kw)
        _reg(self, "sub")


# Buttons
class GhostButton(ctk.CTkButton):
    def __init__(self, master, **kw):
        h = kw.pop("height", 34)
        super().__init__(
            master,
            fg_color="transparent", hover_color=BORDER,
            text_color=TEXT, border_width=1, border_color=BORDER,
            font=BODY(), corner_radius=6, height=h, **kw,
        )
        _reg(self, "body")


class AccentButton(ctk.CTkButton):
    def __init__(self, master, **kw):
        h = kw.pop("height", 38)
        super().__init__(
            master,
            fg_color=ACCENT, hover_color=ACCENT2,
            text_color="#000000", font=SUB(), corner_radius=6, height=h, **kw,
        )
        _reg(self, "sub")


# Log box
class LogBox(ctk.CTkTextbox):
    def __init__(self, master, **kw):
        super().__init__(
            master,
            font=BODY(), fg_color="#0A0A0B", text_color=TEXT,
            border_color=BORDER, border_width=1, corner_radius=6,
            activate_scrollbars=True, **kw,
        )
        _reg(self, "body")
        self.configure(state="disabled")

    def append(self, msg: str) -> None:
        self.configure(state="normal")
        self.insert("end", msg + "\n")
        self.see("end")
        self.configure(state="disabled")

    def clear(self) -> None:
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")


# Cards
class Card(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(
            master,
            fg_color=CARD, corner_radius=10,
            border_width=1, border_color=BORDER, **kw,
        )


class ProgressCard(Card):
    """Progress bar with label and live language update support.

    Internal states:
        "ready"    → before starting or after reset()
        "running"  → process in progress (dynamic text, refresh doesn't overwrite)
        "done_ok"  → completed successfully
        "done_err" → completed with error
    """

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self._state = "ready"
        self.label = _reg(
            ctk.CTkLabel(self, text=t("progress_ready"), font=SMALL(), text_color=MUTED),
            "small",
        )
        self.label.pack(pady=(10, 4), padx=14, anchor="w")
        self.bar = ctk.CTkProgressBar(
            self, fg_color=BORDER, progress_color=ACCENT, corner_radius=4, height=6,
        )
        self.bar.set(0)
        self.bar.pack(fill="x", padx=14, pady=(0, 10))

    def set(self, value: float, text: str = "") -> None:
        self._state = "running"
        self.bar.set(value)
        if text:
            self.label.configure(text=text)

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

    def refresh_lang(self) -> None:
        """Translates the label to the active language without touching dynamic progress."""
        if self._state == "ready":
            self.label.configure(text=t("progress_ready"), text_color=MUTED)
        elif self._state == "done_ok":
            self.label.configure(text=t("progress_completed"), text_color=OK)
        elif self._state == "done_err":
            self.label.configure(text=t("progress_error"), text_color=ERR)


# GIF builder item
class GifThumbItem(ctk.CTkFrame):
    HEIGHT = 72

    def __init__(self, master, number, path, thumb_img,
                 on_up, on_down, on_remove, **kw):
        import os
        super().__init__(
            master,
            fg_color="#181820", corner_radius=6,
            border_width=1, border_color=BORDER,
            height=self.HEIGHT, **kw,
        )
        self.pack_propagate(False)
        self._img_ref = thumb_img

        _reg(ctk.CTkLabel(self, text=f"{number:02d}", font=SMALL(),
                           text_color=ACCENT, width=26), "small").pack(side="left", padx=(8, 2))

        if thumb_img:
            ctk.CTkLabel(self, image=thumb_img, text="").pack(side="left", padx=4)
        else:
            ctk.CTkLabel(self, text="?", width=80, height=55, fg_color=BORDER,
                          corner_radius=4, font=SMALL(), text_color=MUTED).pack(side="left", padx=4)

        name = os.path.basename(path)
        if len(name) > 30:
            name = name[:27] + "…"
        _reg(ctk.CTkLabel(self, text=name, font=SMALL(), text_color=TEXT,
                           anchor="w"), "small").pack(side="left", padx=8, fill="x", expand=True)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(side="right", padx=6)
        GhostButton(bf, text="↑", width=28, height=26, command=on_up).pack(side="left", padx=2)
        GhostButton(bf, text="↓", width=28, height=26, command=on_down).pack(side="left", padx=2)
        GhostButton(bf, text="✕", width=28, height=26, command=on_remove).pack(side="left", padx=(2, 0))

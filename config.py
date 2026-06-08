"""
Global configuration: colors, fonts, optional dependencies, and FFmpeg.
"""
import os
import shutil

import customtkinter as ctk

try:
    import yt_dlp as _yt_dlp_module
    YT_DLP_OK = True
except ImportError:
    _yt_dlp_module = None
    YT_DLP_OK = False

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_OK = True
except ImportError:
    DND_OK = False
    TkinterDnD = None
    DND_FILES = None

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG       = "#070605"
PANEL    = "#0D0A08"
CARD     = "#130F0C"
SURFACE  = "#1B1511"
BORDER   = "#221A15"

SIDEBAR  = "#0D0A08"

ACCENT   = "#E8622A"
ACCENT2  = "#FF8C42"
ACCENT_DIM = "#26130A"
ACCENT_GLOW = "#3D1E0C"

ACCENT_GRADIENT_L = "#C44D1A"
ACCENT_GRADIENT_R = "#FF8C42"

OK       = "#4ADE80"
ERR      = "#F87171"
WARN     = "#FBBF24"
TEXT     = "#F3F3F5"
MUTED    = "#8A7E74"
SUBTLE   = "#2F241D"

FONT_FAMILY = "Segoe UI Variable Display"
FONT_MONO   = "Cascadia Code"
BASE_SIZE   = 10

_POPEN_KW: dict = {}
if os.name == "nt":
    _POPEN_KW["creationflags"] = 0x08000000

_VIDEO_CODEC: dict[str, str] = {
    "mp4": "libx264",
    "avi": "mpeg4",
    "mkv": "libx264",
    "mov": "libx264",
}

def _find_ffmpeg_bins() -> tuple[str, str]:
    ffmpeg  = shutil.which("ffmpeg")  or "ffmpeg"
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    if ffmpeg == "ffmpeg":
        try:
            from moviepy.config import get_setting
            mp = get_setting("FFMPEG_BINARY")
            if mp and os.path.isfile(mp):
                ffmpeg  = mp
                ffprobe = mp.replace("ffmpeg", "ffprobe")
        except Exception:
            pass
    return ffmpeg, ffprobe

FFMPEG, FFPROBE = _find_ffmpeg_bins()
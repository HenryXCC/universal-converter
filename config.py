"""
Global configuration: colors, fonts, optional dependencies, and FFmpeg.
"""
import os
import shutil

import customtkinter as ctk

# Optional dependencies
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

# CTK theme 
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Color palette
BG      = "#0E0E0F"
PANEL   = "#16161A"
CARD    = "#1E1E24"
BORDER  = "#2A2A32"
ACCENT  = "#FF6B35"
ACCENT2 = "#FFB347"
OK      = "#4ADE80"
ERR     = "#F87171"
TEXT    = "#E8E8EE"
MUTED   = "#6E6E80"

# Typography 
FONT_FAMILY = "Courier New"
BASE_SIZE   = 10          # Modified at runtime by apply_font_scale

# FFmpeg / subprocess 
_POPEN_KW: dict = {}
if os.name == "nt":
    _POPEN_KW["creationflags"] = 0x08000000   # CREATE_NO_WINDOW

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

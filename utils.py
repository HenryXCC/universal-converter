"""
Shared Utilities:

- Font scaling widget registration
- Typography helpers / apply_font_scale
- probe_video / run_ffmpeg (with proper error handling)
- smart_gif_fps
"""
import json
import subprocess
import threading
import weakref

import config as _cfg

# Widget registration for font scaling
_all_widgets: list[weakref.ref] = []


def _reg(widget, tag: str):
    """Registers a widget to receive font scale updates."""
    widget._font_tag = tag
    _all_widgets.append(weakref.ref(widget))
    return widget


# Font size helpers
def _sz(delta: int = 0) -> int:
    return max(7, min(26, _cfg.BASE_SIZE + delta))


def HEAD()  -> tuple: return (_cfg.FONT_FAMILY, _sz(+12), "bold")
def SUB()   -> tuple: return (_cfg.FONT_FAMILY, _sz(+1),  "bold")
def BODY()  -> tuple: return (_cfg.FONT_FAMILY, _sz(0))
def SMALL() -> tuple: return (_cfg.FONT_FAMILY, _sz(-1))


def apply_font_scale(delta: int) -> None:
    """Adjusts BASE_SIZE and updates all registered widgets."""
    global _all_widgets
    _cfg.BASE_SIZE = max(7, min(22, 10 + delta))
    live = []
    for ref in _all_widgets:
        w = ref()
        if w is None:
            continue
        live.append(ref)
        try:
            tag = getattr(w, "_font_tag", None)
            if   tag == "head":  w.configure(font=HEAD())
            elif tag == "sub":   w.configure(font=SUB())
            elif tag == "body":  w.configure(font=BODY())
            elif tag == "small": w.configure(font=SMALL())
        except Exception:
            pass
    _all_widgets = live


# FFprobe
class FFmpegNotFoundError(RuntimeError):
    """FFmpeg/FFprobe not found on the system."""


def probe_video(path: str) -> dict:
    """Reads video file metadata via FFprobe.

    Raises:
        FFmpegNotFoundError: if ffprobe is not available.
        RuntimeError: if ffprobe fails to read the file.
    """
    cmd = [_cfg.FFPROBE, "-v", "quiet", "-print_format", "json",
           "-show_streams", "-show_format", path]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, **_cfg._POPEN_KW
        )
    except FileNotFoundError:
        raise FFmpegNotFoundError(
            "FFprobe not found. Install FFmpeg and ensure it is in the PATH."
        )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ffprobe failed.")

    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        raise RuntimeError("ffprobe returned invalid JSON.")

    video = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"), {}
    )

    def _parse_rate(s: str) -> float:
        try:
            n, d = map(int, s.split("/"))
            return n / d if d else 0.0
        except Exception:
            return 0.0

    fps = _parse_rate(video.get("r_frame_rate", "0/1"))
    if fps <= 0:
        fps = _parse_rate(video.get("avg_frame_rate", "0/1"))

    duration = float(
        video.get("duration")
        or data.get("format", {}).get("duration")
        or 0
    )
    return {
        "fps":      fps,
        "duration": duration,
        "width":    int(video.get("width",  0)),
        "height":   int(video.get("height", 0)),
    }


# FFmpeg runner with live progress
def run_ffmpeg(
    args: list[str],
    duration: float,
    progress_cb=None,
    cancel_flag: threading.Event = None,
) -> tuple[bool, str]:
    """Corre FFmpeg con reporte de progreso en vivo.

    Returns:
        (True, "")          si exitoso
        (False, error_tail) si falló o fue cancelado
    Raises:
        FFmpegNotFoundError si ffmpeg no está en el PATH.
    """
    cmd = [_cfg.FFMPEG, "-y", "-progress", "pipe:2"] + args
    try:
        proc = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            **_cfg._POPEN_KW,
        )
    except FileNotFoundError:
        raise FFmpegNotFoundError(
            "FFmpeg not found. Install FFmpeg and ensure it is in the PATH."
        )

    tail: list[str] = []
    try:
        for raw in proc.stderr:
            line = raw.strip()
            if not line:
                continue
            tail.append(line)
            if len(tail) > 40:
                tail.pop(0)

            if cancel_flag and cancel_flag.is_set():
                proc.kill()
                proc.wait()
                return False, "Cancelled."

            if line.startswith("out_time_ms=") and duration > 0 and progress_cb:
                try:
                    ms      = int(line.split("=")[1])
                    current = ms / 1_000_000
                    progress_cb(
                        min(1.0, current / duration),
                        f"{current:.1f}s / {duration:.1f}s",
                    )
                except Exception:
                    pass
            elif "time=" in line and duration > 0 and progress_cb:
                try:
                    ts = line.split("time=")[1].split()[0]
                    h, m, s = ts.split(":")
                    current = int(h) * 3600 + int(m) * 60 + float(s)
                    speed   = (
                        "  " + line.split("speed=")[1].split()[0]
                        if "speed=" in line else ""
                    )
                    progress_cb(
                        min(1.0, current / duration),
                        f"{current:.1f}s / {duration:.1f}s{speed}",
                    )
                except Exception:
                    pass
    except Exception:
        pass

    proc.wait()
    return proc.returncode == 0, "\n".join(tail[-8:])


# GIF FPS recommendation
def smart_gif_fps(src_fps: float) -> int:
    if src_fps <= 0:
        return 12
    raw = src_fps / 2
    for c in (5, 8, 10, 12, 15, 18, 20):
        if c >= raw:
            return c
    return 20
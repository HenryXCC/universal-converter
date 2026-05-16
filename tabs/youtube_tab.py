"""
Pestaña de descarga de audio de YouTube.

Correcciones aplicadas:
  - ANSI stripping en todos los mensajes de error.
  - Exportación nativa de cookies sin extensiones del navegador.
  - cookiefile tiene prioridad sobre cookiesfrombrowser.
  - Lambdas thread-safe con captura explícita de variables.
"""
import io
import os
import re
import shutil
import sqlite3
import tempfile
import threading
import urllib.request
import atexit

import customtkinter as ctk
try:
    from PIL import Image
except ImportError:
    Image = None
from tkinter import filedialog, messagebox

from config import (
    ACCENT, ACCENT2, BORDER, ERR, MUTED, OK, TEXT,
    YT_DLP_OK, _yt_dlp_module,
)
from i18n import t
from utils import _reg, BODY, SMALL, HEAD, SUB
from widgets import (
    AccentButton, Card, GhostButton,
    LogBox, ProgressCard, SectionLabel,
)

# ─── Navegadores para exportación nativa de cookies ──────────────────────────
_BROWSERS = ["Ninguno / None", "Chrome", "Firefox", "Edge", "Brave", "Opera", "Safari"]
_BROWSER_MAP = {
    "Chrome": "chrome", "Firefox": "firefox", "Edge": "edge",
    "Brave": "brave", "Opera": "opera", "Safari": "safari",
}

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m|\[\[[\d;]*m')


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


# ─── Exportación nativa de cookies de YouTube ────────────────────────────────
def _get_youtube_cookie_db_path(browser: str) -> str | None:
    """Devuelve la ruta a la base de datos de cookies del navegador o None."""
    import sys
    home = os.path.expanduser("~")

    paths: dict[str, list[str]] = {
        "Chrome": [
            os.path.join(home, "AppData", "Local", "Google", "Chrome",
                         "User Data", "Default", "Network", "Cookies"),
            os.path.join(home, "AppData", "Local", "Google", "Chrome",
                         "User Data", "Default", "Cookies"),
            os.path.join(home, "Library", "Application Support", "Google", "Chrome",
                         "Default", "Cookies"),
            os.path.join(home, ".config", "google-chrome", "Default", "Cookies"),
        ],
        "Edge": [
            os.path.join(home, "AppData", "Local", "Microsoft", "Edge",
                         "User Data", "Default", "Network", "Cookies"),
            os.path.join(home, "AppData", "Local", "Microsoft", "Edge",
                         "User Data", "Default", "Cookies"),
        ],
        "Brave": [
            os.path.join(home, "AppData", "Local", "BraveSoftware", "Brave-Browser",
                         "User Data", "Default", "Network", "Cookies"),
            os.path.join(home, "AppData", "Local", "BraveSoftware", "Brave-Browser",
                         "User Data", "Default", "Cookies"),
            os.path.join(home, "Library", "Application Support", "BraveSoftware",
                         "Brave-Browser", "Default", "Cookies"),
        ],
        "Opera": [
            os.path.join(home, "AppData", "Roaming", "Opera Software",
                         "Opera Stable", "Network", "Cookies"),
            os.path.join(home, "AppData", "Roaming", "Opera Software",
                         "Opera Stable", "Cookies"),
        ],
        "Firefox": [
            # Firefox usa un profile con nombre aleatorio; buscamos el primero
        ],
        "Safari": [
            os.path.join(home, "Library", "Cookies", "Cookies.binarycookies"),
        ],
    }

    # Firefox: busca el perfil default
    if browser == "Firefox":
        ff_base_win = os.path.join(home, "AppData", "Roaming", "Mozilla",
                                   "Firefox", "Profiles")
        ff_base_mac = os.path.join(home, "Library", "Application Support",
                                   "Firefox", "Profiles")
        ff_base_lin = os.path.join(home, ".mozilla", "firefox")
        for base in (ff_base_win, ff_base_mac, ff_base_lin):
            if os.path.isdir(base):
                for profile in os.listdir(base):
                    candidate = os.path.join(base, profile, "cookies.sqlite")
                    if os.path.isfile(candidate):
                        return candidate
        return None

    for path in paths.get(browser, []):
        if os.path.isfile(path):
            return path
    return None


def _export_youtube_cookies_to_file(browser: str) -> tuple[str | None, str]:
    """
    Exporta las cookies de YouTube del navegador dado a un archivo Netscape temporal.

    Returns:
        (ruta_al_archivo, "") en éxito.
        (None, mensaje_de_error) en fallo.
    """
    db_path = _get_youtube_cookie_db_path(browser)
    if db_path is None:
        return None, t("yt_cookies_db_not_found", browser=browser)

    # Para Chrome/Edge/Brave la DB puede estar bloqueada; copiamos a temp
    # FIX Bug 2: mktemp() está deprecado y tiene race condition (devuelve un
    # nombre sin crear el archivo, otro proceso podría ocuparlo antes del copy).
    # mkstemp() crea y bloquea el archivo atómicamente; cerramos el fd de
    # inmediato porque solo necesitamos la ruta para shutil.copy2.
    _tmp_fd, tmp_db = tempfile.mkstemp(suffix=".db")
    try:
        os.close(_tmp_fd)
    except OSError:
        pass
    try:
        shutil.copy2(db_path, tmp_db)
    except Exception as e:
        return None, t("yt_cookies_copy_err", e=e)

    try:
        if browser == "Firefox":
            rows = _read_firefox_cookies(tmp_db)
        else:
            rows = _read_chromium_cookies(tmp_db, browser)
    except Exception as e:
        return None, t("yt_cookies_read_err", e=e)
    finally:
        try:
            os.unlink(tmp_db)
        except Exception:
            pass

    if not rows:
        return None, t("yt_cookies_empty", browser=browser)

    # Escribir en formato Netscape
    out_fd, out_path = tempfile.mkstemp(suffix="_yt_cookies.txt")
    try:
        with os.fdopen(out_fd, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# Exported automatically by Convertidor Universal\n\n")
            for row in rows:
                f.write("\t".join(str(x) for x in row) + "\n")
    except Exception as e:
        return None, t("yt_cookies_write_err", e=e)

    return out_path, ""


def _read_firefox_cookies(db_path: str) -> list[tuple]:
    """Lee cookies de YouTube de la BD SQLite de Firefox."""
    conn = sqlite3.connect(db_path)
    # FIX Bug 3: proteger la conexión con try/finally igual que en
    # _read_chromium_cookies, para que no quede abierta si hay excepción.
    try:
        cursor = conn.execute(
            """
            SELECT host, path, isSecure, expiry, name, value
            FROM   moz_cookies
            WHERE  host LIKE '%youtube.com%'
                OR host LIKE '%google.com%'
                OR host LIKE '%yt3.ggpht.com%'
            """
        )
        rows = []
        for host, path, secure, expiry, name, value in cursor.fetchall():
            http_only = "FALSE"
            flag      = "TRUE" if secure else "FALSE"
            rows.append((host, "TRUE", path, flag, expiry, name, value))
    finally:
        conn.close()
    return rows


def _read_chromium_cookies(db_path: str, browser: str) -> list[tuple]:
    """
    Lee cookies de YouTube de la BD de Chromium (Chrome/Edge/Brave/Opera).
    Intenta desencriptar valores si es posible; si no, usa el valor crudo.
    """
    conn   = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT host_key, path, is_secure, expires_utc, name,
                   value, encrypted_value
            FROM   cookies
            WHERE  host_key LIKE '%youtube.com%'
                OR host_key LIKE '%google.com%'
                OR host_key LIKE '%googlevideo.com%'
            """
        )
        raw_rows = cursor.fetchall()
    finally:
        conn.close()

    rows = []
    for host, path, secure, expires, name, value, enc_value in raw_rows:
        # Intento de desencriptar (Windows DPAPI / macOS Keychain)
        decoded = value
        if not decoded and enc_value:
            decoded = _try_decrypt(enc_value, browser) or ""

        # Convertir timestamp de Chrome (microsegundos desde 1601) a Unix
        try:
            unix_ts = int((expires - 11644473600 * 10**6) / 10**6)
        except Exception:
            unix_ts = 0

        flag = "TRUE" if secure else "FALSE"
        rows.append(("." + host.lstrip("."), "TRUE", path, flag, unix_ts, name, decoded))
    return rows


def _try_decrypt(enc_value: bytes, browser: str) -> str | None:
    """Intenta desencriptar el valor de una cookie de Chromium."""
    import sys
    if not enc_value:
        return None

    # Cookies encriptadas con AES-GCM (prefijo v10/v11 — Windows y macOS moderno)
    if enc_value[:3] in (b"v10", b"v11"):
        try:
            return _decrypt_aes_gcm(enc_value, browser)
        except Exception:
            pass

    # Fallback: Windows DPAPI clásico
    if sys.platform == "win32":
        try:
            import ctypes
            import ctypes.wintypes

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [("cbData", ctypes.wintypes.DWORD),
                             ("pbData", ctypes.POINTER(ctypes.c_char))]

            p       = ctypes.create_string_buffer(enc_value, len(enc_value))
            blobin  = DATA_BLOB(ctypes.sizeof(p), p)
            blobout = DATA_BLOB()
            ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(blobin), None, None, None, None, 0,
                ctypes.byref(blobout)
            )
            return ctypes.string_at(blobout.pbData, blobout.cbData).decode("utf-8", errors="replace")
        except Exception:
            pass

    return None


def _decrypt_aes_gcm(enc_value: bytes, browser: str) -> str | None:
    """Desencripta cookies con AES-256-GCM usando la clave del Local State."""
    import sys, base64, json

    home = os.path.expanduser("~")
    local_state_paths: dict[str, str] = {
        "Chrome": os.path.join(home, "AppData", "Local", "Google", "Chrome",
                               "User Data", "Local State"),
        "Edge":   os.path.join(home, "AppData", "Local", "Microsoft", "Edge",
                               "User Data", "Local State"),
        "Brave":  os.path.join(home, "AppData", "Local", "BraveSoftware",
                               "Brave-Browser", "User Data", "Local State"),
        "Opera":  os.path.join(home, "AppData", "Roaming", "Opera Software",
                               "Opera Stable", "Local State"),
    }
    ls_path = local_state_paths.get(browser)
    if not ls_path or not os.path.isfile(ls_path):
        return None

    with open(ls_path, "r", encoding="utf-8") as f:
        ls = json.load(f)

    enc_key_b64 = ls.get("os_crypt", {}).get("encrypted_key")
    if not enc_key_b64:
        return None

    enc_key = base64.b64decode(enc_key_b64)[5:]  # quita prefijo DPAPI

    # Desencriptar la master key con DPAPI
    if sys.platform == "win32":
        import ctypes, ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", ctypes.wintypes.DWORD),
                         ("pbData", ctypes.POINTER(ctypes.c_char))]

        p       = ctypes.create_string_buffer(enc_key, len(enc_key))
        blobin  = DATA_BLOB(ctypes.sizeof(p), p)
        blobout = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blobin), None, None, None, None, 0, ctypes.byref(blobout)
        ):
            return None
        master_key = ctypes.string_at(blobout.pbData, blobout.cbData)
    else:
        return None  # macOS Keychain requiere otro flujo

    # Desencriptar el valor con AES-GCM
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce      = enc_value[3:15]
        ciphertext = enc_value[15:]
        return AESGCM(master_key).decrypt(nonce, ciphertext, None).decode("utf-8", errors="replace")
    except Exception:
        return None


class YouTubeTab(ctk.CTkFrame):
    FORMATS   = ["mp3", "m4a", "opus", "wav", "flac", "aac"]
    QUALITIES = ["320k", "256k", "192k", "128k", "96k", "64k"]

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._thumb_ref      = None
        self._has_yt_info    = False
        self._cancel_flag    = threading.Event()
        self._cookies_file   = ctk.StringVar(value="")
        self._tmp_cookie_file: str | None = None   # archivo temporal generado
        self._build()

    # ── UI helpers ────────────────────────────────────────────────────────────
    def _log(self, msg: str) -> None:
        self.after(0, lambda m=msg: self.log.append(m))

    def _set_progress(self, value: float, text: str = "") -> None:
        self.after(0, lambda v=value, tx=text: self.progress.set(v, tx))

    def _done_progress(self, ok: bool) -> None:
        self.after(0, lambda o=ok: self.progress.done(o))

    # ── Construcción de la UI ─────────────────────────────────────────────────
    def _build(self):
        self._lbl_title = _reg(
            ctk.CTkLabel(self, text=t("yt_title"), font=HEAD(), text_color=ACCENT), "head"
        )
        self._lbl_title.pack(pady=(24, 2))
        self._lbl_subtitle = _reg(
            ctk.CTkLabel(self, text=t("yt_subtitle"), font=SMALL(), text_color=MUTED), "small"
        )
        self._lbl_subtitle.pack(pady=(0, 20))

        # URL
        uc = Card(self)
        uc.pack(fill="x", padx=30, pady=6)
        self._lbl_url_section = SectionLabel(uc, text=t("yt_url_section"))
        self._lbl_url_section.pack(anchor="w", padx=16, pady=(14, 6))
        ur = ctk.CTkFrame(uc, fg_color="transparent")
        ur.pack(fill="x", padx=16, pady=(0, 14))
        self.url_var = ctk.StringVar()
        ctk.CTkEntry(
            ur, textvariable=self.url_var,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=BODY(), fg_color=BORDER, border_color=ACCENT, height=36,
        ).pack(side="left", fill="x", expand=True)
        GhostButton(ur, text="✕", width=36,
                    command=lambda: self.url_var.set("")).pack(side="left", padx=6)
        GhostButton(ur, text="🔍 Info", width=90,
                    command=self._fetch_info).pack(side="left")

        # Info del video
        ic = Card(self)
        ic.pack(fill="x", padx=30, pady=6)
        self._lbl_info_section = SectionLabel(ic, text=t("yt_info_section"))
        self._lbl_info_section.pack(anchor="w", padx=16, pady=(14, 6))
        ir = ctk.CTkFrame(ic, fg_color="transparent")
        ir.pack(fill="x", padx=16, pady=(0, 14))
        self.thumb_lbl = ctk.CTkLabel(
            ir, text=t("yt_no_thumb"), width=192, height=108,
            fg_color=BORDER, corner_radius=6, font=SMALL(), text_color=MUTED,
        )
        self.thumb_lbl.pack(side="left", padx=(0, 16))
        # FIX Bug 1: imagen en blanco de respaldo para evitar pasar image=None
        # a CTkLabel, lo que deja el widget en estado roto (no vuelve a mostrar
        # imágenes reales). Mismo problema corregido en image_tab.py.
        _blank_pil = Image.new("RGB", (192, 108), color=(30, 30, 36))
        self._blank_thumb_img = ctk.CTkImage(
            light_image=_blank_pil, dark_image=_blank_pil, size=(192, 108)
        )
        tc = ctk.CTkFrame(ir, fg_color="transparent")
        tc.pack(side="left", fill="both", expand=True)
        self.vid_title = _reg(
            ctk.CTkLabel(tc, text=t("yt_preview_hint"), font=SUB(),
                          text_color=MUTED, justify="left", anchor="w", wraplength=440), "sub"
        )
        self.vid_title.pack(anchor="w", pady=(4, 8))
        self.vid_author = _reg(
            ctk.CTkLabel(tc, text="", font=BODY(), text_color=MUTED,
                          justify="left", anchor="w", wraplength=440), "body"
        )
        self.vid_author.pack(anchor="w", pady=(0, 6))
        self.vid_stats = _reg(
            ctk.CTkLabel(tc, text="", font=BODY(), text_color=MUTED,
                          justify="left", anchor="w", wraplength=440), "body"
        )
        self.vid_stats.pack(anchor="w")

        # Opciones
        oc = Card(self)
        oc.pack(fill="x", padx=30, pady=6)
        self._lbl_options = SectionLabel(oc, text=t("options_section"))
        self._lbl_options.pack(anchor="w", padx=16, pady=(14, 6))

        row = ctk.CTkFrame(oc, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 8))
        self._lbl_fmt = _reg(
            ctk.CTkLabel(row, text=t("yt_format_label"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_fmt.pack(side="left")
        self.fmt_var = ctk.StringVar(value="mp3")
        ctk.CTkOptionMenu(
            row, variable=self.fmt_var, values=self.FORMATS,
            fg_color=BORDER, button_color=ACCENT, button_hover_color=ACCENT2,
            text_color=TEXT, font=BODY(), width=110,
        ).pack(side="left", padx=10)
        self._lbl_quality = _reg(
            ctk.CTkLabel(row, text=t("yt_quality_label"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_quality.pack(side="left", padx=(20, 8))
        self.quality_var = ctk.StringVar(value="192k")
        ctk.CTkOptionMenu(
            row, variable=self.quality_var, values=self.QUALITIES,
            fg_color=BORDER, button_color=ACCENT, button_hover_color=ACCENT2,
            text_color=TEXT, font=BODY(), width=110,
        ).pack(side="left")

        # ── Sección Cookies ───────────────────────────────────────────────────
        ctk.CTkFrame(oc, fg_color=BORDER, height=1).pack(fill="x", padx=16, pady=(8, 10))
        self._lbl_cookies_section = _reg(
            ctk.CTkLabel(oc, text=t("yt_cookies_section"),
                          font=BODY(), text_color=ACCENT2, anchor="w"), "body"
        )
        self._lbl_cookies_section.pack(anchor="w", padx=16, pady=(0, 8))

        # Método 1 — Exportar directamente desde el navegador
        self._lbl_cookies_browser = _reg(
            ctk.CTkLabel(oc, text=t("yt_cookies_label"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_cookies_browser.pack(anchor="w", padx=16, pady=(0, 4))

        br_row = ctk.CTkFrame(oc, fg_color="transparent")
        br_row.pack(fill="x", padx=16, pady=(0, 4))
        self.browser_var = ctk.StringVar(value=_BROWSERS[0])
        self._menu_browser = ctk.CTkOptionMenu(
            br_row, variable=self.browser_var, values=_BROWSERS,
            fg_color=BORDER, button_color=ACCENT, button_hover_color=ACCENT2,
            text_color=TEXT, font=BODY(), width=150,
        )
        self._menu_browser.pack(side="left")
        self._btn_export_cookies = AccentButton(
            br_row, text=t("yt_cookies_export_btn"), height=32, width=200,
            command=self._export_cookies_now,
        )
        self._btn_export_cookies.pack(side="left", padx=(10, 0))

        self._lbl_export_status = _reg(
            ctk.CTkLabel(oc, text=t("yt_cookies_export_hint"),
                          font=SMALL(), text_color=MUTED,
                          justify="left", anchor="w", wraplength=760), "small"
        )
        self._lbl_export_status.pack(anchor="w", padx=16, pady=(2, 8))

        # Método 2 — archivo cookies.txt manual
        ctk.CTkFrame(oc, fg_color=BORDER, height=1).pack(fill="x", padx=16, pady=(0, 8))
        cf_row = ctk.CTkFrame(oc, fg_color="transparent")
        cf_row.pack(fill="x", padx=16, pady=(0, 4))
        self._lbl_cookiefile = _reg(
            ctk.CTkLabel(cf_row, text=t("yt_cookiefile_label"), font=BODY(), text_color=TEXT),
            "body"
        )
        self._lbl_cookiefile.pack(side="left")
        self._entry_cookiefile = ctk.CTkEntry(
            cf_row, textvariable=self._cookies_file,
            placeholder_text="cookies.txt",
            font=SMALL(), fg_color=BORDER, border_color=BORDER, height=30, width=240,
        )
        self._entry_cookiefile.pack(side="left", padx=(10, 6))
        GhostButton(cf_row, text="📂", width=36, height=30,
                    command=self._pick_cookies_file).pack(side="left", padx=(0, 6))
        GhostButton(cf_row, text="✕", width=30, height=30,
                    command=self._clear_cookies_file).pack(side="left")

        self._lbl_cookiefile_hint = _reg(
            ctk.CTkLabel(oc, text=t("yt_cookiefile_hint"),
                          font=SMALL(), text_color=MUTED,
                          justify="left", anchor="w", wraplength=760), "small"
        )
        self._lbl_cookiefile_hint.pack(anchor="w", padx=16, pady=(0, 14))
        self._cookies_file.trace_add("write", self._on_cookiefile_change)

        # Carpeta de salida
        or2 = ctk.CTkFrame(oc, fg_color="transparent")
        or2.pack(fill="x", padx=16, pady=(0, 14))
        self._lbl_outdir = _reg(
            ctk.CTkLabel(or2, text=t("out_dir_label"), font=BODY(), text_color=TEXT), "body"
        )
        self._lbl_outdir.pack(side="left")
        self.out_dir = ctk.StringVar(value=os.path.expanduser("~/Desktop"))
        ctk.CTkEntry(or2, textvariable=self.out_dir, font=BODY(),
                     fg_color=BORDER, border_color=ACCENT, width=280).pack(side="left", padx=10)
        self._btn_browse = GhostButton(or2, text=t("browse"), width=110,
                                       command=self._pick_outdir)
        self._btn_browse.pack(side="left")

        # Progreso, log, botones
        self.progress = ProgressCard(self)
        self.progress.pack(fill="x", padx=30, pady=6)
        self.log = LogBox(self, height=120)
        self.log.pack(fill="x", padx=30, pady=6)
        br2 = ctk.CTkFrame(self, fg_color="transparent")
        br2.pack(pady=18)
        self._btn_download = AccentButton(br2, text=t("yt_download_btn"),
                                          command=self._start, height=44, width=220)
        self._btn_download.pack(side="left")
        self._btn_cancel = GhostButton(br2, text=t("cancel_btn"),
                                       command=self._cancel, height=44, width=120)
        self._btn_cancel.pack(side="left", padx=12)

    # ── Exportación nativa de cookies ─────────────────────────────────────────
    def _export_cookies_now(self) -> None:
        browser = self.browser_var.get()
        if browser == _BROWSERS[0]:
            messagebox.showwarning(
                t("yt_cookies_no_browser_title"),
                t("yt_cookies_no_browser_msg"),
            )
            return
        self._lbl_export_status.configure(
            text=t("yt_cookies_exporting", browser=browser), text_color=MUTED
        )
        self.update_idletasks()
        threading.Thread(
            target=self._do_export_cookies, args=(browser,), daemon=True
        ).start()

    def _do_export_cookies(self, browser: str) -> None:
        # Limpiar archivo temporal previo
        if self._tmp_cookie_file and os.path.isfile(self._tmp_cookie_file):
            try:
                os.unlink(self._tmp_cookie_file)
            except Exception:
                pass
            self._tmp_cookie_file = None

        path, err = _export_youtube_cookies_to_file(browser)
        if path:
            self._tmp_cookie_file = path
            # Register cleanup function to ensure file is deleted on exit
            atexit.register(self._cleanup_tmp_cookie)
            self.after(0, lambda p=path: self._cookies_file.set(p))
            self.after(0, lambda br=browser: self._lbl_export_status.configure(
                text=t("yt_cookies_export_ok", browser=br), text_color=OK
            ))
        else:
            _err = err
            self.after(0, lambda e=_err: self._lbl_export_status.configure(
                text=f"✗ {e}", text_color=ERR
            ))

    # ── Callbacks de cookiefile ───────────────────────────────────────────────
    def _pick_cookies_file(self) -> None:
        path = filedialog.askopenfilename(
            title=t("yt_cookiefile_pick_title"),
            filetypes=[("Netscape cookies", "*.txt"), ("All", "*.*")],
        )
        if path:
            # Si el usuario selecciona un archivo manual, descartamos el temporal
            self._tmp_cookie_file = None
            self._cookies_file.set(path)

    def _clear_cookies_file(self) -> None:
        self._tmp_cookie_file = None
        self._cookies_file.set("")

    def _on_cookiefile_change(self, *_) -> None:
        path = self._cookies_file.get()
        if path and os.path.isfile(path):
            self._entry_cookiefile.configure(border_color=OK)
            self._lbl_cookiefile_hint.configure(
                text=f"✓ {os.path.basename(path)}", text_color=OK
            )
        elif path:
            self._entry_cookiefile.configure(border_color=ERR)
            self._lbl_cookiefile_hint.configure(
                text=t("yt_cookiefile_hint"), text_color=ERR
            )
        else:
            self._entry_cookiefile.configure(border_color=BORDER)
            self._lbl_cookiefile_hint.configure(
                text=t("yt_cookiefile_hint"), text_color=MUTED
            )

    def _get_ydl_opts_base(self, cookiefile: str = "", browser: str = "") -> dict:
        """Opciones base de yt-dlp. Prioridad: cookiefile > navegador."""
        opts: dict = {"quiet": True, "no_warnings": True}
        if not cookiefile and not browser:
            # Fallback: read from StringVar (for other callers)
            cookiefile = self._cookies_file.get().strip()
            browser = self.browser_var.get()
        
        if cookiefile and os.path.isfile(cookiefile):
            opts["cookiefile"] = cookiefile
        else:
            if browser != _BROWSERS[0] and browser in _BROWSER_MAP:
                opts["cookiesfrombrowser"] = (_BROWSER_MAP[browser],)
        return opts

    def _cookie_method_str(self) -> str:
        cookiefile = self._cookies_file.get().strip()
        if cookiefile and os.path.isfile(cookiefile):
            return f"🍪 {os.path.basename(cookiefile)}"
        browser = self.browser_var.get()
        if browser != _BROWSERS[0]:
            return f"🍪 {browser}"
        return ""

    # ── Actualización de idioma en vivo ───────────────────────────────────────
    def refresh_lang(self) -> None:
        self._lbl_title.configure(text=t("yt_title"))
        self._lbl_subtitle.configure(text=t("yt_subtitle"))
        self._lbl_url_section.configure(text=t("yt_url_section"))
        self._lbl_info_section.configure(text=t("yt_info_section"))
        if not self._has_yt_info:
            self.vid_title.configure(text=t("yt_preview_hint"), text_color=MUTED)
            self.thumb_lbl.configure(text=t("yt_no_thumb"))
        self._lbl_options.configure(text=t("options_section"))
        self._lbl_fmt.configure(text=t("yt_format_label"))
        self._lbl_quality.configure(text=t("yt_quality_label"))
        self._lbl_cookies_section.configure(text=t("yt_cookies_section"))
        self._lbl_cookies_browser.configure(text=t("yt_cookies_label"))
        self._btn_export_cookies.configure(text=t("yt_cookies_export_btn"))
        self._lbl_cookiefile.configure(text=t("yt_cookiefile_label"))
        self._on_cookiefile_change()
        self._lbl_outdir.configure(text=t("out_dir_label"))
        self._btn_browse.configure(text=t("browse"))
        self._btn_download.configure(text=t("yt_download_btn"))
        self._btn_cancel.configure(text=t("cancel_btn"))
        self.progress.refresh_lang()

    # ── Directorio de salida ──────────────────────────────────────────────────
    def _pick_outdir(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self.out_dir.set(d)

    # ── Validación de URL ─────────────────────────────────────────────────────
    def _is_youtube_url(self, url: str) -> bool:
        return (("youtube.com" in url or "youtu.be" in url)
                and ("watch" in url or "youtu.be/" in url))

    # ── Info del video ────────────────────────────────────────────────────────
    def _fetch_info(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(t("yt_warn_no_url_title"), t("yt_warn_no_url_msg"))
            return
        if not self._is_youtube_url(url):
            messagebox.showwarning(t("yt_warn_invalid_title"), t("yt_warn_invalid_msg"))
            return
        self._has_yt_info = False
        self.vid_title.configure(text=t("yt_fetching"), text_color=MUTED)
        self.vid_author.configure(text="")
        self.vid_stats.configure(text="")
        self.thumb_lbl.configure(image=self._blank_thumb_img, text=t("yt_loading"))
        
        # Read StringVar values in main thread before spawning daemon
        cookiefile = self._cookies_file.get().strip()
        browser = self.browser_var.get()
        
        threading.Thread(target=self._do_fetch_info, args=(url, cookiefile, browser), daemon=True).start()

    def _do_fetch_info(self, url: str, cookiefile: str, browser: str) -> None:
        try:
            if not YT_DLP_OK:
                raise ImportError(t("yt_no_ytdlp"))
            opts = self._get_ydl_opts_base(cookiefile, browser)
            with _yt_dlp_module.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            mins, secs = divmod(int(info.get("duration", 0)), 60)
            title      = info.get("title", "—")
            channel    = info.get("channel", info.get("uploader", "—"))
            views      = f"{info.get('view_count', 0):,}"
            likes      = info.get("like_count")
            likes_str  = f"{likes:,}" if likes else "—"
            thumbs     = info.get("thumbnails") or []
            thumb_url  = info.get("thumbnail") or (thumbs[-1]["url"] if thumbs else "")
            stats_text = t("yt_views_str", mins=mins, secs=secs, views=views, likes=likes_str)

            self._has_yt_info = True
            _title = title; _chan = channel; _stats = stats_text
            self.after(0, lambda: self.vid_title.configure(text=_title, text_color=TEXT))
            self.after(0, lambda: self.vid_author.configure(
                text=f"👤  {_chan}", text_color=MUTED))
            self.after(0, lambda: self.vid_stats.configure(text=_stats, text_color=MUTED))

            if thumb_url:
                try:
                    req = urllib.request.Request(thumb_url,
                                                 headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        data = resp.read()
                    pil     = Image.open(io.BytesIO(data)).convert("RGB").resize(
                        (192, 108), Image.LANCZOS)
                    ctk_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(192, 108))
                    self._thumb_ref = ctk_img
                    self.after(0, lambda img=ctk_img:
                               self.thumb_lbl.configure(image=img, text=""))
                except Exception:
                    self.after(0, lambda: self.thumb_lbl.configure(
                        text=t("yt_no_thumb"), image=self._blank_thumb_img))
            else:
                self.after(0, lambda: self.thumb_lbl.configure(
                    text=t("yt_no_thumb"), image=self._blank_thumb_img))

        except Exception as e:
            self._has_yt_info = False
            _clean = _strip_ansi(str(e))
            self.after(0, lambda c=_clean:
                       self.vid_title.configure(text=f"✗ {c}", text_color=ERR))
            self.after(0, lambda: [w.configure(text="")
                                   for w in (self.vid_author, self.vid_stats)])
            self.after(0, lambda: self.thumb_lbl.configure(
                text=t("yt_no_thumb"), image=self._blank_thumb_img))

    # ── Descarga ──────────────────────────────────────────────────────────────
    def _start(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(t("yt_warn_no_url_title"), t("yt_warn_no_url_msg"))
            return
        if not self._is_youtube_url(url):
            messagebox.showwarning(t("yt_warn_invalid_title"), t("yt_warn_invalid_msg"))
            return
        self._cancel_flag.clear()
        self.log.clear()
        self.progress.reset()
        # Read StringVar values in the main thread before spawning daemon thread
        cookiefile = self._cookies_file.get().strip()
        browser    = self.browser_var.get()
        threading.Thread(target=self._download, args=(url, cookiefile, browser), daemon=True).start()

    def _download(self, url: str, cookiefile: str, browser: str) -> None:
        if not YT_DLP_OK:
            self._log(t("yt_no_ytdlp"))
            self._done_progress(False)
            return

        out_dir    = self.out_dir.get()
        fmt        = self.fmt_var.get()
        quality    = self.quality_var.get().replace("k", "")
        cookie_str = self._cookie_method_str()
        os.makedirs(out_dir, exist_ok=True)

        _hdr = f"▶ {url}\n  {fmt.upper()} @ {quality}k bps"
        if cookie_str:
            _hdr += f"  |  {cookie_str}"
        self._log(_hdr)
        self._set_progress(0.05, t("yt_connecting"))

        cancel = self._cancel_flag

        def on_progress(d):
            if cancel.is_set():
                raise Exception(t("yt_cancelled"))
            if d.get("status") == "downloading":
                raw = d.get("_percent_str", "0%").strip().replace("%", "")
                try:
                    pct = float(raw) / 100
                    _spd = d.get("_speed_str", "").strip()
                    _eta = d.get("_eta_str", "").strip()
                    self.after(0, lambda p=pct, r=raw, s=_spd, e=_eta:
                               self.progress.set(p, f"{r}% | {s} | ETA {e}"))
                except ValueError:
                    pass
            elif d.get("status") == "finished":
                if not cancel.is_set():
                    self._set_progress(0.9, t("yt_converting"))
                    self._log(t("yt_audio_ready"))

        opts = self._get_ydl_opts_base(cookiefile, browser)
        opts.update({
            "format":         "bestaudio/best",
            "outtmpl":        os.path.join(out_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [on_progress],
            "postprocessors": [{
                "key":              "FFmpegExtractAudio",
                "preferredcodec":   fmt,
                "preferredquality": quality,
            }],
        })

        try:
            with _yt_dlp_module.YoutubeDL(opts) as ydl:
                ydl.download([url])
            if self._cancel_flag.is_set():
                self._log(t("yt_cancelled"))
                self.after(0, lambda: self.progress.reset())
            else:
                self._done_progress(True)
                _out = out_dir
                self._log(t("yt_saved", out_dir=_out))
        except Exception as e:
            if self._cancel_flag.is_set():
                self._log(t("yt_cancelled"))
                self.after(0, lambda: self.progress.reset())
            else:
                _clean = _strip_ansi(str(e))
                self._done_progress(False)
                self._log(f"\n✗ {_clean}")

    def _cancel(self) -> None:
        self._cancel_flag.set()
        self._log(t("yt_cancelling"))

    def __del__(self):
        """Limpia el archivo temporal de cookies al destruir la instancia."""
        self._cleanup_tmp_cookie()
    
    def _cleanup_tmp_cookie(self) -> None:
        """Removes temporary cookie file if it exists."""
        try:
            if hasattr(self, '_tmp_cookie_file') and self._tmp_cookie_file and os.path.isfile(self._tmp_cookie_file):
                try:
                    os.unlink(self._tmp_cookie_file)
                except Exception:
                    pass
        except Exception:
            pass
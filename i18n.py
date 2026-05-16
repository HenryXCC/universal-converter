"""
Internationalization system (i18n).
Supports Spanish (es) and English (en).
"""

_STRINGS: dict[str, dict[str, str]] = {
    # ESPAÑOL 
    "es": {
        # App / ventana principal
        "app_title":        "Convertidor de Formatos Universal",
        "app_header":       "CONVERTIDOR UNIVERSAL",
        "app_subtitle":     "Imagen · Video · YouTube Audio",
        "text_size_label":  "  Texto:",
        "local_proc":       "Procesamiento local",
        "about_btn":        "ℹ Acerca de",
        "lang_btn":         "EN 🌐",
        "footer_deps":      "Pillow · FFmpeg · yt-dlp",

        # Acerca de
        "about_title": "Acerca de Convertidor Universal",
        "about_text": (
            "Convertidor Universal v1.4\n\n"
            "Herramienta para conversión de imágenes, videos\n"
            "y descarga de audio de YouTube.\n\n"
            "Dependencias:\n"
            "• Pillow (imágenes)\n"
            "• FFmpeg / FFprobe (video)\n"
            "• yt-dlp (YouTube)\n"
            "• customtkinter + tkinterdnd2 (UI + Drag & Drop)\n\n"
            "Todo el procesamiento se realiza localmente.\n"
            "Desarrollado como proyecto de portafolio."
        ),

        # Pestañas
        "tab_image":   "🖼  Imagen",
        "tab_video":   "🎬  Video",
        "tab_youtube": "▶  YouTube",

        # Compartidos
        "browse":           "📁 Examinar",
        "out_dir_label":    "Carpeta de salida:",
        "cancel_btn":       "⏹ Cancelar",
        "options_section":  "▸ OPCIONES",

        # ProgressCard
        "progress_ready":     "Listo",
        "progress_completed": "✓ Completado",
        "progress_error":     "✗ Error",

        # Pestaña Imagen 
        "img_title":          "CONVERTIDOR DE IMÁGENES",
        "img_subtitle":       "Convierte múltiples imágenes a distintos formatos",
        "img_format_label":   "Formato destino:",
        "img_quality_label":  "Calidad (JPEG/WebP):",
        "img_input_section":  "▸ ARCHIVOS DE ENTRADA",
        "img_add_btn":        "+ Agregar Imágenes",
        "img_clear_btn":      "✕ Limpiar lista",
        "img_no_files":       "No hay archivos seleccionados…",
        "img_gif_section":    "▸ GIF BUILDER — ordena los frames",
        "img_clear_all_btn":  "✕ Limpiar todo",
        "img_gif_hint":       "Agrega imágenes para construir el GIF.\nCada imagen será un frame.",
        "img_preview_label":  "VISTA PREVIA",
        "img_no_images":      "Sin imágenes",
        "img_frame_dur":      "Duración por frame:",
        "img_loop_check":     "Repetir (loop infinito)",
        "img_convert_btn":    "⚡  CONVERTIR IMÁGENES",

         # diálogos
        "img_pick_title":     "Seleccionar imágenes",
        "img_filetypes":      "Imágenes",
        "img_wrong_fmt_title":"Formato no permitido",
        "img_wrong_fmt_msg":  "No puedes convertir {fmt} a {fmt}. Ignorados: {files}",
        "img_filetypes_excl": "Imágenes (sin {fmt})",
        "img_warn_title":     "Sin archivos",
        "img_warn_msg":       "Agrega al menos una imagen.",

        # mensajes en log
        "img_processing":     "Procesando {cur}/{total}: {stem}",
        "img_gif_loading":    "Cargando frame {cur}/{total}…",
        "img_gif_saving":     "Guardando GIF…",
        "img_gif_building":   "▶ Creando GIF animado con {n} frames…",
        "img_gif_no_imgs":    "✗ No se pudo cargar ninguna imagen.",
        "img_gif_frame_err":  "  ✗ frame {i}: {e}",
        "img_gif_done":       "\n✓ {n} frames · {ms}ms/frame → {dest} ({mb:.2f} MB)",
        "img_summary_ok":     "\n✓ {ok}/{total} convertidas → {out_dir}",
        "img_summary_warn":   "\n⚠ {ok}/{total} convertidas → {out_dir}",
         "img_frames_total":   "{n} frames · {secs:.1f}s total",
         "img_frames_zero":    "0 frames",

         # Pestaña Video
        "vid_title":          "CONVERTIDOR DE VIDEO",
        "vid_subtitle":       "Convierte o extrae audio de archivos de video locales",
        "vid_input_section":  "▸ VIDEO DE ENTRADA",
        "vid_add_btn":        "+ Seleccionar Video(s)",
        "vid_no_file":        "Ningún archivo seleccionado",
        "vid_info_section":   "▸ INFORMACIÓN",
        "vid_info_hint":      "Selecciona un video para ver su información.",
        "vid_gif_fps_label":  "GIF FPS:",
        "vid_fps_auto_hint":  "💡 Selecciona un video para obtener una recomendación automática.",
        "vid_convert_btn":    "⚡  CONVERTIR VIDEO(S)",

         # diálogos
        "vid_pick_title":     "Seleccionar video(s)",
        "vid_filetypes":      "Video",
        "vid_wrong_fmt_title":"Formato incorrecto",
        "vid_wrong_fmt_msg":  "Solo se aceptan archivos {ext}. Ignorados: {files}",
        "vid_warn_title":     "Sin video",
        "vid_warn_msg":       "Selecciona al menos un archivo de video.",

        # mensajes en log / UI
        "vid_files_selected": "{n} archivos seleccionados",
        "vid_cancelling":     "⏹ Cancelando…",
        "vid_cancelled":      "⏹ Cancelado.",
        "vid_done":           "\nProceso finalizado → {out_dir}",
        "vid_processing":     "Procesando {cur}/{total}...",

        # hint de FPS con video cargado
        "vid_fps_hint_src": (
            "📹 Video fuente: {src_fps:.3f} FPS  →  Recomendado: {rec} FPS  (actual: {fps})\n"
            "↑ Más FPS = más fluido, GIF más pesado.  "
            "↓ Menos FPS = GIF más liviano, más entrecortado.\n"
            "Con {fps} FPS: {fl}, {sz}."
        ),
        "vid_fps_fluency_high": "muy fluido",
        "vid_fps_fluency_mid":  "fluido",
        "vid_fps_fluency_low":  "algo entrecortado",
        "vid_fps_size_high":    "GIF grande",
        "vid_fps_size_mid":     "tamaño moderado",
        "vid_fps_size_low":     "GIF liviano",
        "vid_fps_hint_general": (
            "💡 ¿Cuántos FPS elegir?\n"
            "↑ Más FPS = GIF más fluido pero más pesado.  "
            "↓ Menos FPS = GIF más liviano pero más entrecortado.\n"
            "Regla general: usa la mitad de los FPS del video original."
        ),

        # info de video probeado
        "vid_probe_err":      "⚠ No se pudo leer: {e}",

        # Pestaña YouTube 
        "yt_title":           "EXTRACTOR DE AUDIO YOUTUBE",
        "yt_subtitle":        "Descarga y extrae el audio de cualquier video de YouTube",
        "yt_url_section":     "▸ URL DEL VIDEO",
        "yt_info_section":    "▸ INFORMACIÓN DEL VIDEO",
        "yt_no_thumb":        "Sin miniatura",
        "yt_preview_hint":    "Pega una URL y haz clic en 🔍 Info para previsualizar.",
        "yt_format_label":    "Formato:",
        "yt_quality_label":   "Calidad:",
        "yt_download_btn":    "⬇  DESCARGAR AUDIO",

        # diálogos
        "yt_warn_no_url_title":  "Sin URL",
        "yt_warn_no_url_msg":    "Pega una URL de YouTube primero.",
        "yt_warn_invalid_title": "URL inválida",
        "yt_warn_invalid_msg":   "Por favor ingresa una URL válida de YouTube.",

        # mensajes en log / UI
        "yt_fetching":        "🔄 Obteniendo información…",
        "yt_loading":         "Cargando…",
        "yt_no_ytdlp":        "✗ yt-dlp no está instalado. Ejecuta: pip install yt-dlp",
        "yt_connecting":      "Conectando…",
        "yt_converting":      "Convirtiendo…",
        "yt_audio_ready":     "  Descarga lista, procesando audio…",
        "yt_cancelled":       "⏹ Descarga cancelada.",
        "yt_saved":           "\n✓ Guardado en: {out_dir}",
        "yt_cancelling":      "⏹ Cancelando… (puede tardar unos segundos)",
        "yt_views_str":       "⏱  {mins}:{secs:02d}     👁  {views} vistas     👍  {likes}",

        # Cookies
        "yt_cookies_section":          "🍪 AUTENTICACIÓN (necesaria si YouTube bloquea)",
        "yt_cookies_label":            "Exportar cookies del navegador:",
        "yt_cookies_export_btn":       "⬇ Exportar cookies ahora",
        "yt_cookies_export_hint":      "Selecciona tu navegador y haz clic para exportar las cookies de YouTube automáticamente.",
        "yt_cookies_exporting":        "Exportando cookies de {browser}…",
        "yt_cookies_export_ok":        "✓ Cookies de {browser} exportadas — listas para usar.",
        "yt_cookies_no_browser_title": "Sin navegador",
        "yt_cookies_no_browser_msg":   "Selecciona un navegador antes de exportar.",
        "yt_cookies_db_not_found":     "No se encontró la base de datos de cookies de {browser}.",
        "yt_cookies_copy_err":         "No se pudo copiar la BD de cookies: {e}",
        "yt_cookies_read_err":         "No se pudo leer la BD de cookies: {e}",
        "yt_cookies_empty":            "No se encontraron cookies de YouTube en {browser}.",
        "yt_cookies_write_err":        "No se pudo escribir el archivo de cookies: {e}",
        "yt_cookiefile_label":         "O usar archivo cookies.txt manual:",
        "yt_cookiefile_hint":          "Selecciona un archivo cookies.txt en formato Netscape.",
        "yt_cookiefile_pick_title":    "Seleccionar archivo cookies.txt",
    },

    # ENGLISH 
    "en": {
        # App / main window
        "app_title":        "Universal Format Converter",
        "app_header":       "UNIVERSAL CONVERTER",
        "app_subtitle":     "Image · Video · YouTube Audio",
        "text_size_label":  "  Text:",
        "local_proc":       "Local processing",
        "about_btn":        "ℹ About",
        "lang_btn":         "ES 🌐",
        "footer_deps":      "Pillow · FFmpeg · yt-dlp",

        # About
        "about_title": "About Universal Converter",
        "about_text": (
            "Universal Converter v1.4\n\n"
            "Tool for converting images, videos\n"
            "and downloading audio from YouTube.\n\n"
            "Dependencies:\n"
            "• Pillow (images)\n"
            "• FFmpeg / FFprobe (video)\n"
            "• yt-dlp (YouTube)\n"
            "• customtkinter + tkinterdnd2 (UI + Drag & Drop)\n\n"
            "All processing is done locally.\n"
            "Developed as a portfolio project."
        ),

        # Tabs
        "tab_image":   "🖼  Image",
        "tab_video":   "🎬  Video",
        "tab_youtube": "▶  YouTube",

        # Shared
        "browse":           "📁 Browse",
        "out_dir_label":    "Output folder:",
        "cancel_btn":       "⏹ Cancel",
        "options_section":  "▸ OPTIONS",

        # ProgressCard
        "progress_ready":     "Ready",
        "progress_completed": "✓ Completed",
        "progress_error":     "✗ Error",

        # Image Tab 
        "img_title":          "IMAGE CONVERTER",
        "img_subtitle":       "Convert multiple images to different formats",
        "img_format_label":   "Target format:",
        "img_quality_label":  "Quality (JPEG/WebP):",
        "img_input_section":  "▸ INPUT FILES",
        "img_add_btn":        "+ Add Images",
        "img_clear_btn":      "✕ Clear list",
        "img_no_files":       "No files selected…",
        "img_gif_section":    "▸ GIF BUILDER — arrange frames",
        "img_clear_all_btn":  "✕ Clear all",
        "img_gif_hint":       "Add images to build the GIF.\nEach image will be a frame.",
        "img_preview_label":  "PREVIEW",
        "img_no_images":      "No images",
        "img_frame_dur":      "Frame duration:",
        "img_loop_check":     "Repeat (infinite loop)",
        "img_convert_btn":    "⚡  CONVERT IMAGES",

         # dialogs
        "img_pick_title":     "Select images",
        "img_filetypes":      "Images",
        "img_wrong_fmt_title":"Format not allowed",
        "img_wrong_fmt_msg":  "Cannot convert {fmt} to {fmt}. Skipped: {files}",
        "img_filetypes_excl": "Images (no {fmt})",
        "img_warn_title":     "No files",
        "img_warn_msg":       "Add at least one image.",

        # log messages
        "img_processing":     "Processing {cur}/{total}: {stem}",
        "img_gif_loading":    "Loading frame {cur}/{total}…",
        "img_gif_saving":     "Saving GIF…",
        "img_gif_building":   "▶ Creating animated GIF with {n} frames…",
        "img_gif_no_imgs":    "✗ Could not load any image.",
        "img_gif_frame_err":  "  ✗ frame {i}: {e}",
        "img_gif_done":       "\n✓ {n} frames · {ms}ms/frame → {dest} ({mb:.2f} MB)",
        "img_summary_ok":     "\n✓ {ok}/{total} converted → {out_dir}",
        "img_summary_warn":   "\n⚠ {ok}/{total} converted → {out_dir}",
         "img_frames_total":   "{n} frames · {secs:.1f}s total",
         "img_frames_zero":    "0 frames",

         # Video Tab
        "vid_title":          "VIDEO CONVERTER",
        "vid_subtitle":       "Convert or extract audio from local video files",
        "vid_input_section":  "▸ INPUT VIDEO",
        "vid_add_btn":        "+ Select Video(s)",
        "vid_no_file":        "No file selected",
        "vid_info_section":   "▸ INFORMATION",
        "vid_info_hint":      "Select a video to see its information.",
        "vid_gif_fps_label":  "GIF FPS:",
        "vid_fps_auto_hint":  "💡 Select a video to get an automatic recommendation.",
        "vid_convert_btn":    "⚡  CONVERT VIDEO(S)",

         # dialogs
        "vid_pick_title":     "Select video(s)",
        "vid_filetypes":      "Video",
        "vid_wrong_fmt_title":"Wrong format",
        "vid_wrong_fmt_msg":  "Only {ext} files accepted. Skipped: {files}",
        "vid_warn_title":     "No video",
        "vid_warn_msg":       "Select at least one video file.",

        # log / UI messages
        "vid_files_selected": "{n} files selected",
        "vid_cancelling":     "⏹ Cancelling…",
        "vid_cancelled":      "⏹ Cancelled.",
        "vid_done":           "\nProcess finished → {out_dir}",
        "vid_processing":     "Processing {cur}/{total}...",

        # FPS hint with loaded video
        "vid_fps_hint_src": (
            "📹 Source video: {src_fps:.3f} FPS  →  Recommended: {rec} FPS  (current: {fps})\n"
            "↑ More FPS = smoother, heavier GIF.  "
            "↓ Less FPS = lighter, choppier GIF.\n"
            "With {fps} FPS: {fl}, {sz}."
        ),
        "vid_fps_fluency_high": "very smooth",
        "vid_fps_fluency_mid":  "smooth",
        "vid_fps_fluency_low":  "somewhat choppy",
        "vid_fps_size_high":    "large GIF",
        "vid_fps_size_mid":     "moderate size",
        "vid_fps_size_low":     "light GIF",
        "vid_fps_hint_general": (
            "💡 How many FPS to choose?\n"
            "↑ More FPS = smoother GIF but heavier.  "
            "↓ Less FPS = lighter GIF but choppier.\n"
            "General rule: use half the FPS of the original video."
        ),

        # probed video info
        "vid_probe_err":      "⚠ Could not read: {e}",

        # YouTube Tab 
        "yt_title":           "YOUTUBE AUDIO EXTRACTOR",
        "yt_subtitle":        "Download and extract audio from any YouTube video",
        "yt_url_section":     "▸ VIDEO URL",
        "yt_info_section":    "▸ VIDEO INFORMATION",
        "yt_no_thumb":        "No thumbnail",
        "yt_preview_hint":    "Paste a URL and click 🔍 Info to preview.",
        "yt_format_label":    "Format:",
        "yt_quality_label":   "Quality:",
        "yt_download_btn":    "⬇  DOWNLOAD AUDIO",

        # dialogs
        "yt_warn_no_url_title":  "No URL",
        "yt_warn_no_url_msg":    "Paste a YouTube URL first.",
        "yt_warn_invalid_title": "Invalid URL",
        "yt_warn_invalid_msg":   "Please enter a valid YouTube URL.",

        # log / UI messages
        "yt_fetching":        "🔄 Fetching information…",
        "yt_loading":         "Loading…",
        "yt_no_ytdlp":        "✗ yt-dlp is not installed. Run: pip install yt-dlp",
        "yt_connecting":      "Connecting…",
        "yt_converting":      "Converting…",
        "yt_audio_ready":     "  Download ready, processing audio…",
        "yt_cancelled":       "⏹ Download cancelled.",
        "yt_saved":           "\n✓ Saved to: {out_dir}",
        "yt_cancelling":      "⏹ Cancelling… (may take a few seconds)",
        "yt_views_str":       "⏱  {mins}:{secs:02d}     👁  {views} views     👍  {likes}",

        # Cookies
        "yt_cookies_section":          "🍪 AUTHENTICATION (required if YouTube blocks)",
        "yt_cookies_label":            "Export browser cookies:",
        "yt_cookies_export_btn":       "⬇ Export cookies now",
        "yt_cookies_export_hint":      "Select your browser and click to automatically export your YouTube cookies.",
        "yt_cookies_exporting":        "Exporting cookies from {browser}…",
        "yt_cookies_export_ok":        "✓ {browser} cookies exported — ready to use.",
        "yt_cookies_no_browser_title": "No browser selected",
        "yt_cookies_no_browser_msg":   "Select a browser before exporting.",
        "yt_cookies_db_not_found":     "Could not find {browser}'s cookie database.",
        "yt_cookies_copy_err":         "Could not copy cookie database: {e}",
        "yt_cookies_read_err":         "Could not read cookie database: {e}",
        "yt_cookies_empty":            "No YouTube cookies found in {browser}.",
        "yt_cookies_write_err":        "Could not write cookies file: {e}",
        "yt_cookiefile_label":         "Or use a manual cookies.txt file:",
        "yt_cookiefile_hint":          "Select a cookies.txt file in Netscape format.",
        "yt_cookiefile_pick_title":    "Select cookies.txt file",
    },
}

# Estado de idioma actual 
_current_lang: str = "es"


def set_lang(lang: str) -> None:
    global _current_lang
    if lang in _STRINGS:
        _current_lang = lang


def get_lang() -> str:
    return _current_lang


def t(key: str, **kwargs) -> str:
    """Devuelve la cadena traducida al idioma activo.
    Acepta kwargs para formatear la cadena con str.format().
    """
    s = _STRINGS.get(_current_lang, _STRINGS["es"]).get(key, key)
    if kwargs:
        try:
            s = s.format(**kwargs)
        except Exception:
            pass
    return s
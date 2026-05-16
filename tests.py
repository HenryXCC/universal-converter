"""
tests.py — Test Suite for Universal Converter
Run:
python -m pytest tests.py -v
# or with unittest:
python -m unittest tests.py -v
Requirements to run the tests:
pip install pytest pillow
FFmpeg in the PATH for video tests (skipped if not available)
"""

import io
import os
import re
import shutil
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

# Mock GUI dependencies before importing project modules
# This allows testing logic without needing a real screen or tkinter.

# customtkinter: base classes must be real classes (not MagicMock)
# to avoid metaclass conflicts when defining App(*_AppBases).
class _FakeCTk: pass
class _FakeCTkFrame: pass

_ctk_mock = MagicMock()
_ctk_mock.CTk          = _FakeCTk
_ctk_mock.CTkFrame     = _FakeCTkFrame
_ctk_mock.StringVar    = MagicMock
_ctk_mock.IntVar       = MagicMock
_ctk_mock.BooleanVar   = MagicMock

# tkinterdnd2: both TkinterDnD and DnDWrapper must be real classes
class _FakeDnDWrapper: pass
class _FakeTkinterDnD:
    DnDWrapper = _FakeDnDWrapper
    @staticmethod
    def _require(widget): return "1.0"

_dnd_mock = MagicMock()
_dnd_mock.DND_FILES  = "DND_FILES"
_dnd_mock.TkinterDnD = _FakeTkinterDnD

# FIX Bug 4 tests: PIL is imported at module level in youtube_tab.py.
# Strategy: Try to import PIL normally first. Only mock it if not installed.
# This allows tests to use real PIL while still handling missing Pillow gracefully.
_pil_mock = None
_pil_image_mock = None

try:
    # Try to import real PIL to see if it's available
    import PIL
    import PIL.Image as PILImage
    # If successful, don't mock - use real PIL
except ImportError:
    # If PIL is not installed, create mocks so youtube_tab.py can still be imported
    _pil_mock = MagicMock()
    _pil_image_mock = MagicMock()

# Only add to sys.modules if we created mocks (PIL not installed)
if _pil_mock is not None:
    sys.modules.setdefault("PIL",                 _pil_mock)
    sys.modules.setdefault("PIL.Image",           _pil_image_mock)

# Always mock these GUI dependencies (no real tkinter in test environment)
sys.modules.setdefault("customtkinter",       _ctk_mock)
sys.modules.setdefault("tkinterdnd2",         _dnd_mock)
sys.modules.setdefault("tkinter",             MagicMock())
sys.modules.setdefault("tkinter.filedialog",  MagicMock())
sys.modules.setdefault("tkinter.messagebox",  MagicMock())

# FIX Bug 1 tests: main.py does not exist — functions were moved to
# utils.py, config.py and tabs/youtube_tab.py during refactoring.
# Import directly from the correct modules.
from utils import smart_gif_fps, probe_video, run_ffmpeg  # noqa: E402
from config import _find_ffmpeg_bins                       # noqa: E402
from tabs.youtube_tab import YouTubeTab                    # noqa: E402
from tabs.image_tab import ImageTab                        # noqa: E402


class TestSmartGifFps(unittest.TestCase):
    """Tests for smart_gif_fps — FPS recommendation for GIFs."""

    def test_fps_estandar_24(self):
        """A video at 24 FPS should recommend 12 (half)."""
        self.assertEqual(smart_gif_fps(24.0), 12)

    def test_fps_estandar_30(self):
        """A video at 30 FPS should recommend 15."""
        self.assertEqual(smart_gif_fps(30.0), 15)

    def test_fps_estandar_60(self):
        """A video at 60 FPS should recommend the maximum of 20."""
        self.assertEqual(smart_gif_fps(60.0), 20)

    def test_fps_muy_bajo(self):
        """A video at 5 FPS or less should recommend 5 as minimum."""
        self.assertEqual(smart_gif_fps(5.0), 5)

    def test_fps_cero_o_invalido(self):
        """With invalid FPS (0 or negative) should return 12 as fallback."""
        self.assertEqual(smart_gif_fps(0.0),  12)
        self.assertEqual(smart_gif_fps(-1.0), 12)

    def test_fps_fraccionario(self):
        """FPS like 23.976 (NTSC) should be handled correctly."""
        resultado = smart_gif_fps(23.976)
        self.assertIn(resultado, [5, 8, 10, 12, 15, 18, 20])

    def test_resultado_siempre_en_lista_valida(self):
        """All results must be in the allowed values."""
        valores_validos = {5, 8, 10, 12, 15, 18, 20}
        for fps in [1, 5, 10, 15, 24, 25, 30, 50, 60, 120]:
            with self.subTest(fps=fps):
                self.assertIn(smart_gif_fps(float(fps)), valores_validos)


class TestDropPathParsing(unittest.TestCase):
    """Tests for parsing paths from Drag & Drop events."""

    # Same regex used in _on_drop
    _PATTERN = re.compile(r'\{[^}]+\}|\S+')

    def _parse(self, raw: str) -> list[str]:
        paths = self._PATTERN.findall(raw)
        return [p.strip('{}') for p in paths]

    def test_ruta_simple_sin_espacios(self):
        raw = r"C:\Users\user\foto.png"
        self.assertEqual(self._parse(raw), [r"C:\Users\user\foto.png"])

    def test_ruta_con_espacios_entre_llaves(self):
        raw = r"{C:\Users\Mi Usuario\Mi Foto.png}"
        self.assertEqual(self._parse(raw), [r"C:\Users\Mi Usuario\Mi Foto.png"])

    def test_multiples_rutas_sin_espacios(self):
        raw = r"C:\a\foto1.png C:\b\foto2.jpg"
        self.assertEqual(self._parse(raw), [r"C:\a\foto1.png", r"C:\b\foto2.jpg"])

    def test_multiples_rutas_mixtas(self):
        """Mix of paths with and without spaces."""
        raw = r"{C:\Mis Documentos\foto.png} C:\simple\video.mp4"
        resultado = self._parse(raw)
        self.assertEqual(resultado[0], r"C:\Mis Documentos\foto.png")
        self.assertEqual(resultado[1], r"C:\simple\video.mp4")

    def test_ruta_linux(self):
        raw = "/home/user/images/photo.jpg"
        self.assertEqual(self._parse(raw), ["/home/user/images/photo.jpg"])

    def test_datos_vacios(self):
        self.assertEqual(self._parse(""), [])


class TestYouTubeUrlValidation(unittest.TestCase):
    """Tests for YouTubeTab._is_youtube_url."""

    def setUp(self):
        # Instantiate without GUI using a mock master
        master = MagicMock()
        master.winfo_exists = MagicMock(return_value=True)
        self.tab = object.__new__(YouTubeTab)
        # Attach the method directly without going through __init__
        self.tab._is_youtube_url = YouTubeTab._is_youtube_url.__get__(self.tab)

    def test_url_watch_valida(self):
        self.assertTrue(self.tab._is_youtube_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ))

    def test_url_youtu_be_valida(self):
        self.assertTrue(self.tab._is_youtube_url(
            "https://youtu.be/dQw4w9WgXcQ"
        ))

    def test_url_con_parametros_extra(self):
        self.assertTrue(self.tab._is_youtube_url(
            "https://www.youtube.com/watch?v=abc123&t=30s&list=PLxxx"
        ))

    def test_url_no_youtube(self):
        self.assertFalse(self.tab._is_youtube_url("https://vimeo.com/123456"))

    def test_url_youtube_sin_watch(self):
        """URL of channel or playlist without /watch is not valid for download."""
        self.assertFalse(self.tab._is_youtube_url(
            "https://www.youtube.com/channel/UCxxx"
        ))

    def test_cadena_vacia(self):
        self.assertFalse(self.tab._is_youtube_url(""))

    def test_texto_sin_url(self):
        self.assertFalse(self.tab._is_youtube_url("esto no es una url"))


class TestImageAllowedExts(unittest.TestCase):
    """Tests for ImageTab._allowed_exts — source extensions filtering."""

    def setUp(self):
        self.tab = object.__new__(ImageTab)
        self.tab.fmt_var = MagicMock()

    def _check(self, fmt: str, expected_in: list[str], expected_out: list[str]):
        self.tab.fmt_var.get.return_value = fmt
        exts = self.tab._allowed_exts()
        for ext in expected_in:
            self.assertIn(ext, exts)
        for ext in expected_out:
            self.assertNotIn(ext, exts)

    def test_png_excluye_png(self):
        self._check("PNG", [".jpg", ".webp", ".bmp"], [".png"])

    def test_jpeg_excluye_jpg_jpeg(self):
        self._check("JPEG", [".png", ".webp"], [".jpg", ".jpeg"])

    def test_gif_excluye_gif(self):
        self._check("GIF", [".png", ".jpg"], [".gif"])

    def test_webp_excluye_webp(self):
        self._check("WebP", [".png", ".jpg"], [".webp"])

    def test_bmp_excluye_bmp(self):
        self._check("BMP", [".png", ".jpg"], [".bmp"])

    def test_tiff_excluye_tif_tiff(self):
        self._check("TIFF", [".png", ".jpg"], [".tif", ".tiff"])

    def test_ico_excluye_ico(self):
        self._check("ICO", [".png", ".jpg"], [".ico"])


class TestImageConversion(unittest.TestCase):
    """Image conversion tests using temporary files."""

    @classmethod
    def setUpClass(cls):
        try:
            from PIL import Image
            cls.Image = Image
        except ImportError:
            cls.Image = None
        cls.tmp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _skip_if_no_pillow(self):
        if self.Image is None:
            self.skipTest("Pillow is not installed")

    def _make_png(self, name="test.png", mode="RGB", size=(100, 100), color=(255, 100, 50)):
        """Creates a temporary PNG image and returns its path."""
        img = self.Image.new(mode, size, color)
        path = os.path.join(self.tmp_dir, name)
        img.save(path, "PNG")
        return path

    def test_png_a_webp(self):
        self._skip_if_no_pillow()
        src  = self._make_png("origen.png")
        dest = os.path.join(self.tmp_dir, "salida.webp")
        img  = self.Image.open(src)
        img.save(dest, "WEBP", quality=85)
        self.assertTrue(os.path.exists(dest))
        out = self.Image.open(dest)
        self.assertEqual(out.format, "WEBP")

    def test_png_a_jpeg(self):
        self._skip_if_no_pillow()
        src  = self._make_png("origen_jpg.png")
        dest = os.path.join(self.tmp_dir, "salida.jpg")
        img  = self.Image.open(src).convert("RGB")
        img.save(dest, "JPEG", quality=90)
        self.assertTrue(os.path.exists(dest))
        out = self.Image.open(dest)
        self.assertEqual(out.format, "JPEG")

    def test_png_a_bmp(self):
        self._skip_if_no_pillow()
        src  = self._make_png("origen_bmp.png")
        dest = os.path.join(self.tmp_dir, "salida.bmp")
        img  = self.Image.open(src)
        img.save(dest, "BMP")
        self.assertTrue(os.path.exists(dest))

    def test_png_a_ico(self):
        self._skip_if_no_pillow()
        src  = self._make_png("origen_ico.png", size=(64, 64))
        dest = os.path.join(self.tmp_dir, "salida.ico")
        img  = self.Image.open(src)
        img.save(dest, "ICO")
        self.assertTrue(os.path.exists(dest))

    # RGBA -> RGB conversion for JPEG

    def test_rgba_a_jpeg_requiere_conversion(self):
        """JPEG does not support transparency: RGBA must be converted to RGB."""
        self._skip_if_no_pillow()
        src  = self._make_png("rgba.png", mode="RGBA", color=(100, 200, 50, 128))
        dest = os.path.join(self.tmp_dir, "rgba_salida.jpg")
        img  = self.Image.open(src)
        self.assertEqual(img.mode, "RGBA")
        img_rgb = img.convert("RGB")
        img_rgb.save(dest, "JPEG", quality=85)
        self.assertTrue(os.path.exists(dest))

    def test_jpeg_calidad_afecta_tamano(self):
        """Lower JPEG quality should produce a smaller file."""
        self._skip_if_no_pillow()
        src = self._make_png("calidad.png", size=(300, 300))
        img = self.Image.open(src).convert("RGB")

        dest_alta  = os.path.join(self.tmp_dir, "calidad_alta.jpg")
        dest_baja  = os.path.join(self.tmp_dir, "calidad_baja.jpg")
        img.save(dest_alta, "JPEG", quality=95)
        img.save(dest_baja, "JPEG", quality=10)

        self.assertGreater(os.path.getsize(dest_alta), os.path.getsize(dest_baja))

    def test_dimensiones_preservadas_en_conversion(self):
        """Original dimensions should remain after conversion."""
        self._skip_if_no_pillow()
        w, h = 320, 240
        src  = self._make_png("dims.png", size=(w, h))
        dest = os.path.join(self.tmp_dir, "dims_out.webp")
        img  = self.Image.open(src)
        img.save(dest, "WEBP")
        out  = self.Image.open(dest)
        self.assertEqual(out.size, (w, h))


class TestAnimatedGif(unittest.TestCase):
    """Tests for animated GIF creation."""

    @classmethod
    def setUpClass(cls):
        try:
            from PIL import Image
            cls.Image = Image
        except ImportError:
            cls.Image = None
        cls.tmp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _skip_if_no_pillow(self):
        if self.Image is None:
            self.skipTest("Pillow is not installed")

    def _make_frames(self, n=3) -> list:
        """Creates n images with different colors."""
        colores = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (0,255,255)]
        frames  = []
        for i in range(n):
            img = self.Image.new("RGB", (80, 80), colores[i % len(colores)])
            frames.append(img.convert("P", palette=self.Image.ADAPTIVE))
        return frames

    def test_gif_animado_se_crea(self):
        self._skip_if_no_pillow()
        frames = self._make_frames(3)
        dest   = os.path.join(self.tmp_dir, "test_anim.gif")
        frames[0].save(dest, format="GIF", save_all=True,
                       append_images=frames[1:], loop=0, duration=100)
        self.assertTrue(os.path.exists(dest))
        self.assertGreater(os.path.getsize(dest), 0)

    def test_gif_tiene_multiples_frames(self):
        self._skip_if_no_pillow()
        n_frames = 4
        frames   = self._make_frames(n_frames)
        dest     = os.path.join(self.tmp_dir, "multi_frame.gif")
        frames[0].save(dest, format="GIF", save_all=True,
                       append_images=frames[1:], loop=0, duration=150)
        gif = self.Image.open(dest)
        self.assertTrue(getattr(gif, "is_animated", False) or gif.n_frames > 1)
        self.assertEqual(gif.n_frames, n_frames)

    def test_gif_sin_loop_vs_con_loop(self):
        """loop=0 (infinite) and loop=1 (once) should generate valid files."""
        self._skip_if_no_pillow()
        frames     = self._make_frames(2)
        dest_loop  = os.path.join(self.tmp_dir, "loop_inf.gif")
        dest_once  = os.path.join(self.tmp_dir, "loop_once.gif")
        frames[0].save(dest_loop, format="GIF", save_all=True,
                       append_images=frames[1:], loop=0, duration=100)
        frames[0].save(dest_once, format="GIF", save_all=True,
                       append_images=frames[1:], loop=1, duration=100)
        self.assertTrue(os.path.exists(dest_loop))
        self.assertTrue(os.path.exists(dest_once))

    def test_gif_rgba_convertido_correctamente(self):
        """RGBA frames must be converted before saving as GIF."""
        self._skip_if_no_pillow()
        img_rgba = self.Image.new("RGBA", (60, 60), (255, 0, 0, 128))
        bg       = self.Image.new("RGB", img_rgba.size, (255, 255, 255))
        bg.paste(img_rgba.convert("RGBA"), mask=img_rgba.convert("RGBA").split()[-1])
        frame    = bg.convert("P", palette=self.Image.ADAPTIVE)
        dest     = os.path.join(self.tmp_dir, "rgba_gif.gif")
        frame.save(dest, format="GIF")
        self.assertTrue(os.path.exists(dest))


class TestFFmpegIntegracion(unittest.TestCase):
    """
    FFmpeg integration tests.
    Automatically skipped if FFmpeg is not installed.
    """

    @classmethod
    def setUpClass(cls):
        cls.ffmpeg_ok = shutil.which("ffmpeg") is not None
        cls.tmp_dir   = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def setUp(self):
        if not self.ffmpeg_ok:
            self.skipTest("FFmpeg is not in PATH — skipping video tests")

    def _make_test_video(self, filename="test.mp4", duration=2) -> str:
        """Generates a test video with lavfi (without source file)."""
        dest = os.path.join(self.tmp_dir, filename)
        cmd  = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=blue:size=160x120:rate=24:duration={duration}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-shortest", "-c:v", "libx264", "-c:a", "aac",
            dest
        ]
        import subprocess
        result = subprocess.run(cmd, capture_output=True)
        self.assertEqual(result.returncode, 0, "Could not create test video")
        return dest

    def test_probe_retorna_fps_correcto(self):
        video = self._make_test_video("probe_fps.mp4")
        info  = probe_video(video)
        self.assertAlmostEqual(info["fps"], 24.0, delta=0.1)

    def test_probe_retorna_duracion(self):
        video = self._make_test_video("probe_dur.mp4", duration=3)
        info  = probe_video(video)
        self.assertAlmostEqual(info["duration"], 3.0, delta=0.5)

    def test_probe_retorna_dimensiones(self):
        video = self._make_test_video("probe_dims.mp4")
        info  = probe_video(video)
        self.assertEqual(info["width"],  160)
        self.assertEqual(info["height"], 120)

    def test_probe_archivo_inexistente_lanza_excepcion(self):
        # FIX Bug 2 tests: probe_video no longer silently returns zeros;
        # now raises RuntimeError (or FFmpegNotFoundError if FFmpeg doesn't exist).
        # The caller (VideoTab._probe_file) is the one who catches the exception.
        with self.assertRaises(Exception):
            probe_video("/ruta/que/no/existe.mp4")

    def test_conversion_mp4_a_avi(self):
        src  = self._make_test_video("src_avi.mp4")
        dest = os.path.join(self.tmp_dir, "salida.avi")
        args = ["-i", src, "-c:v", "mpeg4", "-q:v", "4", dest]
        ok, _err = run_ffmpeg(args, duration=2.0)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(dest))

    def test_conversion_extrae_audio_mp3(self):
        src  = self._make_test_video("src_audio.mp4")
        dest = os.path.join(self.tmp_dir, "audio.mp3")
        args = ["-i", src, "-vn", "-acodec", "libmp3lame", dest]
        ok, _err = run_ffmpeg(args, duration=2.0)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(dest))

    def test_cancelacion_detiene_proceso(self):
        import threading
        src    = self._make_test_video("src_cancel.mp4", duration=5)
        dest   = os.path.join(self.tmp_dir, "cancelado.avi")
        cancel = threading.Event()
        cancel.set()   # cancel immediately
        ok, msg = run_ffmpeg(
            ["-i", src, "-c:v", "mpeg4", dest],
            duration=5.0,
            cancel_flag=cancel
        )
        self.assertFalse(ok)
        self.assertIn("Cancelled", msg)

    def test_args_invalidos_retornan_fallo(self):
        ok, err = run_ffmpeg(["-i", "archivo_inexistente.mp4", "salida.mp4"], duration=1.0)
        self.assertFalse(ok)
        self.assertIsInstance(err, str)


class TestFindFFmpegBins(unittest.TestCase):
    """Tests for FFmpeg binaries detection."""

    def test_retorna_tupla_de_dos_strings(self):
        ffmpeg, ffprobe = _find_ffmpeg_bins()
        self.assertIsInstance(ffmpeg,  str)
        self.assertIsInstance(ffprobe, str)

    def test_retorna_valor_aunque_no_exista(self):
        """If FFmpeg doesn't exist, should return 'ffmpeg' as fallback."""
        ffmpeg, ffprobe = _find_ffmpeg_bins()
        self.assertTrue(len(ffmpeg) > 0)
        self.assertTrue(len(ffprobe) > 0)

    def test_detecta_ffmpeg_si_esta_instalado(self):
        if shutil.which("ffmpeg"):
            ffmpeg, _ = _find_ffmpeg_bins()
            self.assertNotEqual(ffmpeg, "ffmpeg",
                "FFmpeg is in PATH but _find_ffmpeg_bins returned the fallback")


class TestArchivoCorrupto(unittest.TestCase):
    """
    Verifies that the program handles corrupt files without raising
    unhandled exceptions. A corrupt file is simulated by writing junk bytes
    with the extension of an image or video.
    """

    @classmethod
    def setUpClass(cls):
        try:
            from PIL import Image, UnidentifiedImageError
            cls.Image = Image
            cls.UnidentifiedImageError = UnidentifiedImageError
        except ImportError:
            cls.Image = None
        cls.tmp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _make_corrupto(self, nombre: str) -> str:
        """Creates a file with valid extension but garbage content."""
        path = os.path.join(self.tmp_dir, nombre)
        with open(path, "wb") as f:
            f.write(b"\x00\xFF\xAB\xCD\xEF" * 20)  # bytes that are not a valid image
        return path

    def test_pillow_lanza_excepcion_con_imagen_corrupta(self):
        """
        Pillow should raise an exception when opening a corrupt file.
        The program catches that exception and reports it to the user.
        """
        if self.Image is None:
            self.skipTest("Pillow is not installed")
        src = self._make_corrupto("corrupta.png")
        with self.assertRaises(Exception):
            self.Image.open(src).load()

    def test_conversion_imagen_corrupta_no_rompe_el_loop(self):
        """
        Simulates the conversion loop of ImageTab._convert:
        a corrupt file should log error and continue, not stop everything.
        """
        if self.Image is None:
            self.skipTest("Pillow is not installed")

        archivos    = [self._make_corrupto("c1.png"), self._make_corrupto("c2.png")]
        convertidos = 0
        errores     = 0

        for path in archivos:
            try:
                img = self.Image.open(path)
                img.load()
                convertidos += 1
            except Exception:
                errores += 1  # the program logs the error and continues

        self.assertEqual(errores,     2, "Both corrupt files should generate error")
        self.assertEqual(convertidos, 0, "No corrupt file should be converted")

    def test_probe_video_corrupto_lanza_excepcion(self):
        """
        FIX Bug 2 tests: probe_video no longer silently returns zeros for
        corrupt files; it now raises RuntimeError or FFmpegNotFoundError.
        Error handling is the responsibility of the caller (VideoTab._probe_file).
        """
        src = self._make_corrupto("corrupto.mp4")
        with self.assertRaises(Exception):
            probe_video(src)

    def test_ffmpeg_con_video_corrupto_retorna_fallo(self):
        """
        run_ffmpeg with a corrupt file should return (False, error_message)
        without raising an exception or hanging the process.
        """
        if not shutil.which("ffmpeg"):
            self.skipTest("FFmpeg is not in PATH")
        src  = self._make_corrupto("corrupto2.mp4")
        dest = os.path.join(self.tmp_dir, "salida_corrupta.avi")
        ok, err = run_ffmpeg(["-i", src, dest], duration=1.0)
        self.assertFalse(ok,              "Should return False with corrupt input")
        self.assertIsInstance(err, str,   "Should return an error message string")
        self.assertGreater(len(err), 0,   "Error message should not be empty")

class TestPermisosDenegados(unittest.TestCase):
    """
    Verifies that the program handles permission errors correctly,
    reporting the issue to the user without raising unhandled exceptions.
    Applies only on Linux/macOS — on Windows these tests are skipped.
    """

    @classmethod
    def setUpClass(cls):
        try:
            from PIL import Image
            cls.Image = Image
        except ImportError:
            cls.Image = None
        cls.tmp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        # Restore permissions before cleanup so rmtree works
        for f in os.listdir(cls.tmp_dir):
            try:
                os.chmod(os.path.join(cls.tmp_dir, f), 0o644)
            except Exception:
                pass
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def setUp(self):
        if os.name == "nt":
            self.skipTest("Permission tests not applicable on Windows")
        if os.getuid() == 0:
            self.skipTest("Permission tests not applicable when running as root")

    def test_lectura_imagen_sin_permiso_lanza_excepcion(self):
        """
        A read-protected image file should raise PermissionError
        which the program should catch and report.
        """
        if self.Image is None:
            self.skipTest("Pillow is not installed")

        # Create a valid image and remove read permissions
        img  = self.Image.new("RGB", (50, 50), (255, 0, 0))
        src  = os.path.join(self.tmp_dir, "sin_permiso.png")
        img.save(src)
        os.chmod(src, 0o000)

        with self.assertRaises(Exception):
            self.Image.open(src).load()

    def test_escritura_en_carpeta_sin_permiso_lanza_excepcion(self):
        """
        Trying to save to a folder without write permission
        should raise PermissionError which the program should catch and report.
        """
        if self.Image is None:
            self.skipTest("Pillow is not installed")

        # Create destination folder and remove write permissions
        out_dir = os.path.join(self.tmp_dir, "solo_lectura")
        os.makedirs(out_dir)
        img = self.Image.new("RGB", (50, 50), (0, 255, 0))
        os.chmod(out_dir, 0o444)

        dest = os.path.join(out_dir, "salida.png")
        with self.assertRaises(Exception):
            img.save(dest)

    def test_conversion_maneja_permiso_denegado_sin_romper_loop(self):
        """
        Simulates the conversion loop when no write permission is available:
        should log the error and not stop converting other files.
        """
        if self.Image is None:
            self.skipTest("Pillow is not installed")

        out_dir = os.path.join(self.tmp_dir, "solo_lectura2")
        os.makedirs(out_dir)
        img = self.Image.new("RGB", (50, 50), (0, 0, 255))
        os.chmod(out_dir, 0o444)

        errores = 0
        for nombre in ["a.webp", "b.webp"]:
            try:
                img.save(os.path.join(out_dir, nombre), "WEBP")
            except Exception:
                errores += 1

        self.assertEqual(errores, 2, "Both writes should fail due to permissions")

if __name__ == "__main__":
    unittest.main(verbosity=2)

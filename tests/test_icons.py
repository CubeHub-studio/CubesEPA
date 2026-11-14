import tempfile
import unittest
from pathlib import Path

from cubes_archive.icons import default_icon_path, png_to_ico, resolve_icon


class IconTests(unittest.TestCase):
    def test_bundled_fallback_icon_exists(self):
        self.assertTrue(default_icon_path().is_file())

    def test_custom_icon_takes_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            custom = root / "assets" / "icon.png"
            custom.parent.mkdir()
            custom.write_bytes(b"custom icon")
            self.assertEqual(resolve_icon(root), custom)

    def test_missing_custom_icon_uses_bundled_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(resolve_icon(Path(folder)), default_icon_path())

    def test_png_is_wrapped_as_ico(self):
        # Minimal PNG signature is sufficient for testing the ICO container helper.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            png = root / "icon.png"
            ico = root / "icon.ico"
            png.write_bytes(b"\\x89PNG\\r\\n\\x1a\\n" + b"test")
            png_to_ico(png, ico)
            data = ico.read_bytes()
            self.assertEqual(data[:6], b"\\x00\\x00\\x01\\x00\\x01\\x00")
            self.assertEqual(data[22:], png.read_bytes())


if __name__ == "__main__":
    unittest.main()

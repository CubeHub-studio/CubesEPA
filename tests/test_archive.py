import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from cubes_archive import __version__
from cubes_archive.cli import create_archive, load_manifest, verify_archive


class ArchiveTests(unittest.TestCase):
    def test_requirements_file_is_optional_and_compile_version_is_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "project"
            source.mkdir()
            (source / "main.py").write_text("print('hello')\n", encoding="utf-8")
            output = root / "test.epa"

            create_archive(source, output, "Test", "1.0.0", "Tests", "")

            with zipfile.ZipFile(output) as archive:
                manifest = load_manifest(archive)
                self.assertNotIn("requirements.txt", archive.namelist())
                self.assertEqual(manifest["cubesepa_version"], __version__)
                self.assertEqual(manifest["entrypoint"], "main.py")

            with patch("builtins.print"):
                verify_archive(output)


if __name__ == "__main__":
    unittest.main()

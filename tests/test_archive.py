import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from cubes_archive import __version__
from cubes_archive.cli import EPAError, create_archive, load_manifest, update_archive, verify_archive


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


    def test_update_archive_replaces_contents_and_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "project"
            source.mkdir()
            (source / "main.py").write_text("print('old')\\n", encoding="utf-8")
            output = root / "existing.epa"
            create_archive(source, output, "Existing App", "2.4.1", "Cubes, Studio", "Keep this description", True)
            (source / "main.py").write_text("print('new')\\n", encoding="utf-8")
            (source / "new_asset.txt").write_text("updated", encoding="utf-8")

            update_archive(output, source)

            with zipfile.ZipFile(output) as archive:
                manifest = load_manifest(archive)
                self.assertEqual(manifest["name"], "Existing App")
                self.assertEqual(manifest["version"], "2.4.1")
                self.assertEqual(manifest["publisher"], "Cubes, Studio")
                self.assertEqual(manifest["description"], "Keep this description")
                self.assertIs(manifest["require_admin"], True)
                self.assertEqual(archive.read("main.py"), b"print('new')\\n")
                self.assertEqual(archive.read("new_asset.txt"), b"updated")

    def test_require_admin_flag_is_written_to_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "project"
            source.mkdir()
            (source / "main.py").write_text("print('hello')\n", encoding="utf-8")
            output = root / "admin.epa"

            create_archive(source, output, "Admin Test", "1.0.0", "Tests", "", True)

            with zipfile.ZipFile(output) as archive:
                manifest = load_manifest(archive)
                self.assertIs(manifest["require_admin"], True)

    def test_require_admin_must_be_boolean(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive_path = root / "invalid.epa"
            manifest = {
                "format": "EPA",
                "format_version": 1,
                "name": "Invalid",
                "version": "1.0.0",
                "publisher": "Tests",
                "entrypoint": "main.py",
                "require_admin": "yes",
            }
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("epa.json", json.dumps(manifest))
                archive.writestr("main.py", "pass\n")

            with zipfile.ZipFile(archive_path) as archive:
                with self.assertRaisesRegex(EPAError, "require_admin.*boolean"):
                    load_manifest(archive)


if __name__ == "__main__":
    unittest.main()

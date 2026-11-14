import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cubes_archive import launcher


class LauncherTests(unittest.TestCase):
    def test_missing_entrypoint_shows_error_instead_of_silent_exit(self):
        with patch.object(sys, "argv", ["launcher", "missing-main.py"]), \
             patch.object(launcher, "_write_crash_log", return_value=None), \
             patch.object(launcher, "_show_launch_error") as show_error:
            result = launcher.main()

        self.assertEqual(result, 1)
        show_error.assert_called_once()
        self.assertIn("FileNotFoundError", show_error.call_args.args[0])

    def test_application_exception_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            entrypoint = Path(folder) / "main.py"
            entrypoint.write_text("raise RuntimeError('intentional test failure')\n", encoding="utf-8")
            with patch.object(sys, "argv", ["launcher", str(entrypoint)]), \
                 patch.object(launcher, "_write_crash_log", return_value=None), \
                 patch.object(launcher, "_show_launch_error") as show_error, \
                 patch.object(launcher.runpy, "run_path", side_effect=RuntimeError("intentional test failure")):
                result = launcher.main()

        self.assertEqual(result, 1)
        show_error.assert_called_once()
        self.assertIn("intentional test failure", show_error.call_args.args[0])


if __name__ == "__main__":
    unittest.main()

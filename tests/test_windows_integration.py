import unittest

from cubes_archive.windows_integration import build_open_command


class WindowsIntegrationTests(unittest.TestCase):
    def test_open_command_quotes_python_path_with_spaces(self):
        command = build_open_command(r"C:\Program Files\Python314\python.exe")
        self.assertTrue(command.startswith('"C:\\Program Files\\Python314\\python.exe"'))
        self.assertIn('-m cubes_archive run "%1"', command)

    def test_open_command_uses_selected_interpreter(self):
        command = build_open_command(r"C:\Python314\python.exe")
        self.assertEqual(
            command,
            r"C:\Python314\python.exe -m cubes_archive run %1",
        )


if __name__ == "__main__":
    unittest.main()

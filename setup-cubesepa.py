from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPOSITORY_ARCHIVE = (
    "https://github.com/CubeHub-studio/CubesEPA/archive/refs/heads/main.zip"
)


def add_user_path(directory: Path) -> None:
    """Add the Python user Scripts directory to this Windows user's PATH."""
    import winreg

    directory = directory.resolve()
    key_path = r"Environment"
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE
    ) as key:
        try:
            current, value_type = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current, value_type = "", winreg.REG_EXPAND_SZ

        entries = [part.strip().strip('"') for part in current.split(";") if part.strip()]
        normalized = os.path.normcase(os.path.normpath(str(directory)))
        present = any(
            os.path.normcase(os.path.normpath(os.path.expandvars(part))) == normalized
            for part in entries
        )
        if not present:
            entries.append(str(directory))
            winreg.SetValueEx(key, "Path", 0, value_type, ";".join(entries))

    os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + str(directory)

    # Notify Explorer and other applications that the user environment changed.
    try:
        import ctypes
        from ctypes import wintypes

        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        result = wintypes.DWORD()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            "Environment",
            SMTO_ABORTIFHUNG,
            5000,
            ctypes.byref(result),
        )
    except Exception:
        pass


def main() -> int:
    if os.name != "nt":
        print("CubesEPA's setup installer currently supports Windows only.")
        return 1

    if sys.version_info < (3, 10):
        print("CubesEPA requires Python 3.10 or newer.")
        return 1

    scripts_dir = Path(
        sysconfig.get_path("scripts", sysconfig.get_preferred_scheme("user"))
    )
    if not str(scripts_dir):
        print("Could not determine Python's user Scripts directory.")
        return 1

    print(f"CubesEPA setup — using Python {sys.version.split()[0]}")
    print("Downloading the official CubesEPA repository...")

    with tempfile.TemporaryDirectory(prefix="cubesepa-setup-") as temporary:
        temp_dir = Path(temporary)
        archive_path = temp_dir / "cubesepa-main.zip"

        request = urllib.request.Request(
            REPOSITORY_ARCHIVE,
            headers={"User-Agent": "CubesEPA-Setup"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                with archive_path.open("wb") as output:
                    shutil.copyfileobj(response, output)
        except Exception as exc:
            print(f"Download failed: {exc}")
            return 1

        source_dir = temp_dir / "source"
        source_dir.mkdir()
        try:
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(source_dir)
        except (zipfile.BadZipFile, OSError) as exc:
            print(f"Could not extract the repository archive: {exc}")
            return 1

        project_dirs = [
            path.parent
            for path in source_dir.rglob("pyproject.toml")
            if (path.parent / "cubes_archive").is_dir()
        ]
        if len(project_dirs) != 1:
            print("Could not locate the CubesEPA Python project in the downloaded archive.")
            return 1

        project_dir = project_dirs[0]
        print("Installing CubesEPA with pip...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "--upgrade", str(project_dir)],
            check=False,
        )
        if result.returncode:
            print(f"pip installation failed with exit code {result.returncode}.")
            return result.returncode

    add_user_path(scripts_dir)
    cubes_exe = scripts_dir / "cubes.exe"
    if not cubes_exe.is_file():
        print(f"Installation completed, but cubes.exe was not found at: {cubes_exe}")
        return 1

    print("Registering the .epa file association...")
    result = subprocess.run([str(cubes_exe), "install-windows"], check=False)
    if result.returncode:
        print("Warning: the .epa association could not be registered.")

    print("Creating the CubesEPA Desktop shortcut...")
    result = subprocess.run([str(cubes_exe), "create-shortcut"], check=False)
    if result.returncode:
        print("Warning: the Desktop shortcut could not be created.")

    print()
    print("CubesEPA setup finished.")
    print(f"CLI: {cubes_exe}")
    print("Open a new terminal to use the updated PATH in future sessions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

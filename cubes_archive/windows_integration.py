"""Optional, per-user Windows integration for .epa files.

Registry changes are limited to HKCU\\Software\\Classes. No elevation is
requested, and existing third-party .epa associations are not overwritten.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

PROGID = "CubesArchive.EPA"
EXTENSION = ".epa"


def _require_windows():
    if os.name != "nt":
        raise RuntimeError("Windows integration is available only on Windows.")


def build_open_command(executable: str | None = None) -> str:
    """Return a correctly quoted command used by the Windows file association."""
    executable = executable or sys.executable
    return subprocess.list2cmdline([executable]) + ' -m cubes_archive run "%1"'


def install_file_association() -> None:
    """Register .epa for the current Windows user (HKCU only)."""
    _require_windows()
    import winreg

    extension_key = rf"Software\Classes\{EXTENSION}"
    progid_key = rf"Software\Classes\{PROGID}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, extension_key) as key:
        try:
            current, _ = winreg.QueryValueEx(key, None)
        except FileNotFoundError:
            current = ""
        if current and current != PROGID:
            raise RuntimeError(
                f"{EXTENSION} is already associated with '{current}'. "
                "Change the default app in Windows Settings before installing "
                "Cubes Archive, or remove that association first."
            )
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, PROGID)
        with winreg.CreateKey(key, "OpenWithProgids") as open_with:
            winreg.SetValueEx(open_with, PROGID, 0, winreg.REG_NONE, b"")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, progid_key) as key:
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, "Executable Python Archive")
        with winreg.CreateKey(key, r"DefaultIcon") as icon_key:
            winreg.SetValueEx(
                icon_key, None, 0, winreg.REG_SZ, f'"{sys.executable}",0'
            )
        with winreg.CreateKey(key, r"shell\open\command") as command_key:
            winreg.SetValueEx(
                command_key, None, 0, winreg.REG_SZ, build_open_command()
            )


def _delete_tree(root, path: str) -> None:
    import winreg

    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_tree(root, path + "\\" + child)
        winreg.DeleteKey(root, path)
    except FileNotFoundError:
        pass


def uninstall_file_association() -> bool:
    """Remove our HKCU association without disturbing a different default app."""
    _require_windows()
    import winreg

    extension_key = rf"Software\Classes\{EXTENSION}"
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, extension_key, 0, winreg.KEY_READ
        ) as key:
            current, _ = winreg.QueryValueEx(key, None)
    except FileNotFoundError:
        current = None

    if current == PROGID:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            extension_key,
            0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        ) as key:
            winreg.DeleteValue(key, None)
            try:
                with winreg.OpenKey(
                    key, "OpenWithProgids", 0, winreg.KEY_READ | winreg.KEY_WRITE
                ) as open_with:
                    try:
                        winreg.DeleteValue(open_with, PROGID)
                    except FileNotFoundError:
                        pass
                    values, subkeys, _ = winreg.QueryInfoKey(open_with)
                if values == 0 and subkeys == 0:
                    winreg.DeleteKey(key, "OpenWithProgids")
            except FileNotFoundError:
                pass
            values, subkeys, _ = winreg.QueryInfoKey(key)
        if values == 0 and subkeys == 0:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, extension_key)
        removed = True
    else:
        removed = False

    _delete_tree(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROGID}")
    return removed


def create_desktop_shortcut() -> Path:
    """Create a .lnk shortcut to the Cubes Archive CLI help in the user's Desktop."""
    _require_windows()
    desktop = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    shortcut = desktop / "Cubes Archive.lnk"

    # Encode the PowerShell script as UTF-16LE for -EncodedCommand. Paths are
    # inserted as PowerShell single-quoted literals with embedded quotes escaped.
    def ps_quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    powershell = str(
        Path(os.environ.get("WINDIR", r"C:\\Windows"))
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    command = f'& {ps_quote(sys.executable)} -m cubes_archive --help'
    script = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$link = $shell.CreateShortcut({ps_quote(str(shortcut))}); "
        f"$link.TargetPath = {ps_quote(powershell)}; "
        f"$link.Arguments = {ps_quote('-NoExit -Command ' + command)}; "
        f"$link.WorkingDirectory = {ps_quote(str(Path.home()))}; "
        "$link.Description = 'Cubes Archive command-line runtime'; "
        f"$link.IconLocation = {ps_quote(sys.executable + ',0')}; "
        "$link.Save()"
    )
    encoded = __import__("base64").b64encode(script.encode("utf-16le")).decode("ascii")
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-EncodedCommand", encoded],
        check=True,
        capture_output=True,
        text=True,
    )
    return shortcut

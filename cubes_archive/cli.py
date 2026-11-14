from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import zipfile
from . import __version__, windows_integration
from .icons import resolve_icon

MANIFEST_NAME = "epa.json"
REQUIREMENTS_NAME = "requirements.txt"
FORMAT_NAME = "EPA"
FORMAT_VERSION = 1
CHUNK_SIZE = 1024 * 1024


class EPAError(Exception):
    """Raised when an EPA archive is invalid or cannot be processed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_archive_name(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in name and not (len(name) >= 2 and name[1] == ":")


def load_manifest(archive: zipfile.ZipFile) -> dict:
    try:
        manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
    except KeyError as exc:
        raise EPAError(f"Missing {MANIFEST_NAME}.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EPAError(f"Invalid {MANIFEST_NAME}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise EPAError("EPA manifest must be a JSON object.")
    if manifest.get("format") != FORMAT_NAME:
        raise EPAError("Unrecognized archive format.")
    if manifest.get("format_version") != FORMAT_VERSION:
        raise EPAError(f"Unsupported EPA format version: {manifest.get('format_version')!r}")
    for field in ("name", "version", "publisher", "entrypoint"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            raise EPAError(f"Manifest field '{field}' must be a non-empty string.")
    entrypoint = manifest["entrypoint"]
    if not safe_archive_name(entrypoint):
        raise EPAError("Unsafe entrypoint path.")
    names = archive.namelist()
    if entrypoint not in names:
        raise EPAError(f"Entrypoint '{entrypoint}' does not exist in the archive.")
    try:
        requirements_info = archive.getinfo(REQUIREMENTS_NAME)
    except KeyError:
        requirements_info = None
    if requirements_info is not None and requirements_info.is_dir():
        raise EPAError(f"{REQUIREMENTS_NAME} must be a file, not a directory.")
    if "require_admin" in manifest and not isinstance(manifest["require_admin"], bool):
        raise EPAError("Manifest field 'require_admin' must be a boolean.")
    return manifest


def _powershell_quote(value: str) -> str:
    """Quote one argument for a PowerShell single-quoted string."""
    return "'" + value.replace("'", "''") + "'"


def _run_visible_powershell(
    commands: list[list[str]], cwd: Path, environment: dict[str, str],
    pause_at_end: bool = True,
) -> int:
    """Run commands in a new PowerShell window and leave logs visible afterward."""
    powershell = shutil.which("powershell.exe") or "powershell.exe"
    lines = ["$exitCode = 0"]
    for command in commands:
        quoted = " ".join(_powershell_quote(part) for part in command)
        lines.append(f"if ($exitCode -eq 0) {{ & {quoted}; $exitCode = $LASTEXITCODE }}")
    if pause_at_end:
        lines.extend([
            "Write-Host ''",
            "Read-Host 'EPA finished. Press Enter to close this window'",
        ])
    lines.append("exit $exitCode")
    script = "; ".join(lines)
    creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    result = subprocess.run(
        [powershell, "-NoProfile", "-Command", script],
        cwd=cwd,
        env=environment,
        check=False,
        creationflags=creation_flags,
    )
    return result.returncode



def _run_elevated_windows(command: list[str], cwd: Path) -> int:
    """Launch the EPA with the Windows UAC 'runas' verb and wait for it."""
    if os.name != "nt":
        raise EPAError("Administrator elevation is only supported on Windows.")

    import ctypes
    from ctypes import wintypes

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", wintypes.ULONG),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", ctypes.c_void_p),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", wintypes.LPCWSTR),
            ("hkeyClass", wintypes.HANDLE),
            ("dwHotKey", wintypes.DWORD),
            ("hIconOrMonitor", ctypes.c_void_p),
            ("hProcess", wintypes.HANDLE),
        ]

    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = command[0]
    info.lpParameters = subprocess.list2cmdline(command[1:])
    info.lpDirectory = str(cwd)
    info.nShow = 1  # SW_SHOWNORMAL

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        error = ctypes.get_last_error()
        if error == 1223:  # ERROR_CANCELLED: user declined the UAC prompt
            raise EPAError("Administrator permission was declined. The EPA was not launched.")
        raise ctypes.WinError(error)

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.WaitForSingleObject(info.hProcess, 0xFFFFFFFF)
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code)):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(exit_code.value)
    finally:
        kernel32.CloseHandle(info.hProcess)

def create_archive(source: Path, output: Path, name: str | None, version: str, publisher: str, description: str, require_admin: bool = False) -> None:
    source = source.resolve()
    if not source.is_dir():
        raise EPAError(f"Source directory does not exist: {source}")
    if not (source / "main.py").is_file():
        raise EPAError("Source directory must contain main.py.")
    # requirements.txt is optional: omitted means the EPA uses only the
    # standard library or dependencies already available in the environment.
    output = output.resolve()
    if output == source or source in output.parents:
        raise EPAError("Output archive cannot be placed inside the source directory.")
    manifest = {"format": FORMAT_NAME, "format_version": FORMAT_VERSION, "name": name or source.name, "version": version, "publisher": publisher, "description": description, "entrypoint": "main.py", "cubesepa_version": __version__, "require_admin": require_admin}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2) + "\n")
            for path in sorted(source.rglob("*")):
                if path.is_symlink():
                    raise EPAError(f"Symbolic links are not supported: {path}")
                if not path.is_file():
                    continue
                relative = path.relative_to(source).as_posix()
                if relative == MANIFEST_NAME:
                    raise EPAError(f"'{MANIFEST_NAME}' is reserved by Cubes Archive.")
                archive.write(path, relative)
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(f"Created: {output}")
    print(f"SHA-256: {sha256_file(output)}")


def inspect_archive(path: Path) -> None:
    with zipfile.ZipFile(path, "r") as archive:
        manifest = load_manifest(archive)
        print(json.dumps(manifest, indent=2))
        print(f"\nFiles: {sum(not item.is_dir() for item in archive.infolist())}")
        print(f"Dependencies file: {REQUIREMENTS_NAME if REQUIREMENTS_NAME in archive.namelist() else 'none (Python standard library assumed)'}")


def verify_archive(path: Path) -> None:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            for item in archive.infolist():
                if not safe_archive_name(item.filename):
                    raise EPAError(f"Unsafe archive path: {item.filename}")
            bad_member = archive.testzip()
            if bad_member:
                raise EPAError(f"ZIP integrity check failed at: {bad_member}")
            manifest = load_manifest(archive)
            has_requirements = REQUIREMENTS_NAME in archive.namelist()
        print("EPA structure: OK")
        print("ZIP integrity: OK")
        print(f"Application: {manifest['name']} {manifest['version']}")
        print(f"Publisher label: {manifest['publisher']}")
        print(f"Entrypoint: {manifest['entrypoint']}")
        print(f"Dependencies: {REQUIREMENTS_NAME + ' present' if has_requirements else 'none (Python standard library assumed)'}")
        print(f"Administrator privileges requested: {'yes' if manifest.get('require_admin', False) else 'no'}")
        print(f"Archive SHA-256: {sha256_file(path)}")
        print("\nNote: this checks archive structure and integrity, not publisher identity or application safety.")
    except zipfile.BadZipFile as exc:
        raise EPAError(f"Not a valid ZIP-based EPA archive: {exc}") from exc


def run_archive(path: Path, app_args: list[str]) -> int:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            for item in archive.infolist():
                if not safe_archive_name(item.filename):
                    raise EPAError(f"Unsafe archive path: {item.filename}")
            manifest = load_manifest(archive)
            temporary = tempfile.TemporaryDirectory(prefix="cubes-epa-")
            workdir = Path(temporary.name)
            try:
                for item in archive.infolist():
                    if item.is_dir():
                        continue
                    destination = workdir.joinpath(*PurePosixPath(item.filename).parts)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(item) as source, destination.open("wb") as target:
                        while chunk := source.read(CHUNK_SIZE):
                            target.write(chunk)
            except Exception:
                temporary.cleanup()
                raise
    except zipfile.BadZipFile as exc:
        raise EPAError(f"Not a valid ZIP-based EPA archive: {exc}") from exc

    entrypoint = workdir.joinpath(*PurePosixPath(manifest["entrypoint"]).parts)
    requirements = workdir / REQUIREMENTS_NAME
    try:
        from .safety_dialog import confirm_launch
        requires_admin = manifest.get("require_admin", False)
        confirmed, run_silently = confirm_launch(
            manifest["name"], manifest.get("cubesepa_version"), requires_admin
        )
        if not confirmed:
            print("Launch cancelled.")
            return 1

        environment = os.environ.copy()
        environment["CUBES_EPA_ICON"] = str(resolve_icon(workdir))
        environment["CUBES_EPA_NAME"] = str(manifest["name"])
        launcher_command = [
            str(Path(sys.executable).with_name("python.exe"))
            if os.name == "nt" and Path(sys.executable).with_name("python.exe").is_file()
            else sys.executable,
            "-u", "-m", "cubes_archive.launcher", str(entrypoint), *app_args,
        ]

        has_requirements = requirements.is_file() and bool(
            requirements.read_text(encoding="utf-8-sig").strip()
        )

        if requires_admin:
            if os.name != "nt":
                raise EPAError("This EPA requests administrator privileges, but UAC elevation is only supported on Windows.")
            if has_requirements:
                pip_command = [sys.executable, "-m", "pip", "install", "-r", str(requirements)]
                if run_silently:
                    result = subprocess.run(
                        pip_command, cwd=workdir, check=False,
                        capture_output=True, text=True,
                    )
                    if result.returncode:
                        details = (result.stderr or result.stdout or "").strip()
                        raise EPAError(
                            f"Dependency installation failed (pip exit code {result.returncode}); "
                            f"EPA was not launched.\\n{details}"
                        )
                else:
                    result = _run_visible_powershell(
                        [pip_command], workdir, environment, pause_at_end=False
                    )
                    if result:
                        raise EPAError(f"Dependency installation failed (pip exit code {result}). EPA was not launched.")

            elevated_python = sys.executable
            if run_silently:
                pythonw = Path(sys.executable).with_name("pythonw.exe")
                if pythonw.is_file():
                    elevated_python = str(pythonw)
            elevated_command = [
                elevated_python, "-u", "-m", "cubes_archive.launcher",
                str(entrypoint), *app_args,
            ]
            return _run_elevated_windows(elevated_command, workdir)

        if run_silently:
            if has_requirements:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
                    cwd=workdir, check=False, capture_output=True, text=True,
                )
                if result.returncode:
                    details = (result.stderr or result.stdout or "").strip()
                    raise EPAError(
                        f"Dependency installation failed (pip exit code {result.returncode}); "
                        f"EPA was not launched.\\n{details}"
                    )
            launcher_python = sys.executable
            if os.name == "nt":
                pythonw = Path(sys.executable).with_name("pythonw.exe")
                if pythonw.is_file():
                    launcher_python = str(pythonw)
            result = subprocess.run(
                [launcher_python, "-m", "cubes_archive.launcher", str(entrypoint), *app_args],
                cwd=workdir, env=environment, check=False,
            )
            return result.returncode

        if os.name == "nt":
            commands = []
            if has_requirements:
                commands.append([sys.executable, "-u", "-m", "pip", "install", "-r", str(requirements)])
            commands.append(launcher_command)
            return _run_visible_powershell(commands, workdir, environment)

        if has_requirements:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
                cwd=workdir, check=False,
            )
            if result.returncode:
                return result.returncode
        return subprocess.run(
            launcher_command, cwd=workdir, env=environment, check=False
        ).returncode
    except (OSError, UnicodeError) as exc:
        raise EPAError(f"Could not prepare EPA launch: {exc}") from exc
    finally:
        temporary.cleanup()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cubes", description="Cubes Archive — create and run Executable Python Archives (.epa).")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Package a project directory.")
    create.add_argument("source", type=Path)
    create.add_argument("-o", "--output", type=Path)
    create.add_argument("--name")
    create.add_argument("--app-version", default="1.0.0")
    create.add_argument("--publisher", default="Unknown publisher")
    create.add_argument("--description", default="")
    create.add_argument("--require-admin", action="store_true", help="Request Windows administrator privileges when this EPA is launched.")
    inspect = commands.add_parser("inspect", help="Display EPA metadata.")
    inspect.add_argument("archive", type=Path)
    verify = commands.add_parser("verify", help="Check EPA structure and integrity.")
    verify.add_argument("archive", type=Path)
    commands.add_parser("install-windows", help="Register .epa files for the current Windows user.").set_defaults(windows_action="install")
    commands.add_parser("uninstall-windows", help="Remove the current user's .epa file association.").set_defaults(windows_action="uninstall")
    commands.add_parser("create-shortcut", help="Create a Desktop shortcut that opens the CubesEPA GUI.").set_defaults(windows_action="shortcut")
    run = commands.add_parser("run", help="Run an EPA application.")
    run.add_argument("archive", type=Path)
    run.add_argument("app_args", nargs=argparse.REMAINDER, help="Arguments passed to the EPA application.")
    commands.add_parser("gui", help="Open the CubesEPA Tkinter desktop interface.")
    commands.add_parser("update", help="Update CubesEPA from its official GitHub repository.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "create":
            create_archive(args.source, args.output or Path(f"{args.source.name}.epa"), args.name, args.app_version, args.publisher, args.description, args.require_admin)
            return 0
        if args.command == "inspect":
            inspect_archive(args.archive)
            return 0
        if args.command == "verify":
            verify_archive(args.archive)
            return 0
        if args.command == "run":
            return run_archive(args.archive, args.app_args)
        if args.command == "gui":
            from .gui import main as gui_main
            return gui_main()
        if args.command == "update":
            command = [sys.executable, "-m", "pip", "install", "--user", "--upgrade", "--force-reinstall", "https://github.com/CubeHub-studio/CubesEPA/archive/refs/heads/main.zip"]
            print("Updating CubesEPA from the official GitHub repository... (free; internet required)")
            result = subprocess.run(command, check=False)
            if result.returncode == 0:
                print("Update complete. Close and reopen CubesEPA.")
            return result.returncode
        if args.command == "install-windows":
            windows_integration.install_file_association()
            print("Registered .epa for the current Windows user.")
            return 0
        if args.command == "uninstall-windows":
            removed = windows_integration.uninstall_file_association()
            print("Removed the Cubes Archive .epa association." if removed else "Cubes Archive was not the current per-user .epa association.")
            return 0
        if args.command == "create-shortcut":
            print(f"Created: {windows_integration.create_desktop_shortcut()}")
            return 0
    except Exception as exc:
        if sys.stderr is None:
            try:
                from tkinter import messagebox
                messagebox.showerror("CubesEPA — Error", str(exc))
            except Exception:
                pass
        else:
            print(f"cubes: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

from . import __version__
from . import windows_integration
from .icons import resolve_icon

MANIFEST_NAME = "epa.json"
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
    """Reject absolute paths and traversal paths in archive entries."""
    path = PurePosixPath(name)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and not (len(name) >= 2 and name[1] == ":")
    )


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
        raise EPAError(
            f"Unsupported EPA format version: {manifest.get('format_version')!r}"
        )

    for field in ("name", "version", "publisher", "entrypoint"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            raise EPAError(f"Manifest field '{field}' must be a non-empty string.")

    entrypoint = manifest["entrypoint"]
    if not safe_archive_name(entrypoint):
        raise EPAError("Unsafe entrypoint path.")
    if entrypoint not in archive.namelist():
        raise EPAError(f"Entrypoint '{entrypoint}' does not exist in the archive.")
    return manifest


def create_archive(
    source: Path,
    output: Path,
    name: str | None,
    version: str,
    publisher: str,
    description: str,
) -> None:
    source = source.resolve()
    if not source.is_dir():
        raise EPAError(f"Source directory does not exist: {source}")
    if not (source / "main.py").is_file():
        raise EPAError("Source directory must contain main.py.")

    output = output.resolve()
    if output == source or source in output.parents:
        raise EPAError("Output archive cannot be placed inside the source directory.")

    manifest = {
        "format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
        "name": name or source.name,
        "version": version,
        "publisher": publisher,
        "description": description,
        "entrypoint": "main.py",
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.writestr(
                MANIFEST_NAME, json.dumps(manifest, indent=2) + "\n"
            )
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
        file_count = sum(not item.is_dir() for item in archive.infolist())
        print(f"\nFiles: {file_count}")


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

        print("EPA structure: OK")
        print("ZIP integrity: OK")
        print(f"Application: {manifest['name']} {manifest['version']}")
        print(f"Publisher label: {manifest['publisher']}")
        print(f"Entrypoint: {manifest['entrypoint']}")
        print(f"Archive SHA-256: {sha256_file(path)}")
        print(
            "\nNote: this checks archive structure and integrity, "
            "not publisher identity or application safety."
        )
    except zipfile.BadZipFile as exc:
        raise EPAError(f"Not a valid ZIP-based EPA archive: {exc}") from exc


def run_archive(path: Path, app_args: list[str]) -> int:
    """Extract an EPA to a temporary directory and run its declared entrypoint."""
    try:
        with zipfile.ZipFile(path, "r") as archive:
            for item in archive.infolist():
                if not safe_archive_name(item.filename):
                    raise EPAError(f"Unsafe archive path: {item.filename}")
            manifest = load_manifest(archive)

            temporary = tempfile.TemporaryDirectory(prefix="cubes-epa-")
            workdir = Path(temporary.name)
            try:
                # Extract each validated entry explicitly.
                for item in archive.infolist():
                    if item.is_dir():
                        continue
                    destination = workdir.joinpath(
                        *PurePosixPath(item.filename).parts
                    )
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
    print(f"Launching {manifest['name']} {manifest['version']}...", flush=True)
    print(
        "WARNING: EPA files contain executable code. Only run archives "
        "from sources you trust.",
        flush=True,
    )
    try:
        environment = os.environ.copy()
        environment["CUBES_EPA_ICON"] = str(resolve_icon(workdir))
        environment["CUBES_EPA_NAME"] = str(manifest["name"])
        completed = subprocess.run(
            [sys.executable, "-m", "cubes_archive.launcher", str(entrypoint), *app_args],
            cwd=workdir,
            env=environment,
            check=False,
        )
        return completed.returncode
    finally:
        temporary.cleanup()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cubes",
        description=(
            "Cubes Archive — create and run Executable Python Archives (.epa)."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Package a project directory.")
    create.add_argument("source", type=Path)
    create.add_argument("-o", "--output", type=Path)
    create.add_argument("--name")
    create.add_argument("--app-version", default="1.0.0")
    create.add_argument("--publisher", default="Unknown publisher")
    create.add_argument("--description", default="")

    inspect = commands.add_parser("inspect", help="Display EPA metadata.")
    inspect.add_argument("archive", type=Path)

    verify = commands.add_parser("verify", help="Check EPA structure and integrity.")
    verify.add_argument("archive", type=Path)

    install_windows = commands.add_parser(
        "install-windows", help="Register .epa files for the current Windows user."
    )
    install_windows.set_defaults(windows_action="install")

    uninstall_windows = commands.add_parser(
        "uninstall-windows", help="Remove the current user's .epa file association."
    )
    uninstall_windows.set_defaults(windows_action="uninstall")

    shortcut = commands.add_parser(
        "create-shortcut", help="Create a Cubes Archive shortcut on the Windows Desktop."
    )
    shortcut.set_defaults(windows_action="shortcut")

    run = commands.add_parser("run", help="Run an EPA application.")
    run.add_argument("archive", type=Path)
    run.add_argument(
        "app_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the EPA application.",
    )

    commands.add_parser("gui", help="Open the CubesEPA Tkinter desktop interface.")
    commands.add_parser("update", help="Update CubesEPA from its official GitHub repository.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "create":
            output = args.output or Path(f"{args.source.name}.epa")
            create_archive(
                args.source,
                output,
                args.name,
                args.app_version,
                args.publisher,
                args.description,
            )
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
            command = [
                sys.executable, "-m", "pip", "install", "--upgrade",
                "--force-reinstall",
                "https://github.com/CubeHub-studio/CubesEPA/archive/refs/heads/main.zip",
            ]
            print("Updating CubesEPA from the official GitHub repository...")
            print("This requires an internet connection; the update is free.")
            completed = subprocess.run(command, check=False)
            if completed.returncode == 0:
                print("Update complete. Close and reopen CubesEPA.")
            return completed.returncode
        if args.command == "install-windows":
            windows_integration.install_file_association()
            print("Registered .epa for the current Windows user.")
            print("If Windows asks, choose Cubes Archive/Python as the default .epa app.")
            return 0
        if args.command == "uninstall-windows":
            removed = windows_integration.uninstall_file_association()
            if removed:
                print("Removed the Cubes Archive .epa association.")
            else:
                print("Cubes Archive was not the current per-user .epa association.")
            return 0
        if args.command == "create-shortcut":
            shortcut_path = windows_integration.create_desktop_shortcut()
            print(f"Created: {shortcut_path}")
            return 0
    except (EPAError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"cubes: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

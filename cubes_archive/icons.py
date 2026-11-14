"""Icon helpers for Cubes Archive and EPA applications."""
from __future__ import annotations

from pathlib import Path
import struct


def default_icon_path() -> Path:
    """Return the icon bundled with the installed Cubes Archive package."""
    return Path(__file__).with_name("assets") / "icon.png"


def resolve_icon(application_root: Path | None = None) -> Path:
    """Prefer an EPA's assets/icon.png, otherwise use Cubes Archive's icon."""
    if application_root is not None:
        custom = application_root / "assets" / "icon.png"
        if custom.is_file():
            return custom
    fallback = default_icon_path()
    if fallback.is_file():
        return fallback
    raise FileNotFoundError(f"Cubes Archive default icon is missing: {fallback}")


def png_to_ico(png_path: Path, ico_path: Path) -> Path:
    """Wrap a PNG in a Windows ICO container (supported by modern Windows)."""
    data = png_path.read_bytes()
    if not data.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
        raise ValueError(f"Not a PNG image: {png_path}")
    # ICO directory header followed by one 256x256-or-smaller PNG image.
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(data), 22)
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    ico_path.write_bytes(header + entry + data)
    return ico_path

"""Launch an EPA while automatically applying its icon to Tkinter windows."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


def _install_tk_icon_hook() -> None:
    icon_path = os.environ.get("CUBES_EPA_ICON")
    if not icon_path or not Path(icon_path).is_file():
        return
    try:
        import tkinter
    except ImportError:
        return

    def patch_window_class(window_class):
        original_init = window_class.__init__

        def init_with_icon(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            try:
                image = tkinter.PhotoImage(file=icon_path)
                self.iconphoto(True, image)
                # Keep a reference alive for the lifetime of the window.
                self._cubes_archive_icon = image
            except Exception:
                pass

        window_class.__init__ = init_with_icon

    patch_window_class(tkinter.Tk)
    patch_window_class(tkinter.Toplevel)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m cubes_archive.launcher ENTRYPOINT [ARGS...]")
        return 2
    entrypoint = Path(sys.argv[1]).resolve()
    app_args = sys.argv[2:]
    _install_tk_icon_hook()
    sys.argv = [str(entrypoint), *app_args]
    runpy.run_path(str(entrypoint), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

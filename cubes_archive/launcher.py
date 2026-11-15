"""Launch an EPA while automatically applying its icon to Tkinter windows."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys
import traceback


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


def _install_tk_super_fullscreen_hook() -> None:
    """Add an opt-in F11 fullscreen toggle to Tkinter root and child windows."""
    try:
        import tkinter
    except ImportError:
        return

    original_init = tkinter.Tk.__init__

    def init_with_fullscreen(self, *args, **kwargs):
        original_init(self, *args, **kwargs)

        def toggle_fullscreen(event):
            try:
                window = event.widget.winfo_toplevel()
                if bool(window.attributes("-fullscreen")):
                    window.attributes("-fullscreen", False)
                    geometry = getattr(window, "_cubes_archive_saved_geometry", None)
                    previous_state = getattr(window, "_cubes_archive_saved_state", "normal")
                    if geometry:
                        window.geometry(geometry)
                    if previous_state in ("normal", "zoomed"):
                        window.state(previous_state)
                else:
                    window._cubes_archive_saved_geometry = window.geometry()
                    window._cubes_archive_saved_state = window.state()
                    window.attributes("-fullscreen", True)
            except tkinter.TclError:
                # A window may be closing while its key event is being handled.
                pass
            return "break"

        # bind_all applies to Tkinter windows sharing this interpreter, including Toplevels.
        self.bind_all("<F11>", toggle_fullscreen, add="+")
    
    tkinter.Tk.__init__ = init_with_fullscreen


def _write_crash_log() -> Path | None:
    """Persist a full traceback even when running under pythonw.exe."""
    try:
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        folder = base / "CubesArchive" / "logs"
        folder.mkdir(parents=True, exist_ok=True)
        log_path = folder / "last-launch.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        return log_path
    except OSError:
        return None


def _show_launch_error(message: str) -> None:
    """Show a native GUI error when no console is available."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("EPA launch failed", message, parent=root)
        root.destroy()
        return
    except Exception:
        pass
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, "EPA launch failed", 0x10)
        except Exception:
            pass


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m cubes_archive.launcher ENTRYPOINT [ARGS...]")
        return 2
    entrypoint = Path(sys.argv[1]).resolve()
    app_args = sys.argv[2:]
    try:
        if not entrypoint.is_file():
            raise FileNotFoundError(f"EPA entrypoint was not found: {entrypoint}")
        _install_tk_icon_hook()
        if os.environ.get("CUBES_EPA_SUPER_FULLSCREEN") == "1":
            _install_tk_super_fullscreen_hook()
        sys.argv = [str(entrypoint), *app_args]
        runpy.run_path(str(entrypoint), run_name="__main__")
        return 0
    except Exception as exc:
        log_path = _write_crash_log()
        detail = f"{type(exc).__name__}: {exc}"
        if log_path:
            detail += f"\n\nFull details were saved to:\n{log_path}"
        _show_launch_error(detail)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

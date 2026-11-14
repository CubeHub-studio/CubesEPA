"""Tkinter desktop interface for CubesEPA."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from . import __version__
from .icons import default_icon_path

class CubesArchiveApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"CubesEPA — Cubes Archive {__version__}")
        self.root.geometry("760x500")
        self.root.minsize(620, 400)
        self.selected: Path | None = None
        self._icon = None
        icon = default_icon_path()
        if icon.is_file():
            try:
                self._icon = tk.PhotoImage(file=str(icon))
                root.iconphoto(True, self._icon)
            except tk.TclError:
                pass
        self._build()
        self.refresh()

    def _build(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        heading = ttk.Frame(outer)
        heading.pack(fill="x")
        ttk.Label(heading, text="CubesEPA", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(heading, text="Manage and launch Executable Python Archives", font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 14))
        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Open EPA…", command=self.open_file).pack(side="left")
        ttk.Button(actions, text="Refresh", command=self.refresh).pack(side="left", padx=6)
        ttk.Button(actions, text="Run", command=self.run_selected).pack(side="left")
        ttk.Button(actions, text="Verify", command=lambda: self.inspect_action("verify")).pack(side="left", padx=6)
        ttk.Button(actions, text="Inspect", command=lambda: self.inspect_action("inspect")).pack(side="left")
        body = ttk.LabelFrame(outer, text="Recent EPA files", padding=8)
        body.pack(fill="both", expand=True)
        self.files = tk.Listbox(body, height=12, activestyle="dotbox")
        self.files.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.files.yview)
        scrollbar.pack(side="right", fill="y")
        self.files.configure(yscrollcommand=scrollbar.set)
        self.files.bind("<<ListboxSelect>>", self._select)
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Button(footer, text="Update CubesEPA", command=self.update).pack(side="left")
        ttk.Button(footer, text="Create Desktop Shortcut", command=self.create_shortcut).pack(side="left", padx=8)
        ttk.Label(footer, text=f"Version {__version__}").pack(side="right")
        self.status = tk.StringVar(value="Ready")
        ttk.Label(outer, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x", pady=(12, 0))

    def refresh(self):
        self.files.delete(0, tk.END)
        self._paths = []
        folders = [Path.home() / name for name in ("Desktop", "Downloads", "Documents")]
        found = []
        for folder in folders:
            if folder.is_dir():
                found.extend(folder.glob("*.epa"))
        for path in sorted(set(found), key=lambda p: p.name.lower()):
            self._paths.append(path)
            self.files.insert(tk.END, f"{path.name}    —    {path.parent}")
        self.status.set(f"Found {len(self._paths)} EPA file(s) in Desktop, Downloads, and Documents")

    def _select(self, _event=None):
        selection = self.files.curselection()
        self.selected = self._paths[selection[0]] if selection else None

    def open_file(self):
        chosen = filedialog.askopenfilename(title="Select an EPA application", filetypes=[("Executable Python Archive", "*.epa"), ("All files", "*.*")])
        if chosen:
            self.selected = Path(chosen)
            self.status.set(f"Selected {self.selected.name}")

    def run_selected(self):
        if not self.selected or not self.selected.is_file():
            self.open_file()
        if not self.selected or not self.selected.is_file():
            return
        try:
            subprocess.Popen([sys.executable, "-m", "cubes_archive", "run", str(self.selected)], cwd=str(Path.home()))
            self.status.set(f"Launching {self.selected.name} — safety confirmation required")
        except OSError as exc:
            messagebox.showerror("Launch failed", str(exc))

    def inspect_action(self, action: str):
        if not self.selected or not self.selected.is_file():
            self.open_file()
        if not self.selected or not self.selected.is_file():
            return
        result = subprocess.run([sys.executable, "-m", "cubes_archive", action, str(self.selected)], capture_output=True, text=True, check=False)
        output = result.stdout or result.stderr or "No output."
        if result.returncode == 0:
            messagebox.showinfo(f"EPA {action.title()}", output)
            self.status.set(f"{action.title()} complete: {self.selected.name}")
        else:
            messagebox.showerror(f"EPA {action.title()} failed", output)

    def update(self):
        if not messagebox.askyesno("Update CubesEPA", "Check GitHub and reinstall the latest CubesEPA version? An internet connection is required. This update is free."):
            return
        try:
            subprocess.Popen([sys.executable, "-m", "cubes_archive", "update"], cwd=str(Path.home()))
            messagebox.showinfo("Update started", "The updater has started. Close and reopen CubesEPA after it finishes.")
        except OSError as exc:
            messagebox.showerror("Update failed to start", str(exc))

    def create_shortcut(self):
        try:
            from .windows_integration import create_desktop_shortcut
            path = create_desktop_shortcut()
            messagebox.showinfo("Shortcut created", f"Created the CubesEPA shortcut:\n{path}")
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            messagebox.showerror("Shortcut creation failed", str(exc))

def main() -> int:
    if os.name == "nt":
        try:
            from .windows_integration import create_desktop_shortcut
            create_desktop_shortcut()
        except (OSError, RuntimeError, subprocess.SubprocessError):
            pass
    root = tk.Tk()
    CubesArchiveApp(root)
    root.mainloop()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

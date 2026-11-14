"""Modal confirmation shown before any EPA code or dependencies are run."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import __version__


WARNING_TEXT = (
    "EPA files cannot be confirmed safe, be aware that neither Cubes Studio "
    "or the publisher of this software will be responsible for damage or "
    "data loss caused. Simply press the Continue button twice to launch it anyway."
)

VERSION_WARNING = (
    "This EPA was compiled with a different version of EPA that you are "
    "currently using, this app is not guaranteed to work as intended."
)


def confirm_launch(app_name: str, compiled_version: str | None = None) -> bool:
    # Use the visible window as the Tk root. A withdrawn root with a transient
    # Toplevel can leave the modal warning hidden behind other windows on Windows.
    dialog = tk.Tk()
    dialog.title("CubesEPA — Safety warning")
    dialog.resizable(False, False)

    state = {"confirmed": False, "clicks": 0}

    outer = ttk.Frame(dialog, padding=18)
    outer.pack(fill="both", expand=True)

    ttk.Label(
        outer,
        text=f"Launching: {app_name}",
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w", pady=(0, 10))

    ttk.Label(
        outer,
        text=WARNING_TEXT,
        wraplength=470,
        justify="left",
    ).pack(anchor="w")

    if (
        not isinstance(compiled_version, str)
        or not compiled_version.strip()
        or compiled_version != __version__
    ):
        ttk.Label(
            outer,
            text=VERSION_WARNING,
            wraplength=470,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

    buttons = ttk.Frame(outer)
    buttons.pack(fill="x", pady=(18, 0))

    def continue_clicked() -> None:
        state["clicks"] += 1
        if state["clicks"] == 1:
            continue_button.configure(text="Continue (press again)")
        else:
            state["confirmed"] = True
            dialog.destroy()

    def cancel_clicked() -> None:
        dialog.destroy()

    continue_button = ttk.Button(
        buttons,
        text="Continue (must be pressed twice)",
        command=continue_clicked,
    )
    continue_button.pack(side="right")
    ttk.Button(buttons, text="Cancel", command=cancel_clicked).pack(
        side="right", padx=(0, 8)
    )

    dialog.protocol("WM_DELETE_WINDOW", cancel_clicked)
    dialog.update_idletasks()

    x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
    y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
    dialog.lift()
    dialog.focus_force()
    dialog.mainloop()

    return state["confirmed"]

"""Modal confirmation shown before any EPA code or dependencies are run."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk

WARNING_TEXT = (
    "EPA files cannot be confirmed safe, be aware that neither Cubes Studio "
    "or the publisher of this software will be responsible for damage or "
    "data loss caused. Simply press the Continue button twice to launch it anyway."
)

def confirm_launch(app_name: str) -> bool:
    root = tk.Tk()
    root.withdraw()
    dialog = tk.Toplevel(root)
    dialog.title("CubesEPA — Safety warning")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()
    state = {"confirmed": False, "clicks": 0}
    outer = ttk.Frame(dialog, padding=18)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text=f"Launching: {app_name}", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))
    ttk.Label(outer, text=WARNING_TEXT, wraplength=470, justify="left").pack(anchor="w")
    buttons = ttk.Frame(outer)
    buttons.pack(fill="x", pady=(18, 0))
    def continue_clicked():
        state["clicks"] += 1
        if state["clicks"] == 1:
            continue_button.configure(text="Continue (press again)")
        else:
            state["confirmed"] = True
            dialog.destroy()
    def cancel_clicked():
        dialog.destroy()
    continue_button = ttk.Button(buttons, text="Continue (must be pressed twice)", command=continue_clicked)
    continue_button.pack(side="right")
    ttk.Button(buttons, text="Cancel", command=cancel_clicked).pack(side="right", padx=(0, 8))
    dialog.protocol("WM_DELETE_WINDOW", cancel_clicked)
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
    y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
    dialog.focus_force()
    root.wait_window(dialog)
    root.destroy()
    return state["confirmed"]

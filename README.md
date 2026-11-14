# Cubes Archive

**Cubes Archive** is a Python command-line runtime and packaging tool for **Executable Python Archives** (`.epa` files).

An EPA is a ZIP-based application bundle containing a manifest, a Python entrypoint, and the files needed by the application. The Cubes Archive runtime creates, inspects, verifies, and launches these bundles.

> **Security notice:** An EPA contains executable code. Only run archives from sources you trust. Structural verification and SHA-256 checks detect corruption or unexpected changes; they do not prove that software is safe, identify its author, or make Windows trust an unsigned executable.

## Features

- Create `.epa` files from a project directory.
- Store application metadata in `epa.json`.
- Inspect archive metadata.
- Check ZIP integrity, required metadata, and archive paths.
- Launch an EPA using the active Python interpreter.
- Automatically apply an EPA's `assets/icon.png` to Tkinter windows, with the bundled CubesEPA icon as fallback.
- Open the CubesEPA Tkinter desktop interface with `cubes gui`.
- Update CubesEPA directly from its official GitHub repository with `cubes update`.
- Create a Desktop shortcut that opens the GUI.
- Uses Python's standard library; no runtime third-party dependencies.

## Requirements

- Python 3.10 or newer
- Windows 10/11, or another platform with Python installed

Python 3.14 is supported in principle; the project uses standard-library APIs.

## Install from source

Clone the repository, open PowerShell in the project directory, and install the package:

```powershell
py -m pip install --user .
```

Close and reopen PowerShell if the `cubes` command is not immediately found.

Check the installation:

```powershell
cubes --version
cubes --help
```

You can also run the CLI without installing its command entry point:

```powershell
py -m cubes_archive --help
```

## Windows integration

After installing Cubes Archive, optionally register the `.epa` extension for
your Windows user:

```powershell
cubes install-windows
```

This writes only under
`HKEY_CURRENT_USER\\Software\\Classes` and does not require administrator
rights. The registered command launches the archive with the Python interpreter
used to run Cubes Archive. Windows may still require you to choose the default
app in **Settings → Apps → Default apps**. Windows' protected per-user
`UserChoice` setting can take precedence over application-written associations,
so registration does not guarantee immediate activation on every system.

Double-clicking an associated `.epa` file runs its declared Python entrypoint.
EPA applications execute with your Windows account's permissions; only open
archives from sources you trust.

Open the graphical desktop interface:

```powershell
cubes gui
```

Create a Desktop shortcut named `CubesEPA` that launches the graphical interface:

```powershell
cubes create-shortcut
```

Update to the latest code on the official GitHub `main` branch (internet connection required; free):

```powershell
cubes update
```

The updater uses the current Python interpreter's `pip` to reinstall CubesEPA from GitHub. Close and reopen the GUI after it finishes.

Remove the association before uninstalling the package:

```powershell
cubes uninstall-windows
py -m pip uninstall cubes-archive
```

Uninstall removes the association only if Cubes Archive is still the current
per-user `.epa` handler. It does not remove another app's association. The
shortcut is not automatically deleted; remove `Cubes Archive.lnk` from your
Desktop manually if desired. These commands are Windows-only.

## Create your first EPA

Create a project folder:

```text
HelloEPA/
└── main.py
```

Example `HelloEPA/main.py`:

```python
print("Hello from Cubes Archive!")
input("Press Enter to close...")
```

Build the archive:

```powershell
cubes create .\HelloEPA --publisher "Cubes, Studio." --app-version 1.0.0
```

This creates `HelloEPA.epa` in the current directory by default.

Inspect and verify it:

```powershell
cubes inspect .\HelloEPA.epa
cubes verify .\HelloEPA.epa
```

Run it:

```powershell
cubes run .\HelloEPA.epa
```

Arguments can be passed to the application after `--`:

```powershell
cubes run .\HelloEPA.epa -- --mode demo
```

## Application icons

Add an image at `assets/icon.png` in an EPA project to use it as that app's icon. When Cubes Archive launches the EPA, it automatically applies the image to Tkinter `Tk` and `Toplevel` windows. If the app does not include that file, Cubes Archive uses its bundled `assets/icon.png` icon instead. This automatic window-icon integration applies to Tkinter applications; other GUI frameworks must load their icon using their own APIs.

The `.epa` file association icon is shared by Windows for the file type. The per-app icon is applied to the running Tkinter window, not to every `.epa` file in Explorer.

## EPA format, version 1

An EPA is a ZIP archive with the `.epa` extension. Its root must contain `epa.json` and the entrypoint declared in that manifest.

Example layout:

```text
HelloEPA.epa
├── epa.json
├── main.py
└── assets/
    └── icon.png
```

Example `epa.json`:

```json
{
  "format": "EPA",
  "format_version": 1,
  "name": "Hello EPA",
  "version": "1.0.0",
  "publisher": "Cubes, Studio.",
  "description": "A sample EPA application.",
  "entrypoint": "main.py"
}
```

The `publisher` field is a publisher-supplied display label. In this initial release it is **not cryptographically authenticated** and must not be treated as proof of identity.

## Commands

| Command | Description |
| --- | --- |
| `cubes create FOLDER` | Package a project folder as an EPA |
| `cubes inspect FILE.epa` | Display the archive manifest |
| `cubes verify FILE.epa` | Check archive structure and ZIP integrity |
| `cubes run FILE.epa` | Extract to a temporary directory and run its entrypoint |
| `cubes install-windows` | Register the .epa file association for the current user |
| `cubes uninstall-windows` | Remove the Cubes Archive .epa association |
| `cubes gui` | Open the Tkinter desktop interface |
| `cubes update` | Reinstall the latest version from the official GitHub repository |
| `cubes create-shortcut` | Create a Desktop shortcut that opens the GUI |
| `cubes --version` | Display the runtime version |
| `cubes --help` | Display help |

Run `cubes COMMAND --help` for command-specific options.

## Security and trust model

Cubes Archive is a launcher and packaging format, **not a sandbox**.

- EPA applications execute with the permissions of the current Windows user.
- An EPA can read or modify files and access resources that the launching user can access.
- The runtime extracts an archive to a temporary directory before launching it.
- The runtime rejects absolute paths and parent-directory traversal paths in archive entries.
- `cubes verify` checks the ZIP container, manifest, entrypoint, and archive paths. It does not perform malware analysis.
- A publisher name in `epa.json` is self-asserted in this version.
- SHA-256 is useful for comparing file contents against a separately trusted hash, but a hash stored beside a file does not authenticate its publisher.
- Cubes Archive does not bypass Microsoft Defender, Smart App Control, SmartScreen, or Windows code-signing requirements. It does not make an unsigned EXE a Windows-verified publisher.

Do not run an EPA unless you trust its source and understand that it contains executable code.

## Current limitations

This is an early CLI-focused release.

- The graphical interface uses Tkinter, which must be included with your Python installation.
- Windows integration is opt-in and per-user; a conventional signed installer is not included.
- Desktop shortcut creation is supported; automatic shortcut removal is not.
- No cryptographic publisher signatures yet.
- No sandbox or permission isolation.
- Applications must provide their own dependencies or use modules available to the Python interpreter running Cubes Archive.

## Development

The implementation currently relies on the Python standard library. Run the CLI locally with:

```powershell
py -m cubes_archive --help
```

Contributions, bug reports, and feature suggestions are welcome through GitHub Issues and Pull Requests.

## License

Cubes Archive is released under the **MIT License**. See [LICENSE](LICENSE).

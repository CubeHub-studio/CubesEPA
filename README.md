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
| `cubes create-shortcut` | Create a Desktop shortcut to CLI help |
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

- No graphical interface.
- No Windows installer or automatic `.epa` file association yet.
- No desktop shortcut management yet.
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

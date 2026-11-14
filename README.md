# CubesEPA / Cubes Archive

**CubesEPA** creates, inspects, verifies, and launches **Executable Python Archives** (.epa).

An EPA is a ZIP-based application bundle containing epa.json, a Python entrypoint, application files, and a required root-level requirements.txt.

> **Security notice:** EPA files contain executable code. The warning dialog is a confirmation step, not a sandbox or malware scan. Only run files from sources you trust.

## Features

- Create and run .epa applications.
- Require a root-level requirements.txt in every EPA (it may be empty).
- Show a safety dialog before installing dependencies or launching the app. Continue must be clicked twice.
- Install declared dependencies with the active Python interpreter's pip.
- Apply an EPA assets/icon.png to Tkinter windows, with the CubesEPA icon as fallback.
- Tkinter desktop interface and Windows Desktop shortcut.
- Per-user Windows file association.

## Requirements

- Python 3.10+
- Tkinter (normally included with Windows Python installations)
- Internet access when pip needs to download packages, or when updating CubesEPA.

## Install / update

From the repository folder:

```powershell
py -m pip install --user --upgrade .
```

Or run `cubes update` to reinstall the latest GitHub main branch. Updating is free and requires internet access.

## Desktop shortcut

Run:

```powershell
cubes create-shortcut
```

This creates CubesEPA.lnk in the actual Windows Desktop folder, including a redirected Desktop such as OneDrive. The GUI also creates this shortcut automatically the first time it opens on Windows. Double-click it whenever you want to open CubesEPA. It does not automatically start CubesEPA at Windows sign-in.

## Create an EPA

Every project folder must contain main.py and a root-level requirements.txt. The requirements file may be empty when the app uses only the Python standard library.

Example:

```text
HelloEPA/
├── main.py
└── requirements.txt
```

Example requirements.txt:

```text
requests>=2.32
pillow>=10
```

Create and run:

```powershell
cubes create .\HelloEPA --publisher "Cubes, Studio." --app-version 1.0.0
cubes verify .\HelloEPA.epa
cubes run .\HelloEPA.epa
```

Before CubesEPA installs dependencies or starts the app, a warning window appears. Click Continue twice to proceed, or Cancel. If pip cannot install a dependency, the EPA is not launched.

## Commands

| Command | Purpose |
|---|---|
| cubes gui | Open the desktop interface |
| cubes create FOLDER | Package a project |
| cubes run FILE.epa | Confirm and launch an EPA |
| cubes inspect FILE.epa | Show EPA metadata |
| cubes verify FILE.epa | Check archive structure and integrity |
| cubes create-shortcut | Create the Desktop shortcut |
| cubes install-windows | Register the .epa file association for this user |
| cubes uninstall-windows | Remove the association |
| cubes update | Update from official GitHub main |
| cubes --version | Show version |

## Security model

CubesEPA is **not a sandbox**. After confirmation, an EPA runs with the permissions of the current Windows user. Python packages in requirements.txt are installed into the active Python environment and may execute installation code. The Continue-twice prompt is a deliberate speed bump, not proof that the app is safe. The publisher field is self-declared and is not cryptographically authenticated.

## License

MIT. See LICENSE.

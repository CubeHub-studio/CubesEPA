# CubesEPA / Cubes Archive

**CubesEPA** creates, inspects, verifies, and launches **Executable Python Archives** (.epa).

An EPA is a ZIP-based application bundle containing epa.json, a Python entrypoint, application files, and a required root-level requirements.txt.

> **Security notice:** EPA files contain executable code. The warning dialog is a confirmation step, not a sandbox or malware scan. Only run files from sources you trust.

## Features

- Create and run .epa applications.
- Support an optional root-level requirements.txt using standard pip version specifiers.
- Show a safety dialog before installing dependencies or launching the app. Continue must be clicked twice.
- Optional Windows administrator elevation through the genuine UAC prompt when an EPA is packaged with `--require-admin`; ordinary EPAs do not request elevation.
- Install declared dependencies with the active Python interpreter's pip; if requirements.txt is absent, assume no third-party dependencies are needed.
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

Or run `cubes update` to reinstall the latest GitHub main branch. On Windows, this also recreates the CubesEPA Desktop shortcut so it points to the current Python runtime and icon. Updating is free and requires internet access.

## Desktop shortcut

Run:

```powershell
cubes create-shortcut
```

This creates CubesEPA.lnk in the actual Windows Desktop folder, including a redirected Desktop such as OneDrive. The GUI also creates this shortcut automatically the first time it opens on Windows. Double-click it whenever you want to open CubesEPA. It does not automatically start CubesEPA at Windows sign-in.

## Create an EPA

Every project folder must contain main.py. Add requirements.txt only when the app needs third-party packages; omit it when the app uses only the Python standard library or packages already available in the runtime.

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

To update an existing EPA in place after changing its source folder, run:\n\n```powershell\ncubes update-epa .\\MyEPA.epa .\\MyEPA\n```\n\nThis rebuilds the same `.epa` file, preserving its app name, app version, publisher, description, administrator requirement, and any additional manifest metadata. It updates the recorded CubesEPA packaging version.\n\nCreate and run:

```powershell
cubes create .\HelloEPA --publisher "Cubes, Studio." --app-version 1.0.0
cubes verify .\HelloEPA.epa
cubes run .\HelloEPA.epa
```

Before CubesEPA installs dependencies or starts the app, a warning window appears. Click Continue twice to proceed, or Cancel. The EPA metadata records the CubesEPA runtime version used to create it. If that version differs from the installed runtime—or is missing in an older EPA—the warning also explains that compatibility is not guaranteed. If pip cannot install a dependency, the EPA is not launched.

## Commands

| Command | Purpose |
|---|---|
| cubes gui | Open the desktop interface |
| cubes create FOLDER | Package a project |\n| cubes update-epa FILE.epa SOURCE | Replace an existing EPA with the latest source files while preserving its metadata |
| cubes run FILE.epa | Confirm and launch an EPA |
| cubes inspect FILE.epa | Show EPA metadata |
| cubes verify FILE.epa | Check archive structure and integrity |
| cubes create-shortcut | Create the Desktop shortcut |
| cubes install-windows | Register the .epa file association for this user |
| cubes uninstall-windows | Remove the association |
| cubes update | Update from official GitHub main |
| cubes --version | Show version |

## Security model

CubesEPA is **not a sandbox**. After confirmation, an EPA runs with the permissions of the current Windows user. Python packages in requirements.txt are installed into the active Python environment and may execute installation code. The Continue-twice prompt is a deliberate speed bump, not proof that the app is safe. The publisher field is self-declared and is not cryptographically authenticated. EPAs that request administrator access are clearly identified in the safety dialog; Windows then shows its genuine UAC prompt. If the user declines, the app is not launched. Dependencies are installed before elevation and are not installed as administrator.

## License

MIT. See LICENSE.

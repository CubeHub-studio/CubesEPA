# CubesEPA / Cubes Archive

**CubesEPA** creates, inspects, verifies, and launches **Executable Python Archives** (.epa).

An EPA is a ZIP-based application bundle containing `epa.json`, a Python entrypoint (currently `main.py`), application files, and an optional root-level `requirements.txt`.

> **Security notice:** EPA files contain executable code. The confirmation dialog is a warning step, not a sandbox or malware scan. Only run EPA files from sources you trust.

## Features

- Create, inspect, verify, and run `.epa` applications.
- Support an optional root-level `requirements.txt` using standard pip requirement syntax.
- Show a safety dialog before installing dependencies or launching an app. Continue must be clicked twice.
- Enable silent execution by default, with an option to show a PowerShell window and live logs.
- Optional Windows administrator elevation through the genuine UAC prompt when an EPA is packaged with `--require-admin`; ordinary EPAs do not request elevation.
- Install declared dependencies with the active Python interpreter's pip. If `requirements.txt` is absent or empty, no dependencies are installed.
- Apply an EPA's `assets/icon.png` to Tkinter windows, with the CubesEPA icon as fallback.
- Optional `--allowsuperfullscreen` packaging flag adds an F11 fullscreen toggle to Tkinter windows.
- Tkinter desktop interface and Windows Desktop shortcut.
- Per-user Windows `.epa` file association.

## Requirements

- Python 3.10+
- Tkinter (normally included with Windows Python installations)
- pip
- Internet access when pip needs to download packages or when updating CubesEPA from GitHub

## Windows installation

The recommended Windows setup uses the one-step PowerShell bootstrapper. Run this in PowerShell; it downloads the official repository temporarily, installs CubesEPA, adds Python's user Scripts directory to your **user** PATH, registers the `.epa` association, and creates a Desktop shortcut. No Git clone is needed:

```powershell
irm https://raw.githubusercontent.com/CubeHub-studio/CubesEPA/main/setup-windows.ps1 | iex
```

You can also clone the repository and run `.install-windows.ps1` directly. The installer normally requires no administrator privileges.

No administrator privileges are required. The installer writes the file association under the current user's registry and changes only the current user's PATH. It also updates the current PowerShell process so `cubes` is available immediately; open a new terminal for the persistent PATH change to take effect in other sessions.

The installer accepts these optional switches:

```powershell
.\install-windows.ps1 -SkipFileAssociation
.\install-windows.ps1 -SkipDesktopShortcut
```

### Manual Windows installation

If local PowerShell policy prevents running the script, do not weaken or bypass that policy. Run the equivalent commands manually from the repository folder:

```powershell
py -3 -m pip install --user --upgrade .
$scripts = py -3 -c "import sysconfig; print(sysconfig.get_path('scripts', sysconfig.get_preferred_scheme('user')))"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ";") -notcontains $scripts) {
    $newPath = if ([string]::IsNullOrWhiteSpace($userPath)) { $scripts } else { "$userPath;$scripts" }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}
$env:Path += ";$scripts"
cubes --version
cubes install-windows
cubes create-shortcut
```

`py -3` uses the Python Launcher to select the default installed Python 3 interpreter. Cubes Archive requires version 3.10 or newer.

### File association and shortcut

- `cubes install-windows` registers `.epa` for the current Windows user under `HKEY_CURRENT_USER\Software\Classes`; it does not require administrator access.
- Windows' protected `UserChoice` setting may take precedence over this registration. If double-clicking still opens another app, choose the preferred app for `.epa` in Windows Settings.
- The installer reports a conflict rather than replacing another application's existing `.epa` association.
- `cubes create-shortcut` creates `CubesEPA.lnk` in the actual Windows Desktop folder, including a redirected Desktop such as OneDrive.
- The shortcut opens the CubesEPA desktop interface. It does not start CubesEPA automatically when Windows signs in.

## Update CubesEPA

From the repository folder, install the checked-out version:

```powershell
py -3 -m pip install --user --upgrade .
```

Use the separate Windows updater when you want the full update workflow:

```powershell
.\update-windows.ps1
```

It opens a separate PowerShell window, requests administrator permission so it can stop both ordinary and elevated EPA processes, installs the latest `main` branch, deletes the old Desktop shortcut, creates a fresh one, displays its logs, and closes the window when finished. Updating is free and requires internet access. The simpler `cubes update` command remains available and refreshes the shortcut without the full process-stop workflow.

## Uninstall

From the repository folder, run:

```powershell
.\uninstall-windows.ps1
```

The uninstaller removes Cubes Archive's `.epa` registration, removes the CubesEPA Desktop shortcut, and uninstalls the `cubes-archive` Python package for the default Python 3 installation. It intentionally leaves the Python user Scripts directory on PATH because other Python command-line tools may use that shared directory.

To uninstall manually:

```powershell
cubes uninstall-windows
$desktop = [Environment]::GetFolderPath("Desktop")
Remove-Item -LiteralPath (Join-Path $desktop "CubesEPA.lnk") -ErrorAction SilentlyContinue
py -3 -m pip uninstall cubes-archive
```

If you installed Cubes Archive into a specific Python version rather than the default `py -3` interpreter, use that same interpreter selector for pip uninstall (for example, `py -3.14 -m pip uninstall cubes-archive`).

## Create an EPA

Every project folder must contain `main.py`. Add `requirements.txt` only when the app needs third-party packages; omit it when the app uses only the Python standard library or dependencies already available in the selected Python environment.

Example:

```text
HelloEPA/
├── main.py
└── requirements.txt
```

Example `requirements.txt`:

```text
requests>=2.32
pillow>=10
```

Create, verify, and run:

```powershell
cubes create .\HelloEPA --publisher "Cubes, Studio." --app-version 1.0.0 --allowsuperfullscreen
cubes verify .\HelloEPA.epa
cubes run .\HelloEPA.epa
```

You can also double-click an `.epa` file after registering the association, subject to Windows' default-app settings.

Before CubesEPA installs dependencies or starts the app, a warning window appears. Click Continue twice to proceed, or Cancel. The "Run silently" option is enabled by default; clear it to show a PowerShell window with live logs. If the EPA's recorded CubesEPA packaging version differs from the installed runtime—or is missing in an older EPA—the warning also explains that compatibility is not guaranteed. If pip cannot install a dependency, the EPA is not launched.

### F11 fullscreen support (Tkinter)

Add `--allowsuperfullscreen` to `cubes create` to enable F11 fullscreen toggling in the EPA's Tkinter windows:

```powershell
cubes create .\MyEPA --name "My EPA" --publisher "Your Publisher" --allowsuperfullscreen
```

Press F11 to enter fullscreen; press it again to restore the previous window size and state. This is opt-in and applies to Tkinter root windows and their `Toplevel` windows while the application has focus. Other GUI toolkits are not affected. Without the flag, CubesEPA does not install this shortcut.

To rebuild an existing EPA in place after changing its source folder, run:

```powershell
cubes update-epa .\MyEPA.epa .\MyEPA
```

This rebuilds the same `.epa` file, preserving its app name, app version, publisher, description, administrator requirement, fullscreen setting, and additional manifest metadata. It updates the recorded CubesEPA packaging version.

## Commands

| Command | Purpose |
|---|---|
| `cubes gui` | Open the desktop interface |
| `cubes create FOLDER` | Package a project; supports `--allowsuperfullscreen` for Tkinter F11 fullscreen toggling |
| `cubes update-epa FILE.epa SOURCE` | Rebuild an existing EPA from updated source files |
| `cubes run FILE.epa` | Confirm and launch an EPA |
| `cubes inspect FILE.epa` | Show EPA metadata |
| `cubes verify FILE.epa` | Check archive structure and integrity |
| `cubes create-shortcut` | Create the Desktop shortcut |
| `cubes install-windows` | Register `.epa` for the current Windows user |
| `cubes uninstall-windows` | Remove Cubes Archive's `.epa` registration |
| `cubes update` | Update from official GitHub `main` |
| `cubes --version` | Show the installed runtime version |

## Security model and Windows warnings

CubesEPA is **not a sandbox**. After confirmation, an EPA runs as Python code with the permissions of the current Windows user. It can access files, devices, and network resources available to that account. An EPA that explicitly requests administrator access runs with elevated permissions only after the user approves Windows' genuine UAC prompt.

A `requirements.txt` is installed into the active Python environment before launch. Python package installation can itself execute code, so review dependency names and sources. Dependencies are installed before administrator elevation and are not installed as administrator.

The publisher field in `epa.json` is self-declared. It does not establish publisher identity, cryptographic authenticity, or trust. `verify` checks archive structure and ZIP integrity; it does not prove that an EPA is safe or that its publisher is genuine.

CubesEPA does not disable or bypass Windows Smart App Control, SmartScreen, Microsoft Defender, UAC, or publisher verification. This project does not provide a signed MSI/EXE installer or a code-signing identity; depending on Windows configuration and the origin of a downloaded file, Windows may show warnings or block it. The PowerShell setup scripts do not change those security settings.

## License

MIT. See [LICENSE](LICENSE).

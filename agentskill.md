# CubesEPA Agent Skill

Instructions for AI coding agents that need to create, package, inspect, or validate
CubesEPA Executable Python Archives (`.epa`).

## 1. What an EPA is

An `.epa` file is a ZIP archive containing a Python application and its metadata.
CubesEPA extracts the archive to a temporary working directory and runs the Python
entrypoint with the active user's Python interpreter.

An EPA is **not** a standalone executable and is **not** a sandbox. The application
runs with the permissions of the current user.

Use the official CubesEPA CLI to create archives whenever possible. Do not invent a
different archive layout or metadata schema.

## 2. Required project layout

Every source project must contain a root-level `main.py`.

Example:

```text
MyEPA/
├── main.py
├── requirements.txt       # Optional
├── assets/
│   ├── icon.png           # Optional; used as the app icon where supported
│   └── ...
├── modules/
│   └── helper.py
└── data/
    └── ...
```

Rules:

- `main.py` is the required entrypoint for projects packaged with the current CLI.
- Keep imports and paths compatible with the extracted project directory.
- Include all files the application needs at runtime: Python modules, images, fonts,
  data files, configuration templates, and other assets.
- Use paths relative to the application directory where practical. In Python, a
  reliable pattern is to derive paths from `Path(__file__).resolve().parent`.
- An optional `assets/icon.png` is recognized by CubesEPA's icon integration.
- Do not include generated caches such as `__pycache__`, temporary files, local
  virtual environments, or development-only files unless the application truly needs
  them.
- Do not create your own `epa.json` in the source project. The CubesEPA packager
  generates it. The name `epa.json` is reserved.

## 3. Dependencies

A root-level `requirements.txt` is optional.

- If the app only uses the Python standard library, omit `requirements.txt`.
- If the app needs third-party packages, include a root-level `requirements.txt`.
- Use normal pip requirement syntax and sensible version constraints, for example:

```text
requests>=2.32
Pillow>=10
```

Do not list standard-library modules such as `tkinter`, `json`, `pathlib`, or
`random` as pip dependencies.

At launch, CubesEPA installs declared dependencies using the active Python
interpreter's pip before starting the application. These packages are installed into
that Python environment, not into a private per-EPA virtual environment. Dependency
installation may modify the user's existing Python environment and may require
internet access.

Never add a dependency merely because it is familiar or convenient. Prefer the
standard library when it is sufficient, and include only packages actually imported
or required by the app.

## 4. EPA metadata

The packager writes a UTF-8 JSON file named `epa.json` at the archive root.
The current format uses this structure:

```json
{
  "format": "EPA",
  "format_version": 1,
  "name": "My EPA",
  "version": "1.0.0",
  "publisher": "Publisher name",
  "description": "Short description of the application.",
  "entrypoint": "main.py",
  "cubesepa_version": "0.3.3",
  "require_admin": false
}
```

Field meanings:

| Field | Meaning |
|---|---|
| `format` | Must be exactly `EPA`. |
| `format_version` | Current archive format version; must be integer `1`. |
| `name` | Human-readable application name; required and non-empty. |
| `version` | Application's own version; required and non-empty. |
| `publisher` | Publisher label; required and non-empty. It is self-declared, not verified. |
| `description` | Short application description. |
| `entrypoint` | Path inside the archive to the Python entrypoint. The current CLI packager sets this to `main.py`. |
| `cubesepa_version` | CubesEPA runtime version used to compile/package the archive. The packager fills this in automatically. |
| `require_admin` | Boolean. When `true`, requests Windows administrator privileges at launch through the official UAC prompt. Defaults to `false`. |

When using `cubes create`, do not manually write or override this metadata. The
CLI generates it and records the installed CubesEPA version. Use the
`--require-admin` option when an app genuinely needs administrator privileges;
do not hand-edit the generated manifest.

Older archives may lack `cubesepa_version`. The runtime can display a compatibility
warning when this value is missing or differs from the installed runtime version.

## 5. Create an EPA with the CLI

The preferred packaging workflow is:

1. Finish the application in its project directory.
2. Confirm that the project contains `main.py`.
3. Add `requirements.txt` only if third-party dependencies are needed.
4. Include all runtime assets and modules.
5. Run the CubesEPA packager from the project directory or provide its path.

Example in PowerShell:

```powershell
cubes create .\MyEPA --name "My EPA" --app-version 1.0.0 --publisher "Your Publisher" --description "What the app does"
```

This creates `MyEPA.epa` in the current working directory when no output path is
specified. To choose an explicit output path:

```powershell
cubes create .\MyEPA --output .\dist\MyEPA.epa --name "My EPA" --app-version 1.0.0 --publisher "Your Publisher"
```

The output directory is created if needed. The source project must be outside the
output archive's destination directory; the packager prevents writing the output
inside the source tree.

The CLI recursively includes regular files from the project directory, preserving
their relative paths. It rejects symbolic links and reserves `epa.json` for generated
metadata. The resulting file is a ZIP archive using DEFLATE compression.

## 6. Validate the archive

After creating an archive, run both checks:

```powershell
cubes inspect .\MyEPA.epa
cubes verify .\MyEPA.epa
```

- `inspect` displays the metadata and file/dependency information.
- `verify` checks ZIP integrity, archive member paths, required metadata, and the
  entrypoint's presence.

These checks do **not** prove that the code is safe, that the publisher is authentic,
or that the application will work correctly. If possible, test the application
separately in a disposable development environment before distributing it.

To launch an archive manually:

```powershell
cubes run .\MyEPA.epa
```

The user must confirm the safety warning before dependencies are installed or the
application is run. The warning is not a sandbox or malware scan.

### Requesting administrator privileges (Windows only)

Most EPAs must run without administrator privileges. Only request elevation when
the application's core function genuinely requires it.

Create an EPA with the opt-in flag:

```powershell
cubes create .\\MyEPA --name "My EPA" --publisher "Your Publisher" --require-admin
```

This writes `"require_admin": true` into `epa.json`. Without the flag, the
packager writes `false` and the EPA runs normally.

At launch, CubesEPA explicitly identifies the administrator request in its safety
dialog. After the user confirms that dialog, Windows displays its genuine UAC
consent prompt. The application is launched elevated only if the user approves.
If the user declines, the EPA is not launched. CubesEPA does not bypass, imitate,
or suppress UAC.

Declared Python dependencies are installed before the elevated application starts;
dependency installation itself is not elevated. Administrator elevation is
currently supported only on Windows. An EPA marked `require_admin: true` fails
with a clear message on other operating systems rather than silently running
without the requested privileges.

Do not request administrator access for convenience, and never try to relaunch
yourself through hidden or deceptive elevation mechanisms. Explain to the user
which specific operation needs administrator access.

## 7. Archive layout

A typical finished archive contains:

```text
MyEPA.epa  (ZIP container)
├── epa.json
├── main.py
├── requirements.txt       # Only when needed
├── assets/
│   ├── icon.png
│   └── ...
├── modules/
│   └── helper.py
└── data/
    └── ...
```

The archive root is the project root. Do not put the entire project inside an extra
nested folder unless the entrypoint and all application paths are deliberately
configured for that layout. With the current `cubes create` command, the root
`main.py` requirement is enforced and the generated entrypoint is `main.py`.

## 8. Runtime behavior agents must account for

- CubesEPA extracts archive contents into a temporary directory before launch.
- The application working directory is set to the extracted project directory.
- The launcher sets `CUBES_EPA_NAME` and `CUBES_EPA_ICON` environment variables.
- The icon variable points to the resolved icon path; a default CubesEPA icon may be
  used if the project does not supply a supported icon.
- The safety confirmation appears before dependency installation and app execution.
- The user can choose silent launch or visible PowerShell logging in supported
  Windows runtime versions. Do not assume logs are always visible.
- Temporary extracted files are cleaned up when the launch process finishes.
- The application should save persistent user data to an intentional user-data
  location, not rely on writing into the temporary extraction directory.

## 9. Security and quality requirements

AI agents creating EPAs must follow these rules:

- Do not add code that steals credentials, accesses private data without permission,
  damages files, disables security tools, hides persistence, or performs other
  unauthorized actions.
- Do not describe an EPA as sandboxed, inherently safe, or publisher-authenticated.
- Treat every third-party dependency and install script as executable code.
- Do not silently add network access, telemetry, auto-updaters, or background
  behavior. Explain such behavior and obtain the user's approval where appropriate.
- Do not bundle secrets, API keys, passwords, tokens, or private user data.
- Keep the app's dependencies minimal and document any non-obvious runtime setup.
- Handle expected errors gracefully and provide useful messages.
- Test the app's normal startup path and verify the final archive before reporting
  completion.
- Never claim that an archive was built or tested unless the corresponding command
  actually succeeded.

## 10. Completion report

When you finish creating an EPA, report:

1. The output path and archive filename.
2. The application name and version.
3. Whether `requirements.txt` was included and which third-party dependencies it
   declares.
4. Whether `cubes inspect` and `cubes verify` succeeded.
5. Any testing not performed or known limitations.

Prefer using the installed `cubes` command. If it is unavailable, tell the user that
CubesEPA must be installed before using its packager; do not fabricate an archive or
substitute an undocumented format.

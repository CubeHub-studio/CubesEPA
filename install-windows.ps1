[CmdletBinding()]
param(
    [switch]$SkipFileAssociation,
    [switch]$SkipDesktopShortcut
)

$ErrorActionPreference = "Stop"

$repoRoot = if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $PSScriptRoot
}
elseif (-not [string]::IsNullOrWhiteSpace($env:CUBESEPA_INSTALLER_ROOT)) {
    $env:CUBESEPA_INSTALLER_ROOT
}
else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot "pyproject.toml"))) {
    throw "Run this installer from a CubesEPA repository checkout."
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "The Python Launcher ('py') was not found. Install Python 3.10 or newer from python.org, then reopen PowerShell."
}

$pythonDetails = @(
    & py -3 -c "import sys, sysconfig; print('{0}.{1}'.format(sys.version_info.major, sys.version_info.minor)); print(sysconfig.get_path('scripts', sysconfig.get_preferred_scheme('user')))"
)
if ($LASTEXITCODE -ne 0 -or $pythonDetails.Count -lt 2) {
    throw "Could not query the default Python 3 installation. Check that Python 3 and pip are installed."
}

try {
    $pythonVersion = [version]$pythonDetails[0].Trim()
}
catch {
    throw "Could not understand the Python version returned by 'py -3'."
}
if ($pythonVersion -lt [version]"3.10") {
    throw "Cubes Archive requires Python 3.10 or newer. Found Python $pythonVersion."
}

$scriptsDirectory = $pythonDetails[1].Trim()
if ([string]::IsNullOrWhiteSpace($scriptsDirectory)) {
    throw "Python did not report a user Scripts directory."
}

Write-Host "Installing Cubes Archive for Python $pythonVersion..."
& py -3 -m pip install --user --upgrade $repoRoot
if ($LASTEXITCODE -ne 0) {
    throw "pip installation failed with exit code $LASTEXITCODE."
}

$cubesExe = Join-Path $scriptsDirectory "cubes.exe"
if (-not (Test-Path -LiteralPath $cubesExe)) {
    throw "Installation completed, but the expected CLI was not found at '$cubesExe'."
}

# Add only this Python user Scripts directory. Do not overwrite the user's PATH.
$pathEntries = @()
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not [string]::IsNullOrWhiteSpace($userPath)) {
    $pathEntries = @($userPath -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

$trimChars = [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
$normalizedScripts = [IO.Path]::GetFullPath($scriptsDirectory).TrimEnd($trimChars)
$alreadyInUserPath = $false

foreach ($entry in $pathEntries) {
    $candidate = [Environment]::ExpandEnvironmentVariables($entry.Trim().Trim('"'))
    try {
        $candidate = [IO.Path]::GetFullPath($candidate).TrimEnd($trimChars)
    }
    catch {
        # Keep an unusual PATH entry unchanged; it cannot match the resolved path.
    }

    if ([string]::Equals($candidate, $normalizedScripts, [StringComparison]::OrdinalIgnoreCase)) {
        $alreadyInUserPath = $true
        break
    }
}

if (-not $alreadyInUserPath) {
    $newUserPath = (@($pathEntries) + $scriptsDirectory) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
}

# Update this PowerShell process too, so the CLI works immediately.
$processEntries = @($env:Path -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if (-not ($processEntries -contains $scriptsDirectory)) {
    if ([string]::IsNullOrWhiteSpace($env:Path)) {
        $env:Path = $scriptsDirectory
    }
    else {
        $env:Path = "$env:Path;$scriptsDirectory"
    }
}

Write-Host "Added Python's user Scripts directory to the user PATH."

if (-not $SkipFileAssociation) {
    & $cubesExe install-windows
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "The .epa association was not changed. Another application may already own the association; you can choose the default app in Windows Settings."
    }
}

if (-not $SkipDesktopShortcut) {
    & $cubesExe create-shortcut
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "The CubesEPA Desktop shortcut could not be created."
    }
}

Write-Host ""
Write-Host "Cubes Archive installation finished."
Write-Host "CLI: $cubesExe"
Write-Host "Open a new PowerShell window to use the updated PATH in future sessions."

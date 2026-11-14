[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "The Python Launcher ('py') is required to uninstall the Cubes Archive package."
}

$pythonDetails = @(
    & py -3 -c "import sysconfig; print(sysconfig.get_path('scripts', sysconfig.get_preferred_scheme('user')))"
)
$scriptsDirectory = $null
if ($LASTEXITCODE -eq 0 -and $pythonDetails.Count -gt 0) {
    $scriptsDirectory = $pythonDetails[0].Trim()
}

$cubesExe = if ($scriptsDirectory) {
    Join-Path $scriptsDirectory "cubes.exe"
}
else {
    $null
}

# Remove the association before uninstalling the Python package that owns it.
if ($cubesExe -and (Test-Path -LiteralPath $cubesExe)) {
    & $cubesExe uninstall-windows
    if ($LASTEXITCODE -ne 0) {
        throw "Could not remove the .epa file association. The runtime was left installed."
    }
}
else {
    & py -3 -m cubes_archive uninstall-windows
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "The .epa association could not be checked through the installed runtime."
    }
}

$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
if (-not [string]::IsNullOrWhiteSpace($desktop)) {
    $shortcut = Join-Path $desktop "CubesEPA.lnk"
    if (Test-Path -LiteralPath $shortcut) {
        Remove-Item -LiteralPath $shortcut -Force
        Write-Host "Removed Desktop shortcut: $shortcut"
    }
}

Write-Host "Uninstalling Cubes Archive..."
& py -3 -m pip uninstall -y cubes-archive
if ($LASTEXITCODE -ne 0) {
    throw "pip could not uninstall cubes-archive (exit code $LASTEXITCODE)."
}

Write-Host ""
Write-Host "Cubes Archive was uninstalled for the default Python 3 installation."
Write-Host "The Python user Scripts directory was left on PATH because other Python tools may use it."

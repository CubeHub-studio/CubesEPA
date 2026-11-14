[CmdletBinding()]
param([switch]$Child)

$ErrorActionPreference = "Stop"

# Always run the update in its own visible PowerShell window.
if (-not $Child) {
    $powershell = Join-Path $PSHOME "powershell.exe"
    $script = $PSCommandPath
    Start-Process -FilePath $powershell -ArgumentList @(
        "-NoProfile", "-File", "`"$script`"", "-Child"
    ) -WindowStyle Normal
    exit 0
}

$exitCode = 0
try {
    Write-Host "CubesEPA updater" -ForegroundColor Cyan
    Write-Host "Searching for running EPA processes..."

    # Elevation ensures the updater can stop EPAs that were themselves launched as administrator.
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "Requesting administrator permission to stop every EPA process..."
        $powershell = Join-Path $PSHOME "powershell.exe"
        $script = $PSCommandPath
        Start-Process -FilePath $powershell -Verb RunAs -ArgumentList @(
            "-NoProfile", "-File", "`"$script`"", "-Child"
        ) -WindowStyle Normal
        exit 0
    }

    $processes = @(
        Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match '^(pythonw?\.exe|cubes\.exe)$' -and
            $_.CommandLine -and
            (
                $_.CommandLine -match '(?i)-m\s+cubes_archive\s+run\b' -or
                $_.CommandLine -match '(?i)-m\s+cubes_archive\.launcher\b' -or
                $_.CommandLine -match '(?i)cubes(?:\.exe)?\s+run\b'
            )
        }
    )

    foreach ($process in $processes) {
        Write-Host ("Stopping EPA process {0} (PID {1})..." -f $process.Name, $process.ProcessId)
        Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
    }
    if ($processes.Count -gt 0) {
        Start-Sleep -Seconds 2
        Write-Host ("Stopped {0} EPA process(es)." -f $processes.Count) -ForegroundColor Green
    }
    else {
        Write-Host "No running EPA processes were found."
    }

    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw "Python Launcher 'py' was not found. Install Python 3.10+ and try again."
    }

    Write-Host ""
    Write-Host "Installing the latest CubesEPA version from the official GitHub repository..."
    & py -3 -m pip install --user --upgrade --force-reinstall "https://github.com/CubeHub-studio/CubesEPA/archive/refs/heads/main.zip"
    if ($LASTEXITCODE -ne 0) {
        throw "CubesEPA installation failed (pip exit code $LASTEXITCODE)."
    }

    Write-Host ""
    Write-Host "Removing the old Desktop shortcut..."
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcut = Join-Path $desktop "CubesEPA.lnk"
    if (Test-Path -LiteralPath $shortcut) {
        Remove-Item -LiteralPath $shortcut -Force
    }

    Write-Host "Creating a fresh Desktop shortcut..."
    & py -3 -m cubes_archive.cli create-shortcut
    if ($LASTEXITCODE -ne 0) {
        throw "The runtime updated, but shortcut creation failed (exit code $LASTEXITCODE)."
    }

    Write-Host ""
    Write-Host "CubesEPA update completed successfully." -ForegroundColor Green
}
catch {
    $exitCode = 1
    Write-Host ""
    Write-Host ("UPDATE FAILED: " + $_.Exception.Message) -ForegroundColor Red
}
finally {
    Write-Host ""
    Write-Host "This updater window will close in 3 seconds..."
    Start-Sleep -Seconds 3
}
exit $exitCode

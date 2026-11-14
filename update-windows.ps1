[CmdletBinding()]
param([switch]$Child)

$ErrorActionPreference = "Stop"

# Always run the update in its own visible PowerShell window.
if (-not $Child) {
    $powershell = Join-Path $PSHOME "powershell.exe"
    $script = $PSCommandPath
    Start-Process -FilePath $powershell -Verb RunAs -ArgumentList @(
        "-NoProfile", "-File", "`"$script`"", "-Child"
    ) -WindowStyle Normal
    exit 0
}

$exitCode = 0
try {
    Write-Host "CubesEPA updater" -ForegroundColor Cyan
    Write-Host "Searching for running EPA processes..."

    # This child was started with the genuine Windows UAC prompt.
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
        Write-Host ("Requesting EPA process {0} (PID {1}) to close..." -f $process.Name, $process.ProcessId)
        try {
            $runningProcess = Get-Process -Id $process.ProcessId -ErrorAction Stop
            [void]$runningProcess.CloseMainWindow()
        }
        catch {
            # A console-only or already-exiting process may not have a main window.
        }
    }
    if ($processes.Count -gt 0) {
        Write-Host "Waiting up to 5 seconds for EPA apps to close..."
        Start-Sleep -Seconds 5
        foreach ($process in $processes) {
            if (Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue) {
                Write-Host ("Force-stopping remaining EPA process PID {0}..." -f $process.ProcessId)
                Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
            }
        }
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

# CubesEPA one-step Windows installer.
# Run from PowerShell with:
# irm https://raw.githubusercontent.com/CubeHub-studio/CubesEPA/main/setup-windows.ps1 | iex

$ErrorActionPreference = "Stop"
$repoZip = "https://github.com/CubeHub-studio/CubesEPA/archive/refs/heads/main.zip"
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ("CubesEPA-Setup-" + [guid]::NewGuid().ToString("N"))
$zipPath = Join-Path $tempRoot "CubesEPA.zip"

try {
    Write-Host "CubesEPA setup — downloading the official installer..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    Invoke-WebRequest -Uri $repoZip -OutFile $zipPath
    Expand-Archive -LiteralPath $zipPath -DestinationPath $tempRoot -Force

    $repoFolder = Get-ChildItem -LiteralPath $tempRoot -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "install-windows.ps1") } |
        Select-Object -First 1
    if (-not $repoFolder) {
        throw "The downloaded archive did not contain install-windows.ps1."
    }

    Write-Host "Running CubesEPA installer..." -ForegroundColor Cyan
    $installerPath = Join-Path $repoFolder.FullName "install-windows.ps1"
    $shellName = if ($PSVersionTable.PSEdition -eq "Core") { "pwsh.exe" } else { "powershell.exe" }
    $shellPath = (Get-Command $shellName -ErrorAction Stop).Source

    # Run the downloaded child script with a process-scoped policy override.
    # This does not change the user's machine-wide or current-user execution policy.
    & $shellPath -NoProfile -ExecutionPolicy Bypass -File $installerPath
    $installerExitCode = $LASTEXITCODE
    if ($installerExitCode -ne 0) {
        throw "The CubesEPA installer returned exit code $installerExitCode."
    }

    Write-Host ""
    Write-Host "CubesEPA setup completed." -ForegroundColor Green
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

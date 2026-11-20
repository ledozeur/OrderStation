# Устарело: используйте scripts/create-github-issues.ps1
Write-Host "Перенаправление на scripts/create-github-issues.ps1 ..."
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $root "scripts/create-github-issues.ps1") @args
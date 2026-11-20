#Requires -Version 5.1
<#
.SYNOPSIS
  Создаёт labels, milestones и issues в GitHub через gh CLI.

.DESCRIPTION
  Читает scripts/github-issues.manifest.json.
  Не создаёт дубликаты по точному совпадению title (если не указан -Force).

.EXAMPLE
  gh auth login
  cd C:\path\to\OrderStation
  .\scripts\create-github-issues.ps1 -SetupOnly

.EXAMPLE
  .\scripts\create-github-issues.ps1 -Week w3

.EXAMPLE
  .\scripts\create-github-issues.ps1 -Week all -DryRun

.PARAMETER Repo
  owner/repo (по умолчанию — текущий git remote)

.PARAMETER Week
  setup | w0 | w1 | w2 | w3 | w4 | all

.PARAMETER Force
  Создавать issue даже если title уже есть.

.PARAMETER DryRun
  Только вывод, без вызовов gh issue create.
#>
[CmdletBinding()]
param(
    [string]$Repo = "",
    [ValidateSet("setup", "w0", "w1", "w2", "w3", "w4", "all")]
    [string]$Week = "all",
    [switch]$Force,
    [switch]$DryRun,
    [switch]$SetupOnly
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ManifestPath = Join-Path $ScriptDir "github-issues.manifest.json"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error @"
GitHub CLI (gh) не найден.
Установка: winget install GitHub.cli
Затем: gh auth login
"@
}

if (-not $Repo) {
    try {
        $Repo = (gh repo view --json nameWithOwner -q .nameWithOwner)
    } catch {
        Write-Error "Не удалось определить репозиторий. Укажите -Repo owner/name или запустите из клонированного репо."
    }
}

Write-Host "Repository: $Repo"
Write-Host "Week filter: $Week  DryRun: $DryRun  Force: $Force"

function Invoke-GhBestEffort {
    param([Parameter(Mandatory)][string[]]$GhArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & gh @GhArgs 2>&1 | Out-Null
    $ErrorActionPreference = $prev
}

function Initialize-LabelsAndMilestones {
    $labelDefs = @(
        @{ name = "kirill"; color = "1D76DB" },
        @{ name = "andrey"; color = "F9A825" },
        @{ name = "joint"; color = "6E5494" },
        @{ name = "mentor"; color = "CCCCCC" },
        @{ name = "week-0"; color = "C5DEF5" },
        @{ name = "week-1"; color = "C5DEF5" },
        @{ name = "week-2"; color = "C5DEF5" },
        @{ name = "week-3"; color = "C5DEF5" },
        @{ name = "week-4"; color = "C5DEF5" },
        @{ name = "P0"; color = "B60205" },
        @{ name = "P1"; color = "D93F0B" },
        @{ name = "P2"; color = "0E8A16" },
        @{ name = "blocked"; color = "B60205" }
    )
    foreach ($ld in $labelDefs) {
        if ($DryRun) {
            Write-Host "[dry-run] label: $($ld.name)"
        } else {
            Invoke-GhBestEffort -GhArgs @("label", "create", $ld.name, "--repo", $Repo, "--color", $ld.color, "--force")
        }
    }

    $milestones = @(
        @{ name = "W0 — Подготовка"; desc = "День 0" },
        @{ name = "W1 — Справочники"; desc = "Неделя 1" },
        @{ name = "W2 — Заказы и BOM"; desc = "Неделя 2" },
        @{ name = "W3 — Закупка и сроки"; desc = "Неделя 3" },
        @{ name = "W4 — Релиз MVP"; desc = "Неделя 4" }
    )
    foreach ($m in $milestones) {
        if ($DryRun) {
            Write-Host "[dry-run] milestone: $($m.name)"
        } else {
            Invoke-GhBestEffort -GhArgs @(
                "api", "-X", "POST", "repos/$Repo/milestones",
                "-f", "title=$($m.name)",
                "-f", "description=$($m.desc)"
            )
        }
    }
}

function Get-ExistingIssueTitles {
    if ($DryRun) { return @() }
    $json = gh issue list --repo $Repo --state all --limit 300 --json title
    $items = $json | ConvertFrom-Json
  return @($items | ForEach-Object { $_.title })
}

if (-not (Test-Path $ManifestPath)) {
    Write-Error "Не найден манифест: $ManifestPath"
}

$allIssues = Get-Content -Path $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

if ($SetupOnly -or $Week -eq "setup") {
    Initialize-LabelsAndMilestones
    Write-Host "Готово: labels и milestones."
    if ($SetupOnly -or $Week -eq "setup") { exit 0 }
}

Initialize-LabelsAndMilestones

$weekLabel = switch ($Week) {
    "w0" { "week-0" }
    "w1" { "week-1" }
    "w2" { "week-2" }
    "w3" { "week-3" }
    "w4" { "week-4" }
    default { $null }
}

$toCreate = if ($weekLabel) {
    $allIssues | Where-Object { $_.labels -contains $weekLabel }
} else {
    $allIssues
}

$existing = Get-ExistingIssueTitles
$tmpdir = Join-Path $env:TEMP "orderstation-issues"
New-Item -ItemType Directory -Force -Path $tmpdir | Out-Null

$created = 0
$skipped = 0

foreach ($iss in $toCreate) {
    if (-not $Force -and $existing -contains $iss.title) {
        Write-Host "SKIP (exists): $($iss.title)"
        $skipped++
        continue
    }

    if ($DryRun) {
        $src = if ($iss.bodyFile) { $iss.bodyFile } else { "(inline body)" }
        Write-Host "CREATE: $($iss.title)  [$($iss.labels -join ', ')]  milestone=$($iss.milestone)  body=$src"
        $created++
        continue
    }

    if ($iss.bodyFile) {
        $bodyPath = Join-Path $ScriptDir $iss.bodyFile
        if (-not (Test-Path $bodyPath)) { Write-Error "bodyFile не найден: $bodyPath" }
    } else {
        $safeName = ($iss.title -replace '[^\w\-]', '_').Substring(0, [Math]::Min(60, ($iss.title.Length)))
        $bodyPath = Join-Path $tmpdir "$safeName.md"
        [System.IO.File]::WriteAllText($bodyPath, $iss.body, [System.Text.UTF8Encoding]::new($false))
    }

    $ghArgs = @(
        "issue", "create",
        "--repo", $Repo,
        "--title", $iss.title,
        "--body-file", $bodyPath
    )
    foreach ($l in $iss.labels) { $ghArgs += @("--label", $l) }
    if ($iss.milestone) { $ghArgs += @("--milestone", $iss.milestone) }

    & gh @ghArgs
    Write-Host "OK: $($iss.title)"
    $existing += $iss.title
    $created++
}

Write-Host "Итого: создано/запланировано $created, пропущено $skipped"
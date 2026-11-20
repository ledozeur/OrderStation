# Создание issues через GitHub CLI (опционально).
# Перед запуском: gh auth login
# Проверьте, что вы в корне репозитория с remote на GitHub.

$ErrorActionPreference = "Stop"
$Repo = (gh repo view --json nameWithOwner -q .nameWithOwner)

# gh пишет «already exists» в stderr → в PowerShell это NativeCommandError при Stop
function Invoke-GhBestEffort {
    param([Parameter(Mandatory)][string[]]$GhArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & gh @GhArgs 2>&1 | Out-Null
    $ErrorActionPreference = $prev
}

function New-GhIssue {
    param(
        [string]$Title,
        [string]$BodyFile,
        [string[]]$Labels,
        [string]$Milestone
    )
    $args = @(
        "issue", "create",
        "--repo", $Repo,
        "--title", $Title,
        "--body-file", $BodyFile
    )
    foreach ($l in $Labels) { $args += @("--label", $l) }
    if ($Milestone) { $args += @("--milestone", $Milestone) }
    & gh @args
}

# Labels (идемпотентно: пропуск если уже есть)
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
    Invoke-GhBestEffort -GhArgs @("label", "create", $ld.name, "--color", $ld.color, "--force")
}

# Milestones
$milestones = @(
    @{ name = "W0 — Подготовка"; desc = "День 0" },
    @{ name = "W1 — Справочники"; desc = "Неделя 1" },
    @{ name = "W2 — Заказы и BOM"; desc = "Неделя 2" },
    @{ name = "W3 — Закупка и сроки"; desc = "Неделя 3" },
    @{ name = "W4 — Релиз MVP"; desc = "Неделя 4" }
)
foreach ($m in $milestones) {
    Invoke-GhBestEffort -GhArgs @(
        "api", "-X", "POST", "repos/$Repo/milestones",
        "-f", "title=$($m.name)",
        "-f", "description=$($m.desc)"
    )
}

$tmpdir = Join-Path $env:TEMP "orderstation-issues"
New-Item -ItemType Directory -Force -Path $tmpdir | Out-Null

$issues = @(
    @{
        Title = "M-01: GitHub — labels, milestones, branch protection"
        Labels = @("mentor","week-0","P0")
        Milestone = "W0 — Подготовка"
        Body = @"
## Цель
Подготовить репозиторий к работе практикантов.
## Чеклист
- [ ] Push скелета в main
- [ ] Branch protection
- [ ] Практиканты — collaborators
"@
    },
    @{
        Title = "J-00: Онбординг — окружение и Swagger"
        Labels = @("joint","week-0","kirill","andrey","P0")
        Milestone = "W0 — Подготовка"
        Body = "См. полное описание в docs/GITHUB_ISSUES.md — Issue #2"
    },
    @{
        Title = "K-W1-01: Customers — поиск, валидация, тесты"
        Labels = @("kirill","week-1","P0")
        Milestone = "W1 — Справочники"
        Body = "См. docs/GITHUB_ISSUES.md — Issue #4"
    },
    @{
        Title = "A-W1-01: Parts — Pydantic-схемы"
        Labels = @("andrey","week-1","P0")
        Milestone = "W1 — Справочники"
        Body = "См. docs/GITHUB_ISSUES.md — Issue #5"
    },
    @{
        Title = "A-W1-02: Parts — CRUD API + catalog_service"
        Labels = @("andrey","week-1","P0")
        Milestone = "W1 — Справочники"
        Body = "См. docs/GITHUB_ISSUES.md — Issue #6"
    },
    @{
        Title = "A-W1-04: BOM templates — CRUD + items + preview"
        Labels = @("andrey","week-1","P0")
        Milestone = "W1 — Справочники"
        Body = "См. docs/GITHUB_ISSUES.md — Issue #8"
    },
    @{
        Title = "K-W2-03: order_service + CRUD заказов"
        Labels = @("kirill","week-2","P0")
        Milestone = "W2 — Заказы и BOM"
        Body = "См. docs/GITHUB_ISSUES.md — Issue #14"
    },
    @{
        Title = "K-W2-06: apply-template"
        Labels = @("kirill","week-2","P0")
        Milestone = "W2 — Заказы и BOM"
        Body = "См. docs/GITHUB_ISSUES.md — Issue #17"
    },
    @{
        Title = "A-W2-02: PATCH procurement + RBAC"
        Labels = @("andrey","week-2","P0")
        Milestone = "W2 — Заказы и BOM"
        Body = "См. docs/GITHUB_ISSUES.md — Issue #19"
    },
    @{
        Title = "J-W4-01: Чеклист приёмки MVP"
        Labels = @("joint","kirill","andrey","week-4","P0")
        Milestone = "W4 — Релиз MVP"
        Body = "См. docs/GITHUB_ISSUES.md — Issue #36"
    }
)

Write-Host "Создаётся $($issues.Count) ключевых issues. Полный список — 40 шт. в docs/GITHUB_ISSUES.md"
Write-Host "Дополните массив `$issues` остальными title из MD или создавайте вручную."

foreach ($iss in $issues) {
    $bodyPath = Join-Path $tmpdir "body.txt"
    Set-Content -Path $bodyPath -Value $iss.Body -Encoding UTF8
    New-GhIssue -Title $iss.Title -BodyFile $bodyPath -Labels $iss.Labels -Milestone $iss.Milestone
}

Write-Host "Готово. Repo: $Repo"
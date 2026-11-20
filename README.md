# OrderStation

Backend (REST API) для учёта заказов БПЛА: заказчики → заказ → список запчастей (типовой BOM или вручную) → статусы закупки → контроль сроков.

Работа с системой на этапе MVP — через **Swagger**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) после запуска сервера.

**Стек:** Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL или SQLite.

---

## Кто что делает (практика)

Это **не** роли в программе, а **разделение задач** между практикантами. Задачи по неделям — в GitHub Issues (см. [docs/GITHUB_ISSUES.md](docs/GITHUB_ISSUES.md)).

| | **Кирилл** | **Андрей** |
|---|------------|------------|
| **Домен** | Заказчики, заказы, сроки, отчёты | Запчасти, шаблоны BOM, закупка позиций |
| **API** (`backend/app/api/`) | `customers.py`, `orders.py`, `reports.py` | `parts.py`, `bom_templates.py`, PATCH закупки у линий заказа |
| **Сервисы** (`backend/app/services/`) | `order_service`, `reporting_service` | `catalog_service`, `bom_service`, `procurement_service` |
| **Тесты** | `test_customers`, `test_orders`, `test_reports` | `test_parts`, `test_bom`, `test_procurement` |
| **Скрипты** | — | `seed_demo_data.py`, `demo_walkthrough.py` |

**Совместно:** онбординг, согласование полей `OrderLine`, переход заказа в `in_procurement`, финальная приёмка MVP.

**Чужие файлы не правим** без issue и договорённости. `auth.py` и общий каркас — только с наставником.

**Git:** ветки `feature/KIR-...` / `feature/AND-...`, один issue — один PR, ревью у второго практиканта и наставника.

Подробная карта файлов и день 1 — [docs/onboarding.md](docs/onboarding.md).

---

## Роли **пользователей** в API (в программе)

Это то, **кто логинится** в Swagger (поле `role` у `User`):

| Роль | Что может |
|------|-----------|
| `manager` | Заказчики, заказы, ручные позиции |
| `procurement` | Менять статусы закупки по позициям |
| `viewer` | Только чтение (там, где включим проверку роли) |

Демо-логин после `scripts/create_admin_user.py`: **`admin@example.com`** / **`admin`** (роль `manager`).

---

## Документация — куда смотреть

| Файл | Для кого | Содержание |
|------|----------|------------|
| [docs/TZ.md](docs/TZ.md) | все | ТЗ MVP, критерии приёмки, план по неделям |
| [docs/GITHUB_ISSUES.md](docs/GITHUB_ISSUES.md) | все | Полный бэклог issues (40 шт.) |



### Issues через GitHub CLI

```powershell
winget install GitHub.cli   # если gh ещё нет
gh auth login
cd OrderStation
.\scripts\create-github-issues.ps1 -DryRun              # что будет создано
.\scripts\create-github-issues.ps1 -Week w3             # только Week 3
.\scripts\create-github-issues.ps1 -Week all              # весь манифест (24 issue)
.\scripts\create-github-issues.ps1 -SetupOnly             # только labels + milestones
```

Существующие issues с тем же **title** пропускаются (добавьте `-Force` для дубликатов).
| [docs/onboarding.md](docs/onboarding.md) | Кирилл, Андрей | Первый день, git-процесс, таблица файлов |
| [docs/MENTOR.md](docs/MENTOR.md) | наставник | Как проверять PR без погружения в Python |

---

## Что уже сделано в скелете

| Готово | Ещё нужно сделать (см. issues) |
|--------|--------------------------------|
| Auth (JWT), `/health` | Полный `orders`, `reports` |
| CRUD заказчиков (образец) | Parts, BOM, procurement |
| Модели БД, миграция, CI, pytest | Отчёты, seed, e2e-скрипт |

Заглушки с кодом **501** в Swagger — участки, которые заменяют практиканты.

---

## Быстрый старт

### SQLite (проще для старта, без Docker)

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy ..\.env.example ..\.env
alembic upgrade head
python scripts/create_admin_user.py
uvicorn app.main:app --reload
```

Откройте `/docs` → **Authorize** → username = `admin@example.com`, password = `admin`.

### PostgreSQL (Docker)

Из **корня** репозитория:

```powershell
docker compose up -d db
cd backend
# в ..\.env: DATABASE_URL=postgresql+psycopg://orderstation:orderstation@localhost:5432/orderstation
```

Дальше те же шаги: venv, `pip install`, `alembic upgrade head`, `create_admin_user`, `uvicorn`.

### Тесты

```powershell
cd backend
ruff check .
pytest
```

---

## Структура каталогов

```
OrderStation/
├── backend/app/api/      # HTTP-роуты
├── backend/app/services/ # бизнес-логика
├── backend/app/models/   # таблицы БД
├── backend/tests/
└── docs/                 # ТЗ, issues, онбординг
```
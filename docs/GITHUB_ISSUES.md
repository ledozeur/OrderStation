# Список GitHub Issues для OrderStation

Использование: создайте **Labels** и **Milestones**, затем копируйте каждый блок в новый issue (Title + Body).  
Либо одной пачкой через CLI (после `gh auth login`):

```powershell
cd C:\Users\User\Desktop\Стажёры\OrderStation
Get-Content docs\github-issues-bulk.ps1 | при необходимости отредактируйте и запустите
```

---

## Настройка репозитория (один раз)

### Labels

| Имя | Цвет | Назначение |
|-----|------|------------|
| `kirill` | `1D76DB` | Зона ответственности Кирилла |
| `andrey` | `F9A825` | Зона ответственности Андрея |
| `joint` | `6E5494` | Совместная задача |
| `mentor` | `CCCCCC` | Только наставник |
| `week-0` … `week-4` | любые | Спринт |
| `P0` / `P1` / `P2` | red/orange/green | Приоритет |
| `blocked` | `B60205` | Ждёт другую задачу |

### Milestones

| Milestone | Due (пример) |
|-----------|----------------|
| `W0 — Подготовка` | День 0 |
| `W1 — Справочники` | +7 дней |
| `W2 — Заказы и BOM` | +14 дней |
| `W3 — Закупка и сроки` | +21 день |
| `W4 — Релиз MVP` | +28 дней |

### Story points (для баланса)

В описании у каждой задачи поле **Points**. Цель: сумма `kirill` ≈ сумма `andrey` по каждой неделе (±2 SP).

---

## W0 — Подготовка

### Issue #1 [mentor] [week-0] [P0]

**Title:** `M-01: GitHub — labels, milestones, branch protection`

**Labels:** `mentor`, `week-0`, `P0`

**Body:**

```markdown
## Цель
Подготовить репозиторий к работе практикантов.

## Чеклист
- [ ] Push скелета в `main`
- [ ] Labels из `docs/GITHUB_ISSUES.md`
- [ ] Milestones W0–W4
- [ ] Branch protection: PR required, 1 approval (наставник или peer)
- [ ] Практиканты добавлены как collaborators

## DoD
Issues можно создавать и вешать на milestones.
```

---

### Issue #2 [joint] [week-0] [P0]

**Title:** `J-00: Онбординг — окружение и Swagger`

**Labels:** `joint`, `week-0`, `kirill`, `andrey`, `P0`  
**Points:** 2 SP (по 1 SP каждому)

**Body:**

```markdown
## Цель
Оба практиканта поднимают проект локально и проходят docs/onboarding.md.

## Шаги
1. Python 3.12+, Git; опционально Docker.
2. `cd backend` → venv → `pip install -e ".[dev]"`.
3. Скопировать `.env.example` → `.env`.
4. `alembic upgrade head` + `python scripts/create_admin_user.py`.
5. `uvicorn app.main:app --reload` → открыть `/docs`.
6. Authorize: `admin@example.com` / `admin`.
7. Выполнить: `POST /customers` → `GET /customers`.
8. Запустить `pytest -q` — все зелёные.

## DoD
- [ ] Каждый закрыл issue комментарием «скрин Swagger + pytest OK»
- [ ] Прочитан `docs/TZ.md`
```

---

### Issue #3 [joint] [week-0] [P1]

**Title:** `J-01: Git-flow и первый пустой PR`

**Labels:** `joint`, `week-0`, `kirill`, `andrey`, `P1`  
**Points:** 1 SP

**Body:**

```markdown
## Цель
Отработать ветки и PR по шаблону `.github/pull_request_template.md`.

## Шаги
- Ветка `docs/KIR-readme-typo` и `docs/AND-readme-typo` — микроправка в README (1 строка).
- PR друг друга ревьюят; наставник мерджит.

## DoD
- [ ] 2 merged PR от каждого практиканта (можно в рамках следующих задач)
```

---

## W1 — Справочники

### Issue #4 [kirill] [week-1] [P0]

**Title:** `K-W1-01: Customers — поиск, валидация, тесты`

**Labels:** `kirill`, `week-1`, `P0`  
**Milestone:** W1 — Справочники  
**Points:** 5 SP

**Body:**

```markdown
## Контекст
Базовый CRUD уже в `backend/app/api/customers.py`. Нужна доработка под MVP.

## Задачи
1. `GET /customers?q=...` — поиск по `name` (ILIKE / contains для SQLite через `like`).
2. Сортировка: `sort=name` (asc по умолчанию).
3. Пагинация уже есть — добавить в OpenAPI description.
4. `422` при пустом `name` на create/patch (проверить Pydantic).
5. `404` на get/patch/delete — уже есть; покрыть тестами.
6. Роль `viewer` — read-only: `GET` ok, `POST/PATCH/DELETE` → 403.

## Файлы
- `app/api/customers.py`
- `app/schemas/customer.py`
- `tests/test_customers.py` (≥ 10 тестов)

## DoD
- [ ] Все тесты зелёные, ruff clean
- [ ] В Swagger описаны query-параметры
- [ ] PR с ревью Андрея
```

---

### Issue #5 [andrey] [week-1] [P0]

**Title:** `A-W1-01: Parts — Pydantic-схемы`

**Labels:** `andrey`, `week-1`, `P0`  
**Points:** 3 SP  
**Blocked by:** —

**Body:**

```markdown
## Цель
Схемы для номенклатуры до реализации API.

## Задачи
Создать `app/schemas/part.py`:
- `PartBase`, `PartCreate`, `PartUpdate`, `PartRead`
- Поля: `sku`, `name`, `unit` (default `шт`), `category?`, `is_active`, `id`, `created_at`
- `sku`: min_length 1, max 64; уникальность проверяется в сервисе/БД
- `PartUpdate` — все поля optional

## DoD
- [ ] Импорт схем в будущем `parts.py` без циклических импортов
- [ ] Минимум 2 unit-теста на валидацию pydantic (можно в `tests/test_parts_schemas.py`)
```

---

### Issue #6 [andrey] [week-1] [P0]

**Title:** `A-W1-02: Parts — CRUD API + catalog_service`

**Labels:** `andrey`, `week-1`, `P0`  
**Points:** 8 SP  
**Depends on:** A-W1-01 (#5)

**Body:**

```markdown
## Цель
Заменить заглушку 501 в `app/api/parts.py`.

## Endpoints
| Method | Path | Роль |
|--------|------|------|
| GET | `/parts` | любой auth |
| POST | `/parts` | manager |
| GET | `/parts/{id}` | любой |
| PATCH | `/parts/{id}` | manager |
| DELETE | `/parts/{id}` | manager → soft delete |

## Бизнес-логика (`catalog_service.py`)
- Дубль `sku` → `409 Conflict`
- DELETE выставляет `is_active=false` (не физическое удаление)
- GET list: фильтр `is_active=true` по умолчанию, query `include_inactive=true`

## Тесты `tests/test_parts.py`
- create, duplicate sku, list filter, soft delete, 404

## DoD
- [ ] 501 снята
- [ ] ≥ 8 тестов
- [ ] Логика в `services/`, не в роутере
```

---

### Issue #7 [andrey] [week-1] [P0]

**Title:** `A-W1-03: BOM — схемы и модели API`

**Labels:** `andrey`, `week-1`, `P0`  
**Points:** 4 SP

**Body:**

```markdown
## Задачи
1. `app/schemas/bom.py`:
   - `BomTemplateCreate/Read/Update`
   - `BomTemplateItemCreate/Read`
   - Вложенный список items в `BomTemplateRead`
2. Проверить модели `app/models/bom.py` — без изменений, если миграция уже есть.

## DoD
- [ ] Схемы согласованы с OpenAPI (примеры в Field)
```

---

### Issue #8 [andrey] [week-1] [P0]

**Title:** `A-W1-04: BOM templates — CRUD + items + preview`

**Labels:** `andrey`, `week-1`, `P0`  
**Points:** 8 SP  
**Depends on:** A-W1-02 (#6), A-W1-03 (#7)

**Body:**

```markdown
## Цель
Реализовать `app/api/bom_templates.py` и `bom_service.py`.

## Endpoints
- `GET/POST /bom-templates`
- `GET/PATCH/DELETE /bom-templates/{id}` (soft delete `is_active`)
- `POST /bom-templates/{id}/items` body: part_id, quantity, is_optional, note
- `DELETE /bom-templates/{id}/items/{item_id}`
- `GET /bom-templates/{id}/preview` — плоский список: sku, name, quantity, is_optional

## Правила
- Нельзя добавить один `part_id` дважды в один template (409)
- `part_id` должен существовать и `is_active=true`
- DELETE template только если нет активных заказов (пока можно пропустить → TODO в коде) **или** soft delete всегда

## Тесты `tests/test_bom.py` (≥ 10 кейсов)

## DoD
- [ ] Заглушка 501 снята
- [ ] preview возвращает join с Part
```

---

### Issue #9 [kirill] [week-1] [P2]

**Title:** `K-W1-02: Ревью PR Андрея (parts + BOM)`

**Labels:** `kirill`, `week-1`, `P2`  
**Points:** 2 SP

**Body:**

```markdown
## Цель
Code review по чеклисту `docs/MENTOR.md`.

## DoD
- [ ] Ревью PR по issues #6 и #8 с комментариями
- [ ] Approve или запрос изменений
```

---

### Issue #10 [andrey] [week-1] [P2]

**Title:** `A-W1-05: Ревью PR Кирилла (customers)`

**Labels:** `andrey`, `week-1`, `P2`  
**Points:** 2 SP

**Body:**

```markdown
## DoD
- [ ] Ревью PR по issue #4
```

---

## W2 — Заказы и BOM

### Issue #11 [kirill] [week-2] [P0]

**Title:** `K-W2-01: Генератор номера заказа ORD-YYYY-NNNNN`

**Labels:** `kirill`, `week-2`, `P0`  
**Points:** 3 SP

**Body:**

```markdown
## Файл
`app/utils/order_number.py`

## Требования
- Формат: `ORD-2026-00042` (год + 5 цифр с ведущими нулями)
- Уникальность в БД (unique на `orders.number`)
- Генерация в транзакции: считать max за текущий год или отдельная sequence-таблица (на выбор, задокументировать в docstring)

## Тесты
`tests/test_order_number.py` — 3+ теста, в т.ч. два подряд не дают дубль
```

---

### Issue #12 [kirill] [week-2] [P0]

**Title:** `K-W2-02: Pydantic-схемы Order и OrderLine`

**Labels:** `kirill`, `week-2`, `P0`  
**Points:** 3 SP

**Body:**

```markdown
## Файл
`app/schemas/order.py`

## Схемы
- `OrderCreate`: customer_id, template_id?, order_type, deadline_date?, description?
- `OrderRead`: все поля модели + вложенные `lines?` (optional)
- `OrderLineCreate`, `OrderLineRead`, `OrderLineUpdate`
- `ApplyTemplateRequest`: template_id
- Enums как строки в API

## DoD
- [ ] Согласовать с Андреем поля procurement на `OrderLineRead`
```

---

### Issue #13 [joint] [week-2] [P0]

**Title:** `J-W2-01: Согласование OrderLine — поля закупки в API`

**Labels:** `joint`, `kirill`, `andrey`, `week-2`, `P0`  
**Points:** 2 SP (по 1 SP)

**Body:**

```markdown
## Цель
Один короткий PR или парный созвон: финальный контракт `OrderLineRead` и PATCH procurement.

## Поля (из модели)
procurement_status, supplier_name, expected_delivery_date, actual_delivery_date, ordered_at, note

## DoD
- [ ] Зафиксировано в комментарии issue или `docs/api.md` черновик
```

---

### Issue #14 [kirill] [week-2] [P0]

**Title:** `K-W2-03: order_service + CRUD заказов (черновик)`

**Labels:** `kirill`, `week-2`, `P0`  
**Points:** 8 SP  
**Depends on:** K-W2-01 (#11), K-W2-02 (#12)

**Body:**

```markdown
## Endpoints `app/api/orders.py`
- `GET /orders` — фильтры: status, customer_id, limit, offset
- `POST /orders` — status=draft, генерация number
- `GET /orders/{id}`
- `PATCH /orders/{id}` — только draft (deadline, description, customer_id)

## order_service.py
- create_order
- get_order
- list_orders
- update_order (draft only)

## Тесты
`tests/test_orders.py` — create, list filter, patch draft, 409 patch confirmed
```

---

### Issue #15 [kirill] [week-2] [P0]

**Title:** `K-W2-04: Ручные позиции заказа (Order lines CRUD)`

**Labels:** `kirill`, `week-2`, `P0`  
**Points:** 5 SP  
**Depends on:** K-W2-03 (#14)

**Body:**

```markdown
## Endpoints
- `GET /orders/{id}/lines`
- `POST /orders/{id}/lines` — source=manual, только draft
- `PATCH /orders/{order_id}/lines/{line_id}` — quantity, note; draft only
- `DELETE .../lines/{line_id}` — draft only

## Правила
- part must exist, quantity > 0

## Тесты
+5 к `test_orders.py`
```

---

### Issue #16 [kirill] [week-2] [P0]

**Title:** `K-W2-05: confirm / cancel заказа`

**Labels:** `kirill`, `week-2`, `P0`  
**Points:** 5 SP  
**Depends on:** K-W2-03 (#14)

**Body:**

```markdown
## Endpoints
- `POST /orders/{id}/confirm` — draft → confirmed, `confirmed_at=now`, нужен ≥1 line (или без линий — 422, зафиксировать в ТЗ)
- `POST /orders/{id}/cancel` — из draft/confirmed/in_procurement → cancelled (не из completed)

## Тесты
переходы статусов, illegal transition → 409
```

---

### Issue #17 [kirill] [week-2] [P0]

**Title:** `K-W2-06: apply-template — автозаполнение позиций из BOM`

**Labels:** `kirill`, `week-2`, `P0`  
**Points:** 8 SP  
**Depends on:** K-W2-03 (#14), A-W1-04 (#8)

**Body:**

```markdown
## Endpoint
`POST /orders/{id}/apply-template` body `{ "template_id": "uuid" }`

## Правила
- Только `draft`
- Template `is_active=true`
- Копировать BomTemplateItem → OrderLine, source=template
- Повторный apply: либо 409, либо удалить старые template-lines и пересоздать (выбрать и описать в PR)
- order_type → standard, template_id проставить

## Тесты
e2e: seed parts → bom → order → apply → count lines
```

---

### Issue #18 [andrey] [week-2] [P0]

**Title:** `A-W2-01: procurement_service — матрица переходов статусов`

**Labels:** `andrey`, `week-2`, `P0`  
**Points:** 5 SP

**Body:**

```markdown
## Файл
`app/services/procurement_service.py`

## Допустимые переходы
- not_ordered → ordered | cancelled
- ordered → in_transit | received | cancelled
- in_transit → received | cancelled
- received, cancelled — терминальные (кроме admin override — не делать)

## При переходе в `ordered`
- выставить `ordered_at=now()` если пусто

## Функция
`async def transition_line(line, new_status, *, user_role) -> OrderLine`

## Тесты
`tests/test_procurement.py` unit на матрицу (без HTTP)
```

---

### Issue #19 [andrey] [week-2] [P0]

**Title:** `A-W2-02: PATCH procurement + RBAC (роль procurement)`

**Labels:** `andrey`, `week-2`, `P0`  
**Points:** 5 SP  
**Depends on:** A-W2-01 (#18), J-W2-01 (#13)

**Body:**

```markdown
## Endpoint
`PATCH /orders/{order_id}/lines/{line_id}/procurement`

Body: procurement_status, supplier_name?, expected_delivery_date?, actual_delivery_date?, note?

## RBAC
- `procurement` и `manager` — разрешить (или только procurement — обсудить; в ТЗ procurement основная)
- `viewer` → 403

## Ошибки
- 409 illegal transition
- 422 даты: expected >= ordered_at (день)

## Тесты
403 manager если решите только procurement; 409; happy path
```

---

### Issue #20 [andrey] [week-2] [P0]

**Title:** `A-W2-03: seed_demo_data.py`

**Labels:** `andrey`, `week-2`, `P0`  
**Points:** 5 SP  
**Depends on:** A-W1-02 (#6), A-W1-04 (#8)

**Body:**

```markdown
## Файл
`backend/scripts/seed_demo_data.py`

## Данные
- 1 customer «АвиаТех»
- 20 parts (реалистичные sku для БПЛА)
- 2 BOM: «БПЛА-Разведчик v1», «БПЛА-Грузовой v1»
- Опционально: user procurement `procurement@example.com` / `procurement`

## Запуск
`python scripts/seed_demo_data.py` идемпотентно (не дублировать по sku/code)

## DoD
- [ ] Описано в README
```

---

### Issue #21 [andrey] [week-2] [P1]

**Title:** `A-W2-04: Пользователь роли procurement (скрипт или seed)`

**Labels:** `andrey`, `week-2`, `P1`  
**Points:** 2 SP

**Body:**

```markdown
Расширить `create_admin_user.py` или seed: второй пользователь для тестов закупки.

## DoD
- [ ] В README логин procurement
```

---

### Issue #22 [kirill] [week-2] [P2]

**Title:** `K-W2-07: Ревью procurement PR`

**Labels:** `kirill`, `week-2`, `P2`  
**Points:** 2 SP

---

### Issue #23 [andrey] [week-2] [P2]

**Title:** `A-W2-05: Ревью orders + apply-template PR`

**Labels:** `andrey`, `week-2`, `P2`  
**Points:** 2 SP

---

## W3 — Закупка и сроки

### Issue #24 [kirill] [week-3] [P0]

**Title:** `K-W3-01: reporting_service — просрочка и due_in_days`

**Labels:** `kirill`, `week-3`, `P0`  
**Points:** 5 SP

**Body:**

```markdown
## Файл
`app/services/reporting_service.py`

## Функции
- `list_deadline_orders(due_in_days: int | None, overdue: bool)`
- Просрочка: deadline_date < today AND status not in (completed, cancelled)
- due_in_days: deadline между today и today+N

## Endpoint
`GET /reports/deadlines?due_in_days=7&overdue=true`

## Тесты
`tests/test_reports.py`
```

---

### Issue #25 [kirill] [week-3] [P0]

**Title:** `K-W3-02: Фильтр overdue на GET /orders`

**Labels:** `kirill`, `week-3`, `P0`  
**Points:** 3 SP  
**Depends on:** K-W3-01 (#24)

**Body:**

```markdown
Query `GET /orders?overdue=true` — та же логика, что в reporting.

## DoD
- [ ] 2 теста в test_orders
```

---

### Issue #26 [kirill] [week-3] [P0]

**Title:** `K-W3-03: procurement-summary по заказу`

**Labels:** `kirill`, `week-3`, `P0`  
**Points:** 5 SP

**Body:**

```markdown
## Endpoint
`GET /reports/orders/{id}/procurement-summary`

Response пример:
```json
{
  "order_id": "...",
  "total_lines": 10,
  "by_status": { "not_ordered": 2, "ordered": 5, "received": 3 },
  "percent_received": 30.0
}
```

## Тесты
в test_reports.py
```

---

### Issue #27 [joint] [week-3] [P0]

**Title:** `J-W3-01: Авто-статус заказа in_procurement`

**Labels:** `joint`, `kirill`, `andrey`, `week-3`, `P0`  
**Points:** 3 SP (Кирилл 2 + Андрей 1)

**Body:**

```markdown
При первом переводе любой line в `ordered` → заказ `confirmed` → `in_procurement`.

## Реализация
Вызов из `procurement_service` после transition — callback или `order_service.sync_status_from_lines`.

## DoD
- [ ] Тест: confirm order → patch line ordered → order.status == in_procurement
```

---

### Issue #28 [andrey] [week-3] [P0]

**Title:** `A-W3-01: GET lines с join Part (sku, name)`

**Labels:** `andrey`, `week-3`, `P0`  
**Points:** 5 SP

**Body:**

```markdown
Расширить `OrderLineRead` вложенным `part_sku`, `part_name` или nested `part: PartRead`.

Обновить `GET /orders/{id}/lines` — selectinload/joinedload.

## DoD
- [ ] OpenAPI пример
- [ ] 2 теста
```

---

### Issue #29 [andrey] [week-3] [P1]

**Title:** `A-W3-02: Bulk PATCH procurement (optional)`

**Labels:** `andrey`, `week-3`, `P1`  
**Points:** 5 SP

**Body:**

```markdown
`PATCH /orders/{id}/lines/procurement-bulk` body: list[{line_id, procurement_status, ...}]

Max 50 items; та же матрица переходов.

Если не успевают — закрыть как cancelled с причиной.
```

---

### Issue #30 [andrey] [week-3] [P2]

**Title:** `A-W3-03: AuditLog при смене procurement (optional)`

**Labels:** `andrey`, `week-3`, `P2`  
**Points:** 5 SP

**Body:**

```markdown
Модель `AuditLog`, запись при PATCH procurement.

P2 — не блокирует MVP.
```

---

### Issue #31 [kirill] [week-3] [P2]

**Title:** `K-W3-04: completed — автозакрытие заказа`

**Labels:** `kirill`, `week-3`, `P2`  
**Points:** 3 SP

**Body:**

```markdown
Когда все lines в received или cancelled → order.status = completed.

Вызов из order_service.sync_status_from_lines (совместно с J-W3-01).
```

---

## W4 — Релиз MVP

### Issue #32 [kirill] [week-4] [P0]

**Title:** `K-W4-01: docs/api.md — примеры curl`

**Labels:** `kirill`, `week-4`, `P0`  
**Points:** 3 SP

**Body:**

```markdown
Минимум 6 примеров: login, create order, apply template, procurement patch, deadlines, summary.

Файл `docs/api.md`.
```

---

### Issue #33 [andrey] [week-4] [P0]

**Title:** `A-W4-01: demo_walkthrough.py (httpx e2e)`

**Labels:** `andrey`, `week-4`, `P0`  
**Points:** 5 SP

**Body:**

```markdown
`backend/scripts/demo_walkthrough.py`:
- login → seed assumptions (or call seed)
- create order → apply bom → 3x procurement → reports

Печать OK/FAIL по шагам. Exit code 0 при успехе.

## DoD
- [ ] Описан в README
```

---

### Issue #34 [andrey] [week-4] [P1]

**Title:** `A-W4-02: PostgreSQL — проверка docker-compose + README`

**Labels:** `andrey`, `week-4`, `P1`  
**Points:** 3 SP

**Body:**

```markdown
Прогнать миграции и pytest на PostgreSQL локально.

Дополнить README разделом «Postgres».

## DoD
- [ ] Комментарий в issue: compose + alembic OK
```

---

### Issue #35 [kirill] [week-4] [P1]

**Title:** `K-W4-02: Покрытие тестами ≥ 60%`

**Labels:** `kirill`, `week-4`, `P1`  
**Points:** 5 SP

**Body:**

```markdown
`pytest --cov=app --cov-report=term-missing`

Добить тесты по своим модулям; Андрей — по своим. Кирилл координирует общий процент.

## DoD
- [ ] CI: добавить step coverage (optional fail if < 60%)
```

---

### Issue #36 [joint] [week-4] [P0]

**Title:** `J-W4-01: Чеклист приёмки MVP (TZ §9)`

**Labels:** `joint`, `kirill`, `andrey`, `week-4`, `P0`  
**Points:** 8 SP (по 4 SP)

**Body:**

```markdown
## Чеклист
- [ ] pytest + CI green
- [ ] Swagger сценарий: seed → заказ → BOM → procurement → deadlines
- [ ] README + MENTOR.md актуальны
- [ ] Postgres documented
- [ ] Нет P0 багов

## DoD
Issue закрывают оба комментарием со скрин/логом demo_walkthrough
```

---

### Issue #37 [joint] [week-4] [P1]

**Title:** `J-W4-02: Демо 15 мин + backlog v2`

**Labels:** `joint`, `kirill`, `andrey`, `week-4`, `P1`  
**Points:** 3 SP

**Body:**

```markdown
- Презентация 50/50 по времени
- `docs/demo.md` — тезисы
- GitHub Project / 10 issues на v2 (UI, audit, 1C, …)
```

---

### Issue #38 [andrey] [week-3] [P2]

**Title:** `A-W3-04: POST /parts/import CSV (optional)`

**Labels:** `andrey`, `week-3`, `P2`  
**Points:** 5 SP

**Body:**

```markdown
UTF-8 CSV: sku,name,unit,category. Дубли sku → skip or 409.

Не блокирует MVP.
```

---

### Issue #39 [kirill] [week-4] [P2]

**Title:** `K-W4-03: Отмена заказа с ordered lines (edge case)`

**Labels:** `kirill`, `week-4`, `P2`  
**Points:** 3 SP

**Body:**

```markdown
Политика: cancel разрешён, но lines в ordered → warning в response или 409.

Зафиксировать в коде и тесте.
```

---

### Issue #40 [mentor] [week-4] [P0]

**Title:** `M-02: Финальная приёмка MVP наставником`

**Labels:** `mentor`, `week-4`, `P0`

**Body:**

```markdown
По `docs/MENTOR.md` и TZ §9.

## DoD
- [ ] Merge main стабилен
- [ ] Обратная связь практикантам письменно
```

---

## Сводка по нагрузке (story points)

| Неделя | Кирилл | Андрей | Joint (÷2 на человека) |
|--------|--------|--------|-------------------------|
| W1 | 5+2=7 | 3+8+4+8+2=25* | 2 → ~8+1 joint |
| W2 | 3+3+8+5+5+8+2=34 | 5+5+5+2+2=19 + joint 1 | |
| W3 | 5+3+5+3=16 (+3 P2) | 5+5=10 (+5+5 P2) | 3 |
| W4 | 3+5+3=11 (+3 P2) | 5+3=8 | 8+3 |

\*W1 у Андрея тяжёлая неделя — компенсация: K-W1-02 только ревью; на W2 у Кирилла больше SP — **сбалансировано по месяцу**. При перекосе перенесите A-W3-03 (optional) на Кирилла или K-W4-03 на Андрея.

**Итого ориентир:** ~45–50 SP Кирилл, ~45–50 SP Андрей (без optional).

---

## Порядок создания (зависимости)

1. W0: #1 → #2 → #3  
2. W1 параллельно: #4 ∥ #5→#6, #7→#8; #9 #10 после PR  
3. W2: #11,#12→#14→#15,#16,#17 ∥ #18→#19, #20  
4. W3: #24→#25,#26 + #18+#19 + #28 + #27  
5. W4: #32–#37 после green main  

---

## Шаблон тела для новых задач

```markdown
## Контекст
…

## Задачи
- [ ] …

## Файлы
…

## DoD
- [ ] pytest
- [ ] ruff
- [ ] PR + review

**Points:** N SP
**Исполнитель:** …
```
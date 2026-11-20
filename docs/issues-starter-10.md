# 10 стартовых issues (создать вручную на GitHub)

Репозиторий: https://github.com/ledozeur/OrderStation/issues/new  

**Сначала** создайте labels: `kirill`, `andrey`, `joint`, `mentor`, `week-0`, `week-1`, `week-2`, `week-4`, `P0`, `P1`  
**Milestones:** `W0 — Подготовка`, `W1 — Справочники`, `W2 — Заказы и BOM`, `W4 — Релиз MVP`  

Assignee: назначайте сами.  
Полный бэклог: [GITHUB_ISSUES.md](GITHUB_ISSUES.md).

---

## 1. M-01 (вы, можно без assignee)

- **Title:** `M-01: GitHub — labels, milestones, branch protection`
- **Labels:** `mentor`, `week-0`, `P0`
- **Milestone:** W0 — Подготовка

**Body:**

```markdown
## Цель
Подготовить репозиторий к работе практикантов.

## Чеклист
- [ ] Labels и milestones созданы
- [ ] Практиканты добавлены в collaborators
- [ ] Branch protection: PR в main, CI required (по возможности)
- [ ] Стартовые issues W0–W1 созданы

## DoD
Практиканты видят назначенные issues и могут открыть PR.
```

---

## 2. J-00 (оба)

- **Title:** `J-00: Онбординг — окружение и Swagger`
- **Labels:** `joint`, `week-0`, `kirill`, `andrey`, `P0`
- **Milestone:** W0 — Подготовка

**Body:**

```markdown
## Цель
Поднять проект локально и пройти docs/onboarding.md.

## Шаги
1. `git clone https://github.com/ledozeur/OrderStation.git`
2. `cd OrderStation/backend` → venv → `pip install -e ".[dev]"`
3. `copy ..\.env.example ..\.env`
4. `alembic upgrade head` + `python scripts/create_admin_user.py`
5. `uvicorn app.main:app --reload` → http://127.0.0.1:8000/docs
6. Authorize: `admin@example.com` / `admin`
7. `POST /api/v1/customers` → `GET /api/v1/customers`
8. `pytest -q` — все тесты зелёные

## DoD
- [ ] Каждый оставил комментарий «pytest OK» + при желании скрин Swagger
- [ ] Прочитан README и docs/TZ.md
```

---

## 3. K-W1-01 → Кирилл

- **Title:** `K-W1-01: Customers — поиск, валидация, тесты`
- **Labels:** `kirill`, `week-1`, `P0`
- **Milestone:** W1 — Справочники

**Body:**

```markdown
## Контекст
Базовый CRUD уже в `backend/app/api/customers.py`.

## Задачи
- [ ] `GET /customers?q=...` — поиск по name
- [ ] Роль `viewer`: только GET, POST/PATCH/DELETE → 403
- [ ] Расширить `tests/test_customers.py` (всего ≥ 10 тестов)

## Файлы
`app/api/customers.py`, `app/schemas/customer.py`, `tests/test_customers.py`

## DoD
- [ ] `pytest`, `ruff check .` OK
- [ ] PR, review от Андрея
```

---

## 4. A-W1-01 → Андрей

- **Title:** `A-W1-01: Parts — Pydantic-схемы`
- **Labels:** `andrey`, `week-1`, `P0`
- **Milestone:** W1 — Справочники

**Body:**

```markdown
## Цель
Создать `backend/app/schemas/part.py`:
- PartCreate, PartUpdate, PartRead
- sku, name, unit (default шт), category, is_active

## DoD
- [ ] Минимум 2 теста валидации схем (новый файл или test_parts)
- [ ] PR
```

---

## 5. A-W1-02 → Андрей (после #4)

- **Title:** `A-W1-02: Parts — CRUD API + catalog_service`
- **Labels:** `andrey`, `week-1`, `P0`
- **Milestone:** W1 — Справочники

**Body:**

```markdown
## Цель
Заменить 501 в `app/api/parts.py`.

## Endpoints
GET/POST/PATCH/DELETE `/parts`, soft delete (`is_active=false`), дубль sku → 409.

## Сервис
`app/services/catalog_service.py`

## DoD
- [ ] `tests/test_parts.py` ≥ 8 тестов
- [ ] Логика в service, не только в роутере
```

---

## 6. A-W1-04 → Андрей (после #5)

- **Title:** `A-W1-04: BOM templates — CRUD + items + preview`
- **Labels:** `andrey`, `week-1`, `P0`
- **Milestone:** W1 — Справочники

**Body:**

```markdown
## Endpoints
`/bom-templates` CRUD, items add/remove, `GET .../preview` (sku, name, quantity).

## Файлы
`app/api/bom_templates.py`, `app/services/bom_service.py`, `app/schemas/bom.py`

## DoD
- [ ] `tests/test_bom.py` ≥ 10 кейсов
- [ ] Снята заглушка 501
```

---

## 7. K-W2-03 → Кирилл (W2, можно создать заранее)

- **Title:** `K-W2-03: order_service + CRUD заказов`
- **Labels:** `kirill`, `week-2`, `P0`
- **Milestone:** W2 — Заказы и BOM

**Body:**

```markdown
## Endpoints
GET/POST/PATCH `/orders`, фильтры status/customer_id, только draft редактируется.

## Файлы
`app/api/orders.py`, `app/services/order_service.py`, `app/schemas/order.py`
`app/utils/order_number.py` — ORD-YYYY-NNNNN

## DoD
- [ ] `tests/test_orders.py` — create, list, patch draft
- [ ] Зависит от parts/BOM у Андрея для интеграции позже
```

---

## 8. K-W2-06 → Кирилл (W2)

- **Title:** `K-W2-06: apply-template — позиции из BOM`
- **Labels:** `kirill`, `week-2`, `P0`
- **Milestone:** W2 — Заказы и BOM

**Body:**

```markdown
`POST /orders/{id}/apply-template` body `{ "template_id": "uuid" }`
Только draft, lines source=template, order_type=standard.

## DoD
- [ ] e2e тест: BOM → order → apply → lines count
- [ ] Блокируется если template неактивен (409)
```

---

## 9. A-W2-02 → Андрей (W2)

- **Title:** `A-W2-02: PATCH procurement + RBAC`
- **Labels:** `andrey`, `week-2`, `P0`
- **Milestone:** W2 — Заказы и BOM

**Body:**

```markdown
`PATCH /orders/{order_id}/lines/{line_id}/procurement`
Матрица переходов в `procurement_service.py`
Роль procurement (и/или manager — зафиксировать в PR)
403 для viewer

## DoD
- [ ] `tests/test_procurement.py`
```

---

## 10. J-W4-01 → оба (конец месяца)

- **Title:** `J-W4-01: Чеклист приёмки MVP`
- **Labels:** `joint`, `kirill`, `andrey`, `week-4`, `P0`
- **Milestone:** W4 — Релиз MVP

**Body:**

```markdown
По docs/TZ.md §9:

- [ ] pytest + CI green, покрытие ≥ 60%
- [ ] Swagger: seed → заказ → apply BOM → procurement → deadlines
- [ ] README / docs актуальны
- [ ] demo_walkthrough.py (если готов)

Комментарий обоих с результатом demo.
```

---

## Порядок старта для практикантов

| День | Кирилл | Андрей |
|------|--------|--------|
| 1 | #2, затем #3 | #2, затем #4 → #5 → #6 |
| 2+ | PR #3, ревью Андрея | PR #5/#6, ревью Кирилла |
| Неделя 2 | #7, #8 | #9 + seed (см. GITHUB_ISSUES #20) |

После W1 добавляйте остальные issues из **GITHUB_ISSUES.md** по мере прогресса.
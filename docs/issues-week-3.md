# Week 3 — issues (добавить на GitHub)

Создайте, если ещё нет:

- **Label:** `week-3`
- **Milestone:** `W3 — Закупка и сроки` (Due: +21 день от старта практики)

Зависимости: закрыты основные задачи **W2** (заказы, apply-template, procurement PATCH).

**CLI (рекомендуется):** из корня репо:

```powershell
gh auth login
.\scripts\create-github-issues.ps1 -Week w3
```

Ручное создание: https://github.com/ledozeur/OrderStation/issues/new

---

## W3-1 → Кирилл

- **Title:** `K-W3-01: reporting_service — deadlines и overdue`
- **Labels:** `kirill`, `week-3`, `P0`
- **Milestone:** W3 — Закупка и сроки

**Body:**

```markdown
## Цель
Реализовать отчёт по срокам и сервис `app/services/reporting_service.py`.

## Логика
- **Просрочка:** `deadline_date < today` и `status` не `completed` / `cancelled`
- **due_in_days:** дедлайн в интервале [today, today+N]

## Endpoint
`GET /api/v1/reports/deadlines`
Query: `due_in_days` (int, optional), `overdue` (bool, optional)

Снять заглушку 501 в `app/api/reports.py`.

## Файлы
`app/services/reporting_service.py`, `app/api/reports.py`, `tests/test_reports.py`

## DoD
- [ ] ≥ 4 теста (overdue, due_in_days, пустой результат)
- [ ] PR + review Андрея
```

---

## W3-2 → Кирилл

- **Title:** `K-W3-02: GET /orders?overdue=true`
- **Labels:** `kirill`, `week-3`, `P0`
- **Milestone:** W3 — Закупка и сроки

**Body:**

```markdown
## Цель
Тот же критерий просрочки, что в K-W3-01, на списке заказов.

## Задача
В `GET /orders` добавить query `overdue=true`.

Переиспользовать функцию из `reporting_service` (DRY).

## DoD
- [ ] 2 теста в `tests/test_orders.py`
- [ ] Описание параметра в OpenAPI
```

---

## W3-3 → Кирилл

- **Title:** `K-W3-03: procurement-summary по заказу`
- **Labels:** `kirill`, `week-3`, `P0`
- **Milestone:** W3 — Закупка и сроки

**Body:**

```markdown
## Endpoint
`GET /api/v1/reports/orders/{id}/procurement-summary`

## Response (пример)
`order_id`, `total_lines`, `by_status` (счётчики по каждому procurement_status), `percent_received` (доля received от total_lines).

## DoD
- [ ] 404 если заказа нет
- [ ] Тесты в `tests/test_reports.py`
```

---

## W3-4 → оба (joint)

- **Title:** `J-W3-01: Авто-статус заказа in_procurement`
- **Labels:** `joint`, `kirill`, `andrey`, `week-3`, `P0`
- **Milestone:** W3 — Закупка и сроки

**Body:**

```markdown
## Правило
Когда **первая** позиция заказа переходит в `procurement_status=ordered` → заказ из `confirmed` (или `draft` запретить) в `in_procurement`.

## Реализация
- В `procurement_service` после успешного transition вызвать `order_service.sync_status_from_lines(order_id)` (или аналог).
- Кирилл — метод в `order_service`; Андрей — вызов из PATCH procurement.

## DoD
- [ ] Один совместный интеграционный тест
- [ ] Один PR (пара авторов или два связанных PR с ссылками)
```

---

## W3-5 → Андрей

- **Title:** `A-W3-01: GET /orders/{id}/lines с sku и name запчасти`
- **Labels:** `andrey`, `week-3`, `P0`
- **Milestone:** W3 — Закупка и сроки

**Body:**

```markdown
## Цель
В ответе линии заказа видны человекочитаемые поля номенклатуры.

## Вариант
Расширить `OrderLineRead`: `part_sku`, `part_name` **или** вложенный `part: PartRead` (выбрать один в PR).

## Техника
SQLAlchemy `selectinload` / join Part в `GET /orders/{id}/lines`.

## DoD
- [ ] 2 теста
- [ ] Пример в Swagger
```

---

## W3-6 → Кирилл (P2, по желанию в W3)

- **Title:** `K-W3-04: completed — когда все позиции received/cancelled`
- **Labels:** `kirill`, `week-3`, `P2`
- **Milestone:** W3 — Закупка и сроки

**Body:**

```markdown
## Правило
Если каждая line в `received` или `cancelled` → `order.status = completed`.

Расширить `order_service.sync_status_from_lines` (вместе с J-W3-01).

## DoD
- [ ] Тест: все received → completed
- [ ] Не блокирует MVP, если не успеваем — перенос в W4
```

---

## W3-7 → Андрей (optional, P1)

- **Title:** `A-W3-02: Bulk PATCH procurement (до 50 линий)`
- **Labels:** `andrey`, `week-3`, `P1`
- **Milestone:** W3 — Закупка и сроки

**Body:**

```markdown
`PATCH /orders/{id}/lines/procurement-bulk`
Тело: список `{ line_id, procurement_status, ... }`, max 50.
Та же матрица переходов, что в одиночном PATCH.

Не обязательно для MVP.
```

---

## W3-8 → Андрей (optional, P2)

- **Title:** `A-W3-03: POST /parts/import CSV`
- **Labels:** `andrey`, `week-3`, `P2`
- **Milestone:** W3 — Закупка и сроки

**Body:**

```markdown
UTF-8 CSV: sku,name,unit,category. Дубли sku → пропуск или 409 (задокументировать).

Только если остаётся время после P0.
```

---

## План недели W3 (демо в пятницу)

| День | Кирилл | Андрей |
|------|--------|--------|
| Пн | K-W3-01 | A-W3-01 |
| Вт–Ср | K-W3-02, K-W3-03 | доработка lines / review |
| Ср | **J-W3-01** (созвон 15 мин с Андреем) | **J-W3-01** |
| Чт–Пт | K-W3-04 (optional), тесты | P1/P2 по желанию |

**Демо W3:** seed → заказ с дедлайном → часть линий `ordered` → `GET /reports/deadlines` + `procurement-summary` + фильтр `overdue`.

Подробнее: [GITHUB_ISSUES.md](GITHUB_ISSUES.md) (issues #24–#31, #38).
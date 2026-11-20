# OrderStation — ТЗ (Backend MVP, 4 недели)

## 1. Назначение

REST API для учёта заказов БПЛА: заказчики, заказы, типовые спецификации (BOM), позиции, статусы закупки, сроки. **Клиент — Swagger UI (`/docs`) или любой HTTP-клиент; отдельного frontend нет.**

## 2. Цели MVP

- Реестр заказчиков и заказов
- Типовой заказ: применить BOM → список запчастей
- Нетиповой: ручные позиции
- По каждой позиции: `not_ordered` → `ordered` → `in_transit` → `received`
- Фильтры: просроченные заказы, сводка закупки по заказу
- JWT-авторизация, роли `manager` / `procurement` / `viewer`

## 3. Стек

FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, PostgreSQL / SQLite, pytest, ruff, GitHub Actions.

## 4. Модель данных

См. модели в `backend/app/models/`. Кратко:

- **Customer**, **Part**, **BomTemplate**, **BomTemplateItem**
- **Order**, **OrderLine** (поля закупки на линии)
- **User**

Бизнес-правила — как в предыдущей редакции ТЗ (apply-template, статусы заказа, просрочка по `deadline_date`).

## 5. API (контракт)

Базовый префикс: `/api/v1`.

| Модуль | Endpoints | Исполнитель |
|--------|-----------|-------------|
| auth | login, me | готово в скелете |
| customers | CRUD | Кирилл (скелет CRUD есть) |
| parts | CRUD, soft delete | Андрей |
| bom-templates | CRUD + items + preview | Андрей |
| orders | CRUD, confirm, cancel, apply-template | Кирилл |
| order lines | add/update/delete manual; procurement PATCH | Кирилл + Андрей |
| reports | deadlines, procurement-summary | Кирилл |

## 6. Структура репозитория

```
order-station/
├── backend/app/{api,models,schemas,services,utils}
├── backend/tests/
├── backend/alembic/
├── docs/
├── docker-compose.yml   # только PostgreSQL
└── .github/workflows/ci.yml
```

## 7. Распределение (≈50/50)

**Кирилл:** `customers` (доработка), `orders`, `order_service`, `order_number`, `reporting_service`, `reports`, тесты `test_orders`, `test_reports`, часть `order_lines` (CRUD manual).

**Андрей:** `parts`, `bom_templates`, `catalog_service`, `bom_service`, `procurement_service`, PATCH закупки, тесты `test_parts`, `test_bom`, `test_procurement`, `seed_demo_data.py`, опционально CSV import.

**Совместно:** неделя 1 — auth/CI уже в скелете; неделя 2 — поля `OrderLine` + интеграция apply-template; неделя 4 — интеграционный сценарий.

## 8. План задач (backend-only)

### Неделя 1

| ID | Кто | Задача | DoD |
|----|-----|--------|-----|
| K-W1 | Кирилл | Доработать customers (поиск по имени, 422) | +тесты |
| A-W1 | Андрей | Parts CRUD + схемы | заменить 501 |
| A-W1b | Андрей | BOM templates + items + preview | тесты |
| J-W1 | Оба | Изучить Swagger, пройти онбординг | issue закрыты |

### Неделя 2

| ID | Кто | Задача | DoD |
|----|-----|--------|-----|
| K-W2 | Кирилл | Order + OrderLine models в API, нумератор | тесты |
| K-W2b | Кирилл | apply-template, confirm/cancel | e2e тест |
| A-W2 | Андрей | procurement PATCH + матрица переходов | 403 для manager |
| A-W2b | Андрей | seed_demo_data.py | 2 BOM, 20 parts |

### Неделя 3

| ID | Кто | Задача | DoD |
|----|-----|--------|-----|
| K-W3 | Кирилл | reports/deadlines, overdue filter на orders | тесты |
| K-W3b | Кирилл | auto in_procurement при первом ordered | согласование с Андреем |
| A-W3 | Андрей | GET lines с join part (sku, name) | OpenAPI |
| A-W3b | Андрей | bulk procurement (optional) | тесты |

### Неделя 4

| ID | Кто | Задача | DoD |
|----|-----|--------|-----|
| J-W4 | Оба | Чеклист приёмки, баги P0/P1 | все пункты §9 |
| A-W4 | Андрей | demo_walkthrough.py (httpx) | скрипт в CI optional |
| K-W4 | Кирилл | docs/api.md примеры curl | в docs |

## 9. Критерии приёмки

1. `pytest` и CI зелёные, покрытие backend ≥ 60%.
2. Сценарий в Swagger: seed → заказ → apply BOM → перевод 3 позиций в ordered/received → отчёт deadlines.
3. README + MENTOR.md актуальны.
4. Работа с PostgreSQL через docker-compose документирована.

## 10. Вне scope

UI, 1С, мобильные клиенты, полноценный audit trail (опционально W3).
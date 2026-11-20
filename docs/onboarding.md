# Онбординг практикантов (1 месяц)

## День 1

1. Установить **Python 3.12+**, **Git**, опционально **Docker Desktop**.
2. Клонировать репозиторий.
3. Прочитать [README.md](../README.md) (раздел **«Кто что делает»**) и свои issues в milestone **W1**.
4. Поднять окружение (SQLite — достаточно для старта).
5. Открыть Swagger: `http://127.0.0.1:8000/docs`.
6. Авторизация: **Authorize** → логин `admin@example.com`, пароль `admin` (OAuth2 form: поле username = email).
7. Пройти пример: `POST /api/v1/customers` → `GET /api/v1/customers`.

## Git-процесс

- Одна задача = один issue = одна ветка.
- Имена веток: `feature/KIR-12-orders-list`, `feature/AND-5-parts-crud`.
- Перед PR: `ruff check .`, `ruff format .`, `pytest`.
- Второй практикант делает review, затем смотрит наставник.

## Где что лежит

| Файл / папка | Кто владелец |
|--------------|--------------|
| `app/api/customers.py`, `orders.py`, `reports.py` | Кирилл |
| `app/api/parts.py`, `bom_templates.py` + procurement в линиях | Андрей |
| `app/services/order_service.py`, `reporting_service.py` | Кирилл |
| `app/services/catalog_service.py`, `bom_service.py`, `procurement_service.py` | Андрей |
| `app/models/order.py` | совместно (W2) |
| `app/api/auth.py` | не менять без согласования |

## Демо-сценарий (конец месяца)

Описывается в [TZ.md](TZ.md), раздел «Критерии приёмки». Прогон через Swagger или `scripts/demo_walkthrough.py` (Андрей, W4).
# Шпаргалка наставнику (без углубления в Python)

## Как проверить, что проект живой

```powershell
cd backend
.venv\Scripts\activate
pytest -q
```

Должно быть **все зелёные**. CI на GitHub делает то же самое.

## Что смотреть в PR (чеклист)

1. **CI прошёл** (Actions зелёный).
2. **Тесты добавлены** к новой логике (файлы в `backend/tests/`).
3. **Нет секретов** в коде (пароли, ключи — только `.env`).
4. **Границы модулей**: Кирилл не тянет «всё» в `parts.py`, Андрей — в `orders.py`.
5. **OpenAPI**: в Swagger новые методы с описанием, коды 404/422 где нужно.
6. **Миграции**: при изменении моделей есть файл в `alembic/versions/`.

## Типичные проблемы

| Симптом | Что сказать практикантам |
|---------|---------------------------|
| `pytest` падает на auth | Проверить фикстуру `auth_headers`, не ломали ли `dependencies.py` |
| 401 в Swagger | Нажать Authorize, username = email |
| Alembic ошибка на SQLite | Нужен `render_as_batch` — уже в `alembic/env.py` |
| Дубли логики в роутере | Вынести в `services/` |

## Еженедельное демо (ожидания)

| Неделя | Минимум на демо |
|--------|------------------|
| 1 | Auth + customers (Кирилл) + parts/BOM CRUD (Андрей) |
| 2 | Заказ + apply template + ручные линии |
| 3 | Procurement PATCH + отчёт deadlines |
| 4 | Полный сценарий из TZ, README, seed |

## Полезные команды

```powershell
cd backend
uvicorn app.main:app --reload
alembic revision --autogenerate -m "описание"
alembic upgrade head
ruff check . ; ruff format .
```

Swagger: `/docs` — основной «UI» проекта на этапе Backend-only.
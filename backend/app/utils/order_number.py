import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order

MAX_SEQUENCE = 99_999

_NUMBER_RE = re.compile(r"ORD-(\d{4})-(\d{5})")


def format_order_number(year: int, sequence: int) -> str:
    """Собирает номер из года и порядкового номера: ``(2026, 42)`` -> ``ORD-2026-00042``."""
    if not 1 <= sequence <= MAX_SEQUENCE:
        raise ValueError(
            f"Порядковый номер заказа должен быть от 1 до {MAX_SEQUENCE}, получено {sequence}"
        )
    return f"ORD-{year:04d}-{sequence:05d}"


def parse_order_number(number: str) -> tuple[int, int]:
    """Разбирает номер на год и порядковый номер: ``ORD-2026-00042`` -> ``(2026, 42)``."""
    match = _NUMBER_RE.fullmatch(number)
    if match is None:
        raise ValueError(f"Неверный формат номера заказа: {number!r}")
    return int(match.group(1)), int(match.group(2))


async def generate_order_number(db: AsyncSession, *, today: date | None = None) -> str:
    """Возвращает следующий свободный номер заказа за год ``today`` (по умолчанию — текущий).

    Параметр ``today`` нужен для тестов. Если за год уже выдан номер 99999, поднимается
    ``ValueError``. Если в базе лежит номер этого года в неверном формате (не созданный
    этой функцией), тоже поднимается ``ValueError``: молча пропускать такие данные нельзя.
    """
    year = (today or date.today()).year
    prefix = f"ORD-{year:04d}-"

    last_number = await db.scalar(
        select(func.max(Order.number)).where(Order.number.like(f"{prefix}%"))
    )
    if last_number is None:
        sequence = 1
    else:
        _, last_sequence = parse_order_number(last_number)
        sequence = last_sequence + 1

    return format_order_number(year, sequence)

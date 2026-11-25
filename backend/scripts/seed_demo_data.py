"""Идемпотентно наполняет БД демо-данными: пользователь procurement, заказчик, 20 деталей, 2 BOM."""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, Base, engine
from app.models.bom import BomTemplate, BomTemplateItem
from app.models.customer import Customer
from app.models.part import Part
from app.models.user import User, UserRole
from app.utils.security import hash_password

DEMO_PARTS: list[tuple[str, str, str, str]] = [
    ("UAV-FRM-450", "Рама карбоновая квадрокоптера 450мм", "шт", "Рамы"),
    ("UAV-FRM-850", "Рама гексакоптера складная 850мм", "шт", "Рамы"),
    ("UAV-MOT-2216", "Двигатель бесколлекторный 2216 920KV", "шт", "Двигатели"),
    ("UAV-MOT-4006", "Двигатель грузовой 4006 380KV", "шт", "Двигатели"),
    ("UAV-ESC-40A", "Регулятор оборотов ESC 40A BLHeli", "шт", "Электроника"),
    ("UAV-ESC-60A", "Регулятор оборотов ESC 60A HV", "шт", "Электроника"),
    ("UAV-PRP-1045", "Пропеллер карбоновый 10x4.5 (пара)", "компл", "Винты"),
    ("UAV-PRP-1555", "Пропеллер складной 15x5.5 (пара)", "компл", "Винты"),
    ("UAV-FC-H743", "Полётный контроллер STM32H743", "шт", "Авионика"),
    ("UAV-GPS-M10", "Модуль GPS/ГЛОНАСС M10 с компасом", "шт", "Авионика"),
    ("UAV-VTX-1W", "Видеопередатчик 5.8ГГц 1.6Вт", "шт", "Связь"),
    ("UAV-CAM-HD", "Курсовая камера Low-Light HD", "шт", "Оптика"),
    ("UAV-RX-ELRS", "Приёмник управления ELRS 915МГц", "шт", "Связь"),
    ("UAV-TLM-433", "Модем телеметрии 433МГц 500мВт", "шт", "Связь"),
    ("UAV-BAT-4S", "Аккумулятор LiPo 4S 5200mAh 50C", "шт", "Питание"),
    ("UAV-BAT-6S", "Аккумулятор LiPo 6S 16000mAh 25C", "шт", "Питание"),
    ("UAV-PDB-200", "Плата распределения питания PDB 200A", "шт", "Питание"),
    ("UAV-DROP-01", "Механизм сброса груза сервоприводный", "шт", "Полезная нагрузка"),
    ("UAV-MNT-DMP", "Виброразвязка подвеса демпферная", "компл", "Крепёж"),
    ("UAV-CBL-XT60", "Жгут силовой с разъёмом XT60/XT90", "шт", "Крепёж"),
]

DEMO_BOMS: list[dict[str, object]] = [
    {
        "code": "BOM-SCOUT-V1",
        "name": "БПЛА-Разведчик v1",
        "product_line": "Разведка",
        "version": "1.0",
        "items": [
            ("UAV-FRM-450", Decimal("1"), False, "Базовая рама"),
            ("UAV-MOT-2216", Decimal("4"), False, "4 лучевых мотора"),
            ("UAV-ESC-40A", Decimal("4"), False, None),
            ("UAV-PRP-1045", Decimal("2"), False, "2 пары пропеллеров"),
            ("UAV-FC-H743", Decimal("1"), False, None),
            ("UAV-GPS-M10", Decimal("1"), False, None),
            ("UAV-VTX-1W", Decimal("1"), False, None),
            ("UAV-CAM-HD", Decimal("1"), False, None),
            ("UAV-RX-ELRS", Decimal("1"), False, None),
            ("UAV-BAT-4S", Decimal("1"), False, None),
            ("UAV-CBL-XT60", Decimal("1"), False, None),
        ],
    },
    {
        "code": "BOM-CARGO-V1",
        "name": "БПЛА-Грузовой v1",
        "product_line": "Логистика",
        "version": "1.0",
        "items": [
            ("UAV-FRM-850", Decimal("1"), False, "Несущая гекса-рама"),
            ("UAV-MOT-4006", Decimal("6"), False, "6 грузовых моторов"),
            ("UAV-ESC-60A", Decimal("6"), False, None),
            ("UAV-PRP-1555", Decimal("3"), False, "3 пары пропеллеров"),
            ("UAV-FC-H743", Decimal("1"), False, None),
            ("UAV-GPS-M10", Decimal("1"), False, None),
            ("UAV-TLM-433", Decimal("1"), False, "Дальняя телеметрия"),
            ("UAV-RX-ELRS", Decimal("1"), False, None),
            ("UAV-PDB-200", Decimal("1"), False, None),
            ("UAV-BAT-6S", Decimal("2"), False, "Сдвоенное питание"),
            ("UAV-DROP-01", Decimal("1"), False, "Грузовой узел"),
            ("UAV-MNT-DMP", Decimal("1"), True, "Опциональный демпфер"),
            ("UAV-CBL-XT60", Decimal("2"), False, None),
        ],
    },
]


async def seed_all(session: AsyncSession) -> None:
    user_res = await session.execute(select(User).where(User.email == "procurement@example.com"))
    if user_res.scalar_one_or_none() is None:
        session.add(
            User(
                email="procurement@example.com",
                hashed_password=hash_password("procurement"),
                full_name="Demo Procurement",
                role=UserRole.procurement,
                is_active=True,
            )
        )

    cust_res = await session.execute(select(Customer).where(Customer.name == "АвиаТех"))
    if cust_res.scalar_one_or_none() is None:
        session.add(
            Customer(
                name="АвиаТех",
                contact_person="Иванов Сергей",
                phone="+7 (495) 123-45-67",
                email="zakaz@aviatech-demo.ru",
                notes="Ключевой заказчик серийных БПЛА",
            )
        )

    parts_by_sku: dict[str, Part] = {}
    for sku, name, unit, category in DEMO_PARTS:
        res = await session.execute(select(Part).where(Part.sku == sku))
        part = res.scalar_one_or_none()
        if part is None:
            part = Part(
                sku=sku,
                name=name,
                unit=unit,
                category=category,
                is_active=True,
            )
            session.add(part)
            await session.flush()
        parts_by_sku[part.sku] = part

    for b_data in DEMO_BOMS:
        code = str(b_data["code"])
        res = await session.execute(select(BomTemplate).where(BomTemplate.code == code))
        tpl = res.scalar_one_or_none()
        if tpl is None:
            tpl = BomTemplate(
                code=code,
                name=str(b_data["name"]),
                product_line=str(b_data["product_line"]),
                version=str(b_data["version"]),
                is_active=True,
            )
            session.add(tpl)
            await session.flush()

            for sku, qty, is_opt, note in b_data["items"]:  # type: ignore[attr-defined]
                part = parts_by_sku[sku]
                session.add(
                    BomTemplateItem(
                        template_id=tpl.id,
                        part_id=part.id,
                        quantity=qty,
                        is_optional=is_opt,
                        note=note,
                    )
                )

    await session.commit()


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await seed_all(session)
        print("Демо-данные успешно загружены (заказчик «АвиаТех», 20 деталей, 2 BOM, procurement).")


if __name__ == "__main__":
    asyncio.run(main())

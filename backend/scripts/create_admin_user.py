"""Создаёт пользователя admin@local / admin если его ещё нет."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import AsyncSessionLocal, Base, engine
from app.models.user import User, UserRole
from app.utils.security import hash_password


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "admin@example.com"))
        if result.scalar_one_or_none() is None:
            session.add(
                User(
                    email="admin@example.com",
                    hashed_password=hash_password("admin"),
                    full_name="Demo Manager",
                    role=UserRole.manager,
                )
            )
            await session.commit()
            print("Создан пользователь: admin@example.com / admin")
        else:
            print("Пользователь admin@example.com уже существует")


if __name__ == "__main__":
    asyncio.run(main())

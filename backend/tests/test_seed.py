import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.bom import BomTemplate
from app.models.customer import Customer
from app.models.part import Part
from app.models.user import User, UserRole

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo_data.py"
_SPEC = importlib.util.spec_from_file_location("seed_demo_data", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_SEED_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SEED_MOD)


@pytest.mark.asyncio
async def test_seed_demo_data_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
):
    async with session_factory() as session:
        await _SEED_MOD.seed_all(session)
        # Повторный вызов не должен создавать дубликаты
        await _SEED_MOD.seed_all(session)

        user_res = await session.execute(
            select(User).where(User.email == "procurement@example.com")
        )
        proc_user = user_res.scalar_one_or_none()
        assert proc_user is not None
        assert proc_user.role == UserRole.procurement

        cust_res = await session.execute(
            select(func.count()).select_from(Customer).where(Customer.name == "АвиаТех")
        )
        assert cust_res.scalar_one() == 1

        parts_count = await session.execute(select(func.count()).select_from(Part))
        assert parts_count.scalar_one() >= len(_SEED_MOD.DEMO_PARTS)

        boms_count = await session.execute(select(func.count()).select_from(BomTemplate))
        assert boms_count.scalar_one() >= len(_SEED_MOD.DEMO_BOMS)

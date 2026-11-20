from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, require_roles
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerRead])
async def list_customers(
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Customer]:
    result = await db.execute(select(Customer).order_by(Customer.name).offset(offset).limit(limit))
    return list(result.scalars().all())


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(
    _: Annotated[object, Depends(require_roles("manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: CustomerCreate,
) -> Customer:
    customer = Customer(**body.model_dump())
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    customer_id: UUID,
) -> Customer:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказчик не найден")
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    _: Annotated[object, Depends(require_roles("manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    customer_id: UUID,
    body: CustomerUpdate,
) -> Customer:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказчик не найден")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    await db.flush()
    await db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    _: Annotated[object, Depends(require_roles("manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    customer_id: UUID,
) -> None:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказчик не найден")
    await db.delete(customer)

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("")
async def list_orders_not_implemented() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TODO Кирилл: реестр заказов",
    )

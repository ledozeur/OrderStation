from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/deadlines")
async def deadlines_not_implemented() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TODO Кирилл: отчёт по срокам",
    )
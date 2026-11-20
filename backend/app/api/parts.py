from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/parts", tags=["parts"])


@router.get("")
async def list_parts_not_implemented() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TODO Андрей: список запчастей (см. docs/TZ.md)",
    )

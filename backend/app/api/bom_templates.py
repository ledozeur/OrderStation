from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/bom-templates", tags=["bom"])


@router.get("")
async def list_bom_not_implemented() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TODO Андрей: шаблоны BOM",
    )
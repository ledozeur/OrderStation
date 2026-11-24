from fastapi import APIRouter

from app.api import auth, bom_templates, customers, orders, parts, procurement, reports

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(customers.router)
api_router.include_router(parts.router)
api_router.include_router(bom_templates.router)
api_router.include_router(orders.router)
api_router.include_router(reports.router)
api_router.include_router(procurement.router)

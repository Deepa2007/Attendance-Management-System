
from fastapi import APIRouter

from app.api.v1.endpoints.employees import router as employees_router
from app.api.v1.endpoints.attendance import router as attendance_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.tenants import router as tenants_router


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(employees_router)
api_router.include_router(attendance_router)
api_router.include_router(auth_router)
api_router.include_router(reports_router)
api_router.include_router(tenants_router)

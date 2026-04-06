from fastapi import APIRouter

from app.api.v1.endpoints.sybil import router as sybil_router
from app.api.v1.endpoints.inspector import router as inspector_router
from app.api.v1.endpoints.stats import router as stats_router
from app.api.v1.endpoints.history import router as history_router

api_router = APIRouter()

# Module registration for API v1.
api_router.include_router(sybil_router, prefix="/sybil", tags=["Sybil"])
api_router.include_router(inspector_router, prefix="/inspector", tags=["Inspector"])
api_router.include_router(stats_router, prefix="/stats", tags=["Statistics"])
api_router.include_router(history_router, prefix="/history", tags=["History"])

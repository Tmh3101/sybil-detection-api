from fastapi import APIRouter

from app.api.v1.endpoints.sybil import router as sybil_router

api_router = APIRouter()

# Module registration for API v1.
api_router.include_router(sybil_router)


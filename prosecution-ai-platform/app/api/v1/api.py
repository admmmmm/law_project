from fastapi import APIRouter

from app.api.v1.endpoints.analysis import router as analysis_router
from app.api.v1.endpoints.ingestion import router as ingestion_router


api_router = APIRouter()
api_router.include_router(ingestion_router, tags=["ingestion"])
api_router.include_router(analysis_router, tags=["analysis"])

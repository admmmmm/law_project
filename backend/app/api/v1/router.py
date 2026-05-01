from fastapi import APIRouter

from app.api.v1.routes import analysis, cases, graph, health, ingestion, memories, reports

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(ingestion.router, prefix="/cases", tags=["ingestion"])
api_router.include_router(analysis.router, prefix="/cases", tags=["analysis"])
api_router.include_router(graph.router, prefix="/cases", tags=["graph"])
api_router.include_router(memories.router, prefix="/cases", tags=["memories"])
api_router.include_router(reports.router, prefix="/cases", tags=["reports"])

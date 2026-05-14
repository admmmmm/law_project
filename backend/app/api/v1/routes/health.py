from datetime import datetime, timezone

from fastapi import APIRouter

from app.adapters.algorithm import HippoRagBridge
from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "version": "0.1.0",
        "time": datetime.now(timezone.utc).isoformat(),
        "env": settings.app_env,
    }


@router.get("/health/hipporag")
def hipporag_health_check() -> dict[str, object]:
    status = HippoRagBridge().status()
    status["algorithm_provider"] = settings.algorithm_provider
    status["note"] = "available only means the Python package imports; model/index readiness still depends on BGE-M3 cache and API keys."
    return status

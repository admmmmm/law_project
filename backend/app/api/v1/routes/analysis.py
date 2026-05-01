from fastapi import APIRouter

from app.core.dependencies import AnalysisServiceDep
from app.schemas.analysis import AnalysisRunRequest, AnalysisRunResult

router = APIRouter()


@router.post("/{case_id}/analysis/run", response_model=AnalysisRunResult)
def run_analysis(case_id: str, payload: AnalysisRunRequest, service: AnalysisServiceDep) -> AnalysisRunResult:
    return service.run(case_id, payload)

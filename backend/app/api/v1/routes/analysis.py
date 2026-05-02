from fastapi import APIRouter

from app.core.dependencies import AnalysisServiceDep
from app.schemas.analysis import AnalysisRunRequest, AnalysisRunResult, ChatRequest, ChatResult, TraceRequest, TraceResult

router = APIRouter()


@router.post("/{case_id}/analysis/run", response_model=AnalysisRunResult)
def run_analysis(case_id: str, payload: AnalysisRunRequest, service: AnalysisServiceDep) -> AnalysisRunResult:
    return service.run(case_id, payload)


@router.post("/{case_id}/analysis/trace", response_model=TraceResult)
def trace_analysis(case_id: str, payload: TraceRequest, service: AnalysisServiceDep) -> TraceResult:
    return service.trace(case_id, payload)


@router.post("/{case_id}/analysis/chat", response_model=ChatResult)
def chat_analysis(case_id: str, payload: ChatRequest, service: AnalysisServiceDep) -> ChatResult:
    return service.chat(case_id, payload)

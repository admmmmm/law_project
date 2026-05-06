from fastapi import APIRouter

from app.core.dependencies import AnalysisServiceDep
from app.schemas.analysis import (
    AnalysisRunRequest,
    AnalysisRunResult,
    AnalysisThread,
    AnalysisThreadCreate,
    AnalysisThreadDetail,
    AnalysisThreadMessageCreate,
    ChatRequest,
    ChatResult,
    PortraitFactsResult,
    SuspicionAnalysisRequest,
    SuspicionAnalysisResult,
    TraceRequest,
    TraceResult,
)

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


@router.post("/{case_id}/analysis/portrait-facts", response_model=PortraitFactsResult)
def portrait_facts(case_id: str, service: AnalysisServiceDep, force: bool = False) -> PortraitFactsResult:
    return service.portrait_facts(case_id, force=force)


@router.post("/{case_id}/analysis/suspicion", response_model=SuspicionAnalysisResult)
def suspicion_analysis(case_id: str, payload: SuspicionAnalysisRequest, service: AnalysisServiceDep) -> SuspicionAnalysisResult:
    return service.suspicion_analysis(case_id, payload)


@router.get("/{case_id}/analysis/threads", response_model=list[AnalysisThread])
def list_analysis_threads(case_id: str, service: AnalysisServiceDep, mode: str | None = None) -> list[AnalysisThread]:
    return service.list_threads(case_id, mode=mode)


@router.post("/{case_id}/analysis/threads", response_model=AnalysisThreadDetail)
def create_analysis_thread(case_id: str, payload: AnalysisThreadCreate, service: AnalysisServiceDep) -> AnalysisThreadDetail:
    return service.create_thread(case_id, payload)


@router.get("/{case_id}/analysis/threads/{thread_id}", response_model=AnalysisThreadDetail)
def get_analysis_thread(case_id: str, thread_id: str, service: AnalysisServiceDep) -> AnalysisThreadDetail:
    return service.get_thread(case_id, thread_id)


@router.post("/{case_id}/analysis/threads/{thread_id}/messages", response_model=AnalysisThreadDetail)
def add_analysis_thread_message(case_id: str, thread_id: str, payload: AnalysisThreadMessageCreate, service: AnalysisServiceDep) -> AnalysisThreadDetail:
    return service.add_thread_message(case_id, thread_id, payload)


@router.delete("/{case_id}/analysis/threads/{thread_id}", status_code=204)
def delete_analysis_thread(case_id: str, thread_id: str, service: AnalysisServiceDep) -> None:
    service.delete_thread(case_id, thread_id)

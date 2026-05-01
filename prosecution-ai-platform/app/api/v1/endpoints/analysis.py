from fastapi import APIRouter, Body, HTTPException

from app.schemas.analysis import AnalysisRunRequest, AnalysisRunResponse
from app.services.case_store import list_case_extractions


router = APIRouter(prefix="/cases/{case_id}/analysis")


@router.post("/run", response_model=AnalysisRunResponse)
@router.post(
    "/run-graph",
    response_model=AnalysisRunResponse,
    summary="触发案件图谱分析任务",
    description="触发异步分析流程，返回 queued 状态。",
)
async def run_analysis(
    case_id: str,
    payload: AnalysisRunRequest | None = Body(default=None),
) -> AnalysisRunResponse:
    """
    触发案件分析流程。
    这里保留轻量实现，后续可接入任务队列或图谱构建流水线。
    """
    try:
        notes = payload.notes if payload else None
        _ = notes
        extractions = list_case_extractions(case_id)
        if not extractions:
            raise HTTPException(status_code=422, detail="当前案件暂无已接入证据，请先调用 ingestion 接口。")
        triples_count = sum(len(item.triples) for item in extractions)
        return AnalysisRunResponse(
            case_id=case_id,
            accepted=True,
            analyzed_evidence_count=len(extractions),
            triples_count=triples_count,
            message="分析任务已触发，已汇聚证据三元组缓冲区。",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"触发分析失败: {exc}") from exc

from pydantic import BaseModel, Field


class AnalysisRunRequest(BaseModel):
    notes: str | None = Field(default=None, description="可选分析备注")

    model_config = {
        "json_schema_extra": {
            "example": {
                "notes": "关注资金往来与时间线异常点。",
            }
        }
    }


class AnalysisRunResponse(BaseModel):
    case_id: str
    accepted: bool
    analyzed_evidence_count: int
    triples_count: int
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "case_01",
                "accepted": True,
                "analyzed_evidence_count": 3,
                "triples_count": 18,
                "message": "分析任务已触发，已汇聚证据三元组缓冲区。",
            }
        }
    }

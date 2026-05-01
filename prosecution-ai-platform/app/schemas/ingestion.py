from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    TEXT = "text"
    RECORD = "笔录"
    TRANSFER = "流水"
    DOC = "doc"
    DOCX = "docx"
    PDF = "pdf"
    TXT = "txt"
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"
    UNKNOWN = "unknown"


class IngestionTextRequest(BaseModel):
    title: str = Field(..., description="材料标题")
    content: str = Field(..., description="材料正文")
    source_type: SourceType = Field(..., description="来源类型，用于分流")

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "银行流水截图OCR文本",
                "content": "2024年3月12日，账户转出人民币50000元，收款方李四。",
                "source_type": "笔录",
            }
        }
    }


class Triple(BaseModel):
    subject: str
    relation: str
    object: str


class PassageItem(BaseModel):
    text: str
    triple_index: int


class ExtractionResult(BaseModel):
    route: str = Field(..., description="实际分流路径：structured/unstructured")
    triples: list[Triple]
    passages: list[PassageItem]
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionTextResponse(BaseModel):
    case_id: str
    accepted: bool
    evidences: list["EvidenceItem"]
    next_step: str = Field(default="run_analysis", description="建议前端调用的下一步动作")

    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "case_01",
                "accepted": True,
                "evidences": [
                    {
                        "evidence_id": "evd_8f5f5a1d",
                        "title": "银行流水截图OCR文本",
                        "source_type": "笔录",
                        "source_ref": "ingestion:text",
                        "content_preview": "2024年3月12日，账户转出人民币50000元，收款方李四。",
                        "created_at": "2026-04-30T01:59:08.928Z",
                    }
                ],
                "next_step": "run_analysis",
            }
        }
    }


class EvidenceItem(BaseModel):
    evidence_id: str
    title: str
    source_type: SourceType
    source_ref: str = Field(..., description="来源定位：如 ingestion:text、上传文件名等")
    content_preview: str = Field(..., description="入库正文截断预览")
    created_at: str

from datetime import datetime

from pydantic import BaseModel, Field


class TextIngestionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    source_type: str = "text"
    source_ref: str | None = None


class EvidenceRecord(BaseModel):
    evidence_id: str
    case_id: str
    title: str
    source_type: str
    source_ref: str | None = None
    content_preview: str
    created_at: datetime


class IngestionResult(BaseModel):
    case_id: str
    accepted: bool
    evidence: EvidenceRecord
    next_step: str = "run_analysis"

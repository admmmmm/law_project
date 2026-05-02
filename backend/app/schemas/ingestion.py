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


class EvidenceDetail(EvidenceRecord):
    content: str


class ExtractedTriple(BaseModel):
    subject: str
    relation: str
    object: str
    evidence_id: str | None = None
    properties: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class PassageRecord(BaseModel):
    text: str
    evidence_id: str | None = None
    triple_index: int | None = None


class ExtractionResult(BaseModel):
    route: str
    triples: list[ExtractedTriple] = Field(default_factory=list)
    passages: list[PassageRecord] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class IngestionResult(BaseModel):
    case_id: str
    accepted: bool
    evidence: EvidenceRecord
    extraction: ExtractionResult | None = None
    next_step: str = "run_analysis"


class BatchIngestionResult(BaseModel):
    case_id: str
    accepted: bool
    imported_count: int = 0
    skipped_count: int = 0
    evidences: list[EvidenceRecord] = Field(default_factory=list)
    results: list[IngestionResult] = Field(default_factory=list)
    skipped: list[dict[str, str]] = Field(default_factory=list)
    next_step: str = "run_analysis"

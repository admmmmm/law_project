from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ClaimStatus = Literal["verified", "unverified_claim", "rejected"]


class PassageRef(BaseModel):
    passage_index: int
    evidence_id: str | None = None
    text: str = ""


class DocumentClaim(BaseModel):
    claim_id: str
    claim: str
    claim_type: str = "fact"
    supporting_passage_refs: list[PassageRef] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    status: ClaimStatus = "unverified_claim"


class DocumentGenerationMeta(BaseModel):
    method: str = "rules"
    model: str = ""
    schema_version: str = "0.1.0"
    generated_at: datetime


class DocumentMotherNode(BaseModel):
    doc_id: str
    evidence_id: str
    title: str
    doc_type: str = "未知文书"
    process_stage: str = "未归类"
    formation_time: str | None = None
    event_time: str | None = None
    source_quality: str = "unknown"
    summary: str = ""
    proof_purpose: str = ""
    key_claims: list[DocumentClaim] = Field(default_factory=list)
    key_entities: list[str] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)
    quality_status: str = "ok"
    warnings: list[str] = Field(default_factory=list)
    source_content_hash: str
    extraction_hash: str
    builder_version: str = "document_mother_builder_v1"
    generation: DocumentGenerationMeta


class DocumentMotherGraph(BaseModel):
    case_id: str
    nodes: list[DocumentMotherNode] = Field(default_factory=list)
    rebuilt_count: int = 0
    warnings: list[str] = Field(default_factory=list)

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.document_mother import DocumentClaim


class SkillRegistryEntry(BaseModel):
    name: str
    title: str
    version: str = "0.1.0"
    description: str = ""
    enabled: bool = True
    manifest_hash: str
    content_hash: str
    manifest_json: dict[str, Any] = Field(default_factory=dict)
    synced_at: datetime


class RulePackSummary(BaseModel):
    name: str
    title: str
    version: str = "0.1.0"
    description: str = ""
    enabled: bool = True
    case_types: list[str] = Field(default_factory=list)
    task_types: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    content_hash: str = ""


class RuleFinding(BaseModel):
    finding_id: str
    skill_name: str
    rule_id: str
    finding_type: str
    severity: str = "medium"
    title: str
    reason: str
    supporting_documents: list[str] = Field(default_factory=list)
    supporting_claims: list[DocumentClaim] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    process_stage: str | None = None
    next_actions: list[str] = Field(default_factory=list)
    legal_caution: str = "该 finding 只提示风险、缺口或核查方向，不构成犯罪定性结论。"
    confidence: float = Field(default=0.0, ge=0, le=1)
    evidence_level: str = "low"
    data_completeness: str = "unknown"
    related_hypotheses: list[str] = Field(default_factory=list)
    debug_trace: list[str] = Field(default_factory=list)
    created_from: str = "rule_pack"
    status: str = "active"


class NotTriggeredRule(BaseModel):
    rule_id: str
    reason: str


class RulePackRunResult(BaseModel):
    case_id: str
    rule_pack: str
    status: str = "completed"
    findings: list[RuleFinding] = Field(default_factory=list)
    not_triggered: list[NotTriggeredRule] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    created_at: datetime


class RuleBundleRunRequest(BaseModel):
    skill_names: list[str] = Field(default_factory=list)


class RuleBundleRunResult(BaseModel):
    case_id: str
    status: str = "completed"
    results: list[RulePackRunResult] = Field(default_factory=list)

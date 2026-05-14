from datetime import datetime

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = None
    legal_basis: str | None = None
    offense_id: str | None = None
    owner: str | None = None


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    legal_basis: str | None = None
    offense_id: str | None = None
    owner: str | None = None


class CaseSummary(BaseModel):
    case_id: str
    title: str
    status: str
    created_at: datetime
    evidence_count: int = 0
    memory_count: int = 0
    offense_id: str | None = None
    legal_basis: str | None = None


class CaseDetail(CaseSummary):
    description: str | None = None
    owner: str | None = None


class CaseOverviewStats(BaseModel):
    evidence_count: int = 0
    passage_count: int = 0
    document_graph_node_count: int = 0
    document_graph_edge_count: int = 0
    passage_graph_node_count: int = 0
    passage_graph_edge_count: int = 0
    raw_graph_node_count: int = 0
    raw_graph_edge_count: int = 0
    analysis_count: int = 0
    portrait_count: int = 0
    report_count: int = 0


class CaseOverviewNextStep(BaseModel):
    label: str
    reason: str
    target: str


class CaseOverviewEvidence(BaseModel):
    evidence_id: str
    name: str
    brief: str = ""
    evidence_type: str = ""
    proof_item: str = ""
    status: str = "已解析"
    created_at: datetime
    passage_count: int = 0


class CaseOverview(BaseModel):
    case_id: str
    name: str
    case_number: str = ""
    suspects: list[str] = Field(default_factory=list)
    offense: str = ""
    case_type: str = ""
    stage: str
    created_at: datetime
    updated_at: datetime
    stats: CaseOverviewStats
    next_step: CaseOverviewNextStep
    recent_evidence: list[CaseOverviewEvidence] = Field(default_factory=list)

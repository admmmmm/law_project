from pydantic import BaseModel, Field

from app.schemas.graph import InvestigationGraph


class AnalysisRunRequest(BaseModel):
    scopes: list[str] = Field(default_factory=lambda: ["entities", "relations", "collision", "portrait"])
    focus_person_ids: list[str] = Field(default_factory=list)
    force_rebuild: bool = False


class AnalysisRunResult(BaseModel):
    case_id: str
    status: str
    summary: str
    graph: InvestigationGraph


class TraceRequest(BaseModel):
    query: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=8, ge=1, le=30)


class TracePassage(BaseModel):
    rank: int
    score: float
    passage: str
    evidence_id: str | None = None
    evidence_title: str | None = None


class TracePath(BaseModel):
    source: str
    relation: str
    target: str
    score: float
    evidence_ids: list[str] = Field(default_factory=list)


class TraceResult(BaseModel):
    case_id: str
    query: str
    provider: str
    passages: list[TracePassage] = Field(default_factory=list)
    paths: list[TracePath] = Field(default_factory=list)
    error: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=8, ge=1, le=30)


class ChatResult(BaseModel):
    case_id: str
    question: str
    answer: str
    provider: str
    passages: list[TracePassage] = Field(default_factory=list)
    paths: list[TracePath] = Field(default_factory=list)
    error: str | None = None

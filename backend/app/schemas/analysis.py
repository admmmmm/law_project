from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.graph import InvestigationGraph
from app.schemas.analysis_skill import RuleFinding


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


class PortraitFact(BaseModel):
    fact_id: str
    category: str
    group: str
    subject: str
    relation: str
    object: str
    text: str
    time: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    passages: list[TracePassage] = Field(default_factory=list)
    confidence: float = 0.0
    source: str = "hipporag"


class RagToolCall(BaseModel):
    name: str = "HippoRAG.retrieve_trace"
    query: str
    mode: str = "semantic_ppr"
    top_k: int = 10
    returned: int = 0
    note: str | None = None


class RetrievalArtifact(BaseModel):
    artifact_id: str
    artifact_type: str = Field(pattern="^(passage|graph_fact|legal_passage|entity|summary)$")
    title: str = ""
    text: str
    score: float = 0.0
    evidence_id: str | None = None
    source_id: str | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class RetrievalToolCall(BaseModel):
    tool_call_id: str
    tool_name: str
    arguments: dict[str, str | int | float | bool | list[str] | None] = Field(default_factory=dict)
    summary: str = ""
    passages: list[TracePassage] = Field(default_factory=list)
    graph_facts: list[str] = Field(default_factory=list)
    legal_passages: list[TracePassage] = Field(default_factory=list)
    rule_findings: list[RuleFinding] = Field(default_factory=list)
    document_groups: list[dict[str, object]] = Field(default_factory=list)
    new_entities: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RetrievalStep(BaseModel):
    step_id: str
    session_id: str
    round_index: int
    retrieval_goals: list[str] = Field(default_factory=list)
    tool_calls: list[RetrievalToolCall] = Field(default_factory=list)
    coverage_summary: str = ""
    unresolved_gaps: list[str] = Field(default_factory=list)
    ready_to_answer: bool = False
    created_at: datetime


class RetrievalSession(BaseModel):
    session_id: str
    case_id: str
    mode: str
    question: str
    status: str = "running"
    planner_model: str = ""
    analysis_model: str = ""
    tool_call_summary: str = ""
    retrieval_steps_count: int = 0
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class RetrievalSessionDetail(BaseModel):
    session: RetrievalSession
    steps: list[RetrievalStep] = Field(default_factory=list)


class PortraitFactsResult(BaseModel):
    case_id: str
    provider: str
    relationship_narrative: str = ""
    behavior_narrative: str = ""
    relationship_facts: list[PortraitFact] = Field(default_factory=list)
    behavior_facts: list[PortraitFact] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    tool_calls: list[RagToolCall] = Field(default_factory=list)
    tool_call_note: str = ""
    tool_call_summary: str = ""
    retrieval_session_id: str | None = None
    retrieval_steps_count: int = 0
    error: str | None = None


class SuspicionAnalysisRequest(BaseModel):
    mode: str = Field(default="hypothesis", pattern="^(cross_case|hypothesis|financial_flow)$")
    hypothesis: str | None = None
    selected_case_ids: list[str] = Field(default_factory=list)
    max_items: int = Field(default=12, ge=1, le=50)


class SuspicionCandidate(BaseModel):
    candidate_id: str
    title: str
    category: str
    method: str
    risk_level: str = "medium"
    status: str = "candidate"
    confidence: float = Field(default=0.0, ge=0, le=1)
    explanation: str
    support_paths: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    supporting_passages: list[TracePassage] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    gnn_note: str | None = None


class SuspicionAnalysisResult(BaseModel):
    case_id: str
    provider: str
    summary: str
    candidates: list[SuspicionCandidate] = Field(default_factory=list)
    adopted_hint: str = "本接口只生成疑点候选。是否采纳由检察官在前端确认。"
    error: str | None = None


class GroundedSentence(BaseModel):
    sentence_id: str
    text: str
    start: int = 0
    end: int = 0
    status: str = "weak"
    supporting_passages: list[TracePassage] = Field(default_factory=list)
    supporting_graph_paths: list[TracePath] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)


class AnalysisThread(BaseModel):
    thread_id: str
    case_id: str
    mode: str = Field(pattern="^(hypothesis|financial_flow)$")
    title: str
    summary: str = ""
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class AnalysisMessage(BaseModel):
    message_id: str
    thread_id: str
    role: str = Field(pattern="^(user|assistant)$")
    content: str
    created_at: datetime
    claims: list[GroundedSentence] = Field(default_factory=list)
    retrievals: list[TracePassage] = Field(default_factory=list)
    graph_context: list[str] = Field(default_factory=list)
    legal_context: list[TracePassage] = Field(default_factory=list)
    mentioned_evidence_ids: list[str] = Field(default_factory=list)
    tool_call_summary: str = ""
    retrieval_session_id: str | None = None
    retrieval_steps_count: int = 0
    error: str | None = None


class AnalysisThreadCreate(BaseModel):
    mode: str = Field(pattern="^(hypothesis|financial_flow)$")
    title: str | None = None
    initial_question: str = Field(min_length=1)


class AnalysisThreadMessageCreate(BaseModel):
    question: str = Field(min_length=1)


class AnalysisThreadDetail(BaseModel):
    thread: AnalysisThread
    messages: list[AnalysisMessage] = Field(default_factory=list)

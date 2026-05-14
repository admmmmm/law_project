from pydantic import BaseModel, Field


class EvidenceDocumentNode(BaseModel):
    id: str
    type: str = "document"
    evidence_id: str
    title: str
    doc_type: str = "未知文书"
    process_stage: str = "未归类"
    summary: str = ""
    proof_purpose: str = ""
    map_tags: list[str] = Field(default_factory=list)
    passage_count: int = 0
    triple_count: int = 0
    finding_count: int = 0
    quality_status: str = "ok"
    event_time: str | None = None
    formation_time: str | None = None


class EvidencePassageNode(BaseModel):
    id: str
    type: str = "passage"
    parent_doc_id: str
    evidence_id: str
    passage_index: int
    summary: str = ""
    text_preview: str = ""
    text: str = ""
    triple_count: int = 0
    entities: list[str] = Field(default_factory=list)
    referenced_by_report: bool = False


class EvidenceTripleNode(BaseModel):
    id: str
    type: str = "triple"
    parent_passage_id: str
    subject: str
    predicate: str
    object: str
    confidence: str = "medium"
    supporting_text: str = ""
    source_doc_id: str
    evidence_id: str


class EvidenceContainmentEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str


class EvidenceDocumentEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    label: str
    reason: str
    supporting_passage_ids: list[str] = Field(default_factory=list)
    supporting_triple_ids: list[str] = Field(default_factory=list)
    shared_entities: list[str] = Field(default_factory=list)
    weight: float = Field(default=0.0, ge=0, le=1)
    visible_by_default: bool = True


class EvidencePassageEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    label: str
    supporting_triple_ids: list[str] = Field(default_factory=list)
    shared_entities: list[str] = Field(default_factory=list)
    weight: float = Field(default=0.0, ge=0, le=1)
    visible_by_default: bool = True


class EvidenceMap(BaseModel):
    case_id: str
    documents: list[EvidenceDocumentNode] = Field(default_factory=list)
    passages: list[EvidencePassageNode] = Field(default_factory=list)
    triples: list[EvidenceTripleNode] = Field(default_factory=list)
    document_edges: list[EvidenceDocumentEdge] = Field(default_factory=list)
    passage_edges: list[EvidencePassageEdge] = Field(default_factory=list)
    containment_edges: list[EvidenceContainmentEdge] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

from typing import Any, Literal

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    node_id: str
    label: str
    type: str
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    timestamp: str | None = None
    time_range: list[str] = Field(default_factory=list)
    manually_verified: bool = False


class GraphEdge(BaseModel):
    edge_id: str
    source_id: str
    target_id: str
    relation: str
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)
    properties: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    timestamp: str | None = None
    time_range: list[str] = Field(default_factory=list)
    manually_verified: bool = False


class SuspiciousClue(BaseModel):
    clue_id: str
    title: str
    category: str
    description: str
    risk_level: str = "medium"
    evidence_ids: list[str] = Field(default_factory=list)
    source_passages: list[dict[str, str | int | float | None]] = Field(default_factory=list)


class InvestigationGraph(BaseModel):
    case_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    clues: list[SuspiciousClue] = Field(default_factory=list)


class MergedGraphRequest(BaseModel):
    selected_case_ids: list[str] = Field(default_factory=list)


class GraphInterventionRequest(BaseModel):
    action: str = Field(pattern="^(upsert_node|upsert_edge|delete_node|delete_edge|verify_node|verify_edge)$")
    node: GraphNode | None = None
    edge: GraphEdge | None = None
    target_id: str | None = None
    reason: str | None = None


RawGraphAction = Literal["create_node", "update_node", "delete_node", "create_edge", "update_edge", "delete_edge"]


class RawGraphActionRequest(BaseModel):
    action: RawGraphAction
    layer: str = "raw"
    payload: dict[str, Any] = Field(default_factory=dict)


class RawGraphActionResponse(BaseModel):
    status: str = "ok"
    message: str
    action: RawGraphAction
    updated_layer: str = "raw"
    graph: dict[str, Any] = Field(default_factory=dict)

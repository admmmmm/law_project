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

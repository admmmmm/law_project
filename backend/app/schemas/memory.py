from datetime import datetime

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1)
    source: str = "investigator_interaction"
    evidence_hint: str | None = None
    confirmed: bool = False


class MemoryRecord(BaseModel):
    memory_id: str
    case_id: str
    content: str
    source: str
    evidence_hint: str | None = None
    confirmed: bool
    written_back_to_graph: bool
    created_at: datetime

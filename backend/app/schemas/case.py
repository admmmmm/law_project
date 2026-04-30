from datetime import datetime

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = None
    legal_basis: str | None = None
    owner: str | None = None


class CaseSummary(BaseModel):
    case_id: str
    title: str
    status: str
    created_at: datetime
    evidence_count: int = 0
    memory_count: int = 0


class CaseDetail(CaseSummary):
    description: str | None = None
    legal_basis: str | None = None
    owner: str | None = None

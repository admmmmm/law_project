from datetime import datetime

from pydantic import BaseModel, Field


class PortraitSection(BaseModel):
    title: str
    items: list[str] = Field(default_factory=list)
    claims: list["PortraitClaim"] = Field(default_factory=list)


class ClaimPassage(BaseModel):
    evidence_id: str
    evidence_title: str | None = None
    passage: str
    score: float = 0.0


class PortraitClaim(BaseModel):
    claim_id: str
    text: str
    section: str
    element: str | None = None
    status: str = "weak"
    confidence: float = 0.0
    supporting_passages: list[ClaimPassage] = Field(default_factory=list)
    verification_notes: str = ""


class PortraitReport(BaseModel):
    report_id: str
    case_id: str
    generated_at: datetime
    title: str
    sections: list[PortraitSection]
    suggestions: list[str] = Field(default_factory=list)
    generation_method: str = "template_fallback"

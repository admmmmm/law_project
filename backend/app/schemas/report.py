from datetime import datetime

from pydantic import BaseModel, Field


class PortraitSection(BaseModel):
    title: str
    items: list[str] = Field(default_factory=list)


class PortraitReport(BaseModel):
    report_id: str
    case_id: str
    generated_at: datetime
    title: str
    sections: list[PortraitSection]
    suggestions: list[str] = Field(default_factory=list)

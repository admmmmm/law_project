from dataclasses import dataclass, field
from threading import Lock

from app.schemas.case import CaseDetail
from app.schemas.graph import InvestigationGraph
from app.schemas.ingestion import EvidenceRecord, ExtractionResult
from app.schemas.memory import MemoryRecord
from app.schemas.report import PortraitReport


@dataclass
class MemoryStore:
    cases: dict[str, CaseDetail] = field(default_factory=dict)
    evidence: dict[str, list[EvidenceRecord]] = field(default_factory=dict)
    extractions: dict[str, ExtractionResult] = field(default_factory=dict)
    graphs: dict[str, InvestigationGraph] = field(default_factory=dict)
    reports: dict[str, PortraitReport] = field(default_factory=dict)
    memories: dict[str, list[MemoryRecord]] = field(default_factory=dict)
    raw_contents: dict[str, str] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)


_store = MemoryStore()


def get_store() -> MemoryStore:
    return _store

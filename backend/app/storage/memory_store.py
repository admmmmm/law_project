import json
from dataclasses import dataclass, field
from pathlib import Path
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
    state_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / "outputs" / "local_store" / "state.json"
    )

    def load(self) -> None:
        if not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            broken_path = self.state_path.with_suffix(".broken.json")
            try:
                self.state_path.replace(broken_path)
            except Exception:
                pass
            return

        try:
            self.cases = {case_id: CaseDetail.model_validate(item) for case_id, item in data.get("cases", {}).items()}
            self.evidence = {
                case_id: [EvidenceRecord.model_validate(item) for item in items]
                for case_id, items in data.get("evidence", {}).items()
            }
            self.extractions = {
                evidence_id: ExtractionResult.model_validate(item)
                for evidence_id, item in data.get("extractions", {}).items()
            }
            self.graphs = {
                case_id: InvestigationGraph.model_validate(item)
                for case_id, item in data.get("graphs", {}).items()
            }
            self.reports = {
                case_id: PortraitReport.model_validate(item)
                for case_id, item in data.get("reports", {}).items()
            }
            self.memories = {
                case_id: [MemoryRecord.model_validate(item) for item in items]
                for case_id, items in data.get("memories", {}).items()
            }
            self.raw_contents = {str(key): str(value) for key, value in data.get("raw_contents", {}).items()}
        except Exception:
            broken_path = self.state_path.with_suffix(".broken.json")
            try:
                self.state_path.replace(broken_path)
            except Exception:
                pass

    def save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "cases": {case_id: item.model_dump(mode="json") for case_id, item in self.cases.items()},
            "evidence": {
                case_id: [item.model_dump(mode="json") for item in items]
                for case_id, items in self.evidence.items()
            },
            "extractions": {
                evidence_id: item.model_dump(mode="json")
                for evidence_id, item in self.extractions.items()
            },
            "graphs": {case_id: item.model_dump(mode="json") for case_id, item in self.graphs.items()},
            "reports": {case_id: item.model_dump(mode="json") for case_id, item in self.reports.items()},
            "memories": {
                case_id: [item.model_dump(mode="json") for item in items]
                for case_id, items in self.memories.items()
            },
            "raw_contents": self.raw_contents,
        }
        temp_path = self.state_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.state_path)


_store = MemoryStore()
_store.load()


def get_store() -> MemoryStore:
    return _store

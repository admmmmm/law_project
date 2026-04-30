from app.core.errors import not_found
from app.schemas.case import CaseCreate, CaseDetail, CaseSummary
from app.schemas.common import new_id, now_utc
from app.schemas.graph import InvestigationGraph
from app.storage.memory_store import MemoryStore


class CaseService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def create_case(self, payload: CaseCreate) -> CaseDetail:
        with self.store.lock:
            case_id = new_id("case")
            case = CaseDetail(
                case_id=case_id,
                title=payload.title,
                description=payload.description,
                legal_basis=payload.legal_basis,
                owner=payload.owner,
                status="created",
                created_at=now_utc(),
                evidence_count=0,
                memory_count=0,
            )
            self.store.cases[case_id] = case
            self.store.evidence[case_id] = []
            self.store.memories[case_id] = []
            self.store.graphs[case_id] = InvestigationGraph(case_id=case_id)
            return case

    def list_cases(self) -> list[CaseSummary]:
        with self.store.lock:
            return [
                CaseSummary(
                    case_id=case.case_id,
                    title=case.title,
                    status=case.status,
                    created_at=case.created_at,
                    evidence_count=len(self.store.evidence.get(case.case_id, [])),
                    memory_count=len(self.store.memories.get(case.case_id, [])),
                )
                for case in self.store.cases.values()
            ]

    def get_case(self, case_id: str) -> CaseDetail:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")
            return case.model_copy(
                update={
                    "evidence_count": len(self.store.evidence.get(case_id, [])),
                    "memory_count": len(self.store.memories.get(case_id, [])),
                }
            )

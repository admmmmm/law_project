import sqlite3

from app.core.errors import not_found
from app.schemas.case import CaseCreate, CaseDetail, CaseSummary, CaseUpdate
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
                offense_id=payload.offense_id,
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
            self.store.flush_case(case_id)
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
                    offense_id=case.offense_id,
                    legal_basis=case.legal_basis,
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

    def update_case(self, case_id: str, payload: CaseUpdate) -> CaseDetail:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")

            updates = payload.model_dump(exclude_unset=True)
            if "offense_id" in updates and updates["offense_id"] == "":
                updates["offense_id"] = None
            updated = case.model_copy(update=updates)
            self.store.cases[case_id] = updated
            self.store.flush_case(case_id)
            return updated.model_copy(
                update={
                    "evidence_count": len(self.store.evidence.get(case_id, [])),
                    "memory_count": len(self.store.memories.get(case_id, [])),
                }
            )

    def delete_case(self, case_id: str) -> None:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")

            evidence_ids = [item.evidence_id for item in self.store.evidence.get(case_id, [])]
            self.store.cases.pop(case_id, None)
            self.store.evidence.pop(case_id, None)
            self.store.graphs.pop(case_id, None)
            self.store.reports.pop(case_id, None)
            self.store.portrait_facts.pop(case_id, None)
            self.store.memories.pop(case_id, None)
            self.store.analysis_threads.pop(case_id, None)
            self.store.analysis_messages.pop(case_id, None)
            for evidence_id in evidence_ids:
                self.store.raw_contents.pop(evidence_id, None)
                self.store.extractions.pop(evidence_id, None)

            with sqlite3.connect(self.store.db_path) as conn:
                for table in ["cases", "evidence", "raw_contents", "extractions", "graphs", "reports", "portrait_facts", "memories", "analysis_threads", "analysis_messages"]:
                    conn.execute(f"DELETE FROM {table} WHERE case_id = ?", (case_id,))
                conn.commit()

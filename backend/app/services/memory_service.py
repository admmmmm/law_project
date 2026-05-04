from app.core.errors import bad_request, not_found
from app.schemas.common import new_id, now_utc
from app.schemas.graph import GraphNode
from app.schemas.memory import MemoryCreate, MemoryRecord
from app.storage.memory_store import MemoryStore


class MemoryService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def create(self, case_id: str, payload: MemoryCreate) -> MemoryRecord:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            record = MemoryRecord(
                memory_id=new_id("mem"),
                case_id=case_id,
                content=payload.content,
                source=payload.source,
                evidence_hint=payload.evidence_hint,
                confirmed=payload.confirmed,
                written_back_to_graph=False,
                created_at=now_utc(),
            )
            self.store.memories.setdefault(case_id, []).append(record)
            self.store.flush_case(case_id)
            return record

    def list_by_case(self, case_id: str) -> list[MemoryRecord]:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            return self.store.memories.get(case_id, [])

    def writeback_to_graph(self, case_id: str, memory_id: str) -> MemoryRecord:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            records = self.store.memories.get(case_id, [])
            target = next((record for record in records if record.memory_id == memory_id), None)
            if not target:
                raise not_found("memory not found")
            if not target.confirmed:
                raise bad_request("only confirmed memory can be written back to graph")

            graph = self.store.graphs[case_id]
            graph.nodes.append(
                GraphNode(
                    node_id=f"memory:{target.memory_id}",
                    label=target.content[:40],
                    type="confirmed_memory",
                    properties={"source": target.source, "evidence_hint": target.evidence_hint},
                    manually_verified=True,
                )
            )

            updated = target.model_copy(update={"written_back_to_graph": True})
            self.store.memories[case_id] = [updated if record.memory_id == memory_id else record for record in records]
            self.store.graphs[case_id] = graph
            self.store.flush_case(case_id)
            return updated

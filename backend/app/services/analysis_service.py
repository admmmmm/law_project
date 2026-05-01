from app.adapters.algorithm import AlgorithmAdapter
from app.core.errors import not_found
from app.schemas.analysis import AnalysisRunRequest, AnalysisRunResult
from app.storage.memory_store import MemoryStore


class AnalysisService:
    def __init__(self, store: MemoryStore, algorithm: AlgorithmAdapter) -> None:
        self.store = store
        self.algorithm = algorithm

    def run(self, case_id: str, payload: AnalysisRunRequest) -> AnalysisRunResult:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")

            evidence = self.store.evidence.get(case_id, [])
            graph = self.algorithm.build_graph(case_id, evidence, self.store.raw_contents)
            self.store.graphs[case_id] = graph
            self.store.cases[case_id] = case.model_copy(update={"status": "analyzed"})

            scope_text = "、".join(payload.scopes)
            summary = f"已完成 {scope_text} 分析，生成 {len(graph.nodes)} 个节点、{len(graph.edges)} 条关系、{len(graph.clues)} 条线索。"
            return AnalysisRunResult(case_id=case_id, status="completed", summary=summary, graph=graph)

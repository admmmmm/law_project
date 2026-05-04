from app.adapters.algorithm import AlgorithmAdapter
from app.core.errors import not_found
from app.schemas.analysis import AnalysisRunRequest, AnalysisRunResult, ChatRequest, ChatResult, TracePath, TraceRequest, TraceResult
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
            graph = self.algorithm.build_graph(case_id, evidence, self.store.raw_contents, self.store.extractions)
            self.store.graphs[case_id] = graph
            self.store.cases[case_id] = case.model_copy(update={"status": "analyzed"})
            self.store.flush_case(case_id)

            scope_text = " / ".join(payload.scopes)
            summary = (
                f"已完成 {scope_text} 分析，"
                f"生成 {len(graph.nodes)} 个节点、{len(graph.edges)} 条关系、{len(graph.clues)} 条线索。"
            )
            return AnalysisRunResult(case_id=case_id, status="completed", summary=summary, graph=graph)

    def trace(self, case_id: str, payload: TraceRequest) -> TraceResult:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")
            evidence = list(self.store.evidence.get(case_id, []))
            raw_contents = dict(self.store.raw_contents)
            extractions = dict(self.store.extractions)
            graph = self.store.graphs.get(case_id)

        passages, error = self.algorithm.retrieve_trace(
            case_id=case_id,
            query=payload.query,
            evidence=evidence,
            raw_contents=raw_contents,
            extractions=extractions,
            top_k=payload.top_k,
        )
        return TraceResult(
            case_id=case_id,
            query=payload.query,
            provider=self.algorithm.provider,
            passages=passages,
            paths=_rank_graph_paths(payload.query, graph, payload.evidence_ids),
            error=error,
        )

    def chat(self, case_id: str, payload: ChatRequest) -> ChatResult:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")
            evidence = list(self.store.evidence.get(case_id, []))
            raw_contents = dict(self.store.raw_contents)
            extractions = dict(self.store.extractions)
            graph = self.store.graphs.get(case_id)

        answer, passages, error = self.algorithm.answer_question(
            case_id=case_id,
            question=payload.question,
            evidence=evidence,
            raw_contents=raw_contents,
            extractions=extractions,
            top_k=payload.top_k,
        )
        return ChatResult(
            case_id=case_id,
            question=payload.question,
            answer=answer,
            provider=self.algorithm.provider,
            passages=passages,
            paths=_rank_graph_paths(payload.question, graph, payload.evidence_ids),
            error=error,
        )


def _rank_graph_paths(query: str, graph, evidence_ids: list[str], limit: int = 12) -> list[TracePath]:
    if not graph:
        return []
    query_terms = [term for term in query.replace(",", " ").replace("，", " ").replace("。", " ").split() if term]
    evidence_set = set(evidence_ids)
    labels = {node.node_id: node.label for node in graph.nodes}
    paths: list[TracePath] = []
    for edge in graph.edges:
        source = labels.get(edge.source_id, edge.source_id)
        target = labels.get(edge.target_id, edge.target_id)
        text = f"{source} {edge.relation} {target} {' '.join(str(v) for v in edge.properties.values())}"
        term_score = sum(1 for term in query_terms if term and term in text)
        evidence_score = 2 if evidence_set and evidence_set.intersection(edge.evidence_ids) else 0
        count_score = min(float(edge.properties.get("count", 1) or 1), 5.0) / 5.0
        score = float(term_score + evidence_score + count_score)
        if score <= 0 and query_terms:
            continue
        paths.append(
            TracePath(
                source=source,
                relation=edge.relation,
                target=target,
                score=score,
                evidence_ids=edge.evidence_ids,
            )
        )
    return sorted(paths, key=lambda item: item.score, reverse=True)[:limit]

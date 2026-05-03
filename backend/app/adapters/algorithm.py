from __future__ import annotations

import re
import sys
from collections import defaultdict
from os import getenv
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.schemas.analysis import TracePassage
from app.schemas.common import new_id
from app.schemas.graph import GraphEdge, GraphNode, InvestigationGraph, SuspiciousClue
from app.schemas.ingestion import EvidenceRecord, ExtractionResult, ExtractedTriple
from app.services.llm_context_debug import log_llm_context


class HippoRagBridge:
    """Lazy bridge to the vendored HippoRAG code under need/HippoRAG."""

    def __init__(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[3]
        self.hipporag_src = self.repo_root / "need" / "HippoRAG" / "src"
        self.available = self.hipporag_src.exists()
        self.error: str | None = None

    def load_class(self) -> type[Any] | None:
        if not self.available:
            self.error = f"HippoRAG source not found: {self.hipporag_src}"
            return None
        if str(self.hipporag_src) not in sys.path:
            sys.path.insert(0, str(self.hipporag_src))
        try:
            from hipporag.HippoRAG import HippoRAG

            return HippoRAG
        except Exception as exc:  # pragma: no cover - depends on optional local deps
            self.error = str(exc)
            return None

    def load_config_class(self) -> type[Any] | None:
        if str(self.hipporag_src) not in sys.path:
            sys.path.insert(0, str(self.hipporag_src))
        try:
            from hipporag.utils.config_utils import BaseConfig

            return BaseConfig
        except Exception as exc:  # pragma: no cover - depends on optional local deps
            self.error = str(exc)
            return None

    def status(self) -> dict[str, Any]:
        klass = self.load_class()
        return {
            "provider": "hipporag",
            "source": str(self.hipporag_src),
            "available": bool(klass),
            "error": self.error,
        }


class AlgorithmAdapter:
    """Algorithm boundary for graph building, retrieval, and clue generation."""

    def __init__(self, provider: str = "stub") -> None:
        self.provider = provider
        self.hipporag = HippoRagBridge() if provider == "hipporag" else None

    def build_graph(
        self,
        case_id: str,
        evidence: list[EvidenceRecord],
        raw_contents: dict[str, str],
        extractions: dict[str, ExtractionResult] | None = None,
    ) -> InvestigationGraph:
        extractions = extractions or {}
        hippo_result = self._run_hipporag(case_id, evidence, raw_contents, extractions) if self.hipporag else None
        if self.hipporag and hippo_result and hippo_result.get("error") and settings.hipporag_fail_fast:
            raise RuntimeError(f"HippoRAG analysis failed: {hippo_result['error']}")
        if hippo_result and hippo_result["triples"]:
            extractions = self._merge_hipporag_extractions(extractions, hippo_result)
        graph = self._build_aggregated_graph(case_id, evidence, raw_contents, extractions)
        if self.hipporag:
            properties = self.hipporag.status()
            if hippo_result:
                properties.update(
                    {
                        "indexed_docs": hippo_result.get("indexed_docs", 0),
                        "openie_triples": len(hippo_result.get("triples", [])),
                        "openie_entities": len(hippo_result.get("entities", [])),
                        "graph_nodes": hippo_result.get("graph_nodes"),
                        "graph_edges": hippo_result.get("graph_edges"),
                        "qa_answers": len(hippo_result.get("qa", [])),
                        "retrieve_ready": hippo_result.get("retrieve_ready", False),
                        "error": hippo_result.get("error"),
                    }
                )
            graph.nodes.append(
                GraphNode(
                    node_id="algorithm:hipporag",
                    label="HippoRAG",
                    type="algorithm_provider",
                    properties=properties,
                    manually_verified=not bool(properties.get("error")),
                )
            )
            if hippo_result and hippo_result.get("qa"):
                graph.clues.extend(self._clues_from_hipporag_qa(hippo_result["qa"]))
        return graph

    def retrieve_trace(
        self,
        case_id: str,
        query: str,
        evidence: list[EvidenceRecord],
        raw_contents: dict[str, str],
        extractions: dict[str, ExtractionResult] | None = None,
        top_k: int = 8,
    ) -> tuple[list[TracePassage], str | None]:
        if not self.hipporag:
            return [], "当前 ALGORITHM_PROVIDER 不是 hipporag，无法返回 PPR 检索结果。"

        klass = self.hipporag.load_class()
        config_class = self.hipporag.load_config_class()
        if klass is None or config_class is None:
            return [], self.hipporag.error or "HippoRAG class is unavailable"
        if not (getenv("DEEPSEEK_API_KEY") or getenv("OPENAI_API_KEY")):
            return [], "DEEPSEEK_API_KEY is not set, so HippoRAG retrieval/rerank cannot call the LLM"

        docs, doc_evidence = self._build_hipporag_docs(evidence, raw_contents, extractions or {}, include_structured=True)
        if not docs:
            return [], "no passages available for HippoRAG retrieval"
        docs = docs[: max(settings.hipporag_max_docs, 1)]
        normalized_doc_evidence = {" ".join(doc.split()): doc_evidence.get(doc) for doc in docs}
        titles = {item.evidence_id: item.title for item in evidence}

        try:
            save_dir = self._case_hipporag_save_dir(case_id)
            config = config_class(
                llm_name=settings.hipporag_llm_name,
                llm_base_url=settings.hipporag_llm_base_url,
                embedding_model_name=settings.hipporag_embedding_model,
                save_dir=str(save_dir),
                retrieval_top_k=max(top_k, settings.hipporag_retrieval_top_k),
                qa_top_k=settings.hipporag_qa_top_k,
            )
            hipporag = klass(global_config=config)
            hipporag.index(docs)
            results = _safe_sequence(hipporag.retrieve([query], num_to_retrieve=top_k))
            solution = results[0] if results else None
            if solution is None:
                return [], None

            passages: list[TracePassage] = []
            scores = _safe_sequence(getattr(solution, "doc_scores", []))
            docs_out = _safe_sequence(getattr(solution, "docs", []))
            for idx, doc in enumerate(docs_out[:top_k]):
                normalized = " ".join(str(doc).split())
                evidence_id = normalized_doc_evidence.get(normalized)
                score = float(scores[idx]) if idx < len(scores) else 0.0
                passage = _trim_passage_for_query(str(doc), query, settings.hipporag_trace_window_chars)
                passages.append(
                    TracePassage(
                        rank=idx + 1,
                        score=score,
                        passage=passage,
                        evidence_id=evidence_id,
                        evidence_title=titles.get(evidence_id or ""),
                    )
                )
            return passages, None
        except Exception as exc:  # pragma: no cover - requires external model/API
            return [], str(exc)

    def answer_question(
        self,
        case_id: str,
        question: str,
        evidence: list[EvidenceRecord],
        raw_contents: dict[str, str],
        extractions: dict[str, ExtractionResult] | None = None,
        top_k: int = 8,
    ) -> tuple[str, list[TracePassage], str | None]:
        if not self.hipporag:
            return "", [], "当前 ALGORITHM_PROVIDER 不是 hipporag，无法执行 RAG 对话。"

        klass = self.hipporag.load_class()
        config_class = self.hipporag.load_config_class()
        if klass is None or config_class is None:
            return "", [], self.hipporag.error or "HippoRAG class is unavailable"
        if not (getenv("DEEPSEEK_API_KEY") or getenv("OPENAI_API_KEY")):
            return "", [], "DEEPSEEK_API_KEY is not set, so HippoRAG RAG QA cannot call the LLM"

        docs, doc_evidence = self._build_hipporag_docs(evidence, raw_contents, extractions or {}, include_structured=True)
        if not docs:
            return "", [], "no passages available for HippoRAG RAG QA"
        docs = docs[: max(settings.hipporag_max_docs, 1)]
        log_llm_context(
            "hipporag_rag_qa_index_docs",
            question=question,
            passages=_docs_for_context_log(docs, doc_evidence),
            extra={"case_id": case_id, "top_k": top_k, "model": settings.hipporag_llm_name},
        )
        normalized_doc_evidence = {" ".join(doc.split()): doc_evidence.get(doc) for doc in docs}
        titles = {item.evidence_id: item.title for item in evidence}
        guarded_question = (
            "请只使用简体中文回答。请基于当前案件证据回答，不能脱离证据自由发挥；"
            "结论后请说明主要依据和仍需补强之处。最后必须另起一行写：Answer: <中文答案>，"
            "以便系统解析答案。\n"
            f"问题：{question}"
        )

        try:
            save_dir = self._case_hipporag_save_dir(case_id)
            config = config_class(
                llm_name=settings.hipporag_llm_name,
                llm_base_url=settings.hipporag_llm_base_url,
                embedding_model_name=settings.hipporag_embedding_model,
                save_dir=str(save_dir),
                retrieval_top_k=max(top_k, settings.hipporag_retrieval_top_k),
                qa_top_k=max(top_k, settings.hipporag_qa_top_k),
            )
            hipporag = klass(global_config=config)
            hipporag.index(docs)
            solutions_out = _safe_sequence(hipporag.rag_qa([guarded_question])[0])
            solution = solutions_out[0] if solutions_out else None
            if solution is None:
                return "", [], None

            passages: list[TracePassage] = []
            scores = _safe_sequence(getattr(solution, "doc_scores", []))
            docs_out = _safe_sequence(getattr(solution, "docs", []))
            for idx, doc in enumerate(docs_out[:top_k]):
                normalized = " ".join(str(doc).split())
                evidence_id = normalized_doc_evidence.get(normalized)
                score = float(scores[idx]) if idx < len(scores) else 0.0
                passage = _trim_passage_for_query(str(doc), question, settings.hipporag_trace_window_chars)
                passages.append(
                    TracePassage(
                        rank=idx + 1,
                        score=score,
                        passage=passage,
                        evidence_id=evidence_id,
                        evidence_title=titles.get(evidence_id or ""),
                    )
                )
            return str(getattr(solution, "answer", "") or ""), passages, None
        except Exception as exc:  # pragma: no cover - requires external model/API
            return "", [], str(exc)

    def _clues_from_hipporag_qa(self, qa_results: list[dict[str, Any]]) -> list[SuspiciousClue]:
        clues: list[SuspiciousClue] = []
        risk_by_category = {
            "basic_profile": "medium",
            "behavior_reconstruction": "high",
            "subjective_reasoning": "high",
        }
        for item in qa_results:
            answer = str(item.get("answer") or "").strip()
            if not answer:
                continue
            clues.append(
                SuspiciousClue(
                    clue_id=new_id("clue"),
                    title=f"HippoRAG问答：{item.get('title', '案件分析')}",
                    category=str(item.get("category") or "hipporag_qa"),
                    description=answer,
                    risk_level=risk_by_category.get(str(item.get("category")), "medium"),
                    evidence_ids=[str(eid) for eid in item.get("evidence_ids", []) if eid],
                    source_passages=item.get("source_passages", []),
                )
            )
        return clues

    def _run_hipporag(
        self,
        case_id: str,
        evidence: list[EvidenceRecord],
        raw_contents: dict[str, str],
        extractions: dict[str, ExtractionResult],
    ) -> dict[str, Any]:
        assert self.hipporag is not None
        result: dict[str, Any] = {
            "triples": [],
            "entities": [],
            "doc_evidence": {},
            "indexed_docs": 0,
            "retrieve_ready": False,
            "error": None,
        }
        klass = self.hipporag.load_class()
        config_class = self.hipporag.load_config_class()
        if klass is None or config_class is None:
            result["error"] = self.hipporag.error or "HippoRAG class is unavailable"
            return result
        if not (getenv("DEEPSEEK_API_KEY") or getenv("OPENAI_API_KEY")):
            result["error"] = "DEEPSEEK_API_KEY is not set, so HippoRAG OpenIE cannot call the LLM"
            return result

        docs, doc_evidence = self._build_hipporag_docs(evidence, raw_contents, extractions, include_structured=False)
        if not docs:
            result["error"] = "no passages available for HippoRAG indexing"
            return result
        docs = docs[: max(settings.hipporag_max_docs, 1)]
        result["doc_evidence"] = {doc: doc_evidence.get(doc) for doc in docs}
        result["indexed_docs"] = len(docs)
        log_llm_context(
            "hipporag_openie_index_docs",
            question="HippoRAG OpenIE indexing documents",
            passages=_docs_for_context_log(docs, doc_evidence),
            extra={"case_id": case_id, "model": settings.hipporag_llm_name},
        )

        try:
            save_dir = self._case_hipporag_save_dir(case_id)
            config = config_class(
                llm_name=settings.hipporag_llm_name,
                llm_base_url=settings.hipporag_llm_base_url,
                embedding_model_name=settings.hipporag_embedding_model,
                save_dir=str(save_dir),
                retrieval_top_k=settings.hipporag_retrieval_top_k,
                qa_top_k=settings.hipporag_qa_top_k,
            )
            hipporag = klass(global_config=config)
            hipporag.index(docs)
            result.update(self._read_hipporag_openie(hipporag, result["doc_evidence"]))
            if settings.hipporag_enable_qa:
                result["qa"] = self._run_hipporag_case_qa(hipporag, result["doc_evidence"])
            graph = getattr(hipporag, "graph", None)
            if graph is not None:
                result["graph_nodes"] = graph.vcount()
                result["graph_edges"] = graph.ecount()
            result["retrieve_ready"] = True
        except Exception as exc:  # pragma: no cover - requires external model/API
            result["error"] = str(exc)
        return result

    def _build_hipporag_docs(
        self,
        evidence: list[EvidenceRecord],
        raw_contents: dict[str, str],
        extractions: dict[str, ExtractionResult],
        *,
        include_structured: bool,
    ) -> tuple[list[str], dict[str, str]]:
        docs: list[str] = []
        doc_evidence: dict[str, str] = {}
        seen: set[str] = set()

        def add_doc(text: str, evidence_id: str) -> None:
            for chunk in _split_passage_text(str(text or ""), settings.hipporag_passage_max_chars):
                normalized = " ".join(chunk.split())
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                docs.append(normalized)
                doc_evidence[normalized] = evidence_id

        for item in evidence:
            extraction = extractions.get(item.evidence_id)
            if extraction and extraction.passages:
                if extraction.route == "structured" and not include_structured:
                    continue
                for passage in extraction.passages:
                    add_doc(passage.text, passage.evidence_id or item.evidence_id)
            else:
                add_doc(raw_contents.get(item.evidence_id, item.content_preview), item.evidence_id)

        return docs, doc_evidence

    def _case_hipporag_save_dir(self, case_id: str) -> Path:
        root = Path(settings.hipporag_save_dir)
        if not root.is_absolute():
            root = Path(__file__).resolve().parents[3] / root
        path = root / case_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _read_hipporag_openie(self, hipporag: Any, doc_evidence: dict[str, str | None]) -> dict[str, Any]:
        all_openie_info, _ = hipporag.load_existing_openie([])
        triples: list[ExtractedTriple] = []
        entities: set[str] = set()
        for row in all_openie_info:
            passage = " ".join(str(row.get("passage", "")).split())
            evidence_id = doc_evidence.get(passage)
            if not evidence_id:
                continue
            row_entities = [str(entity).strip() for entity in row.get("extracted_entities", []) if str(entity).strip()]
            if _looks_like_prompt_example_leak(passage, row_entities, row.get("extracted_triples", [])):
                continue
            entities.update(entity for entity in row_entities if _entity_grounded_in_passage(entity, passage))
            for item in row.get("extracted_triples", []):
                if not isinstance(item, (list, tuple)) or len(item) < 3:
                    continue
                subject, relation, obj = (str(item[0]).strip(), str(item[1]).strip(), str(item[2]).strip())
                if not subject or not relation or not obj:
                    continue
                if _looks_like_prompt_example_leak(passage, [subject, obj], [item]):
                    continue
                if not (_entity_grounded_in_passage(subject, passage) or _entity_grounded_in_passage(obj, passage)):
                    continue
                triples.append(
                    ExtractedTriple(
                        subject=subject,
                        relation=relation,
                        object=obj,
                        evidence_id=evidence_id,
                        properties={
                            "source_dataset": "hipporag_openie",
                            "graph_eligible": True,
                            "passage": passage[:300],
                        },
                    )
                )
        return {"triples": triples, "entities": sorted(entities)}

    def _run_hipporag_case_qa(self, hipporag: Any, doc_evidence: dict[str, str | None]) -> list[dict[str, Any]]:
        language_guard = (
            "请只使用简体中文回答，不要混用英文、乱码或其他语言；"
            "结论必须标注支持证据与仍需补强之处。最后必须另起一行写：Answer: <中文答案>，以便系统解析答案。"
        )
        questions = [
            {
                "category": "basic_profile",
                "title": "第一层：基础信息聚合",
                "question": f"{language_guard} 基于证据材料，杨周武是谁、在哪里任职、具有什么职权？同时列出与其有关的关键人员关系。",
            },
            {
                "category": "behavior_reconstruction",
                "title": "第二层：行为事实还原",
                "question": f"{language_guard} 基于证据材料，还原杨周武、王静、何晓初、刘力飚等人的关键行为链条，包括资金往来、调解安排、案件处置结果。",
            },
            {
                "category": "subjective_reasoning",
                "title": "第三层：主观方面推理",
                "question": f"{language_guard} 基于证据材料，分析杨周武是否可能明知、是否存在徇私动机、是否故意使相关人员逃避刑事追究。请指出支持和仍需补强的证据。",
            },
        ]
        solutions, _, _ = hipporag.rag_qa([item["question"] for item in questions])
        answers: list[dict[str, Any]] = []
        for item, solution in zip(questions, solutions):
            docs = _safe_sequence(getattr(solution, "docs", []))[: settings.hipporag_qa_top_k]
            scores = _safe_sequence(getattr(solution, "doc_scores", []))
            source_passages = []
            evidence_ids: set[str] = set()
            for idx, doc in enumerate(docs):
                normalized = " ".join(str(doc).split())
                evidence_id = doc_evidence.get(normalized)
                if evidence_id:
                    evidence_ids.add(evidence_id)
                source_passages.append(
                    {
                        "rank": idx + 1,
                        "score": float(scores[idx]) if idx < len(scores) else 0.0,
                        "passage": str(doc),
                        "evidence_id": evidence_id,
                    }
                )
            log_llm_context(
                "hipporag_case_qa_bound_sources",
                question=item["question"],
                passages=source_passages,
                extra={"category": item["category"], "title": item["title"], "answer_chars": len(solution.answer or "")},
            )
            answers.append(
                {
                    "category": item["category"],
                    "title": item["title"],
                    "question": item["question"],
                    "answer": solution.answer or "",
                    "docs": [str(doc) for doc in docs],
                    "evidence_ids": sorted(evidence_ids),
                    "source_passages": source_passages,
                }
            )
        return answers

    def _merge_hipporag_extractions(
        self,
        extractions: dict[str, ExtractionResult],
        hippo_result: dict[str, Any],
    ) -> dict[str, ExtractionResult]:
        merged = dict(extractions)
        for triple in hippo_result["triples"]:
            evidence_id = triple.evidence_id or "hipporag"
            existing = merged.get(evidence_id)
            if existing is None:
                merged[evidence_id] = ExtractionResult(route="hipporag_openie", triples=[triple], passages=[], metadata={})
            else:
                merged[evidence_id] = existing.model_copy(update={"triples": [*existing.triples, triple]})
        return merged

    def _build_aggregated_graph(
        self,
        case_id: str,
        evidence: list[EvidenceRecord],
        raw_contents: dict[str, str],
        extractions: dict[str, ExtractionResult],
    ) -> InvestigationGraph:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        clues: list[SuspiciousClue] = []
        node_ids: set[str] = set()
        grouped: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "amount_total": 0.0, "times": set(), "evidence_ids": set()}
        )

        def add_node(node_id: str, label: str, node_type: str, evidence_id: str, properties: dict[str, Any] | None = None) -> None:
            if node_id in node_ids:
                return
            node_ids.add(node_id)
            nodes.append(
                GraphNode(
                    node_id=node_id,
                    label=label,
                    type=node_type,
                    properties={key: value for key, value in (properties or {}).items() if value not in (None, "")},
                    evidence_ids=[evidence_id],
                )
            )

        for item in evidence:
            content = raw_contents.get(item.evidence_id, item.content_preview)
            add_node(
                f"doc:{item.evidence_id}",
                item.title,
                "evidence",
                item.evidence_id,
                {"source_type": item.source_type, "preview": item.content_preview},
            )
            extraction = extractions.get(item.evidence_id)
            if extraction:
                for triple in extraction.triples:
                    self._collect_triple(grouped, triple, item.evidence_id)

        for (subject, relation, obj), data in grouped.items():
            subject_id = f"entity:{subject}"
            object_id = f"entity:{obj}"
            evidence_ids = sorted(data["evidence_ids"])
            primary_evidence_id = evidence_ids[0] if evidence_ids else ""
            add_node(subject_id, subject, "entity", primary_evidence_id)
            add_node(object_id, obj, _node_type_for(relation), primary_evidence_id)
            count = int(data["count"])
            amount_total = float(data["amount_total"])
            times = sorted(data["times"])
            edges.append(
                GraphEdge(
                    edge_id=new_id("edge"),
                    source_id=subject_id,
                    target_id=object_id,
                    relation=relation,
                    confidence=0.82 if count > 1 else 0.72,
                    properties={
                        "count": count,
                        "amount_total": round(amount_total, 2) if amount_total else None,
                        "time_sample": "；".join(times[:3]) if times else None,
                    },
                    evidence_ids=evidence_ids,
                )
            )

        clues.extend(self._clues_from_graph(edges, evidence, raw_contents))
        return InvestigationGraph(case_id=case_id, nodes=nodes, edges=edges, clues=clues)

    def _collect_triple(
        self,
        grouped: dict[tuple[str, str, str], dict[str, Any]],
        triple: ExtractedTriple,
        evidence_id: str,
    ) -> None:
        if triple.properties.get("graph_eligible") is False:
            return
        if triple.relation in {"交易金额", "发生时间"}:
            return
        key = (triple.subject, triple.relation, triple.object)
        item = grouped[key]
        item["count"] += 1
        item["evidence_ids"].add(evidence_id)
        amount = _to_float(triple.properties.get("amount"))
        if amount:
            item["amount_total"] += amount
        if triple.properties.get("time"):
            item["times"].add(str(triple.properties["time"]))

    def _clues_from_graph(
        self,
        edges: list[GraphEdge],
        evidence: list[EvidenceRecord],
        raw_contents: dict[str, str],
    ) -> list[SuspiciousClue]:
        clues: list[SuspiciousClue] = []
        evidence_ids = [item.evidence_id for item in evidence]
        titles = "；".join(item.title for item in evidence)
        corpus = "\n".join(raw_contents.get(item.evidence_id, item.content_preview) for item in evidence)

        fund_edges = [edge for edge in edges if edge.properties.get("amount_total") or _contains_any(edge.relation, ("转账", "资金", "交易", "收款", "付款", "赔偿"))]
        fund_total = sum(_to_float(edge.properties.get("amount_total")) for edge in fund_edges)
        if fund_edges:
            clues.append(
                SuspiciousClue(
                    clue_id=new_id("clue"),
                    title="资金链条需要重点核验",
                    category="fund_flow",
                    description=(
                        f"已从结构化流水中聚合出 {len(fund_edges)} 条资金相关关系"
                        f"{f'，涉及金额约 {fund_total:.2f} 元' if fund_total else ''}。"
                        "应优先核查行贿款、现金取存、赔偿款是否与请托和调解节点前后呼应。"
                    ),
                    risk_level="high" if fund_total >= 100000 else "medium",
                    evidence_ids=_edge_evidence_ids(fund_edges) or evidence_ids,
                )
            )

        duty_hits = [word for word in ("立案", "拘留", "释放", "调解", "撤销", "履职", "报告", "决定") if word in corpus or word in titles]
        if duty_hits:
            clues.append(
                SuspiciousClue(
                    clue_id=new_id("clue"),
                    title="职务处置链条已形成",
                    category="duty_behavior",
                    description=(
                        f"证据中出现 {', '.join(duty_hits[:6])} 等执法处置节点。"
                        "分析重点不应停留在是否办过案，而应核查处置方向是否受到请托、收钱、调解结果影响。"
                    ),
                    risk_level="high",
                    evidence_ids=_evidence_ids_by_keywords(evidence, raw_contents, duty_hits) or evidence_ids,
                )
            )

        subjective_hits = [word for word in ("明知", "故意", "徇私", "隐瞒", "请托", "好处", "短信", "宴请", "安排") if word in corpus or word in titles]
        if subjective_hits:
            clues.append(
                SuspiciousClue(
                    clue_id=new_id("clue"),
                    title="主观明知与徇私动机存在证明入口",
                    category="subjective_state",
                    description=(
                        f"材料中出现 {', '.join(subjective_hits[:6])} 等主观状态或请托利益词。"
                        "下一步应把短信、询问笔录、证人证言、资金流时间点放在同一时间轴上，判断是否能推出明知和徇私动机。"
                    ),
                    risk_level="high",
                    evidence_ids=_evidence_ids_by_keywords(evidence, raw_contents, subjective_hits) or evidence_ids,
                )
            )

        if "现金" in corpus or "ATM" in corpus or "柜台" in corpus:
            clues.append(
                SuspiciousClue(
                    clue_id=new_id("clue"),
                    title="现金链条需要补强原始凭证",
                    category="evidence_gap",
                    description="材料中出现现金取现、柜台存款或 ATM 线索。现金链证明力依赖取现凭证、存现凭证、监控、证人证言之间的闭合。",
                    risk_level="medium",
                    evidence_ids=_evidence_ids_by_keywords(evidence, raw_contents, ("现金", "ATM", "柜台")),
                )
            )

        return clues or [
            SuspiciousClue(
                clue_id=new_id("clue"),
                title="材料已入库，待形成案件级碰撞",
                category="analysis_pending",
                description="当前证据已经生成图谱，但尚未识别出明确的资金链、职务处置链或主观状态线索。建议补充结构化流水、通话记录或关键笔录。",
                risk_level="low",
                evidence_ids=evidence_ids,
            )
        ]

    def _clues_from_content(self, item: EvidenceRecord, content: str) -> list[SuspiciousClue]:
        clues: list[SuspiciousClue] = []
        if any(keyword in content for keyword in ["转账", "流水", "金额", "交易", "银行", "收款", "付款"]):
            clues.append(
                SuspiciousClue(
                    clue_id=new_id("clue"),
                    title="资金往来线索",
                    category="fund_flow",
                    description=f"证据《{item.title}》包含交易、流水或金额信息，已按主体关系聚合入图。",
                    risk_level="medium",
                    evidence_ids=[item.evidence_id],
                )
            )
        if any(keyword in content for keyword in ["明知", "故意", "徇私", "隐瞒", "释放", "拘留", "立案", "调解"]):
            clues.append(
                SuspiciousClue(
                    clue_id=new_id("clue"),
                    title="职务行为与主观状态线索",
                    category="duty_behavior",
                    description=f"证据《{item.title}》包含可能关联徇私、明知、隐瞒或执法处置的表述。",
                    risk_level="high",
                    evidence_ids=[item.evidence_id],
                )
            )
        return clues


def _node_type_for(relation: str) -> str:
    if any(word in relation for word in ("资金", "交易", "收入", "支出", "转账")):
        return "transaction"
    return "entity"


def _entity_grounded_in_passage(entity: str, passage: str) -> bool:
    normalized_entity = " ".join(str(entity or "").split()).strip("：:，,。.;；、()（）[]【】")
    normalized_passage = " ".join(str(passage or "").split())
    if not normalized_entity or not normalized_passage:
        return False
    if normalized_entity in normalized_passage:
        return True
    # Allow common file/document labels that may be partly normalized by OpenIE.
    if len(normalized_entity) >= 4 and normalized_entity.replace("《", "").replace("》", "") in normalized_passage.replace("《", "").replace("》", ""):
        return True
    return False


def _looks_like_prompt_example_leak(passage: str, entities: list[str], triples: Any) -> bool:
    """HippoRAG's bundled few-shot prompt mentions Radio City; discard it if it appears without source support."""

    prompt_example_terms = {
        "Radio City",
        "PlanetRadiocity.com",
        "Hindi",
        "English",
        "New Media",
        "regional songs",
        "music portal",
        "India",
        "3 July 2001",
        "May 2008",
    }
    haystack = " ".join([*entities, str(triples)])
    if not any(term in haystack for term in prompt_example_terms):
        return False
    return not any(term in passage for term in prompt_example_terms)


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _safe_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        converted = tolist()
        if isinstance(converted, list):
            return converted
        if isinstance(converted, tuple):
            return list(converted)
        return [converted]
    try:
        return list(value)
    except TypeError:
        return [value]


def _split_passage_text(text: str, max_chars: int) -> list[str]:
    normalized = " ".join(str(text or "").replace("\r", "\n").split())
    if not normalized:
        return []
    limit = max(int(max_chars or 180), 60)
    sentence_parts = [part.strip() for part in re.split(r"(?<=[。！？!?；;])\s*|\n+", normalized) if part.strip()]
    if not sentence_parts:
        sentence_parts = [normalized]

    chunks: list[str] = []
    current = ""
    for sentence in sentence_parts:
        if len(sentence) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(sentence[start : start + limit] for start in range(0, len(sentence), limit))
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def _trim_passage_for_query(passage: str, query: str, window_chars: int) -> str:
    normalized = " ".join(str(passage or "").split())
    if not normalized:
        return ""
    limit = max(int(window_chars or 220), 80)
    if len(normalized) <= limit:
        return normalized

    query_terms = [
        term
        for term in re.split(r"[\s，,。；;：:、（）()《》<>【】\[\]\"']+", str(query or ""))
        if len(term) >= 2
    ]
    hit_positions = [normalized.find(term) for term in query_terms if normalized.find(term) >= 0]
    center = min(hit_positions) if hit_positions else 0
    start = max(center - limit // 3, 0)
    end = min(start + limit, len(normalized))
    if end - start < limit:
        start = max(end - limit, 0)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(normalized) else ""
    return f"{prefix}{normalized[start:end]}{suffix}"


def _edge_evidence_ids(edges: list[GraphEdge]) -> list[str]:
    ids: set[str] = set()
    for edge in edges:
        ids.update(edge.evidence_ids)
    return sorted(ids)


def _docs_for_context_log(docs: list[str], doc_evidence: dict[str, str | None]) -> list[dict[str, Any]]:
    return [
        {
            "doc_id": f"doc_{idx + 1}",
            "evidence_id": doc_evidence.get(doc),
            "passage": doc,
        }
        for idx, doc in enumerate(docs)
    ]


def _evidence_ids_by_keywords(
    evidence: list[EvidenceRecord],
    raw_contents: dict[str, str],
    keywords: tuple[str, ...] | list[str],
) -> list[str]:
    ids: list[str] = []
    for item in evidence:
        text = f"{item.title}\n{raw_contents.get(item.evidence_id, item.content_preview)}"
        if any(keyword in text for keyword in keywords):
            ids.append(item.evidence_id)
    return ids


def _to_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return 0.0


def get_algorithm_adapter() -> AlgorithmAdapter:
    return AlgorithmAdapter(provider=settings.algorithm_provider)

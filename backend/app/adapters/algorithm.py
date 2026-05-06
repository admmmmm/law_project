# [2026-05-05 13:25] mimo模型编辑
# 用户输入：错误信息 "HippoRAG analysis failed: No module named 'hipporag'"
# 修改内容：修复hipporag导入路径，将 ackend/app/hipporag 改为 ackend/app 

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
        self.hipporag_src = self.repo_root / "backend" / "app"
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
                    tags=["algorithm"],
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
            typed_entities = {
                str(item.get("text", "")).strip(): item
                for item in row.get("typed_entities", [])
                if isinstance(item, dict) and str(item.get("text", "")).strip()
            }
            typed_triples = {
                _triple_key(item.get("subject"), item.get("relation"), item.get("object")): item
                for item in row.get("typed_triples", [])
                if isinstance(item, dict)
            }
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
                typed = typed_triples.get(_triple_key(subject, relation, obj), {})
                subject_info = typed_entities.get(subject, {})
                object_info = typed_entities.get(obj, {})
                base_props = {
                    "source_dataset": "hipporag_openie",
                    "graph_eligible": True,
                    "passage": passage[:300],
                }
                subject_type = _clean_node_type(typed.get("subject_type") or subject_info.get("type")) or _entity_type_for_label(
                    subject, relation, base_props, "subject"
                )
                object_type = _clean_node_type(typed.get("object_type") or object_info.get("type")) or _entity_type_for_label(
                    obj, relation, base_props, "object"
                )
                relation_category = _clean_relation_category(typed.get("relation_category")) or _relation_category_for(relation, base_props)
                typed_tags = _clean_tags(typed.get("tags")) or _clean_tags(subject_info.get("tags")) + _clean_tags(object_info.get("tags"))
                triples.append(
                    ExtractedTriple(
                        subject=subject,
                        relation=relation,
                        object=obj,
                        evidence_id=evidence_id,
                        properties={
                            **base_props,
                            "subject_type": subject_type,
                            "object_type": object_type,
                            "relation_category": relation_category,
                            "subject_tags": ",".join(_clean_tags(subject_info.get("tags"))),
                            "object_tags": ",".join(_clean_tags(object_info.get("tags"))),
                            "tags": ",".join(_dedupe([*typed_tags, *_tags_for_type(subject_type), *_tags_for_type(object_type), *_tags_for_category(relation_category)])),
                            "llm_typed": bool(typed or subject_info or object_info),
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
        grouped: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(_graph_group)

        def add_node(
            node_id: str,
            label: str,
            node_type: str,
            evidence_id: str,
            properties: dict[str, Any] | None = None,
            timestamp: str | None = None,
            time_range: list[str] | None = None,
        ) -> None:
            if node_id in node_ids:
                for node in nodes:
                    if node.node_id != node_id:
                        continue
                    if evidence_id and evidence_id not in node.evidence_ids:
                        node.evidence_ids.append(evidence_id)
                    if timestamp and not node.timestamp:
                        node.timestamp = timestamp
                    for item in time_range or []:
                        if item and item not in node.time_range:
                            node.time_range.append(item)
                    for tag in _node_tags(node_type, label, properties or {}):
                        if tag not in node.tags:
                            node.tags.append(tag)
                return
            node_ids.add(node_id)
            clean_properties = {key: value for key, value in (properties or {}).items() if value not in (None, "")}
            nodes.append(
                GraphNode(
                    node_id=node_id,
                    label=label,
                    type=node_type,
                    tags=_node_tags(node_type, label, clean_properties),
                    properties=clean_properties,
                    evidence_ids=[evidence_id] if evidence_id else [],
                    timestamp=timestamp,
                    time_range=time_range or ([timestamp] if timestamp else []),
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
                timestamp=extract_timestamp(item.title) or extract_timestamp(content),
            )
            extraction = extractions.get(item.evidence_id)
            if extraction:
                for triple in extraction.triples:
                    self._collect_triple(grouped, triple, item.evidence_id)

        self._add_collapsed_action_edges(grouped)

        for (subject_id, relation, object_id), data in grouped.items():
            evidence_ids = sorted(data["evidence_ids"])
            primary_evidence_id = evidence_ids[0] if evidence_ids else ""
            count = int(data["count"])
            amount_total = float(data["amount_total"])
            times = sorted(data["times"])
            first_time = times[0] if times else None
            add_node(
                subject_id, data["source_label"], data["source_type"], primary_evidence_id,
                {
                    "ontology_type": data["source_type"],
                    "canonical_label": data["source_label"],
                    "tags": ",".join(sorted(data["source_tags"])),
                },
                timestamp=first_time, time_range=times,
            )
            add_node(
                object_id, data["target_label"], data["target_type"], primary_evidence_id,
                {
                    "ontology_type": data["target_type"],
                    "canonical_label": data["target_label"],
                    "tags": ",".join(sorted(data["target_tags"])),
                },
                timestamp=first_time, time_range=times,
            )
            edge_properties = dict(data["properties"])
            edge_properties.update({
                "count": count,
                "amount_total": round(amount_total, 2) if amount_total else None,
                "time_sample": "；".join(times[:3]) if times else None,
                "relation_category": data["relation_category"],
                "raw_relations": " / ".join(sorted(data["raw_relations"])[:6]),
                "ontology_constrained": data["ontology_constrained"],
                "tags": ",".join(sorted(data["edge_tags"])),
            })
            edges.append(
                GraphEdge(
                    edge_id=new_id("edge"),
                    source_id=subject_id,
                    target_id=object_id,
                    relation=relation,
                    tags=_edge_tags(relation, edge_properties, times),
                    confidence=min(0.96, float(data["confidence"]) + (0.04 if count > 1 else 0.0)),
                    properties={key: value for key, value in edge_properties.items() if value not in (None, "")},
                    evidence_ids=evidence_ids,
                    timestamp=first_time,
                    time_range=times,
                )
            )

        clues.extend(_clues_from_ontology_graph(nodes, edges, evidence))
        return InvestigationGraph(case_id=case_id, nodes=nodes, edges=edges, clues=clues)

    def _collect_triple(
        self,
        grouped: dict[tuple[str, str, str], dict[str, Any]],
        triple: ExtractedTriple,
        evidence_id: str,
    ) -> None:
        if triple.properties.get("graph_eligible") is False:
            return
        if triple.relation in {"交易金额", "发生时间", "äº¤æ˜“é‡‘é¢", "å‘ç”Ÿæ—¶é—´"}:
            return
        props = dict(triple.properties or {})
        relation_category = _relation_category_for(triple.relation) if _is_temporal_relation(triple.relation) else (
            _clean_relation_category(props.get("relation_category")) or _relation_category_for(triple.relation, props)
        )
        relation_label = _normalize_relation_label(triple.relation, relation_category)
        source_type = _clean_node_type(props.get("subject_type")) or _entity_type_for_label(triple.subject, triple.relation, props, "subject")
        target_type = _clean_node_type(props.get("object_type")) or _entity_type_for_label(triple.object, triple.relation, props, "object")
        if props.get("is_bank_flow") or props.get("amount") or props.get("source_dataset") in {"case_relevant_bank_flows.xlsx", "cleaned_bank_flows.csv", "cleaned_bank_flows.xlsx"}:
            source_type = _bank_flow_endpoint_type(triple.subject, props, "subject")
            target_type = _bank_flow_endpoint_type(triple.object, props, "object")
        if props.get("is_call_record"):
            source_type = "person"
            target_type = "person"
            relation_category = "communication"
        source_label = _canonical_label(triple.subject, source_type, props, "subject")
        target_label = _canonical_label(triple.object, target_type, props, "object")
        timestamp = (
            extract_timestamp(props.get("time"))
            or extract_timestamp(props.get("mapped_case_time"))
            or extract_timestamp(props.get("original_time"))
            or extract_timestamp(triple.subject)
            or extract_timestamp(triple.object)
        )
        if source_type == "time" or target_type == "time":
            return
        source_id = f"{source_type}:{_stable_key(source_label)}"
        target_id = f"{target_type}:{_stable_key(target_label)}"
        source_tags = _dedupe([*_clean_tags(props.get("subject_tags")), *_tags_for_type(source_type)])
        target_tags = _dedupe([*_clean_tags(props.get("object_tags")), *_tags_for_type(target_type)])
        edge_tags = _dedupe([*_clean_tags(props.get("tags")), *_tags_for_category(relation_category)])
        props.update(
            {
                "relation_category": relation_category,
                "subject_type": source_type,
                "object_type": target_type,
                "source_label": source_label,
                "target_label": target_label,
                "timestamp": timestamp,
                "llm_typed": bool(props.get("llm_typed")),
            }
        )
        key = (source_id, relation_label, target_id)
        item = grouped[key]
        item["count"] += 1
        item["evidence_ids"].add(evidence_id)
        item["source_label"] = source_label
        item["target_label"] = target_label
        item["source_type"] = source_type
        item["target_type"] = target_type
        item["relation"] = relation_label
        item["relation_category"] = relation_category
        item["raw_relations"].add(str(triple.relation))
        item["ontology_constrained"] = False
        item["confidence"] = max(float(item["confidence"]), _relation_confidence(relation_category, bool(props.get("llm_typed"))))
        item["source_tags"].update(source_tags)
        item["target_tags"].update(target_tags)
        item["edge_tags"].update(edge_tags)
        item["properties"].update({key: value for key, value in props.items() if value not in (None, "")})
        amount = _to_float(triple.properties.get("amount"))
        if amount:
            item["amount_total"] += amount
        if timestamp:
            item["times"].add(timestamp)
        elif triple.properties.get("time"):
            item["times"].add(str(triple.properties["time"]))

    def _add_collapsed_action_edges(self, grouped: dict[tuple[str, str, str], dict[str, Any]]) -> None:
        """Add direct person-to-person edges for chains shaped as person -> action -> person."""

        incoming: dict[str, list[tuple[tuple[str, str, str], dict[str, Any]]]] = defaultdict(list)
        outgoing: dict[str, list[tuple[tuple[str, str, str], dict[str, Any]]]] = defaultdict(list)
        for key, data in list(grouped.items()):
            source_id, _, target_id = key
            outgoing[source_id].append((key, data))
            incoming[target_id].append((key, data))

        action_types = {"duty_action", "event", "entity"}
        for action_id, left_edges in incoming.items():
            right_edges = outgoing.get(action_id, [])
            if not right_edges:
                continue
            for left_key, left in left_edges:
                if left.get("source_type") != "person" or left.get("target_type") not in action_types:
                    continue
                action_label = str(left.get("target_label") or left.get("relation") or "").strip()
                if not _is_action_bridge_label(action_label, str(left.get("relation") or "")):
                    continue
                for _, right in right_edges:
                    if right.get("target_type") != "person":
                        continue
                    source_id = left_key[0]
                    target_label = str(right.get("target_label") or "").strip()
                    target_id = f"person:{_stable_key(target_label)}"
                    if source_id == target_id:
                        continue
                    relation = action_label or str(left.get("relation") or right.get("relation") or "关联")
                    key = (source_id, relation, target_id)
                    item = grouped[key]
                    item["count"] += max(1, min(int(left.get("count", 1)), int(right.get("count", 1))))
                    item["evidence_ids"].update(left.get("evidence_ids", set()))
                    item["evidence_ids"].update(right.get("evidence_ids", set()))
                    item["source_label"] = str(left.get("source_label") or "")
                    item["target_label"] = target_label
                    item["source_type"] = "person"
                    item["target_type"] = "person"
                    item["relation"] = relation
                    item["relation_category"] = str(left.get("relation_category") or right.get("relation_category") or "duty_behavior")
                    item["raw_relations"].update(left.get("raw_relations", set()))
                    item["raw_relations"].update(right.get("raw_relations", set()))
                    item["raw_relations"].add("collapsed_action_bridge")
                    item["confidence"] = max(float(item["confidence"]), 0.68)
                    item["source_tags"].add("person")
                    item["target_tags"].add("person")
                    item["edge_tags"].update(_tags_for_category(item["relation_category"]))
                    item["properties"].update(
                        {
                            "collapsed_action_bridge": True,
                            "bridge_action_node": action_id,
                            "bridge_action_label": action_label,
                        }
                    )
                    item["times"].update(left.get("times", set()))
                    item["times"].update(right.get("times", set()))
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


_ALLOWED_TAGS = {
    "evidence",
    "person",
    "organization",
    "account",
    "bank_flow",
    "call_record",
    "law_document",
    "duty_behavior",
    "subjective_state",
    "alias_candidate",
    "time_mapped",
    "manual",
    "algorithm",
    "other",
}

_KNOWN_PERSON_NAMES = {
    "\u6768\u5468\u6b66",
    "\u738b\u9759",
    "\u4f55\u6653\u521d",
    "\u5218\u529b\u98da",
    "\u7f57\u8d24\u6d9b",
    "\u6613\u627f\u6842",
    "\u6c5f\u519b",
    "\u6c6a\u6625\u84c9",
    "\u8d75\u5fd7\u9ad8",
    "\u5f20\u590f\u5929",
    "\u9648\u4e09\u4e00",
    "\u7f57\u5b87",
    "\u5f20\u4e09",
    "\u674e\u56db",
    "\u66fe\u9ece",
    "\u9976\u8776",
    "\u5468\u82b7",
}

_PERSON_CONTEXT_WORDS = (
    "\u88ab\u544a\u4eba", "\u72af\u7f6a\u5acc\u7591\u4eba", "\u5acc\u7591\u4eba", "\u8bc1\u4eba", "\u88ab\u5bb3\u4eba", "\u6c11\u8b66", "\u6240\u957f",
    "\u526f\u6240\u957f", "\u7ecf\u8425\u8005", "\u6cd5\u533b", "\u627f\u529e\u4eba", "\u6279\u51c6\u4eba", "\u7533\u8bf7\u4eba",
    "\u59d4\u6258\u4eba", "\u59bb", "\u4e08\u592b", "\u4eb2\u5c5e", "\u5458\u5de5", "\u4eba\u5458",
)

_PERSON_RELATION_WORDS = (
    "\u8bf7\u6258", "\u53d7\u8bf7\u6258", "\u6307\u6d3e", "\u5b89\u6392", "\u627f\u8bfa", "\u6536\u53d7", "\u884c\u8d3f", "\u8d54\u507f",
    "\u8054\u7cfb", "\u901a\u8bdd", "\u77ed\u4fe1", "\u62a5\u544a", "\u6c47\u62a5", "\u4efb\u804c", "\u804c\u52a1",
    "\u4ecb\u5165", "\u8c03\u89e3", "\u91ca\u653e", "\u62d8\u7559", "\u6279\u51c6",
)

_NON_PERSON_TERMS = {
    "登记材料",
    "安全要求",
    "超时经营",
    "消防隐患",
    "人员拥挤",
    "酒后滋事",
    "治安纠纷",
    "拘留",
    "释放",
    "调解",
    "结案",
    "立案",
    "审批",
    "报告",
    "整改",
    "复查",
    "现金柜台",
    "ATM取现",
    "柜台存款",
    "交易流水",
    "刑事案件",
    "故意伤害",
    "徇私枉法",
    "玩忽职守",
}


def extract_timestamp(value: Any) -> str | None:
    text = str(value or "")
    match = re.search(r"((?:19|20)\d{2})\D{0,3}(\d{1,2})?\D{0,3}(\d{1,2})?", text)
    if not match:
        return None
    year = match.group(1)
    month = int(match.group(2) or 1)
    day = int(match.group(3) or 1)
    return f"{year}-{month:02d}-{day:02d}"


def _is_time_label(value: Any) -> bool:
    text = str(value or "").strip()
    if not extract_timestamp(text):
        return False
    if len(text) > 18:
        return False
    return not _contains_any(text, ("行动", "小组", "专案", "专项", "机构", "单位", "俱乐部", "派出所"))


def _triple_key(subject: Any, relation: Any, obj: Any) -> str:
    return "\u241f".join(str(item or "").strip() for item in (subject, relation, obj))


def _dedupe(items: list[Any]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        values.append(text)
    return values


def _clean_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = re.split(r"[,，;；\s]+", value)
    elif isinstance(value, (list, tuple, set)):
        raw_items = [str(item) for item in value]
    else:
        raw_items = [str(value)]
    return [item for item in _dedupe(raw_items) if item in _ALLOWED_TAGS]


def _clean_node_type(value: Any) -> str:
    raw = str(value or "").strip()
    mapping = {
        "person": "person",
        "\u4eba\u7269": "person",
        "\u4eba": "person",
        "\u4eba员": "person",
        "人物": "person",
        "organization": "organization",
        "\u673a\u6784": "organization",
        "\u516c\u53f8": "organization",
        "\u5355\u4f4d": "organization",
        "机构": "organization",
        "机构/公司": "organization",
        "account": "account",
        "\u8d26\u6237": "account",
        "\u8d44\u91d1\u5bf9\u8c61": "account",
        "amount": "money",
        "fund_method": "account",
        "time": "time",
        "location": "location",
        "legal_document": "legal_document",
        "\u6267\u6cd5\u6587\u4e66": "legal_document",
        "\u6cd5\u5f8b\u6587\u4e66": "legal_document",
        "duty_action": "duty_action",
        "\u804c\u52a1\u884c\u4e3a": "duty_action",
        "\u6267\u6cd5\u884c\u4e3a": "duty_action",
        "procedure_action": "duty_action",
        "legal_charge": "legal_charge",
        "event": "event",
        "entity": "entity",
    }
    return mapping.get(raw, "")


def _clean_relation_category(value: Any) -> str:
    category = str(value or "").strip()
    allowed = {
        "fund_flow",
        "communication",
        "duty_identity",
        "duty_behavior",
        "procedure",
        "subjective_state",
        "temporal",
        "case_fact",
        "evidence_link",
        "related",
    }
    return category if category in allowed else ""


def _tags_for_type(entity_type: str) -> list[str]:
    mapping = {
        "evidence": ["evidence"],
        "algorithm_provider": ["algorithm"],
        "person": ["person"],
        "organization": ["organization"],
        "account": ["account", "bank_flow"],
        "money": ["bank_flow"],
        "communication": ["call_record"],
        "legal_document": ["law_document"],
        "case": ["law_document"],
        "duty_action": ["duty_behavior", "law_document"],
        "event": ["duty_behavior"],
        "time": ["time_mapped"],
    }
    return mapping.get(entity_type, [])


def _tags_for_category(category: str) -> list[str]:
    mapping = {
        "fund_flow": ["bank_flow"],
        "communication": ["call_record"],
        "duty_identity": ["duty_behavior", "law_document"],
        "duty_behavior": ["duty_behavior", "law_document"],
        "procedure": ["duty_behavior", "law_document"],
        "subjective_state": ["subjective_state"],
        "temporal": ["time_mapped"],
        "evidence_link": ["evidence"],
    }
    return mapping.get(category, [])


def _relation_category_for(relation: str, properties: dict[str, Any] | None = None) -> str:
    props = properties or {}
    explicit = _clean_relation_category(props.get("relation_category"))
    if explicit:
        return explicit
    label = str(relation or "").strip()

    if props.get("is_call_record"):
        return "communication"
    if props.get("is_bank_flow") or props.get("amount"):
        return "fund_flow"

    if _contains_any(label, ("\u901a\u8bdd", "\u7535\u8bdd", "\u77ed\u4fe1", "\u8054\u7cfb", "\u5fae\u4fe1", "\u62e8\u6253")):
        return "communication"
    if _contains_any(label, ("\u4efb\u804c", "\u804c\u52a1", "\u8eab\u4efd", "\u6240\u957f", "\u6c11\u8b66", "\u5de5\u4f5c\u5355\u4f4d", "\u8d1f\u8d23")):
        return "duty_identity"
    if _contains_any(label, ("\u6279\u51c6", "\u5ba1\u6279", "\u7b7e\u6279", "\u51b3\u5b9a", "\u6307\u6d3e", "\u5b89\u6392", "\u4ecb\u5165", "\u7acb\u6848", "\u62d8\u7559", "\u91ca\u653e", "\u8c03\u89e3", "\u64a4\u6848", "\u64a4\u9500", "\u7ed3\u6848", "\u4fa6\u67e5", "\u5904\u7f6e", "\u62a5\u544a", "\u6c47\u62a5")):
        return "procedure"
    if _contains_any(label, ("\u8bf7\u6258", "\u597d\u5904", "\u5f87\u79c1", "\u660e\u77e5", "\u6545\u610f", "\u9690\u7792", "\u89c4\u907f", "\u53d7\u8bf7\u6258", "\u627f\u8bfa", "\u5229\u7528\u804c\u6743")):
        return "subjective_state"
    if _contains_any(label, ("\u8f6c\u8d26", "\u652f\u51fa", "\u6536\u5165", "\u4ed8\u6b3e", "\u6536\u6b3e", "\u652f\u4ed8", "\u6c47\u6b3e", "\u5165\u8d26", "\u91d1\u989d", "\u4ea4\u6613", "\u73b0\u91d1", "\u53d6\u73b0", "\u5b58\u5165", "\u67dc\u53f0", "ATM", "\u8d54\u507f", "\u6536\u53d7", "\u884c\u8d3f")):
        return "fund_flow"
    if _contains_any(label, ("\u53d1\u751f\u65f6\u95f4", "\u65f6\u95f4", "\u65e5\u671f", "precedes", "follows")):
        return "temporal"
    return "related"


def _is_temporal_relation(relation: str) -> bool:
    return str(relation or "").strip() in {"发生时间", "时间", "日期", "起始时间", "结束时间", "å‘ç”Ÿæ—¶é—´"}


def _bank_flow_endpoint_type(label: str, properties: dict[str, Any], role: str) -> str:
    text = str(label or "").strip()
    if _contains_any(text, ("现金", "柜台", "ATM", "银行", "账户", "账号", "银行卡", "微信", "支付宝")):
        return "account"
    flag = properties.get("is_case_person") if role == "subject" else properties.get("is_core_counterparty")
    if _truthy_value(flag):
        return "person"
    return "account"


def _truthy_value(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y", "是", "核心"}



def _is_action_bridge_label(label: str, relation: str = "") -> bool:
    text = f"{label} {relation}"
    return _contains_any(
        text,
        (
            "\u6307\u6d3e", "\u5b89\u6392", "\u4ecb\u5165", "\u8c03\u89e3", "\u91ca\u653e", "\u62d8\u7559", "\u6279\u51c6", "\u8bf7\u6258",
            "\u627f\u8bfa", "\u6536\u53d7", "\u5229\u7528\u804c\u6743", "\u660e\u77e5", "\u8054\u7cfb", "\u901a\u8bdd", "\u77ed\u4fe1", "\u62a5\u544a", "\u6c47\u62a5",
        ),
    )


def _normalize_relation_label(relation: str, category: str) -> str:
    label = str(relation or "").strip() or "关联"
    if label == "出":
        return "转账/支出"
    if label == "入":
        return "转账/收入"
    if _contains_any(label, ("现金柜台", "柜台存款", "ATM取现", "取现", "存入")):
        return "现金流转"
    if category == "related" and label in {"提及", "相关", "关联", "涉及"}:
        return "关联"
    return label


def _relation_confidence(category: str, llm_typed: bool) -> float:
    if llm_typed and category != "related":
        return 0.76
    if category != "related":
        return 0.64
    return 0.42



def _looks_like_case_person(label: str, relation: str = "", properties: dict[str, Any] | None = None) -> bool:
    text = str(label or "").strip()
    if text in _KNOWN_PERSON_NAMES:
        return True
    if re.fullmatch(r"[\u4e00-\u9fa5]{1,3}(?:\u6240\u957f|\u526f\u6240\u957f|\u6c11\u8b66|\u6cd5\u533b|\u68c0\u5bdf\u5b98|\u8b66\u5b98)", text):
        return True
    if any(name in text for name in _KNOWN_PERSON_NAMES) and re.fullmatch(r"[\u4e00-\u9fa5]{2,8}", text):
        return True
    return False

def _entity_type_for_label(label: str, relation: str = "", properties: dict[str, Any] | None = None, role: str = "") -> str:
    text = str(label or "").strip()
    haystack = f"{text} {relation} {properties or {}}"
    if not text:
        return "entity"
    if _is_time_label(text):
        return "time"
    if re.search(r"\d+(?:\.\d+)?\s*(?:元|万元|人民币)", text):
        return "money"
    if _contains_any(text, ("\u8bc1\u636e", ".md", ".csv", ".xlsx", "\u7b14\u5f55", "\u901a\u77e5\u4e66", "\u51b3\u5b9a\u4e66", "\u62a5\u544a\u4e66", "\u9274\u5b9a\u4e66", "\u767b\u8bb0\u8868", "\u8bb8\u53ef\u8bc1", "\u8425\u4e1a\u6267\u7167")):
        return "legal_document"
    if _contains_any(haystack, ("账户", "银行卡", "微信", "支付宝", "现金", "柜台", "ATM", "取现", "存入", "银行流水", "交易流水", "账号", "手机号")):
        return "account"
    if _contains_any(text, ("民警", "法医", "检察官", "警官", "办案人员", "承办人")) and not _contains_any(text, ("公安局", "派出所", "检察院", "法院", "医院", "政府", "公司")):
        return "person"
    if _contains_any(text, ("公安局", "派出所", "检察院", "法院", "医院", "政府", "俱乐部", "公司", "委员会", "消防", "公安", "民警")):
        return "organization"
    if _contains_any(text, ("徇私枉法", "玩忽职守", "故意伤害", "受贿", "行贿")):
        return "legal_charge"
    if _contains_any(text, ("立案", "拘留", "释放", "调解", "结案", "撤案", "整改", "审批", "批准", "指派", "安排", "侦查", "处置")):
        return "duty_action"
    if _contains_any(text, ("火灾", "事故", "纠纷", "斗殴", "伤害", "案件", "隐患", "经营")):
        return "event"
    if _looks_like_case_person(text, relation, properties):
        return "person"
    return "entity"


def _canonical_label(label: str, entity_type: str, properties: dict[str, Any] | None = None, role: str = "") -> str:
    return re.sub(r"\s+", " ", str(label or "").strip())


def _stable_key(value: str) -> str:
    text = _canonical_label(value, "entity")
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fa5_.-]+", "_", text).strip("_")[:80] or "unknown"


def _graph_group() -> dict[str, Any]:
    return {
        "count": 0,
        "amount_total": 0.0,
        "times": set(),
        "evidence_ids": set(),
        "source_label": "",
        "target_label": "",
        "source_type": "entity",
        "target_type": "entity",
        "relation": "关联",
        "relation_category": "related",
        "raw_relations": set(),
        "ontology_constrained": False,
        "confidence": 0.42,
        "source_tags": set(),
        "target_tags": set(),
        "edge_tags": set(),
        "properties": {},
    }


def _node_tags(node_type: str, label: str, properties: dict[str, Any] | None = None) -> list[str]:
    props = properties or {}
    ontology_type = str(props.get("ontology_type") or node_type or "entity")
    text = f"{label} {node_type} {ontology_type} {props}"
    tags: set[str] = set(_clean_tags(props.get("tags")))
    type_map = {
        "evidence": "evidence",
        "algorithm_provider": "algorithm",
        "person": "person",
        "organization": "organization",
        "account": "account",
        "money": "account",
        "communication": "call_record",
        "legal_document": "law_document",
        "case": "law_document",
        "duty_action": "duty_behavior",
        "event": "duty_behavior",
    }
    if ontology_type in type_map:
        tags.add(type_map[ontology_type])
    if node_type in type_map:
        tags.add(type_map[node_type])
    if "time" in props or "date" in props or "timestamp" in props:
        tags.add("time_mapped")
    if _contains_any(text, ("账户", "银行卡", "微信", "支付宝", "现金", "交易", "流水", "bank", "account")):
        tags.update({"account", "bank_flow"})
    if _contains_any(text, ("电话", "通话", "短信", "微信聊天", "call", "sms")):
        tags.add("call_record")
    if _contains_any(text, ("立案", "拘留", "释放", "撤销", "调解", "报告", "笔录", "鉴定", "文书", "决定", "通知")):
        tags.add("law_document")
    if _contains_any(text, ("别名", "假名", "马甲", "曾用", "控制账户", "代持")):
        tags.add("alias_candidate")
    if props.get("manual") or node_type == "manual":
        tags.add("manual")
    if not tags:
        tags.add("other")
    return sorted(tags)


def _edge_tags(relation: str, properties: dict[str, Any] | None = None, times: list[str] | set[str] | None = None) -> list[str]:
    props = properties or {}
    category = _clean_relation_category(props.get("relation_category")) or _relation_category_for(relation, props)
    text = f"{relation} {category} {props}"
    tags: set[str] = set(_clean_tags(props.get("tags")))
    category_map = {
        "fund_flow": {"bank_flow"},
        "communication": {"call_record"},
        "duty_behavior": {"duty_behavior", "law_document"},
        "procedure": {"duty_behavior", "law_document"},
        "subjective_state": {"subjective_state"},
        "temporal": {"time_mapped"},
        "evidence_link": {"evidence"},
    }
    tags.update(category_map.get(category, set()))
    if _contains_any(text, ("账户", "别名", "假名", "马甲", "控制", "代持", "同一")):
        tags.add("alias_candidate")
    if category != "communication" and _contains_any(text, ("资金", "交易", "转账", "收款", "付款", "金额", "现金", "ATM", "取现", "存入", "流水", "bank", "flow")):
        tags.add("bank_flow")
    if category != "fund_flow" and _contains_any(text, ("电话", "通话", "短信", "联系", "微信")):
        tags.add("call_record")
    if _contains_any(text, ("明知", "故意", "徇私", "隐瞒", "放任", "授意", "串通", "请托", "动机")):
        tags.add("subjective_state")
    if times or props.get("time_sample") or props.get("time"):
        tags.add("time_mapped")
    if props.get("manual"):
        tags.add("manual")
    if not tags:
        tags.add("other")
    return sorted(tags)


def enrich_graph_tags(graph: InvestigationGraph) -> InvestigationGraph:
    for node in graph.nodes:
        merged = set(node.tags or [])
        merged.update(_node_tags(node.type, node.label, node.properties or {}))
        if node.manually_verified:
            merged.add("manual")
        node.tags = sorted(merged)

    for edge in graph.edges:
        merged = set(edge.tags or [])
        merged.update(_edge_tags(edge.relation, edge.properties or {}, edge.time_range or []))
        if edge.manually_verified:
            merged.add("manual")
        edge.tags = sorted(merged)

    return graph


def _clues_from_ontology_graph(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    evidence: list[EvidenceRecord],
) -> list[SuspiciousClue]:
    evidence_ids = [item.evidence_id for item in evidence]
    typed_edges: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in edges:
        typed_edges[str(edge.properties.get("relation_category") or "related")].append(edge)

    clues: list[SuspiciousClue] = []
    fund_edges = typed_edges.get("fund_flow", [])
    duty_edges = typed_edges.get("duty_behavior", []) + typed_edges.get("procedure", [])
    subjective_edges = typed_edges.get("subjective_state", [])
    communication_edges = typed_edges.get("communication", [])
    temporal_edges = [edge for edge in edges if edge.timestamp or edge.time_range]

    if fund_edges and duty_edges:
        shared = _shared_endpoint_edges(fund_edges, duty_edges)
        clues.append(
            SuspiciousClue(
                clue_id=new_id("clue"),
                title="资金链与职务处置存在交叉",
                category="graph_path",
                description=(
                    f"图谱中存在 {len(fund_edges)} 条资金关系、{len(duty_edges)} 条职务/程序关系。"
                    f"其中 {len(shared)} 组关系共享主体或共同证据，建议按时间轴核查请托、收钱、调解/释放是否闭合。"
                ),
                risk_level="high" if shared else "medium",
                evidence_ids=_edge_evidence_ids(shared or fund_edges[:8] + duty_edges[:8]) or evidence_ids,
            )
        )

    if subjective_edges and duty_edges:
        shared = _shared_endpoint_edges(subjective_edges, duty_edges)
        clues.append(
            SuspiciousClue(
                clue_id=new_id("clue"),
                title="主观状态线索与处置行为相连",
                category="graph_path",
                description=(
                    f"图谱中主观状态关系 {len(subjective_edges)} 条，职务/程序关系 {len(duty_edges)} 条。"
                    "这些关系来自 ontology 归类后的关系集合，应优先查看共享主体、共同证据和前后时间。"
                ),
                risk_level="high",
                evidence_ids=_edge_evidence_ids(shared or subjective_edges[:8] + duty_edges[:8]) or evidence_ids,
            )
        )

    if communication_edges and (fund_edges or duty_edges):
        bridge = _shared_endpoint_edges(communication_edges, fund_edges + duty_edges)
        clues.append(
            SuspiciousClue(
                clue_id=new_id("clue"),
                title="通讯记录可能连接资金或处置节点",
                category="communication_bridge",
                description=(
                    f"图谱中通讯关系 {len(communication_edges)} 条，与资金/处置关系形成 {len(bridge)} 个共享端点或共同证据候选。"
                    "这类线索适合用于还原请托、协调和反侦察式规避留痕。"
                ),
                risk_level="medium" if bridge else "low",
                evidence_ids=_edge_evidence_ids(bridge or communication_edges[:8]) or evidence_ids,
            )
        )

    unconstrained_edges = [edge for edge in edges if edge.properties.get("ontology_constrained") is False]
    if unconstrained_edges:
        clues.append(
            SuspiciousClue(
                clue_id=new_id("clue"),
                title="存在未被 ontology 约束的开放关系",
                category="ontology_gap",
                description=(
                    f"有 {len(unconstrained_edges)} 条关系被降级为‘关联’。这通常意味着 OpenIE 输出不符合当前案件本体，"
                    "需要人工补充关系类型、别名规则或罪名模板。"
                ),
                risk_level="low",
                evidence_ids=_edge_evidence_ids(unconstrained_edges[:12]) or evidence_ids,
            )
        )

    if temporal_edges:
        clues.append(
            SuspiciousClue(
                clue_id=new_id("clue"),
                title="图谱关系已挂载时间戳",
                category="timeline",
                description=f"当前有 {len(temporal_edges)} 条关系携带 timestamp/time_range，可用于证据生长、先后顺序和因果链核查。",
                risk_level="medium",
                evidence_ids=_edge_evidence_ids(temporal_edges[:12]) or evidence_ids,
            )
        )

    if clues:
        return clues
    return [
        SuspiciousClue(
            clue_id=new_id("clue"),
            title="图谱分析等待更多结构化关系",
            category="analysis_pending",
            description="当前证据已按 ontology 入图，但尚未形成资金、职务、主观、通讯之间的交叉路径。",
            risk_level="low",
            evidence_ids=evidence_ids,
        )
    ]


def _shared_endpoint_edges(left: list[GraphEdge], right: list[GraphEdge]) -> list[GraphEdge]:
    related: list[GraphEdge] = []
    for first in left:
        first_nodes = {first.source_id, first.target_id}
        first_evidence = set(first.evidence_ids)
        for second in right:
            if first_nodes.intersection({second.source_id, second.target_id}) or first_evidence.intersection(second.evidence_ids):
                related.extend([first, second])
    unique: dict[str, GraphEdge] = {}
    for edge in related:
        unique[edge.edge_id] = edge
    return list(unique.values())


def _node_type_for(relation: str) -> str:
    return _relation_category_for(relation)


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



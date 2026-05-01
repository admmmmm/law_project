from __future__ import annotations

import sys
from collections import defaultdict
from os import getenv
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.schemas.common import new_id
from app.schemas.graph import GraphEdge, GraphNode, InvestigationGraph, SuspiciousClue
from app.schemas.ingestion import EvidenceRecord, ExtractionResult, ExtractedTriple


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
        return graph

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

        docs, doc_evidence = self._build_hipporag_docs(evidence, raw_contents, extractions)
        if not docs:
            result["error"] = "no passages available for HippoRAG indexing"
            return result
        docs = docs[: max(settings.hipporag_max_docs, 1)]
        result["doc_evidence"] = {doc: doc_evidence.get(doc) for doc in docs}
        result["indexed_docs"] = len(docs)

        try:
            save_dir = self._case_hipporag_save_dir(case_id)
            config = config_class(
                llm_name=settings.hipporag_llm_name,
                llm_base_url=settings.hipporag_llm_base_url,
                embedding_model_name=settings.hipporag_embedding_model,
                save_dir=str(save_dir),
                retrieval_top_k=settings.hipporag_retrieval_top_k,
            )
            hipporag = klass(global_config=config)
            hipporag.index(docs)
            result.update(self._read_hipporag_openie(hipporag, result["doc_evidence"]))
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
    ) -> tuple[list[str], dict[str, str]]:
        docs: list[str] = []
        doc_evidence: dict[str, str] = {}
        seen: set[str] = set()

        def add_doc(text: str, evidence_id: str) -> None:
            normalized = " ".join(str(text or "").split())
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            docs.append(normalized)
            doc_evidence[normalized] = evidence_id

        for item in evidence:
            extraction = extractions.get(item.evidence_id)
            if extraction and extraction.passages:
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
            entities.update(str(entity) for entity in row.get("extracted_entities", []) if entity)
            for item in row.get("extracted_triples", []):
                if not isinstance(item, (list, tuple)) or len(item) < 3:
                    continue
                subject, relation, obj = (str(item[0]).strip(), str(item[1]).strip(), str(item[2]).strip())
                if not subject or not relation or not obj:
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
            clues.extend(self._clues_from_content(item, content))

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


def _to_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return 0.0


def get_algorithm_adapter() -> AlgorithmAdapter:
    return AlgorithmAdapter(provider=settings.algorithm_provider)

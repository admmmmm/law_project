from __future__ import annotations

import sys
from collections import defaultdict
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
        graph = self._build_aggregated_graph(case_id, evidence, raw_contents, extractions or {})
        if self.hipporag:
            graph.nodes.append(
                GraphNode(
                    node_id="algorithm:hipporag",
                    label="HippoRAG",
                    type="algorithm_provider",
                    properties=self.hipporag.status(),
                    manually_verified=True,
                )
            )
        return graph

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

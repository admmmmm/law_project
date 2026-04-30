from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.schemas.common import new_id
from app.schemas.graph import GraphEdge, GraphNode, InvestigationGraph, SuspiciousClue
from app.schemas.ingestion import EvidenceRecord


class HippoRagBridge:
    """Lazy bridge to the vendored HippoRAG code under need/HippoRAG.

    HippoRAG has heavy optional dependencies, so importing it at FastAPI startup would
    make the backend brittle. This bridge only loads the package when the provider is
    explicitly selected.
    """

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
        except Exception as exc:  # pragma: no cover - depends on local heavy deps
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

    def build_graph(self, case_id: str, evidence: list[EvidenceRecord], raw_contents: dict[str, str]) -> InvestigationGraph:
        graph = self._build_stub_graph(case_id, evidence, raw_contents)
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

    def _build_stub_graph(self, case_id: str, evidence: list[EvidenceRecord], raw_contents: dict[str, str]) -> InvestigationGraph:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        clues: list[SuspiciousClue] = []

        for item in evidence:
            content = raw_contents.get(item.evidence_id, item.content_preview)
            doc_node_id = f"doc:{item.evidence_id}"
            nodes.append(
                GraphNode(
                    node_id=doc_node_id,
                    label=item.title,
                    type="evidence",
                    properties={"source_type": item.source_type, "preview": item.content_preview},
                    evidence_ids=[item.evidence_id],
                )
            )

            if any(keyword in content for keyword in ["资金", "转账", "交易", "流水", "好处费", "受贿"]):
                clues.append(
                    SuspiciousClue(
                        clue_id=new_id("clue"),
                        title="疑似资金流动线索",
                        category="fund_flow",
                        description=f"材料《{item.title}》包含资金、交易或受贿相关信息，建议与人物关系和时间线继续碰撞。",
                        risk_level="medium",
                        evidence_ids=[item.evidence_id],
                    )
                )

            if any(keyword in content for keyword in ["徇私", "枉法", "裁判", "执行", "调解", "释放"]):
                clues.append(
                    SuspiciousClue(
                        clue_id=new_id("clue"),
                        title="疑似职务行为异常线索",
                        category="duty_behavior",
                        description=f"材料《{item.title}》出现徇私、枉法、调解或释放相关表述，建议核查职权边界和案件流程。",
                        risk_level="high",
                        evidence_ids=[item.evidence_id],
                    )
                )

        if len(nodes) >= 2:
            for previous, current in zip(nodes, nodes[1:]):
                edges.append(
                    GraphEdge(
                        edge_id=new_id("edge"),
                        source_id=previous.node_id,
                        target_id=current.node_id,
                        relation="same_case_material",
                        confidence=0.6,
                        evidence_ids=list(set(previous.evidence_ids + current.evidence_ids)),
                    )
                )

        return InvestigationGraph(case_id=case_id, nodes=nodes, edges=edges, clues=clues)


def get_algorithm_adapter() -> AlgorithmAdapter:
    return AlgorithmAdapter(provider=settings.algorithm_provider)

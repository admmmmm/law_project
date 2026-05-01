from app.schemas.common import new_id
from app.schemas.graph import GraphEdge, GraphNode, InvestigationGraph, SuspiciousClue
from app.schemas.ingestion import EvidenceRecord


class AlgorithmAdapter:
    """Boundary for HippoRAG/BGE-M3/LLM/graph algorithms.

    The stub keeps the backend runnable while the real algorithm module is being integrated.
    """

    def build_graph(self, case_id: str, evidence: list[EvidenceRecord], raw_contents: dict[str, str]) -> InvestigationGraph:
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

            if any(keyword in content for keyword in ["资金", "转账", "交易", "流水"]):
                clue_id = new_id("clue")
                clues.append(
                    SuspiciousClue(
                        clue_id=clue_id,
                        title="疑似资金流动线索",
                        category="fund_flow",
                        description=f"材料《{item.title}》包含资金或交易相关信息，建议与人员关系、时间线继续碰撞。",
                        risk_level="medium",
                        evidence_ids=[item.evidence_id],
                    )
                )

            if any(keyword in content for keyword in ["徇私", "枉法", "裁判", "执行"]):
                clue_id = new_id("clue")
                clues.append(
                    SuspiciousClue(
                        clue_id=clue_id,
                        title="疑似职务行为异常线索",
                        category="duty_behavior",
                        description=f"材料《{item.title}》出现徇私、枉法、裁判或执行相关表述，建议核查职权边界和案件流程。",
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
    return AlgorithmAdapter()

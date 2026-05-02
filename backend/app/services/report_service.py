from app.core.errors import not_found
from app.schemas.common import new_id, now_utc
from app.schemas.report import PortraitReport, PortraitSection
from app.storage.memory_store import MemoryStore


class ReportService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def generate_portrait(self, case_id: str) -> PortraitReport:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")

            graph = self.store.graphs.get(case_id)
            memories = self.store.memories.get(case_id, [])
            clues = graph.clues if graph else []
            evidence = self.store.evidence.get(case_id, [])

            basic_qa = [clue.description for clue in clues if clue.category == "basic_profile"]
            behavior_qa = [clue.description for clue in clues if clue.category == "behavior_reconstruction"]
            subjective_qa = [clue.description for clue in clues if clue.category == "subjective_reasoning"]
            fund_clues = [clue.description for clue in clues if clue.category == "fund_flow"]
            duty_clues = [clue.description for clue in clues if clue.category == "duty_behavior"]
            subjective_clues = [clue.description for clue in clues if clue.category == "subjective_state"]
            gap_clues = [clue.description for clue in clues if clue.category == "evidence_gap"]
            main_subjects = _top_entity_labels(graph) if graph else []

            sections = [
                PortraitSection(
                    title="基础信息聚合",
                    items=[
                        f"案件：{case.title}",
                        f"证据材料数量：{len(evidence)}",
                        f"当前图谱规模：{len(graph.nodes) if graph else 0} 个节点、{len(graph.edges) if graph else 0} 条关系",
                        f"高频主体/对象：{', '.join(main_subjects) if main_subjects else '待识别'}",
                        *basic_qa,
                    ],
                ),
                PortraitSection(
                    title="行为事实还原",
                    items=[
                        *behavior_qa,
                        *(fund_clues or ["暂无明确资金链条，需要补充或重新导入流水材料。"]),
                        *(duty_clues or ["暂无明确职务处置链条，需要补充立案、拘留、调解、释放等程序材料。"]),
                    ],
                ),
                PortraitSection(
                    title="主观方面推理",
                    items=subjective_clues
                    + subjective_qa
                    or [
                        "暂未形成足够主观状态线索。应重点补强请托、明知、徇私动机、收受利益后处置方向变化等证据。"
                    ],
                ),
                PortraitSection(
                    title="证据缺口与补强方向",
                    items=gap_clues
                    or [
                        "建议围绕资金凭证、通话详单、短信聊天、证人证言、内部审批记录继续补强，避免仅凭材料关键词得出结论。"
                    ],
                ),
                PortraitSection(
                    title="人工确认记忆",
                    items=[record.content for record in memories if record.confirmed] or ["暂无人工确认的新事实。"],
                ),
            ]

            suggestions = [
                "按“主体身份与职权 -> 行为事实 -> 主观明知/徇私动机”的顺序回看证据。",
                "把资金流水、通话记录、短信笔录和程序性文书放到同一时间轴，核查是否存在先请托、后收钱、再调解/释放的闭合链。",
                "当前报告是侦查参考，不替代人工审查、证据合法性判断和法律定性。",
            ]

            return PortraitReport(
                report_id=new_id("rpt"),
                case_id=case_id,
                generated_at=now_utc(),
                title=f"{case.title} 信息画像报告",
                sections=sections,
                suggestions=suggestions,
            )


def _top_entity_labels(graph, limit: int = 8) -> list[str]:
    if not graph:
        return []
    degree: dict[str, int] = {}
    labels = {node.node_id: node.label for node in graph.nodes if node.type != "evidence" and node.type != "algorithm_provider"}
    for edge in graph.edges:
        if edge.source_id in labels:
            degree[edge.source_id] = degree.get(edge.source_id, 0) + 1
        if edge.target_id in labels:
            degree[edge.target_id] = degree.get(edge.target_id, 0) + 1
    return [labels[node_id] for node_id, _ in sorted(degree.items(), key=lambda item: item[1], reverse=True)[:limit]]

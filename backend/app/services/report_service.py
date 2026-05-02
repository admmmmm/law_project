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
            behavior_modes = _behavior_mode_notes(graph)
            defenses = _defense_predictions(graph, clues)

            sections = [
                PortraitSection(
                    title="基础信息聚合",
                    items=[
                        f"**案件**：{case.title}",
                        f"**证据材料数量**：{len(evidence)}",
                        f"**当前图谱规模**：{len(graph.nodes) if graph else 0} 个节点，{len(graph.edges) if graph else 0} 条关系。",
                        f"**高频主体/对象**：{', '.join(main_subjects) if main_subjects else '待识别'}",
                        *(basic_qa or ["暂无模型生成的基础身份画像。"]),
                    ],
                ),
                PortraitSection(
                    title="行为事实还原",
                    items=[
                        *(behavior_qa or ["暂无完整行为链条，需要继续补充证据或重新运行 HippoRAG 分析。"]),
                        *(fund_clues or ["**资金链条**：暂无明确资金链条，需补充或重新导入流水材料。"]),
                        *(duty_clues or ["**职务处置链条**：暂无明确职务处置链条，需补充立案、拘留、调解、释放等程序材料。"]),
                    ],
                ),
                PortraitSection(
                    title="行为方式与反侦察迹象",
                    items=behavior_modes
                    or [
                        "暂未发现足够明确的隐瞒、规避留痕、白手套过桥、现金取存闭环或文书倒签迹象。建议继续交叉核查流水、通话、短信和文书时间。"
                    ],
                ),
                PortraitSection(
                    title="要件拆解与证据归类",
                    items=[
                        _element_line("主体要件", bool(main_subjects), "司法工作人员身份、职务权限、经办范围。"),
                        _element_line("客观行为", bool(duty_clues), "立案、拘留、调解、撤案、释放等处置链条。"),
                        _element_line("主观方面", bool(subjective_clues or subjective_qa), "明知、徇私动机、请托、利益输送。"),
                        _element_line("结果与因果", bool(gap_clues is not None and graph and graph.edges), "错误处置、逃避追诉、被害人权益受损及因果关系。"),
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
                    title="缺口标红与补强方向",
                    items=gap_clues
                    or [
                        "==缺口==：建议围绕资金凭证、通话详单、短信聊天、证人证言、内部审批记录继续补强，避免仅凭关键词得出结论。"
                    ],
                ),
                PortraitSection(
                    title="抗辩预判",
                    items=defenses,
                ),
                PortraitSection(
                    title="人工确认记忆",
                    items=[record.content for record in memories if record.confirmed] or ["暂无人工确认的新事实。"],
                ),
            ]

            suggestions = [
                "按 **主体身份与职权 -> 行为事实 -> 主观明知/徇私动机 -> 结果因果** 的顺序回看证据。",
                "把资金流水、通话记录、短信笔录和程序性文书放到同一时间轴，核查是否存在“先请托、后收钱、再调解/释放”的闭合链。",
                "对别名、假名、马甲账户只输出合并建议和置信度，最终合并必须人工确认。",
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


def _behavior_mode_notes(graph) -> list[str]:
    if not graph:
        return []
    notes: list[str] = []
    text_edges = " ".join(edge.relation + " " + " ".join(str(v) for v in edge.properties.values()) for edge in graph.edges)
    if any(word in text_edges for word in ["现金", "取现", "存入", "ATM"]):
        notes.append("**现金化处理**：图谱中出现取现、存入或现金相关表述，应核查是否用于切断资金流留痕。")
    if any(word in text_edges for word in ["过桥", "代持", "控制", "马甲", "假名", "别名"]):
        notes.append("**白手套/马甲账户**：出现控制、代持、马甲或别名线索，应建立真人合并建议并人工确认。")
    if any(word in text_edges for word in ["删除", "隐瞒", "倒签", "补录", "撤销", "释放"]):
        notes.append("**程序规避或留痕异常**：出现删除、隐瞒、倒签、补录、撤销、释放等词，需核查文书时间和审批链。")
    return notes


def _defense_predictions(graph, clues) -> list[str]:
    items = [
        "**认识错误抗辩**：可能主张只是业务判断或事实认识偏差。应补强其知悉伤情、案件事实、法律后果的证据。",
        "**程序瑕疵抗辩**：可能主张只是程序不规范而非徇私枉法。应证明异常处置与请托、利益输送或特定关系存在关联。",
        "**资金无关抗辩**：可能主张资金是借款、还款、投资或正常往来。应核查备注、资金来源、过桥账户、现金取存闭环与处置节点。",
        "**职责边界抗辩**：可能主张没有决定权或只是执行上级意见。应还原经办、审批、授意、协调、签批链条。",
    ]
    if graph and len(graph.edges) == 0 and not clues:
        items.append("==缺口==：当前图谱关系不足，抗辩预判只能作为模板，不能作为案件结论。")
    return items


def _element_line(title: str, passed: bool, description: str) -> str:
    status = "已有支撑" if passed else "==待补强=="
    return f"**{title}**：{status}。{description}"

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

            sections = [
                PortraitSection(
                    title="基础信息聚合",
                    items=[f"案件：{case.title}", f"证据材料数量：{len(self.store.evidence.get(case_id, []))}"],
                ),
                PortraitSection(
                    title="行为事实还原",
                    items=[clue.description for clue in clues] or ["暂无自动生成线索，建议补充材料后重新分析。"],
                ),
                PortraitSection(
                    title="人工确认记忆",
                    items=[record.content for record in memories if record.confirmed] or ["暂无人工确认的新事实。"],
                ),
            ]

            suggestions = [
                "对高风险线索回看原始材料，核查证据来源、时间线和关联人员。",
                "对资金流动、人员关系、职务行为三类数据继续做交叉比对。",
                "所有结论仅作为侦查参考，不替代人工审查和法律判断。",
            ]

            return PortraitReport(
                report_id=new_id("rpt"),
                case_id=case_id,
                generated_at=now_utc(),
                title=f"{case.title} 信息画像报告",
                sections=sections,
                suggestions=suggestions,
            )

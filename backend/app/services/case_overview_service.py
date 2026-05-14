from __future__ import annotations

from datetime import datetime

from app.core.errors import not_found
from app.schemas.case import CaseOverview, CaseOverviewEvidence, CaseOverviewNextStep, CaseOverviewStats
from app.services.evidence_map_service import EvidenceMapService
from app.services.ingestion_service import IngestionService
from app.storage.memory_store import MemoryStore


class CaseOverviewService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def get_overview(self, case_id: str) -> CaseOverview:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")

        evidence_service = IngestionService(self.store)
        evidence = evidence_service.list_evidence(case_id)
        stats = self._stats(case_id)
        stage = self._stage(case_id, stats)
        recent_evidence = [
            CaseOverviewEvidence(
                evidence_id=item.evidence_id,
                name=item.name or item.title,
                brief=item.brief,
                evidence_type=item.evidence_type,
                proof_item=item.proof_item,
                status=item.status,
                created_at=item.created_at,
                passage_count=item.passage_count,
            )
            for item in sorted(evidence, key=lambda row: row.created_at, reverse=True)[:10]
        ]
        updated_at = self._updated_at(case.created_at, evidence)
        offense = case.legal_basis or case.offense_id or ""
        return CaseOverview(
            case_id=case_id,
            name=case.title,
            case_number="",
            suspects=[],
            offense=offense,
            case_type="司法工作人员职务犯罪" if offense else "",
            stage=stage,
            created_at=case.created_at,
            updated_at=updated_at,
            stats=stats,
            next_step=self._next_step(case_id, stats, stage),
            recent_evidence=recent_evidence,
        )

    def _stats(self, case_id: str) -> CaseOverviewStats:
        with self.store.lock:
            evidence = list(self.store.evidence.get(case_id, []))
            passage_count = sum(len(self.store.extractions.get(item.evidence_id).passages) for item in evidence if self.store.extractions.get(item.evidence_id))
            graph = self.store.graphs.get(case_id)
            analysis_count = len(self.store.analysis_threads.get(case_id, []))
            portrait_count = 1 if case_id in self.store.portrait_facts else 0
            report_count = 1 if case_id in self.store.reports else 0

        try:
            evidence_map = EvidenceMapService(self.store).get_map(case_id)
        except Exception:
            evidence_map = None

        return CaseOverviewStats(
            evidence_count=len(evidence),
            passage_count=passage_count,
            document_graph_node_count=len(evidence_map.documents) if evidence_map else 0,
            document_graph_edge_count=len(evidence_map.document_edges) if evidence_map else 0,
            passage_graph_node_count=len(evidence_map.passages) if evidence_map else 0,
            passage_graph_edge_count=len(evidence_map.passage_edges) if evidence_map else 0,
            raw_graph_node_count=len(graph.nodes) if graph else 0,
            raw_graph_edge_count=len(graph.edges) if graph else 0,
            analysis_count=analysis_count,
            portrait_count=portrait_count,
            report_count=report_count,
        )

    def _stage(self, case_id: str, stats: CaseOverviewStats) -> str:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            status = str(getattr(case, "status", "") or "").lower() if case else ""
        if status in {"archived", "closed", "已归档"} or "archived" in status or "closed" in status:
            return "已归档"
        if stats.evidence_count <= 0:
            return "材料整理中"
        if stats.raw_graph_node_count <= 0 and stats.document_graph_node_count <= 0:
            return "材料整理中"
        if stats.analysis_count > 0 or stats.portrait_count > 0 or stats.report_count > 0:
            return "辅助分析中"
        return "证据地图已生成"

    def _next_step(self, case_id: str, stats: CaseOverviewStats, stage: str) -> CaseOverviewNextStep:
        if stats.evidence_count <= 0:
            return CaseOverviewNextStep(label="导入证据", reason="当前案件尚未导入证据材料。", target=f"/cases/{case_id}/import")
        if stage == "证据地图已生成":
            return CaseOverviewNextStep(label="开始智能分析", reason="当前案件已导入证据并生成证据地图，可以继续进行辅助分析。", target=f"/cases/{case_id}/analysis")
        if stage == "辅助分析中":
            return CaseOverviewNextStep(label="复核画像报告", reason="当前案件已有分析或画像结果，建议进入画像页复核证据支撑。", target=f"/cases/{case_id}/portrait")
        if stage == "已归档":
            return CaseOverviewNextStep(label="查看归档材料", reason="当前案件已归档，可查看证据地图和历史分析结果。", target=f"/cases/{case_id}/graph")
        return CaseOverviewNextStep(label="查看证据地图", reason="当前案件证据仍在整理中，建议先核查证据地图。", target=f"/cases/{case_id}/graph")

    def _updated_at(self, created_at: datetime, evidence: list) -> datetime:
        values = [getattr(item, "updated_at", None) or getattr(item, "created_at", None) for item in evidence]
        values = [item for item in values if item]
        return max(values) if values else created_at

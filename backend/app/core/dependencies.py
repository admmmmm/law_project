from typing import Annotated

from fastapi import Depends

from app.adapters.algorithm import AlgorithmAdapter, get_algorithm_adapter
from app.services.analysis_skill_service import AnalysisSkillService
from app.services.analysis_service import AnalysisService
from app.services.case_service import CaseService
from app.services.case_overview_service import CaseOverviewService
from app.services.document_mother_service import DocumentMotherService
from app.services.evidence_map_service import EvidenceMapService
from app.services.graph_service import GraphService
from app.services.ingestion_service import IngestionService
from app.services.legal_knowledge_service import LegalKnowledgeService
from app.services.memory_service import MemoryService
from app.services.report_service import ReportService
from app.storage.memory_store import MemoryStore, get_store


def get_case_service(store: MemoryStore = Depends(get_store)) -> CaseService:
    return CaseService(store)


def get_case_overview_service(store: MemoryStore = Depends(get_store)) -> CaseOverviewService:
    return CaseOverviewService(store)


def get_ingestion_service(store: MemoryStore = Depends(get_store)) -> IngestionService:
    return IngestionService(store)


def get_graph_service(store: MemoryStore = Depends(get_store)) -> GraphService:
    return GraphService(store)


def get_evidence_map_service(store: MemoryStore = Depends(get_store)) -> EvidenceMapService:
    return EvidenceMapService(store)


def get_document_mother_service(store: MemoryStore = Depends(get_store)) -> DocumentMotherService:
    return DocumentMotherService(store)


def get_analysis_service(
    store: MemoryStore = Depends(get_store),
    algorithm: AlgorithmAdapter = Depends(get_algorithm_adapter),
) -> AnalysisService:
    return AnalysisService(store, algorithm)


def get_analysis_skill_service(store: MemoryStore = Depends(get_store)) -> AnalysisSkillService:
    return AnalysisSkillService(store)


def get_memory_service(store: MemoryStore = Depends(get_store)) -> MemoryService:
    return MemoryService(store)


def get_report_service(store: MemoryStore = Depends(get_store)) -> ReportService:
    return ReportService(store)


def get_legal_knowledge_service() -> LegalKnowledgeService:
    return LegalKnowledgeService()


CaseServiceDep = Annotated[CaseService, Depends(get_case_service)]
CaseOverviewServiceDep = Annotated[CaseOverviewService, Depends(get_case_overview_service)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]
EvidenceMapServiceDep = Annotated[EvidenceMapService, Depends(get_evidence_map_service)]
DocumentMotherServiceDep = Annotated[DocumentMotherService, Depends(get_document_mother_service)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
AnalysisSkillServiceDep = Annotated[AnalysisSkillService, Depends(get_analysis_skill_service)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
LegalKnowledgeServiceDep = Annotated[LegalKnowledgeService, Depends(get_legal_knowledge_service)]

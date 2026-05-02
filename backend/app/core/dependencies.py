from typing import Annotated

from fastapi import Depends

from app.adapters.algorithm import AlgorithmAdapter, get_algorithm_adapter
from app.services.analysis_service import AnalysisService
from app.services.case_service import CaseService
from app.services.graph_service import GraphService
from app.services.ingestion_service import IngestionService
from app.services.legal_knowledge_service import LegalKnowledgeService
from app.services.memory_service import MemoryService
from app.services.report_service import ReportService
from app.storage.memory_store import MemoryStore, get_store


def get_case_service(store: MemoryStore = Depends(get_store)) -> CaseService:
    return CaseService(store)


def get_ingestion_service(store: MemoryStore = Depends(get_store)) -> IngestionService:
    return IngestionService(store)


def get_graph_service(store: MemoryStore = Depends(get_store)) -> GraphService:
    return GraphService(store)


def get_analysis_service(
    store: MemoryStore = Depends(get_store),
    algorithm: AlgorithmAdapter = Depends(get_algorithm_adapter),
) -> AnalysisService:
    return AnalysisService(store, algorithm)


def get_memory_service(store: MemoryStore = Depends(get_store)) -> MemoryService:
    return MemoryService(store)


def get_report_service(store: MemoryStore = Depends(get_store)) -> ReportService:
    return ReportService(store)


def get_legal_knowledge_service() -> LegalKnowledgeService:
    return LegalKnowledgeService()


CaseServiceDep = Annotated[CaseService, Depends(get_case_service)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
GraphServiceDep = Annotated[GraphService, Depends(get_graph_service)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
LegalKnowledgeServiceDep = Annotated[LegalKnowledgeService, Depends(get_legal_knowledge_service)]

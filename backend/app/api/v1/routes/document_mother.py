from fastapi import APIRouter

from app.core.dependencies import DocumentMotherServiceDep
from app.schemas.document_mother import DocumentMotherGraph

router = APIRouter()


@router.get("/{case_id}/document-mother-graph", response_model=DocumentMotherGraph)
def get_document_mother_graph(case_id: str, service: DocumentMotherServiceDep) -> DocumentMotherGraph:
    return service.get_graph(case_id)


@router.post("/{case_id}/document-mother-graph/rebuild", response_model=DocumentMotherGraph)
def rebuild_document_mother_graph(case_id: str, service: DocumentMotherServiceDep) -> DocumentMotherGraph:
    return service.rebuild(case_id)

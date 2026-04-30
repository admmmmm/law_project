from fastapi import APIRouter

from app.core.dependencies import GraphServiceDep
from app.schemas.graph import GraphInterventionRequest, InvestigationGraph

router = APIRouter()


@router.get("/{case_id}/graph", response_model=InvestigationGraph)
def get_graph(case_id: str, service: GraphServiceDep) -> InvestigationGraph:
    return service.get_graph(case_id)


@router.patch("/{case_id}/graph/interventions", response_model=InvestigationGraph)
def apply_intervention(case_id: str, payload: GraphInterventionRequest, service: GraphServiceDep) -> InvestigationGraph:
    return service.apply_intervention(case_id, payload)

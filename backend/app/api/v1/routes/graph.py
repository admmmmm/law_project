from fastapi import APIRouter

from app.core.dependencies import GraphServiceDep
from app.schemas.graph import GraphInterventionRequest, InvestigationGraph, MergedGraphRequest

router = APIRouter()


@router.get("/{case_id}/graph", response_model=InvestigationGraph)
def get_graph(case_id: str, service: GraphServiceDep) -> InvestigationGraph:
    return service.get_graph(case_id)


@router.post("/{case_id}/graph/merged", response_model=InvestigationGraph)
def get_merged_graph(case_id: str, payload: MergedGraphRequest, service: GraphServiceDep) -> InvestigationGraph:
    return service.get_merged_graph(case_id, payload.selected_case_ids)


@router.patch("/{case_id}/graph/interventions", response_model=InvestigationGraph)
def apply_intervention(case_id: str, payload: GraphInterventionRequest, service: GraphServiceDep) -> InvestigationGraph:
    return service.apply_intervention(case_id, payload)

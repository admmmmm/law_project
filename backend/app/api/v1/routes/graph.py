from fastapi import APIRouter

from app.core.dependencies import EvidenceMapServiceDep, GraphServiceDep
from app.schemas.evidence_map import EvidenceMap
from app.schemas.graph import GraphInterventionRequest, InvestigationGraph, MergedGraphRequest, RawGraphActionRequest, RawGraphActionResponse

router = APIRouter()


@router.get("/{case_id}/graph", response_model=InvestigationGraph)
def get_graph(case_id: str, service: GraphServiceDep) -> InvestigationGraph:
    return service.get_graph(case_id)


@router.get("/{case_id}/evidence-map", response_model=EvidenceMap)
def get_evidence_map(case_id: str, service: EvidenceMapServiceDep) -> EvidenceMap:
    return service.get_map(case_id)


@router.post("/{case_id}/evidence-map/rebuild")
def rebuild_evidence_map(case_id: str, service: EvidenceMapServiceDep) -> dict:
    evidence_map = service.get_map(case_id)
    return {
        "status": "ok",
        "message": "证据地图已重建",
        "stats": evidence_map.stats.model_dump(),
    }


@router.post("/{case_id}/graph/merged", response_model=InvestigationGraph)
def get_merged_graph(case_id: str, payload: MergedGraphRequest, service: GraphServiceDep) -> InvestigationGraph:
    return service.get_merged_graph(case_id, payload.selected_case_ids)


@router.patch("/{case_id}/graph/interventions", response_model=InvestigationGraph)
def apply_intervention(case_id: str, payload: GraphInterventionRequest, service: GraphServiceDep) -> InvestigationGraph:
    return service.apply_intervention(case_id, payload)


@router.post("/{case_id}/graph/raw/actions", response_model=RawGraphActionResponse)
def apply_raw_graph_action(case_id: str, payload: RawGraphActionRequest, service: GraphServiceDep) -> RawGraphActionResponse:
    return service.apply_raw_action(case_id, payload)

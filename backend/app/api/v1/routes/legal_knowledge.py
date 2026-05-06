from typing import Any

from fastapi import APIRouter, Query

from app.core.dependencies import LegalKnowledgeServiceDep
from app.schemas.analysis import TraceResult

router = APIRouter()


@router.get("/sources")
def list_sources(service: LegalKnowledgeServiceDep) -> list[dict[str, Any]]:
    return service.list_sources()


@router.get("/template-schema")
def get_template_schema(service: LegalKnowledgeServiceDep) -> dict[str, Any]:
    return service.get_template_schema()


@router.get("/evidence-type-mapping")
def get_evidence_type_mapping(service: LegalKnowledgeServiceDep) -> dict[str, Any]:
    return service.get_evidence_type_mapping()


@router.get("/alias-resolution-rules")
def get_alias_resolution_rules(service: LegalKnowledgeServiceDep) -> dict[str, Any]:
    return service.get_alias_resolution_rules()


@router.get("/offense-templates")
def list_offense_templates(service: LegalKnowledgeServiceDep) -> list[dict[str, Any]]:
    return service.list_offense_templates()


@router.get("/retrieve", response_model=TraceResult)
def retrieve_legal_knowledge(
    service: LegalKnowledgeServiceDep,
    query: str = Query(min_length=1),
    offense_id: str | None = None,
    top_k: int = Query(default=8, ge=1, le=20),
) -> TraceResult:
    return service.retrieve(query=query, offense_id=offense_id or None, top_k=top_k)


@router.get("/offense-templates/{offense_id}")
def get_offense_template(offense_id: str, service: LegalKnowledgeServiceDep) -> dict[str, Any]:
    return service.get_offense_template(offense_id)

from typing import Any

from fastapi import APIRouter

from app.core.dependencies import LegalKnowledgeServiceDep

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


@router.get("/offense-templates/{offense_id}")
def get_offense_template(offense_id: str, service: LegalKnowledgeServiceDep) -> dict[str, Any]:
    return service.get_offense_template(offense_id)

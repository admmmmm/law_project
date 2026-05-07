from typing import Any

from fastapi import APIRouter, File, Form, Query, UploadFile
from pydantic import BaseModel, Field

from app.core.dependencies import LegalKnowledgeServiceDep
from app.schemas.analysis import TraceResult

router = APIRouter()


class ProcedureFlowCreate(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    kind: str = "user_knowledge"


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


@router.get("/procedure-flows")
def list_procedure_flows(service: LegalKnowledgeServiceDep) -> list[dict[str, Any]]:
    return service.list_procedure_flows()


@router.get("/procedure-flows/{knowledge_id}")
def get_procedure_flow(knowledge_id: str, service: LegalKnowledgeServiceDep) -> dict[str, Any]:
    return service.get_procedure_flow(knowledge_id)


@router.post("/procedure-flows")
def create_procedure_flow(payload: ProcedureFlowCreate, service: LegalKnowledgeServiceDep) -> dict[str, Any]:
    return service.create_procedure_flow(title=payload.title, content=payload.content, kind=payload.kind)


@router.post("/procedure-flows/upload")
async def upload_procedure_flow(
    service: LegalKnowledgeServiceDep,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    kind: str = Form(default="user_knowledge"),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    return service.create_procedure_flow(title=title or file.filename or "上传办案知识", content=content, kind=kind)


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

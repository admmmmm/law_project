from fastapi import APIRouter, File, Form, UploadFile

from app.core.dependencies import IngestionServiceDep
from app.schemas.ingestion import BatchIngestionResult, EvidenceDetail, IngestionResult, TextIngestionRequest
from app.schemas.ingestion import EvidenceRecord

router = APIRouter()


@router.post("/{case_id}/ingestions/text", response_model=IngestionResult)
def ingest_text(case_id: str, payload: TextIngestionRequest, service: IngestionServiceDep) -> IngestionResult:
    return service.ingest_text(case_id, payload)


@router.get("/{case_id}/evidence/{evidence_id}", response_model=EvidenceDetail)
def get_evidence_detail(case_id: str, evidence_id: str, service: IngestionServiceDep) -> EvidenceDetail:
    return service.get_evidence_detail(case_id, evidence_id)


@router.get("/{case_id}/evidence", response_model=list[EvidenceRecord])
def list_evidence(case_id: str, service: IngestionServiceDep) -> list[EvidenceRecord]:
    return service.list_evidence(case_id)


@router.post("/{case_id}/ingestions/files", response_model=IngestionResult)
async def ingest_file(
    case_id: str,
    service: IngestionServiceDep,
    file: UploadFile = File(...),
    source_type: str = Form(default="unknown"),
    title: str | None = Form(default=None),
) -> IngestionResult:
    content = await file.read()
    return service.ingest_file(case_id=case_id, filename=title or file.filename or "uploaded-file", content=content, source_type=source_type)


@router.post("/{case_id}/ingestions/batch", response_model=BatchIngestionResult)
async def ingest_batch(
    case_id: str,
    service: IngestionServiceDep,
    files: list[UploadFile] = File(...),
    source_type: str = Form(default="unknown"),
) -> BatchIngestionResult:
    payload: list[tuple[str, bytes]] = []
    for file in files:
        payload.append((file.filename or "uploaded-file", await file.read()))
    return service.ingest_many_files(case_id=case_id, files=payload, source_type=source_type)


@router.post("/{case_id}/ingestions/archive", response_model=BatchIngestionResult)
async def ingest_archive(
    case_id: str,
    service: IngestionServiceDep,
    file: UploadFile = File(...),
) -> BatchIngestionResult:
    return service.ingest_archive(case_id=case_id, filename=file.filename or "archive.zip", content=await file.read())

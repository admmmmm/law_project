from fastapi import APIRouter, File, Form, UploadFile

from app.core.dependencies import IngestionServiceDep
from app.schemas.ingestion import IngestionResult, TextIngestionRequest

router = APIRouter()


@router.post("/{case_id}/ingestions/text", response_model=IngestionResult)
def ingest_text(case_id: str, payload: TextIngestionRequest, service: IngestionServiceDep) -> IngestionResult:
    return service.ingest_text(case_id, payload)


@router.post("/{case_id}/ingestions/files", response_model=IngestionResult)
async def ingest_file(
    case_id: str,
    service: IngestionServiceDep,
    file: UploadFile = File(...),
    source_type: str = Form(default="unknown"),
) -> IngestionResult:
    content = await file.read()
    return service.ingest_file(case_id=case_id, filename=file.filename or "uploaded-file", content=content, source_type=source_type)

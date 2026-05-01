import io
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.ingestion import (
    IngestionTextRequest,
    IngestionTextResponse,
    SourceType,
)
from app.services.case_store import add_evidence
from src.information_extraction.router import route_extraction


router = APIRouter(prefix="/cases/{case_id}/ingestion")
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_UPLOAD_SUFFIXES = {"txt", "text", "csv", "xlsx", "json", "pdf", "doc", "docx"}


def _decode_text_bytes(raw: bytes) -> str:
    """
    优先按 UTF-8 解码，失败后回退到 GB18030。
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("gb18030", errors="ignore")


def _extract_text_for_ingestion(resolved_type: str, raw: bytes) -> str:
    """
    按文件类型提取可用于抽取的文本，避免对二进制文件直接强制 UTF-8 解码。
    """
    if resolved_type in {"text", "txt", "csv", "json"}:
        return _decode_text_bytes(raw)

    if resolved_type == "pdf":
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise ValueError("解析 PDF 需要安装 pypdf。") from exc
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if resolved_type == "docx":
        try:
            from docx import Document
        except Exception as exc:
            raise ValueError("解析 DOCX 需要安装 python-docx。") from exc
        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs).strip()

    if resolved_type == "doc":
        raise ValueError("暂不支持直接解析 .doc，请转换为 .docx、.txt 或 .pdf 后再上传。")

    return _decode_text_bytes(raw)


def _resolve_upload_source_type(source_type: SourceType | None, suffix: str) -> str:
    """
    上传场景的类型判定：
    - 调用方显式指定且不是 unknown 时，优先使用显式值
    - 否则回退到文件后缀
    """
    if source_type and source_type != SourceType.UNKNOWN:
        return source_type.value
    if suffix:
        return suffix
    return SourceType.UNKNOWN.value


def _to_source_type(value: str) -> SourceType:
    return SourceType(value) if value in SourceType._value2member_map_ else SourceType.UNKNOWN


@router.post(
    "/text",
    response_model=IngestionTextResponse,
    summary="提交文本证据并抽取结构化结果",
    responses={422: {"description": "文本为空或类型不支持"}},
)
async def ingest_text(case_id: str, payload: IngestionTextRequest) -> IngestionTextResponse:
    """
    接收纯文本证据并触发抽取。
    """
    try:
        if not payload.content.strip():
            raise ValueError("文本内容不能为空。")
        result = await route_extraction(
            source_type=payload.source_type.value,
            content=payload.content,
            filename=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文本入库失败: {exc}") from exc

    evidence = add_evidence(
        case_id=case_id,
        title=payload.title,
        source_type=payload.source_type,
        extraction=result,
        source_ref="ingestion:text",
        content=payload.content,
    )
    return IngestionTextResponse(case_id=case_id, accepted=True, evidences=[evidence], next_step="run_analysis")


@router.post(
    "/file",
    response_model=IngestionTextResponse,
    summary="上传证据文件并抽取结构化结果",
    description=(
        "支持 txt/text/csv/xlsx/json/pdf/docx/doc。"
        "doc 仅识别类型，建议先转换为 docx 后上传。"
    ),
    responses={
        413: {"description": "文件过大（默认限制 10MB）"},
        422: {"description": "文件为空、类型不支持或文本提取失败"},
    },
)
async def ingest_file(
    case_id: str,
    file: UploadFile = File(...),
    title: str = Form("上传文件"),
    source_type: SourceType | None = Form(default=None),
) -> IngestionTextResponse:
    """
    接收 multipart/form-data 文件并自动分流处理。
    """
    try:
        raw = await file.read()
        if not raw:
            raise ValueError("上传文件为空，无法解析。")
        if len(raw) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="上传文件过大，当前限制为 10MB。")
        suffix = Path(file.filename or "").suffix.lower().lstrip(".")
        if suffix and suffix not in ALLOWED_UPLOAD_SUFFIXES:
            raise ValueError(f"不支持的文件后缀: .{suffix}")
        resolved_type = _resolve_upload_source_type(source_type=source_type, suffix=suffix)
        extraction_type = suffix or resolved_type
        content = _extract_text_for_ingestion(resolved_type=extraction_type, raw=raw)
        if not content.strip():
            raise ValueError("文件中未提取到有效文本内容。")
        result = await route_extraction(
            source_type=resolved_type,
            content=content,
            filename=file.filename,
            raw_bytes=raw,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文件入库失败: {exc}") from exc
    finally:
        await file.close()

    source_ref = file.filename or "ingestion:file"
    evidence = add_evidence(
        case_id=case_id,
        title=title,
        source_type=_to_source_type(resolved_type),
        extraction=result,
        source_ref=source_ref,
        content=content,
    )
    return IngestionTextResponse(case_id=case_id, accepted=True, evidences=[evidence], next_step="run_analysis")

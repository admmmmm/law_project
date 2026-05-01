from pathlib import Path

from app.schemas.ingestion import ExtractionResult
from src.information_extraction.structured.parser import parse_structured_content
from src.information_extraction.structured.passage_builder import build_passages_from_triples
from src.information_extraction.structured.triple_mapper import map_rows_to_triples
from src.information_extraction.unstructured.processor import extract_unstructured_triples


STRUCTURED_TYPES = {"csv", "xlsx", "json"}
UNSTRUCTURED_TYPES = {"doc", "docx", "pdf", "txt", "text"}
STRUCTURED_ALIAS_TO_TYPE = {"流水": "流水"}
UNSTRUCTURED_ALIASES = {"笔录"}


def _resolve_source_type(source_type: str, filename: str | None) -> str:
    st = (source_type or "").strip().lower()
    if st:
        return st
    if filename:
        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix:
            return suffix
    return "unknown"


async def route_extraction(
    source_type: str,
    content: str,
    filename: str | None = None,
    raw_bytes: bytes | None = None,
) -> ExtractionResult:
    """
    分流核心：
    - source_type 或文件后缀为 csv/xlsx/json -> 结构化流程
    - source_type 或文件后缀为 doc/docx/pdf/txt/text -> 非结构化流程
    """
    resolved = _resolve_source_type(source_type=source_type, filename=filename)

    if resolved in STRUCTURED_TYPES or resolved in STRUCTURED_ALIAS_TO_TYPE:
        normalized_type = STRUCTURED_ALIAS_TO_TYPE.get(resolved, resolved)
        rows = parse_structured_content(source_type=normalized_type, content=content, raw_bytes=raw_bytes)
        triples = map_rows_to_triples(rows)
        passages = build_passages_from_triples(triples)
        return ExtractionResult(
            route="structured",
            triples=triples,
            passages=passages,
            metadata={"source_type": resolved, "normalized_type": normalized_type, "rows_count": len(rows)},
        )

    if resolved in UNSTRUCTURED_TYPES or resolved in UNSTRUCTURED_ALIASES:
        triples, passages = await extract_unstructured_triples(content)
        return ExtractionResult(
            route="unstructured",
            triples=triples,
            passages=passages,
            metadata={"source_type": resolved, "chars": len(content)},
        )

    raise ValueError(f"无法识别的数据类型: {resolved}，请指定 source_type 或提供可识别后缀。")

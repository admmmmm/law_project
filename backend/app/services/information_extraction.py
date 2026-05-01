from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from app.schemas.ingestion import ExtractedTriple, ExtractionResult, PassageRecord

STRUCTURED_TYPES = {"csv", "xlsx", "json", "流水", "bank_flow", "transaction"}


def decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def resolve_source_type(source_type: str | None, filename: str | None = None) -> str:
    value = (source_type or "").strip()
    if value and value != "unknown":
        return value
    if filename:
        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix:
            return suffix
    return "unknown"


def extract_content(source_type: str, raw_bytes: bytes | None = None, content: str | None = None) -> str:
    normalized = source_type.lower()
    if raw_bytes is None:
        return content or ""
    if normalized in {"txt", "text", "csv", "json"}:
        return decode_text(raw_bytes)
    if normalized == "xlsx":
        return content or ""
    if normalized == "doc":
        raise ValueError("暂不支持直接解析 .doc，请转成 .docx、.txt、.pdf、.csv 或 .xlsx 后再上传。")
    if normalized == "docx":
        try:
            from docx import Document
        except Exception as exc:
            raise ValueError("解析 DOCX 需要安装 python-docx。") from exc
        doc = Document(io.BytesIO(raw_bytes))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    if normalized == "pdf":
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise ValueError("解析 PDF 需要安装 pypdf。") from exc
        reader = PdfReader(io.BytesIO(raw_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    return decode_text(raw_bytes)


def route_extraction(
    *,
    source_type: str,
    content: str,
    raw_bytes: bytes | None = None,
    filename: str | None = None,
    evidence_id: str | None = None,
) -> ExtractionResult:
    resolved = resolve_source_type(source_type, filename)
    if resolved.lower() in STRUCTURED_TYPES or resolved in STRUCTURED_TYPES:
        rows = parse_structured_content(source_type=resolved, content=content, raw_bytes=raw_bytes)
        triples = map_rows_to_triples(rows, evidence_id=evidence_id)
        return ExtractionResult(
            route="structured",
            triples=triples,
            passages=build_passages_from_triples(triples),
            metadata={"source_type": resolved, "rows_count": len(rows)},
        )
    triples, passages = extract_unstructured_triples(content, evidence_id=evidence_id)
    return ExtractionResult(
        route="unstructured",
        triples=triples,
        passages=passages,
        metadata={"source_type": resolved, "chars": len(content)},
    )


def parse_structured_content(source_type: str, content: str, raw_bytes: bytes | None = None) -> list[dict[str, str]]:
    normalized = source_type.lower()
    if normalized == "json":
        data = json.loads(content)
        if isinstance(data, dict):
            return [{str(k): _cell(v) for k, v in data.items()}]
        if isinstance(data, list):
            return [{str(k): _cell(v) for k, v in row.items()} for row in data if isinstance(row, dict)]
        raise ValueError("JSON 内容必须是对象或对象数组。")
    if normalized == "xlsx":
        if raw_bytes is None:
            raise ValueError("解析 XLSX 需要原始文件字节。")
        try:
            from openpyxl import load_workbook
        except Exception as exc:
            raise ValueError("解析 XLSX 需要安装 openpyxl。") from exc
        workbook = load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
        rows: list[dict[str, str]] = []
        for sheet in workbook.worksheets:
            iterator = sheet.iter_rows(values_only=True)
            headers = next(iterator, None)
            if not headers:
                continue
            keys = [_cell(h) for h in headers]
            for values in iterator:
                row = {key: _cell(value) for key, value in zip(keys, values) if key}
                if any(row.values()):
                    row["_sheet"] = sheet.title
                    rows.append(row)
        return rows
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames:
        return [{str(k): _cell(v) for k, v in row.items()} for row in reader]
    rows: list[dict[str, str]] = []
    for line in content.splitlines():
        parts = [part.strip() for part in re.split(r"[,，\t]", line) if part.strip()]
        if len(parts) >= 3:
            rows.append({"subject": parts[0], "relation": parts[1], "object": parts[2]})
    return rows


def map_rows_to_triples(rows: list[dict[str, str]], evidence_id: str | None = None) -> list[ExtractedTriple]:
    triples: list[ExtractedTriple] = []
    for index, row in enumerate(rows, start=1):
        lowered = {key.strip().lower(): value.strip() for key, value in row.items()}
        subject = _pick(row, lowered, "subject", "主体", "账户真实姓名", "账户假名", "付款方", "交易方", "姓名", "用户ID") or f"记录{index}"
        relation = _pick(row, lowered, "relation", "关系", "借贷类型", "资金方向_按账户", "交易业务类型", "交易用途类型") or "关联"
        obj = _pick(row, lowered, "object", "客体", "对手真实姓名", "对手假名", "对手方ID", "收款方", "对方户名", "value") or "未识别对象"
        amount = _pick(row, lowered, "交易金额_元", "金额", "交易金额", "amount")
        time = _pick(row, lowered, "映射案情时间", "交易时间", "原始交易时间", "time", "date")
        properties = {
            "row_index": index,
            "amount": amount,
            "time": time,
            "account_alias": _pick(row, lowered, "账户假名"),
            "counterparty_alias": _pick(row, lowered, "对手假名"),
            "source_file": _pick(row, lowered, "来源文件"),
        }
        props = {key: value for key, value in properties.items() if value not in (None, "")}
        triples.append(ExtractedTriple(subject=subject, relation=relation, object=obj, evidence_id=evidence_id, properties=props))
        if amount:
            triples.append(ExtractedTriple(subject=subject, relation="交易金额", object=amount, evidence_id=evidence_id, properties=props))
        if time:
            triples.append(ExtractedTriple(subject=subject, relation="发生时间", object=time, evidence_id=evidence_id, properties=props))
    return triples


def build_passages_from_triples(triples: list[ExtractedTriple]) -> list[PassageRecord]:
    passages: list[PassageRecord] = []
    for index, triple in enumerate(triples):
        extra = []
        if triple.properties.get("amount"):
            extra.append(f"金额 {triple.properties['amount']}")
        if triple.properties.get("time"):
            extra.append(f"时间 {triple.properties['time']}")
        suffix = f"（{'，'.join(extra)}）" if extra else ""
        passages.append(PassageRecord(text=f"{triple.subject} --{triple.relation}-> {triple.object}{suffix}", evidence_id=triple.evidence_id, triple_index=index))
    return passages


def extract_unstructured_triples(content: str, evidence_id: str | None = None) -> tuple[list[ExtractedTriple], list[PassageRecord]]:
    sentences = [item.strip() for item in re.split(r"[。！？!?；;\n]+", content) if item.strip()]
    triples: list[ExtractedTriple] = []
    passages: list[PassageRecord] = []
    for index, sentence in enumerate(sentences[:80], start=1):
        people = re.findall(r"[\u4e00-\u9fa5]{2,4}", sentence)
        subject = people[0] if people else f"文本片段{index}"
        obj = people[1] if len(people) > 1 else sentence[:80]
        triple = ExtractedTriple(subject=subject, relation=_infer_relation(sentence), object=obj, evidence_id=evidence_id)
        triples.append(triple)
        passages.append(PassageRecord(text=sentence, evidence_id=evidence_id, triple_index=index - 1))
    if not triples and content.strip():
        triples.append(ExtractedTriple(subject="文本证据", relation="包含", object=content[:120], evidence_id=evidence_id))
        passages.append(PassageRecord(text=content.strip(), evidence_id=evidence_id, triple_index=0))
    return triples, passages


def _infer_relation(sentence: str) -> str:
    if any(word in sentence for word in ("转账", "收款", "付款", "流水", "金额")):
        return "资金往来"
    if any(word in sentence for word in ("明知", "故意", "徇私", "隐瞒")):
        return "主观状态线索"
    if any(word in sentence for word in ("职务", "审批", "办理", "释放", "拘留", "立案")):
        return "职务行为"
    return "提及"


def _pick(original: dict[str, str], lowered: dict[str, str], *names: str) -> str | None:
    for name in names:
        key = name.lower()
        if key in lowered and lowered[key]:
            return lowered[key]
        for source_key, value in original.items():
            if name in source_key and value:
                return value.strip()
    return None


def _cell(value: Any) -> str:
    return "" if value is None else str(value).strip()

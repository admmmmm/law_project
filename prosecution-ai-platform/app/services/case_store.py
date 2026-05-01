from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.ingestion import EvidenceItem, ExtractionResult, SourceType


_CASE_EVIDENCE_STORE: dict[str, list[dict[str, object]]] = {}


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _content_preview(text: str, max_chars: int = 280) -> str:
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    return stripped[: max_chars - 1] + "…"


def add_evidence(
    case_id: str,
    title: str,
    source_type: SourceType,
    extraction: ExtractionResult,
    *,
    source_ref: str,
    content: str,
) -> EvidenceItem:
    evidence = EvidenceItem(
        evidence_id=f"evd_{uuid4().hex[:8]}",
        title=title,
        source_type=source_type,
        source_ref=source_ref,
        content_preview=_content_preview(content),
        created_at=_iso_utc_now(),
    )
    items = _CASE_EVIDENCE_STORE.setdefault(case_id, [])
    items.append(
        {
            "evidence": evidence,
            "extraction": extraction,
        }
    )
    return evidence


def list_case_evidences(case_id: str) -> list[EvidenceItem]:
    return [item["evidence"] for item in _CASE_EVIDENCE_STORE.get(case_id, [])]


def list_case_extractions(case_id: str) -> list[ExtractionResult]:
    return [item["extraction"] for item in _CASE_EVIDENCE_STORE.get(case_id, [])]

from app.core.errors import not_found
from app.schemas.common import new_id, now_utc
from app.schemas.ingestion import EvidenceRecord, IngestionResult, TextIngestionRequest
from app.services.information_extraction import extract_content, resolve_source_type, route_extraction
from app.storage.memory_store import MemoryStore


class IngestionService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def ingest_text(self, case_id: str, payload: TextIngestionRequest) -> IngestionResult:
        return self._save_evidence(
            case_id=case_id,
            title=payload.title,
            content=payload.content,
            raw_bytes=None,
            filename=None,
            source_type=payload.source_type,
            source_ref=payload.source_ref,
        )

    def ingest_file(self, case_id: str, filename: str, content: bytes, source_type: str) -> IngestionResult:
        resolved_type = resolve_source_type(source_type, filename)
        text = extract_content(source_type=resolved_type, raw_bytes=content)
        return self._save_evidence(
            case_id=case_id,
            title=filename,
            content=text or f"[binary file: {filename}]",
            raw_bytes=content,
            filename=filename,
            source_type=resolved_type,
            source_ref=filename,
        )

    def _save_evidence(
        self,
        case_id: str,
        title: str,
        content: str,
        raw_bytes: bytes | None,
        filename: str | None,
        source_type: str,
        source_ref: str | None,
    ) -> IngestionResult:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")

            evidence = EvidenceRecord(
                evidence_id=new_id("evd"),
                case_id=case_id,
                title=title,
                source_type=source_type,
                source_ref=source_ref,
                content_preview=content[:240],
                created_at=now_utc(),
            )
            extraction = route_extraction(
                source_type=source_type,
                content=content,
                raw_bytes=raw_bytes,
                filename=filename,
                evidence_id=evidence.evidence_id,
            )
            self.store.evidence.setdefault(case_id, []).append(evidence)
            self.store.raw_contents[evidence.evidence_id] = content
            self.store.extractions[evidence.evidence_id] = extraction
            self.store.cases[case_id] = case.model_copy(update={"status": "data_ingested"})
            return IngestionResult(case_id=case_id, accepted=True, evidence=evidence, extraction=extraction)

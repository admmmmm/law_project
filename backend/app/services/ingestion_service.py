from app.core.errors import not_found
from app.schemas.common import new_id, now_utc
import zipfile
from io import BytesIO
from pathlib import Path

from app.schemas.ingestion import BatchIngestionResult, EvidenceRecord, IngestionResult, TextIngestionRequest
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

    def ingest_many_files(self, case_id: str, files: list[tuple[str, bytes]], source_type: str = "unknown") -> BatchIngestionResult:
        results: list[IngestionResult] = []
        skipped: list[dict[str, str]] = []
        for filename, content in files:
            if self._should_skip(filename):
                skipped.append({"filename": filename, "reason": "unsupported_or_system_file"})
                continue
            try:
                results.append(self.ingest_file(case_id=case_id, filename=filename, content=content, source_type=source_type))
            except Exception as exc:
                skipped.append({"filename": filename, "reason": str(exc)})
        return BatchIngestionResult(
            case_id=case_id,
            accepted=bool(results),
            imported_count=len(results),
            skipped_count=len(skipped),
            evidences=[result.evidence for result in results],
            results=results,
            skipped=skipped,
        )

    def ingest_archive(self, case_id: str, filename: str, content: bytes) -> BatchIngestionResult:
        if not zipfile.is_zipfile(BytesIO(content)):
            single = self.ingest_file(case_id=case_id, filename=filename, content=content, source_type="unknown")
            return BatchIngestionResult(case_id=case_id, accepted=True, imported_count=1, evidences=[single.evidence], results=[single])

        files: list[tuple[str, bytes]] = []
        with zipfile.ZipFile(BytesIO(content)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                if self._should_skip(name):
                    continue
                files.append((name, archive.read(info)))
        return self.ingest_many_files(case_id=case_id, files=files)

    def _should_skip(self, filename: str) -> bool:
        suffix = Path(filename).suffix.lower()
        name = Path(filename).name
        if name.startswith(".") or "__MACOSX" in filename:
            return True
        return suffix not in {".txt", ".md", ".csv", ".xlsx", ".json", ".pdf", ".docx"}

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

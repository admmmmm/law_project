from app.core.errors import not_found
from app.schemas.common import new_id, now_utc
import zipfile
from io import BytesIO
from pathlib import Path

from app.schemas.ingestion import (
    BatchIngestionResult,
    EvidenceDetail,
    EvidenceRecord,
    EvidenceReviewUpdate,
    IngestionResult,
    PassageDetail,
    TextIngestionRequest,
    TripleDetail,
)
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

    def get_evidence_detail(self, case_id: str, evidence_id: str) -> EvidenceDetail:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            for evidence in self.store.evidence.get(case_id, []):
                if evidence.evidence_id == evidence_id:
                    extraction = self.store.extractions.get(evidence_id)
                    return EvidenceDetail(
                        **self._enrich_evidence(evidence).model_dump(),
                        content=self.store.raw_contents.get(evidence_id, evidence.content_preview),
                        metadata=dict(extraction.metadata) if extraction else {},
                        passages=_passage_details(evidence_id, extraction),
                        triples=_triple_details(evidence_id, extraction),
                    )
            raise not_found("evidence not found")

    def list_evidence(self, case_id: str) -> list[EvidenceRecord]:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            return [self._enrich_evidence(item) for item in self.store.evidence.get(case_id, [])]

    def update_evidence_review(self, case_id: str, evidence_id: str, payload: EvidenceReviewUpdate) -> EvidenceDetail:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            rows = self.store.evidence.get(case_id, [])
            for index, evidence in enumerate(rows):
                if evidence.evidence_id != evidence_id:
                    continue
                updates = payload.model_dump(exclude_unset=True)
                if updates.get("status") == "":
                    updates["status"] = "待审阅"
                updates["updated_at"] = now_utc()
                rows[index] = evidence.model_copy(update=updates)
                self.store.evidence[case_id] = rows
                self.store.flush_case(case_id)
                return self.get_evidence_detail(case_id, evidence_id)
            raise not_found("evidence not found")

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
                updated_at=now_utc(),
                name=title,
                brief=_brief_from_content(content),
                evidence_type=_evidence_type(title, source_type),
                status="已解析",
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
            self.store.portrait_facts.pop(case_id, None)
            self.store.cases[case_id] = case.model_copy(update={"status": "data_ingested"})
            self.store.flush_case(case_id)
            return IngestionResult(case_id=case_id, accepted=True, evidence=evidence, extraction=extraction)

    def _enrich_evidence(self, evidence: EvidenceRecord) -> EvidenceRecord:
        extraction = self.store.extractions.get(evidence.evidence_id)
        content = self.store.raw_contents.get(evidence.evidence_id, evidence.content_preview)
        return evidence.model_copy(
            update={
                "name": evidence.name or evidence.title,
                "brief": evidence.brief or _brief_from_content(content),
                "evidence_type": evidence.evidence_type or _evidence_type(evidence.title, evidence.source_type),
                "proof_item": evidence.proof_item or "",
                "status": evidence.status or ("已解析" if extraction else "上传完成"),
                "passage_count": len(extraction.passages) if extraction else 0,
                "updated_at": evidence.updated_at or evidence.created_at,
            }
        )


def _brief_from_content(content: str, limit: int = 120) -> str:
    text = " ".join(str(content or "").split())
    return text[:limit] + ("..." if len(text) > limit else "")


def _evidence_type(title: str, source_type: str) -> str:
    text = f"{title} {source_type}"
    mapping = [
        ("营业执照", "工商登记材料"),
        ("接警", "接警材料"),
        ("伤情", "伤情鉴定材料"),
        ("鉴定", "鉴定材料"),
        ("立案", "立案文书"),
        ("拘留", "强制措施文书"),
        ("释放", "释放文书"),
        ("调解", "调解/撤案材料"),
        ("撤销", "调解/撤案材料"),
        ("询问", "询问笔录"),
        ("证言", "证人证言"),
        ("短信", "通信记录"),
        ("通话", "通信记录"),
        ("银行", "资金流水"),
        ("流水", "资金流水"),
        ("csv", "结构化数据"),
        ("xlsx", "结构化数据"),
    ]
    for keyword, label in mapping:
        if keyword in text:
            return label
    return "未知类型"


def _passage_details(evidence_id: str, extraction) -> list[PassageDetail]:
    if not extraction:
        return []
    return [
        PassageDetail(
            passage_id=f"passage:{evidence_id}:{index}",
            text=passage.text,
            summary=_brief_from_content(passage.text, 80),
            index=index,
        )
        for index, passage in enumerate(extraction.passages)
    ]


def _triple_details(evidence_id: str, extraction) -> list[TripleDetail]:
    if not extraction:
        return []
    rows: list[TripleDetail] = []
    for index, triple in enumerate(extraction.triples):
        passage_index = triple.properties.get("passage_index")
        source_passage_id = f"passage:{evidence_id}:{passage_index}" if isinstance(passage_index, int) else None
        rows.append(
            TripleDetail(
                triple_id=f"triple:{evidence_id}:{index}",
                subject=triple.subject,
                predicate=triple.relation,
                object=triple.object,
                source_passage_id=source_passage_id,
            )
        )
    return rows

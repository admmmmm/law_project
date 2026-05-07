from app.schemas.case import CaseCreate
from app.schemas.ingestion import TextIngestionRequest
from app.services.analysis_skill_service import AnalysisSkillService
from app.services.case_service import CaseService
from app.services.document_mother_service import DocumentMotherService
from app.services.ingestion_service import IngestionService
from app.storage.memory_store import MemoryStore


def _case_with_turning_point(tmp_path: Path) -> tuple[MemoryStore, str]:
    store = MemoryStore(db_path=tmp_path / "test.db")
    case = CaseService(store).create_case(CaseCreate(title="pytest 文书母图案"))
    ingestion = IngestionService(store)
    ingestion.ingest_text(
        case.case_id,
        TextIngestionRequest(title="证据1-3_立案决定书.md", content="2024年8月12日，公安机关对罗贤涛故意伤害案刑事立案。批准人：杨周武。"),
    )
    ingestion.ingest_text(
        case.case_id,
        TextIngestionRequest(title="证据4-1_呈请撤销案件_调解处理报告书.md", content="2024年9月6日，案件调解处理。杨周武签字同意调解结案，立即放人。"),
    )
    return store, case.case_id


def test_document_mother_rebuild_is_idempotent(tmp_path: Path):
    store, case_id = _case_with_turning_point(tmp_path)
    service = DocumentMotherService(store)
    first = service.rebuild(case_id)
    second = service.rebuild(case_id)
    assert len(first.nodes) == 2
    assert len(second.nodes) == 2
    assert len(service.get_graph(case_id).nodes) == 2


def test_unverified_claim_does_not_support_finding(tmp_path: Path):
    store, case_id = _case_with_turning_point(tmp_path)
    DocumentMotherService(store).rebuild(case_id)
    nodes = store.document_mother_nodes[case_id]
    nodes[0].key_claims[0] = nodes[0].key_claims[0].model_copy(update={"status": "unverified_claim", "supporting_passage_refs": []})
    run = AnalysisSkillService(store).run_rule_pack(case_id, "process_turning_point")
    assert run.findings
    assert all(claim.status == "verified" for finding in run.findings for claim in finding.supporting_claims)


def test_skill_registry_hash_exists_and_no_findings_returns_debug_info(tmp_path: Path):
    store, case_id = _case_with_turning_point(tmp_path)
    service = AnalysisSkillService(store)
    packs = service.list_rule_packs()
    assert any(pack.name == "document_completeness" and pack.content_hash for pack in packs)
    DocumentMotherService(store).rebuild(case_id)
    run = service.run_rule_pack(case_id, "document_completeness")
    assert run.findings or run.not_triggered or run.data_gaps
from pathlib import Path

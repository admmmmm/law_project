from pathlib import Path

from app.schemas.case import CaseCreate
from app.schemas.ingestion import TextIngestionRequest
from app.services.analysis_skill_service import AnalysisSkillService
from app.services.case_service import CaseService
from app.services.document_mother_service import DocumentMotherService
from app.services.evidence_map_service import FORBIDDEN_WORDS, EvidenceMapService
from app.services.ingestion_service import IngestionService
from app.storage.memory_store import MemoryStore


def _case_with_map_data(tmp_path: Path) -> tuple[MemoryStore, str]:
    store = MemoryStore(db_path=tmp_path / "test.db")
    case = CaseService(store).create_case(CaseCreate(title="pytest 证据地图案"))
    ingestion = IngestionService(store)
    ingestion.ingest_text(
        case.case_id,
        TextIngestionRequest(title="证据1-1_接警记录.md", content="2024年8月12日，江军报警称舞王俱乐部发生伤害事件。接警民警记录警情。"),
    )
    ingestion.ingest_text(
        case.case_id,
        TextIngestionRequest(title="证据1-3_立案决定书.md", content="2024年8月13日，对罗贤涛、易承桂涉嫌故意伤害案刑事立案。批准人：杨周武。"),
    )
    ingestion.ingest_text(
        case.case_id,
        TextIngestionRequest(title="证据4-2_释放通知书.md", content="2024年9月6日，罗贤涛、易承桂被释放。批准人：杨周武。"),
    )
    DocumentMotherService(store).rebuild(case.case_id)
    AnalysisSkillService(store).run_rule_pack(case.case_id, "process_turning_point")
    return store, case.case_id


def test_evidence_map_document_defaults_and_no_forbidden_words(tmp_path: Path):
    store, case_id = _case_with_map_data(tmp_path)
    result = EvidenceMapService(store).get_map(case_id)
    assert result.documents
    rendered = result.model_dump_json()
    assert all(word not in rendered for word in FORBIDDEN_WORDS)
    assert all(set(doc.map_tags) for doc in result.documents)


def test_evidence_map_process_next_requires_support(tmp_path: Path):
    store, case_id = _case_with_map_data(tmp_path)
    result = EvidenceMapService(store).get_map(case_id)
    process_edges = [edge for edge in result.document_edges if edge.type == "PROCESS_NEXT"]
    assert process_edges
    assert all(edge.supporting_passage_ids or edge.supporting_triple_ids or edge.shared_entities or edge.weight >= 0.35 for edge in process_edges)


def test_evidence_map_edge_limits_and_supports_same_finding(tmp_path: Path):
    store, case_id = _case_with_map_data(tmp_path)
    result = EvidenceMapService(store).get_map(case_id)
    degree: dict[str, int] = {}
    seen_pairs: set[tuple[str, str, str]] = set()
    for edge in result.document_edges:
        degree[edge.source] = degree.get(edge.source, 0) + 1
        degree[edge.target] = degree.get(edge.target, 0) + 1
        pair = tuple(sorted([edge.source, edge.target]) + [edge.type])
        assert pair not in seen_pairs
        seen_pairs.add(pair)
        assert edge.weight >= 0.35
        if edge.type == "SHARED_ENTITY":
            assert len(edge.shared_entities) <= 3
    assert all(count <= 8 for count in degree.values())


def test_evidence_map_contains_passages_and_triples(tmp_path: Path):
    store, case_id = _case_with_map_data(tmp_path)
    result = EvidenceMapService(store).get_map(case_id)
    assert result.passages
    assert result.triples
    assert any(edge.type == "CONTAINS" for edge in result.containment_edges)
    assert any(edge.type == "EXTRACTS" for edge in result.containment_edges)

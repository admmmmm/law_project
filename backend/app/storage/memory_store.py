from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock

from app.core.config import settings
from app.schemas.case import CaseDetail
from app.schemas.graph import InvestigationGraph
from app.schemas.ingestion import EvidenceRecord, ExtractionResult
from app.schemas.memory import MemoryRecord
from app.schemas.report import PortraitReport
from app.schemas.analysis import AnalysisMessage, AnalysisThread, PortraitFactsResult, RetrievalSession, RetrievalStep
from app.schemas.analysis_skill import RulePackRunResult, SkillRegistryEntry
from app.schemas.document_mother import DocumentMotherNode


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_db_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = (_backend_root() / path).resolve()
    return path


@dataclass
class MemoryStore:
    cases: dict[str, CaseDetail] = field(default_factory=dict)
    evidence: dict[str, list[EvidenceRecord]] = field(default_factory=dict)
    extractions: dict[str, ExtractionResult] = field(default_factory=dict)
    graphs: dict[str, InvestigationGraph] = field(default_factory=dict)
    reports: dict[str, PortraitReport] = field(default_factory=dict)
    memories: dict[str, list[MemoryRecord]] = field(default_factory=dict)
    analysis_threads: dict[str, list[AnalysisThread]] = field(default_factory=dict)
    analysis_messages: dict[str, list[AnalysisMessage]] = field(default_factory=dict)
    portrait_facts: dict[str, PortraitFactsResult] = field(default_factory=dict)
    retrieval_sessions: dict[str, list[RetrievalSession]] = field(default_factory=dict)
    retrieval_steps: dict[str, list[RetrievalStep]] = field(default_factory=dict)
    document_mother_nodes: dict[str, list[DocumentMotherNode]] = field(default_factory=dict)
    rule_pack_runs: dict[str, list[RulePackRunResult]] = field(default_factory=dict)
    analysis_skill_registry: dict[str, SkillRegistryEntry] = field(default_factory=dict)
    raw_contents: dict[str, str] = field(default_factory=dict)
    db_path: Path = field(default_factory=lambda: _resolve_db_path(settings.storage_db_path))
    lock: RLock = field(default_factory=RLock)

    def __post_init__(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()
        self._load_from_db()

    def flush_case(self, case_id: str) -> None:
        case = self.cases.get(case_id)
        if not case:
            return

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cases (case_id, payload) VALUES (?, ?)",
                (case_id, case.model_dump_json()),
            )

            conn.execute("DELETE FROM evidence WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM raw_contents WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM extractions WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM memories WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM analysis_threads WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM analysis_messages WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM portrait_facts WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM retrieval_sessions WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM retrieval_steps WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM document_mother_nodes WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM rule_pack_runs WHERE case_id = ?", (case_id,))

            for item in self.evidence.get(case_id, []):
                conn.execute(
                    "INSERT OR REPLACE INTO evidence (case_id, evidence_id, payload) VALUES (?, ?, ?)",
                    (case_id, item.evidence_id, item.model_dump_json()),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO raw_contents (case_id, evidence_id, content) VALUES (?, ?, ?)",
                    (case_id, item.evidence_id, self.raw_contents.get(item.evidence_id, item.content_preview)),
                )
                extraction = self.extractions.get(item.evidence_id)
                if extraction:
                    conn.execute(
                        "INSERT OR REPLACE INTO extractions (case_id, evidence_id, payload) VALUES (?, ?, ?)",
                        (case_id, item.evidence_id, extraction.model_dump_json()),
                    )

            for record in self.memories.get(case_id, []):
                conn.execute(
                    "INSERT OR REPLACE INTO memories (case_id, memory_id, payload) VALUES (?, ?, ?)",
                    (case_id, record.memory_id, record.model_dump_json()),
                )

            for thread in self.analysis_threads.get(case_id, []):
                conn.execute(
                    "INSERT OR REPLACE INTO analysis_threads (case_id, thread_id, payload) VALUES (?, ?, ?)",
                    (case_id, thread.thread_id, thread.model_dump_json()),
                )

            for message in self.analysis_messages.get(case_id, []):
                conn.execute(
                    "INSERT OR REPLACE INTO analysis_messages (case_id, thread_id, message_id, payload) VALUES (?, ?, ?, ?)",
                    (case_id, message.thread_id, message.message_id, message.model_dump_json()),
                )

            for session in self.retrieval_sessions.get(case_id, []):
                conn.execute(
                    "INSERT OR REPLACE INTO retrieval_sessions (case_id, session_id, payload) VALUES (?, ?, ?)",
                    (case_id, session.session_id, session.model_dump_json()),
                )

            for step in self.retrieval_steps.get(case_id, []):
                conn.execute(
                    "INSERT OR REPLACE INTO retrieval_steps (case_id, session_id, step_id, payload) VALUES (?, ?, ?, ?)",
                    (case_id, step.session_id, step.step_id, step.model_dump_json()),
                )

            for node in self.document_mother_nodes.get(case_id, []):
                conn.execute(
                    "INSERT OR REPLACE INTO document_mother_nodes (case_id, doc_id, evidence_id, payload) VALUES (?, ?, ?, ?)",
                    (case_id, node.doc_id, node.evidence_id, node.model_dump_json()),
                )

            for run in self.rule_pack_runs.get(case_id, []):
                run_id = f"{run.rule_pack}:{run.created_at.isoformat()}"
                conn.execute(
                    "INSERT OR REPLACE INTO rule_pack_runs (case_id, run_id, payload) VALUES (?, ?, ?)",
                    (case_id, run_id, run.model_dump_json()),
                )

            graph = self.graphs.get(case_id)
            if graph:
                conn.execute(
                    "INSERT OR REPLACE INTO graphs (case_id, payload) VALUES (?, ?)",
                    (case_id, graph.model_dump_json()),
                )
            else:
                conn.execute("DELETE FROM graphs WHERE case_id = ?", (case_id,))

            report = self.reports.get(case_id)
            if report:
                conn.execute(
                    "INSERT OR REPLACE INTO reports (case_id, payload) VALUES (?, ?)",
                    (case_id, report.model_dump_json()),
                )
            else:
                conn.execute("DELETE FROM reports WHERE case_id = ?", (case_id,))

            portrait_facts = self.portrait_facts.get(case_id)
            if portrait_facts:
                conn.execute(
                    "INSERT OR REPLACE INTO portrait_facts (case_id, payload) VALUES (?, ?)",
                    (case_id, portrait_facts.model_dump_json()),
                )
            else:
                conn.execute("DELETE FROM portrait_facts WHERE case_id = ?", (case_id,))

            conn.commit()

    def _initialize_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evidence (
                    case_id TEXT NOT NULL,
                    evidence_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS raw_contents (
                    case_id TEXT NOT NULL,
                    evidence_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS extractions (
                    case_id TEXT NOT NULL,
                    evidence_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS graphs (
                    case_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reports (
                    case_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS portrait_facts (
                    case_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS memories (
                    case_id TEXT NOT NULL,
                    memory_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS analysis_threads (
                    case_id TEXT NOT NULL,
                    thread_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS analysis_messages (
                    case_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    message_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS retrieval_sessions (
                    case_id TEXT NOT NULL,
                    session_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS retrieval_steps (
                    case_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    step_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS document_mother_nodes (
                    case_id TEXT NOT NULL,
                    doc_id TEXT PRIMARY KEY,
                    evidence_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS analysis_skill_registry (
                    name TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rule_pack_runs (
                    case_id TEXT NOT NULL,
                    run_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def _load_from_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            self.cases = {
                row["case_id"]: CaseDetail.model_validate_json(row["payload"])
                for row in conn.execute("SELECT case_id, payload FROM cases")
            }

            self.evidence = {case_id: [] for case_id in self.cases}
            for row in conn.execute("SELECT case_id, payload FROM evidence ORDER BY rowid"):
                self.evidence.setdefault(row["case_id"], []).append(EvidenceRecord.model_validate_json(row["payload"]))

            self.raw_contents = {
                row["evidence_id"]: row["content"]
                for row in conn.execute("SELECT evidence_id, content FROM raw_contents")
            }

            self.extractions = {
                row["evidence_id"]: ExtractionResult.model_validate_json(row["payload"])
                for row in conn.execute("SELECT evidence_id, payload FROM extractions")
            }

            self.graphs = {
                row["case_id"]: InvestigationGraph.model_validate_json(row["payload"])
                for row in conn.execute("SELECT case_id, payload FROM graphs")
            }

            self.reports = {
                row["case_id"]: PortraitReport.model_validate_json(row["payload"])
                for row in conn.execute("SELECT case_id, payload FROM reports")
            }

            self.portrait_facts = {
                row["case_id"]: PortraitFactsResult.model_validate_json(row["payload"])
                for row in conn.execute("SELECT case_id, payload FROM portrait_facts")
            }

            self.document_mother_nodes = {case_id: [] for case_id in self.cases}
            for row in conn.execute("SELECT case_id, payload FROM document_mother_nodes ORDER BY rowid"):
                self.document_mother_nodes.setdefault(row["case_id"], []).append(DocumentMotherNode.model_validate_json(row["payload"]))

            self.analysis_skill_registry = {
                row["name"]: SkillRegistryEntry.model_validate_json(row["payload"])
                for row in conn.execute("SELECT name, payload FROM analysis_skill_registry")
            }

            self.rule_pack_runs = {case_id: [] for case_id in self.cases}
            for row in conn.execute("SELECT case_id, payload FROM rule_pack_runs ORDER BY rowid"):
                self.rule_pack_runs.setdefault(row["case_id"], []).append(RulePackRunResult.model_validate_json(row["payload"]))

            self.memories = {case_id: [] for case_id in self.cases}
            for row in conn.execute("SELECT case_id, payload FROM memories ORDER BY rowid"):
                self.memories.setdefault(row["case_id"], []).append(MemoryRecord.model_validate_json(row["payload"]))

            self.analysis_threads = {case_id: [] for case_id in self.cases}
            for row in conn.execute("SELECT case_id, payload FROM analysis_threads ORDER BY rowid"):
                self.analysis_threads.setdefault(row["case_id"], []).append(AnalysisThread.model_validate_json(row["payload"]))

            self.analysis_messages = {case_id: [] for case_id in self.cases}
            for row in conn.execute("SELECT case_id, payload FROM analysis_messages ORDER BY rowid"):
                self.analysis_messages.setdefault(row["case_id"], []).append(AnalysisMessage.model_validate_json(row["payload"]))

            self.retrieval_sessions = {case_id: [] for case_id in self.cases}
            for row in conn.execute("SELECT case_id, payload FROM retrieval_sessions ORDER BY rowid"):
                self.retrieval_sessions.setdefault(row["case_id"], []).append(RetrievalSession.model_validate_json(row["payload"]))

            self.retrieval_steps = {case_id: [] for case_id in self.cases}
            for row in conn.execute("SELECT case_id, payload FROM retrieval_steps ORDER BY rowid"):
                self.retrieval_steps.setdefault(row["case_id"], []).append(RetrievalStep.model_validate_json(row["payload"]))

        for case_id in self.cases:
            self.evidence.setdefault(case_id, [])
            self.memories.setdefault(case_id, [])
            self.analysis_threads.setdefault(case_id, [])
            self.analysis_messages.setdefault(case_id, [])
            self.retrieval_sessions.setdefault(case_id, [])
            self.retrieval_steps.setdefault(case_id, [])
            self.graphs.setdefault(case_id, InvestigationGraph(case_id=case_id))


_store = MemoryStore()


def get_store() -> MemoryStore:
    return _store

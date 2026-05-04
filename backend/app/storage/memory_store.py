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

                CREATE TABLE IF NOT EXISTS memories (
                    case_id TEXT NOT NULL,
                    memory_id TEXT PRIMARY KEY,
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

            self.memories = {case_id: [] for case_id in self.cases}
            for row in conn.execute("SELECT case_id, payload FROM memories ORDER BY rowid"):
                self.memories.setdefault(row["case_id"], []).append(MemoryRecord.model_validate_json(row["payload"]))

        for case_id in self.cases:
            self.evidence.setdefault(case_id, [])
            self.memories.setdefault(case_id, [])
            self.graphs.setdefault(case_id, InvestigationGraph(case_id=case_id))


_store = MemoryStore()


def get_store() -> MemoryStore:
    return _store

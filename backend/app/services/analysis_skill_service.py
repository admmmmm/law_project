from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.core.errors import not_found
from app.schemas.analysis_skill import NotTriggeredRule, RuleBundleRunRequest, RuleBundleRunResult, RuleFinding, RulePackRunResult, RulePackSummary, SkillRegistryEntry
from app.schemas.common import new_id, now_utc
from app.schemas.document_mother import DocumentClaim, DocumentMotherNode
from app.storage.memory_store import MemoryStore


class AnalysisSkillService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.packs_dir = Path(__file__).resolve().parents[1] / "analysis_skills" / "packs"

    def sync_registry(self) -> list[SkillRegistryEntry]:
        entries: list[SkillRegistryEntry] = []
        for manifest_path in sorted(self.packs_dir.glob("*/manifest.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            folder = manifest_path.parent
            manifest_hash = _hash_text(manifest_path.read_text(encoding="utf-8"))
            content_hash = _hash_folder(folder)
            entry = SkillRegistryEntry(
                name=str(manifest.get("name") or folder.name),
                title=str(manifest.get("title") or folder.name),
                version=str(manifest.get("version") or "0.1.0"),
                description=str(manifest.get("description") or ""),
                enabled=bool(manifest.get("enabled", True)),
                manifest_hash=manifest_hash,
                content_hash=content_hash,
                manifest_json=manifest,
                synced_at=now_utc(),
            )
            entries.append(entry)
        with self.store.lock:
            for entry in entries:
                self.store.analysis_skill_registry[entry.name] = entry
            _flush_registry(self.store)
        return entries

    def list_rule_packs(self) -> list[RulePackSummary]:
        entries = self.sync_registry()
        return [
            RulePackSummary(
                name=item.name,
                title=item.title,
                version=item.version,
                description=item.description,
                enabled=item.enabled,
                case_types=[str(v) for v in item.manifest_json.get("case_types", [])],
                task_types=[str(v) for v in item.manifest_json.get("task_types", [])],
                triggers=[str(v) for v in item.manifest_json.get("triggers", [])],
                content_hash=item.content_hash,
            )
            for item in entries
            if item.enabled
        ]

    def run_rule_pack(self, case_id: str, pack_name: str) -> RulePackRunResult:
        self.sync_registry()
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            nodes = list(self.store.document_mother_nodes.get(case_id, []))
            evidence = list(self.store.evidence.get(case_id, []))
            extractions = dict(self.store.extractions)
        if not nodes:
            from app.services.document_mother_service import DocumentMotherService

            nodes = DocumentMotherService(self.store).rebuild(case_id).nodes
        checks = _load_checks(self.packs_dir, pack_name)
        result = _execute_pack(case_id, pack_name, checks, nodes, evidence, extractions)
        with self.store.lock:
            self.store.rule_pack_runs.setdefault(case_id, []).append(result)
            self.store.flush_case(case_id)
        return result

    def run_bundle(self, case_id: str, payload: RuleBundleRunRequest) -> RuleBundleRunResult:
        names = payload.skill_names or [item.name for item in self.list_rule_packs()]
        return RuleBundleRunResult(case_id=case_id, results=[self.run_rule_pack(case_id, name) for name in names])


def _execute_pack(case_id: str, pack_name: str, checks: dict[str, Any], nodes: list[DocumentMotherNode], evidence: list[Any], extractions: dict[str, Any]) -> RulePackRunResult:
    findings: list[RuleFinding] = []
    not_triggered: list[NotTriggeredRule] = []
    data_gaps: list[str] = []
    stages = {node.process_stage for node in nodes}
    doc_types = {node.doc_type for node in nodes}
    all_text = "\n".join([node.title + "\n" + node.summary + "\n" + " ".join(claim.claim for claim in node.key_claims) for node in nodes])
    for check in checks.get("checks", []):
        rule_id = str(check.get("id") or "rule")
        triggered, reason = _check_trigger(check.get("trigger") or {}, stages, doc_types, all_text, nodes)
        if not triggered:
            not_triggered.append(NotTriggeredRule(rule_id=rule_id, reason=reason))
            continue
        missing = [doc for doc in check.get("expected_doc_types", []) if doc not in doc_types]
        if check.get("expected_doc_types") and not missing:
            not_triggered.append(NotTriggeredRule(rule_id=rule_id, reason="预期材料已发现，未形成材料缺口。"))
            continue
        support_nodes = _support_nodes(check, nodes)
        supporting_claims = _verified_claims(support_nodes)
        findings.append(
            RuleFinding(
                finding_id=new_id("find"),
                skill_name=pack_name,
                rule_id=rule_id,
                finding_type=str(check.get("finding_type") or pack_name),
                severity=str(check.get("severity") or "medium"),
                title=str(check.get("title") or rule_id),
                reason=_finding_reason(check, support_nodes, missing),
                supporting_documents=[node.doc_id for node in support_nodes],
                supporting_claims=supporting_claims,
                missing_documents=[str(v) for v in (check.get("missing_documents") or missing)],
                process_stage=", ".join(sorted({node.process_stage for node in support_nodes if node.process_stage})),
                next_actions=[str(v) for v in check.get("next_actions", [])],
                confidence=0.72 if supporting_claims else 0.45,
                evidence_level="medium" if supporting_claims else "low",
                data_completeness="partial" if missing else "unknown",
                related_hypotheses=[str(check.get("title") or rule_id)],
                debug_trace=[f"stages={sorted(stages)}", f"doc_types={sorted(doc_types)}", f"support_docs={[node.doc_id for node in support_nodes]}"],
                created_from="rule_pack",
            )
        )
    if not nodes:
        data_gaps.append("未生成文件母图。")
    if not evidence:
        data_gaps.append("当前案件没有证据材料。")
    if not findings and not data_gaps:
        data_gaps.append("未发现满足当前规则包触发条件的文件组合。")
    return RulePackRunResult(case_id=case_id, rule_pack=pack_name, findings=findings, not_triggered=not_triggered, data_gaps=data_gaps, created_at=now_utc())


def _check_trigger(trigger: dict[str, Any], stages: set[str], doc_types: set[str], all_text: str, nodes: list[DocumentMotherNode]) -> tuple[bool, str]:
    for stage in trigger.get("all_stages", []):
        if stage not in stages:
            return False, f"未发现流程阶段：{stage}"
    if trigger.get("any_stage") and not any(stage in stages for stage in trigger["any_stage"]):
        return False, f"未发现任一流程阶段：{', '.join(trigger['any_stage'])}"
    if trigger.get("keywords") and not any(word in all_text for word in trigger["keywords"]):
        return False, f"未发现关键词：{', '.join(trigger['keywords'])}"
    if trigger.get("claim_keywords") and not any(any(word in claim.claim for word in trigger["claim_keywords"]) for node in nodes for claim in node.key_claims):
        return False, f"未发现 claim 关键词：{', '.join(trigger['claim_keywords'])}"
    return True, "命中触发条件。"


def _support_nodes(check: dict[str, Any], nodes: list[DocumentMotherNode]) -> list[DocumentMotherNode]:
    trigger = check.get("trigger") or {}
    wanted_stages = set(trigger.get("all_stages", []) + trigger.get("any_stage", []))
    keywords = set(trigger.get("keywords", []) + trigger.get("claim_keywords", []))
    rows = []
    for node in nodes:
        text = f"{node.title} {node.summary} {' '.join(c.claim for c in node.key_claims)}"
        if node.process_stage in wanted_stages or any(word in text for word in keywords):
            rows.append(node)
    return rows[:8] or nodes[:4]


def _verified_claims(nodes: list[DocumentMotherNode]) -> list[DocumentClaim]:
    claims: list[DocumentClaim] = []
    for node in nodes:
        claims.extend([claim for claim in node.key_claims if claim.status == "verified"])
    return claims[:12]


def _finding_reason(check: dict[str, Any], nodes: list[DocumentMotherNode], missing: list[str]) -> str:
    docs = "、".join(node.doc_id for node in nodes[:5]) or "当前文件母图"
    gap = f"；缺失/待核查材料：{'、'.join(missing)}" if missing else ""
    return f"规则“{check.get('title')}”基于 {docs} 命中{gap}。"


def _load_checks(root: Path, pack_name: str) -> dict[str, Any]:
    path = root / pack_name / "checks.json"
    if not path.exists():
        raise not_found(f"rule pack '{pack_name}' not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_folder(folder: Path) -> str:
    chunks = []
    for path in sorted(folder.glob("*")):
        if path.is_file():
            chunks.append(path.name)
            chunks.append(path.read_text(encoding="utf-8"))
    return _hash_text("\n".join(chunks))


def _hash_text(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _flush_registry(store: MemoryStore) -> None:
    import sqlite3

    with sqlite3.connect(store.db_path) as conn:
        for entry in store.analysis_skill_registry.values():
            conn.execute("INSERT OR REPLACE INTO analysis_skill_registry (name, payload) VALUES (?, ?)", (entry.name, entry.model_dump_json()))
        conn.commit()

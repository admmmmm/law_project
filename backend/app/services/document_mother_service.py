from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from os import getenv
from typing import Any

from app.core.config import settings
from app.core.errors import not_found
from app.schemas.common import now_utc
from app.schemas.document_mother import DocumentClaim, DocumentGenerationMeta, DocumentMotherGraph, DocumentMotherNode, PassageRef
from app.schemas.ingestion import EvidenceRecord, ExtractionResult, PassageRecord
from app.storage.memory_store import MemoryStore


SCHEMA_VERSION = "0.1.0"
BUILDER_VERSION = "document_mother_builder_v1"


class DocumentMotherService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def get_graph(self, case_id: str) -> DocumentMotherGraph:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            return DocumentMotherGraph(case_id=case_id, nodes=list(self.store.document_mother_nodes.get(case_id, [])))

    def rebuild(self, case_id: str) -> DocumentMotherGraph:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            evidence = list(self.store.evidence.get(case_id, []))
            raw_contents = dict(self.store.raw_contents)
            extractions = dict(self.store.extractions)

        nodes: list[DocumentMotherNode] = []
        warnings: list[str] = []
        for item in evidence:
            content = raw_contents.get(item.evidence_id, item.content_preview)
            extraction = extractions.get(item.evidence_id)
            try:
                nodes.append(_build_document_node(item, content, extraction))
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{item.title}: {exc}")

        with self.store.lock:
            existing = {node.doc_id: node for node in self.store.document_mother_nodes.get(case_id, [])}
            for node in nodes:
                existing[node.doc_id] = node
            self.store.document_mother_nodes[case_id] = list(existing.values())
            self.store.portrait_facts.pop(case_id, None)
            self.store.flush_case(case_id)

        return DocumentMotherGraph(case_id=case_id, nodes=nodes, rebuilt_count=len(nodes), warnings=warnings)


def _build_document_node(evidence: EvidenceRecord, content: str, extraction: ExtractionResult | None) -> DocumentMotherNode:
    doc_id = _doc_id(evidence)
    passages = _passages(evidence, content, extraction)
    doc_type = _infer_doc_type(evidence.title, content)
    process_stage = _infer_process_stage(doc_type, evidence.title, content)
    source_quality = _infer_source_quality(evidence.title, content)
    formation_time = _extract_time(evidence.title + "\n" + content)
    event_time = _extract_event_time(content) or formation_time
    key_entities = _extract_entities(content, extraction)
    llm_payload, llm_error = _llm_document_summary(evidence, content, passages, doc_type, process_stage)
    generated = bool(llm_payload)

    summary = str((llm_payload or {}).get("summary") or _fallback_summary(evidence.title, doc_type, process_stage, content))
    proof_purpose = str((llm_payload or {}).get("proof_purpose") or _fallback_proof_purpose(doc_type, process_stage))
    risk_tags = [str(item) for item in _safe_list((llm_payload or {}).get("risk_tags"))][:8] or _risk_tags(doc_type, process_stage, content)
    raw_claims = _safe_list((llm_payload or {}).get("key_claims")) or _fallback_claims(content, doc_type, process_stage)
    claims = _validate_claims(raw_claims, passages, evidence.evidence_id)
    warnings: list[str] = []
    if llm_error:
        warnings.append(llm_error)
    if any(claim.status == "unverified_claim" for claim in claims):
        warnings.append("存在无 passage 支撑的 claim，已标记为 unverified_claim。")

    return DocumentMotherNode(
        doc_id=doc_id,
        evidence_id=evidence.evidence_id,
        title=evidence.title,
        doc_type=doc_type,
        process_stage=process_stage,
        formation_time=formation_time,
        event_time=event_time,
        source_quality=source_quality,
        summary=summary[:800],
        proof_purpose=proof_purpose[:800],
        key_claims=claims,
        key_entities=key_entities[:30],
        risk_tags=risk_tags,
        quality_status="needs_review" if warnings else "ok",
        warnings=warnings,
        source_content_hash=_hash_text(content),
        extraction_hash=_hash_text(extraction.model_dump_json() if extraction else ""),
        builder_version=BUILDER_VERSION,
        generation=DocumentGenerationMeta(
            method="rules+deepseek" if generated else "rules",
            model=settings.deepseek_analysis_model if generated else "",
            schema_version=SCHEMA_VERSION,
            generated_at=now_utc(),
        ),
    )


def _llm_document_summary(
    evidence: EvidenceRecord,
    content: str,
    passages: list[PassageRecord],
    doc_type: str,
    process_stage: str,
) -> tuple[dict[str, Any] | None, str | None]:
    api_key = getenv("DEEPSEEK_API_KEY")
    if not settings.deepseek_analysis_enabled or not api_key:
        return None, None
    prompt = {
        "title": evidence.title,
        "doc_type_fixed": doc_type,
        "process_stage_fixed": process_stage,
        "passages": [{"index": idx, "text": p.text[:500]} for idx, p in enumerate(passages[:12])],
        "allowed_output": {
            "summary": "只概括本文件已载明事实",
            "proof_purpose": "本文件可能证明什么",
            "key_claims": [{"claim": "一句事实", "claim_type": "fact|procedure|identity|fund|call|risk"}],
            "risk_tags": ["标签"],
        },
        "rules": [
            "必须输出 JSON object。",
            "不要改变 doc_type_fixed/process_stage_fixed。",
            "不得写 passages 中没有依据的新事实。",
            "key_claims 每条必须能在某个 passage 中找到文字依据。",
        ],
    }
    body = {
        "model": settings.deepseek_analysis_model,
        "messages": [
            {"role": "system", "content": "你是证据文件摘要器，只输出 JSON。"},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{settings.hipporag_llm_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=min(settings.deepseek_analysis_timeout, 45)) as response:
            data = json.loads(response.read().decode("utf-8"))
        parsed = json.loads(data["choices"][0]["message"]["content"])
        if not isinstance(parsed, dict):
            return None, "DeepSeek 文件摘要不是 JSON object。"
        return parsed, None
    except Exception as exc:  # noqa: BLE001
        return None, f"DeepSeek 文件摘要失败：{exc}"


def _validate_claims(raw_claims: list[Any], passages: list[PassageRecord], evidence_id: str) -> list[DocumentClaim]:
    claims: list[DocumentClaim] = []
    for idx, raw in enumerate(raw_claims[:12], start=1):
        if isinstance(raw, dict):
            text = str(raw.get("claim") or "").strip()
            claim_type = str(raw.get("claim_type") or "fact")
        else:
            text = str(raw or "").strip()
            claim_type = "fact"
        if not text:
            continue
        refs = _supporting_passages(text, passages, evidence_id)
        status = "verified" if refs else "unverified_claim"
        claims.append(
            DocumentClaim(
                claim_id=f"claim_{idx}",
                claim=text[:500],
                claim_type=claim_type[:40],
                supporting_passage_refs=refs,
                confidence=0.82 if refs else 0.25,
                status=status,
            )
        )
    return claims


def _supporting_passages(claim: str, passages: list[PassageRecord], evidence_id: str) -> list[PassageRef]:
    terms = [term for term in re.findall(r"[\u4e00-\u9fa5]{2,}|\d+(?:\.\d+)?万?元?", claim) if len(term) >= 2]
    refs: list[PassageRef] = []
    for idx, passage in enumerate(passages):
        if claim in passage.text or (terms and sum(1 for term in terms if term in passage.text) / max(len(terms), 1) >= 0.45):
            refs.append(PassageRef(passage_index=idx, evidence_id=evidence_id, text=passage.text[:500]))
        if len(refs) >= 3:
            break
    return refs


def _doc_id(evidence: EvidenceRecord) -> str:
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", evidence.title).replace("\\", "/").split("/")[-1]
    match = re.search(r"证据\d+(?:-\d+)?", stem)
    return match.group(0) if match else evidence.evidence_id


def _passages(evidence: EvidenceRecord, content: str, extraction: ExtractionResult | None) -> list[PassageRecord]:
    if extraction and extraction.passages:
        return extraction.passages
    parts = [part.strip() for part in re.split(r"\n+|(?<=[。！？；])", content) if len(part.strip()) >= 8]
    return [PassageRecord(text=part[:1000], evidence_id=evidence.evidence_id) for part in parts[:40]]


def _infer_doc_type(title: str, content: str) -> str:
    text = f"{title}\n{content[:500]}"
    mapping = [
        ("接警", "接警记录"),
        ("受案", "受案登记"),
        ("伤情", "伤情鉴定/送检"),
        ("鉴定", "伤情鉴定/送检"),
        ("立案决定", "立案决定书"),
        ("刑事案件登记", "刑事案件登记表"),
        ("拘留证", "拘留证"),
        ("拘留通知", "拘留通知书"),
        ("释放通知", "释放通知书"),
        ("调解", "调解处理报告书"),
        ("撤销案件", "调解处理报告书"),
        ("询问笔录", "询问笔录"),
        ("证人证言", "证人证言"),
        ("短信", "短信记录"),
        ("通话", "通话记录"),
        ("银行", "银行流水"),
        ("流水", "银行流水"),
        ("勘验", "勘验检查笔录"),
        ("履职情况专报", "履职情况专报"),
    ]
    for keyword, doc_type in mapping:
        if keyword in text:
            return doc_type
    return "未知文书"


def _infer_process_stage(doc_type: str, title: str, content: str) -> str:
    if doc_type in {"接警记录"}:
        return "接警"
    if doc_type in {"受案登记"}:
        return "受案登记"
    if doc_type == "伤情鉴定/送检":
        return "伤情鉴定/送检"
    if doc_type in {"立案决定书", "刑事案件登记表"}:
        return "立案"
    if doc_type in {"拘留证", "拘留通知书"}:
        return "强制措施"
    if doc_type == "释放通知书":
        return "释放"
    if doc_type == "调解处理报告书":
        return "调解/撤案"
    if doc_type in {"勘验检查笔录", "履职情况专报"} or any(word in f"{title}\n{content}" for word in ("火灾", "事故", "死亡", "受伤")):
        return "事故后果"
    if doc_type in {"询问笔录", "证人证言", "短信记录", "通话记录", "银行流水"}:
        return "侦查取证"
    return "未归类"


def _infer_source_quality(title: str, content: str) -> str:
    text = f"{title}\n{content[:300]}"
    if "副本" in text:
        return "copy"
    if "打印件" in text:
        return "printout"
    if "节录" in text:
        return "excerpt"
    if "复印" in text:
        return "photocopy"
    return "unknown"


def _extract_time(text: str) -> str | None:
    match = re.search(r"20\d{2}[-年/.]\d{1,2}[-月/.]\d{1,2}日?|20\d{2}年\d{1,2}月|20\d{2}-\d{1,2}-\d{1,2}", text)
    return match.group(0) if match else None


def _extract_event_time(content: str) -> str | None:
    for marker in ("案发", "报警", "发生", "时间", "交易时间", "通话时间"):
        idx = content.find(marker)
        if idx >= 0:
            found = _extract_time(content[max(0, idx - 40): idx + 120])
            if found:
                return found
    return None


def _extract_entities(content: str, extraction: ExtractionResult | None) -> list[str]:
    items: list[str] = []
    if extraction:
        for triple in extraction.triples:
            items.extend([triple.subject, triple.object])
    items.extend(re.findall(r"[\u4e00-\u9fa5]{2,4}", content[:3000]))
    stop = {"证明", "案件", "时间", "情况", "记录", "通知", "决定", "报告", "同意", "调解"}
    return [item for item in dict.fromkeys(items) if item and item not in stop][:40]


def _fallback_summary(title: str, doc_type: str, process_stage: str, content: str) -> str:
    first = re.sub(r"\s+", " ", content.strip())[:180]
    return f"{title}属于{doc_type}，对应流程阶段为{process_stage}。{first}"


def _fallback_proof_purpose(doc_type: str, process_stage: str) -> str:
    return f"用于证明案件在“{process_stage}”阶段存在相应材料或事实留痕。"


def _risk_tags(doc_type: str, process_stage: str, content: str) -> list[str]:
    tags = [process_stage, doc_type]
    if process_stage in {"释放", "调解/撤案"}:
        tags.append("程序转向材料")
    if any(word in content for word in ("批准", "同意", "指派", "安排")):
        tags.append("审批/指派节点")
    if any(word in content for word in ("请托", "收受", "转账", "现金")):
        tags.append("利益输送线索")
    return list(dict.fromkeys(tags))[:8]


def _fallback_claims(content: str, doc_type: str, process_stage: str) -> list[dict[str, str]]:
    claims = []
    for part in re.split(r"\n+|(?<=[。！？；])", content):
        text = part.strip(" -#\t")
        if len(text) >= 12:
            claims.append({"claim": text[:180], "claim_type": "fact"})
        if len(claims) >= 5:
            break
    if not claims:
        claims.append({"claim": f"该文件属于{doc_type}，对应{process_stage}阶段。", "claim_type": "procedure"})
    return claims


def _hash_text(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []

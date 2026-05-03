from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from os import getenv
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.errors import not_found
from app.schemas.common import new_id, now_utc
from app.schemas.report import ClaimPassage, PortraitClaim, PortraitReport, PortraitSection
from app.storage.memory_store import MemoryStore


class ReportService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def generate_portrait(self, case_id: str) -> PortraitReport:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")

            graph = self.store.graphs.get(case_id)
            memories = self.store.memories.get(case_id, [])
            clues = graph.clues if graph else []
            evidence = self.store.evidence.get(case_id, [])
            raw_contents = dict(self.store.raw_contents)

            basic_qa = [clue.description for clue in clues if clue.category == "basic_profile"]
            behavior_qa = [clue.description for clue in clues if clue.category == "behavior_reconstruction"]
            subjective_qa = [clue.description for clue in clues if clue.category == "subjective_reasoning"]
            fund_clues = [clue.description for clue in clues if clue.category == "fund_flow"]
            duty_clues = [clue.description for clue in clues if clue.category == "duty_behavior"]
            subjective_clues = [clue.description for clue in clues if clue.category == "subjective_state"]
            gap_clues = [clue.description for clue in clues if clue.category == "evidence_gap"]
            main_subjects = _top_entity_labels(graph) if graph else []
            behavior_modes = _behavior_mode_notes(graph)
            defenses = _defense_predictions(graph, clues)

            sections = [
                PortraitSection(
                    title="基础信息聚合",
                    items=[
                        f"**案件**：{case.title}",
                        f"**证据材料数量**：{len(evidence)}",
                        f"**当前图谱规模**：{len(graph.nodes) if graph else 0} 个节点，{len(graph.edges) if graph else 0} 条关系。",
                        f"**高频主体/对象**：{', '.join(main_subjects) if main_subjects else '待识别'}",
                        *(basic_qa or ["暂无模型生成的基础身份画像。"]),
                    ],
                ),
                PortraitSection(
                    title="行为事实还原",
                    items=[
                        *(behavior_qa or ["暂无完整行为链条，需要继续补充证据或重新运行 HippoRAG 分析。"]),
                        *(fund_clues or ["**资金链条**：暂无明确资金链条，需补充或重新导入流水材料。"]),
                        *(duty_clues or ["**职务处置链条**：暂无明确职务处置链条，需补充立案、拘留、调解、释放等程序材料。"]),
                    ],
                ),
                PortraitSection(
                    title="行为方式与反侦察迹象",
                    items=behavior_modes
                    or [
                        "暂未发现足够明确的隐瞒、规避留痕、白手套过桥、现金取存闭环或文书倒签迹象。建议继续交叉核查流水、通话、短信和文书时间。"
                    ],
                ),
                PortraitSection(
                    title="要件拆解与证据归类",
                    items=[
                        _element_line("主体要件", bool(main_subjects), "司法工作人员身份、职务权限、经办范围。"),
                        _element_line("客观行为", bool(duty_clues), "立案、拘留、调解、撤案、释放等处置链条。"),
                        _element_line("主观方面", bool(subjective_clues or subjective_qa), "明知、徇私动机、请托、利益输送。"),
                        _element_line("结果与因果", bool(gap_clues is not None and graph and graph.edges), "错误处置、逃避追诉、被害人权益受损及因果关系。"),
                    ],
                ),
                PortraitSection(
                    title="主观方面推理",
                    items=subjective_clues
                    + subjective_qa
                    or [
                        "暂未形成足够主观状态线索。应重点补强请托、明知、徇私动机、收受利益后处置方向变化等证据。"
                    ],
                ),
                PortraitSection(
                    title="缺口标红与补强方向",
                    items=gap_clues
                    or [
                        "==缺口==：建议围绕资金凭证、通话详单、短信聊天、证人证言、内部审批记录继续补强，避免仅凭关键词得出结论。"
                    ],
                ),
                PortraitSection(
                    title="抗辩预判",
                    items=defenses,
                ),
                PortraitSection(
                    title="人工确认记忆",
                    items=[record.content for record in memories if record.confirmed] or ["暂无人工确认的新事实。"],
                ),
            ]

            suggestions = [
                "按 **主体身份与职权 -> 行为事实 -> 主观明知/徇私动机 -> 结果因果** 的顺序回看证据。",
                "把资金流水、通话记录、短信笔录和程序性文书放到同一时间轴，核查是否存在“先请托、后收钱、再调解/释放”的闭合链。",
                "对别名、假名、马甲账户只输出合并建议和置信度，最终合并必须人工确认。",
                "当前报告是侦查参考，不替代人工审查、证据合法性判断和法律定性。",
            ]
            claim_sections, generation_method = _generate_grounded_claim_sections(
                case_title=case.title,
                sections=sections,
                evidence=evidence,
                raw_contents=raw_contents,
                graph=graph,
            )

            return PortraitReport(
                report_id=new_id("rpt"),
                case_id=case_id,
                generated_at=now_utc(),
                title=f"{case.title} 信息画像报告",
                sections=claim_sections,
                suggestions=suggestions,
                generation_method=generation_method,
            )


def _generate_grounded_claim_sections(
    *,
    case_title: str,
    sections: list[PortraitSection],
    evidence,
    raw_contents: dict[str, str],
    graph,
) -> tuple[list[PortraitSection], str]:
    passages = _build_evidence_passages(evidence, raw_contents)
    if settings.deepseek_analysis_enabled and getenv("DEEPSEEK_API_KEY") and passages:
        llm_claims = _try_deepseek_claims(case_title, sections, passages, graph)
        if llm_claims:
            return _attach_claims_to_sections(sections, llm_claims, passages), f"deepseek:{settings.deepseek_analysis_model}"
    fallback_claims = []
    for section in sections:
        for item in section.items:
            for sentence in _split_claim_sentences(item):
                fallback_claims.append({"section": section.title, "text": sentence, "element": section.title})
    return _attach_claims_to_sections(sections, fallback_claims, passages), "template_fallback_verified"


def _try_deepseek_claims(case_title: str, sections: list[PortraitSection], passages: list[dict[str, Any]], graph) -> list[dict[str, Any]]:
    selected_passages = passages[:80]
    legal_context = _legal_context()
    graph_summary = {
        "nodes": len(graph.nodes) if graph else 0,
        "edges": len(graph.edges) if graph else 0,
        "clues": [clue.model_dump() for clue in (graph.clues[:8] if graph else [])],
    }
    prompt = {
        "case_title": case_title,
        "task": "请基于证据片段、法律知识和办案模板，输出逐句可验证的画像分析 claim。只能输出 JSON。",
        "rules": [
            "必须使用简体中文。",
            "每条 claim 只表达一个事实、判断或证据缺口。",
            "不能编造证据。证据不足时写成待核查或需补证。",
            "重点覆盖主体要件、客观行为、主观方面、结果因果、反侦察行为、抗辩预判。",
            "每条 claim 必须给出 section、element、text、evidence_ids。",
        ],
        "legal_context": legal_context[:6000],
        "current_template_sections": [section.model_dump(exclude={"claims"}) for section in sections],
        "graph_summary": graph_summary,
        "passages": selected_passages,
        "output_schema": {
            "claims": [
                {"section": "主体要件", "element": "司法工作人员身份", "text": "一句结论", "evidence_ids": ["evd_xxx"]}
            ]
        },
    }
    body = {
        "model": settings.deepseek_analysis_model,
        "messages": [
            {"role": "system", "content": "你是检察侦查案件画像分析助手。你必须严守证据，不得输出无依据结论。"},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{settings.hipporag_llm_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {getenv('DEEPSEEK_API_KEY')}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.deepseek_analysis_timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        claims = parsed.get("claims", [])
        return claims if isinstance(claims, list) else []
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, TypeError, ValueError):
        return []


def _attach_claims_to_sections(
    sections: list[PortraitSection],
    raw_claims: list[dict[str, Any]],
    passages: list[dict[str, Any]],
) -> list[PortraitSection]:
    grouped: dict[str, list[PortraitClaim]] = {section.title: [] for section in sections}
    for raw in raw_claims:
        text = _clean_claim_text(str(raw.get("text") or ""))
        if not _is_selectable_claim_text(text):
            continue
        section_title = _match_section_title(str(raw.get("section") or ""), sections)
        claim = _verify_claim(text, section_title, str(raw.get("element") or ""), raw.get("evidence_ids") or [], passages)
        grouped.setdefault(section_title, []).append(claim)
    return [
        section.model_copy(update={"claims": grouped.get(section.title, []), "items": [claim.text for claim in grouped.get(section.title, [])] or section.items})
        for section in sections
    ]


def _verify_claim(text: str, section: str, element: str, evidence_ids: list[str], passages: list[dict[str, Any]]) -> PortraitClaim:
    candidates = [p for p in passages if not evidence_ids or p["evidence_id"] in evidence_ids]
    scored = sorted((_score_passage(text, p), p) for p in candidates)
    top = [(score, p) for score, p in reversed(scored) if score > 0][:5]
    support = [
        ClaimPassage(
            evidence_id=p["evidence_id"],
            evidence_title=p.get("evidence_title"),
            passage=p["passage"],
            score=round(score, 4),
        )
        for score, p in top
    ]
    best = support[0].score if support else 0.0
    status = "supported" if best >= 0.42 else "weak" if best >= 0.2 else "unsupported"
    note = "已找到可对应证据片段。" if status == "supported" else "证据关联较弱，需人工复核。" if status == "weak" else "未找到可靠证据片段，不能作为正式结论。"
    return PortraitClaim(
        claim_id=new_id("claim"),
        text=text,
        section=section,
        element=element or section,
        status=status,
        confidence=min(best, 0.99),
        supporting_passages=support,
        verification_notes=note,
    )


def _score_passage(claim: str, passage: dict[str, Any]) -> float:
    claim_terms = _claim_terms(claim)
    passage_text = passage["passage"]
    if not claim_terms:
        return 0.0
    hits = sum(1 for term in claim_terms if term in passage_text)
    coverage = hits / max(len(claim_terms), 1)
    important_hits = sum(1 for term in claim_terms if len(term) >= 3 and term in passage_text)
    return coverage * 0.75 + min(important_hits, 4) * 0.06


def _claim_terms(text: str) -> list[str]:
    words = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z0-9_.-]{2,}", text)
    stop = {"当前", "已经", "可能", "需要", "证据", "材料", "关系", "情况", "分析", "显示", "应当"}
    return [word for word in words if word not in stop][:16]


def _build_evidence_passages(evidence, raw_contents: dict[str, str]) -> list[dict[str, Any]]:
    titles = {item.evidence_id: item.title for item in evidence}
    rows: list[dict[str, Any]] = []
    for item in evidence:
        content = raw_contents.get(item.evidence_id, item.content_preview)
        for passage in _split_evidence_text(content):
            rows.append({"evidence_id": item.evidence_id, "evidence_title": titles[item.evidence_id], "passage": passage})
    return rows


def _split_evidence_text(content: str, limit: int = 220) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[。！？!?；;])\s*|\n+", content or "") if part.strip()]
    chunks: list[str] = []
    for part in parts:
        if len(part) <= limit:
            chunks.append(part)
        else:
            chunks.extend(part[start : start + limit] for start in range(0, len(part), limit))
    return chunks


def _split_claim_sentences(value: str) -> list[str]:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", value or "").replace("==", "")
    sentences: list[str] = []
    for part in re.split(r"(?<=[。！？!?；;])\s*|\n+", text):
        sentence = _clean_claim_text(part)
        if _is_selectable_claim_text(sentence):
            sentences.append(sentence)
    return sentences


def _clean_claim_text(value: str) -> str:
    return (
        (value or "")
        .strip()
        .lstrip("-*• \t")
        .replace("**", "")
        .replace("==", "")
        .strip(" \t\r\n\"'“”‘’")
    )


def _is_selectable_claim_text(value: str) -> bool:
    text = _clean_claim_text(value)
    label = re.sub(r"[：:]\s*$", "", text).strip()
    if len(label) < 8:
        return False
    if re.fullmatch(r"[\s*#\-•：:]+", label):
        return False
    if re.fullmatch(r"(结论|支持证据|仍需补强|证明力|身份|任职|职权|关键人员关系|案件对象|批准人|发信人|收信人|证明事项|来源文件)", label):
        return False
    if re.fullmatch(r"(证据|材料|相关证据)\s*\d*(?:-\d+)?", label):
        return False
    if re.fullmatch(r"(第一层|第二层|第三层|主体要件|客观行为|主观方面|结果与因果|抗辩预判)", label):
        return False
    return True


def _match_section_title(value: str, sections: list[PortraitSection]) -> str:
    for section in sections:
        if value and (value in section.title or section.title in value):
            return section.title
    return sections[0].title if sections else "画像分析"


def _legal_context() -> str:
    root = Path(__file__).resolve().parents[3] / "data" / "legal_knowledge"
    pieces: list[str] = []
    for path in [root / "README.md", root / "evidence_type_mapping.json", root / "offense_templates" / "xunsi_wangfa.json"]:
        if path.exists():
            pieces.append(path.read_text(encoding="utf-8", errors="ignore")[:5000])
    return "\n\n".join(pieces)


def _top_entity_labels(graph, limit: int = 8) -> list[str]:
    if not graph:
        return []
    degree: dict[str, int] = {}
    labels = {node.node_id: node.label for node in graph.nodes if node.type != "evidence" and node.type != "algorithm_provider"}
    for edge in graph.edges:
        if edge.source_id in labels:
            degree[edge.source_id] = degree.get(edge.source_id, 0) + 1
        if edge.target_id in labels:
            degree[edge.target_id] = degree.get(edge.target_id, 0) + 1
    return [labels[node_id] for node_id, _ in sorted(degree.items(), key=lambda item: item[1], reverse=True)[:limit]]


def _behavior_mode_notes(graph) -> list[str]:
    if not graph:
        return []
    notes: list[str] = []
    text_edges = " ".join(edge.relation + " " + " ".join(str(v) for v in edge.properties.values()) for edge in graph.edges)
    if any(word in text_edges for word in ["现金", "取现", "存入", "ATM"]):
        notes.append("**现金化处理**：图谱中出现取现、存入或现金相关表述，应核查是否用于切断资金流留痕。")
    if any(word in text_edges for word in ["过桥", "代持", "控制", "马甲", "假名", "别名"]):
        notes.append("**白手套/马甲账户**：出现控制、代持、马甲或别名线索，应建立真人合并建议并人工确认。")
    if any(word in text_edges for word in ["删除", "隐瞒", "倒签", "补录", "撤销", "释放"]):
        notes.append("**程序规避或留痕异常**：出现删除、隐瞒、倒签、补录、撤销、释放等词，需核查文书时间和审批链。")
    return notes


def _defense_predictions(graph, clues) -> list[str]:
    items = [
        "**认识错误抗辩**：可能主张只是业务判断或事实认识偏差。应补强其知悉伤情、案件事实、法律后果的证据。",
        "**程序瑕疵抗辩**：可能主张只是程序不规范而非徇私枉法。应证明异常处置与请托、利益输送或特定关系存在关联。",
        "**资金无关抗辩**：可能主张资金是借款、还款、投资或正常往来。应核查备注、资金来源、过桥账户、现金取存闭环与处置节点。",
        "**职责边界抗辩**：可能主张没有决定权或只是执行上级意见。应还原经办、审批、授意、协调、签批链条。",
    ]
    if graph and len(graph.edges) == 0 and not clues:
        items.append("==缺口==：当前图谱关系不足，抗辩预判只能作为模板，不能作为案件结论。")
    return items


def _element_line(title: str, passed: bool, description: str) -> str:
    status = "已有支撑" if passed else "==待补强=="
    return f"**{title}**：{status}。{description}"

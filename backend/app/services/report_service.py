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
from app.adapters.algorithm import get_algorithm_adapter
from app.schemas.common import new_id, now_utc
from app.schemas.report import ClaimPassage, PortraitClaim, PortraitReport, PortraitSection
from app.services.llm_context_debug import log_llm_context
from app.storage.memory_store import MemoryStore


class ReportService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def get_latest_portrait(self, case_id: str) -> PortraitReport:
        with self.store.lock:
            report = self.store.reports.get(case_id)
            if report:
                return report
            case = self.store.cases.get(case_id)
            title = case.title if case else case_id
            return _empty_portrait_report(case_id, title)

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
            extractions = {item.evidence_id: self.store.extractions[item.evidence_id] for item in evidence if item.evidence_id in self.store.extractions}

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
            sections = _build_clean_portrait_sections(case.title, evidence, raw_contents, graph, clues, memories)

            suggestions = [
                "按 **主体身份与职权 -> 行为事实 -> 主观明知/徇私动机 -> 结果因果** 的顺序回看证据。",
                "把资金流水、通话记录、短信笔录和程序性文书放到同一时间轴，核查是否存在“先请托、后收钱、再调解/释放”的闭合链。",
                "对别名、假名、马甲账户只输出合并建议和置信度，最终合并必须人工确认。",
                "当前报告是侦查参考，不替代人工审查、证据合法性判断和法律定性。",
            ]
            claim_sections, generation_method = _generate_grounded_claim_sections(
                case_id=case_id,
                case_title=case.title,
                sections=sections,
                evidence=evidence,
                raw_contents=raw_contents,
                extractions=extractions,
                graph=graph,
            )

            report = PortraitReport(
                report_id=new_id("rpt"),
                case_id=case_id,
                generated_at=now_utc(),
                title=f"{case.title} 信息画像报告",
                sections=claim_sections,
                suggestions=suggestions,
                generation_method=generation_method,
            )
            self.store.reports[case_id] = report
            self.store.flush_case(case_id)
            return report


def _empty_portrait_report(case_id: str, case_title: str) -> PortraitReport:
    return PortraitReport(
        report_id="rpt_pending",
        case_id=case_id,
        generated_at=now_utc(),
        title=f"{case_title} 画像报告（待生成）",
        sections=[],
        suggestions=[],
        generation_method="pending",
    )


def _build_clean_portrait_sections(case_title: str, evidence, raw_contents: dict[str, str], graph, clues, memories) -> list[PortraitSection]:
    passages = _build_evidence_passages(evidence, raw_contents)
    element_items = _build_element_analysis_items(passages)
    basic_items = [
        f"案件：{case_title}",
        f"证据材料数量：{len(evidence)}。",
        f"当前图谱规模：{len(graph.nodes) if graph else 0} 个节点，{len(graph.edges) if graph else 0} 条关系。",
        f"高频主体/对象：{', '.join(_top_entity_labels(graph)) if graph else '待识别'}。",
    ]
    return [
        PortraitSection(title="基础信息聚合", items=basic_items),
        PortraitSection(title="行为事实还原", items=_build_behavior_items(passages, clues)),
        PortraitSection(title="行为方式与反侦察迹象", items=_behavior_mode_notes(graph) or ["现有材料尚未稳定识别出反侦察操作；应继续核查现金取存、白手套账户、文书倒签补录、异常通话和证据缺失。"]),
        PortraitSection(title="要件核查结论", items=element_items),
        PortraitSection(title="主观方面推理", items=_build_subjective_items(passages, clues)),
        PortraitSection(title="缺口标红与补强方向", items=_build_gap_items(passages)),
        PortraitSection(title="抗辩预判", items=_defense_predictions(graph, clues)),
        PortraitSection(title="人工确认记忆", items=[record.content for record in memories if record.confirmed] or ["暂无人工确认的新事实。"]),
    ]


def _build_element_analysis_items(passages: list[dict[str, Any]]) -> list[str]:
    specs = [
        {
            "title": "主体要件",
            "requirement": "行为人须属于司法工作人员，且对相关刑事案件或治安案件处置具有职务权限、指派权限、审批权限或实际影响力。",
            "keywords": ["杨周武", "同乐派出所", "所长", "民警", "指派", "批准人", "责任区民警", "公安", "扫雷"],
            "positive": "可初步推断目标人员与公安机关案件处置存在职务关联。",
            "gap": "尚需明确任职文件、干部履历、岗位职责说明、案件审批权限或指派权限来源。",
            "suggestion": "调取杨周武任职文件、岗位职责、分工记录、同乐派出所层级关系及相关文书审批流。",
        },
        {
            "title": "客观行为",
            "requirement": "存在应依法追究而不追究、违法调解、撤案、释放、降格处理、隐瞒事实或改变处置方向等枉法处置行为。",
            "keywords": ["立案", "拘留", "释放", "调解", "撤销", "结案", "伤情", "鉴定", "赔偿", "刘力飚", "罗贤涛", "易承桂"],
            "positive": "材料中已经出现案件处置、调解赔偿、释放或文书办理节点，可以作为客观行为链条的入口。",
            "gap": "尚需把案发事实、伤情结论、处置决定、调解结案、释放结果按时间线闭合，避免只看到单个文书节点。",
            "suggestion": "按时间轴核对接警、鉴定、拘留、调解、撤案或结案、释放、后续追责材料是否互相矛盾。",
        },
        {
            "title": "主观方面",
            "requirement": "需要证明明知案件事实或法律后果，仍因徇私动机故意作出枉法处置；徇私动机可由请托、利益输送、亲友关系、异常联系等间接证明。",
            "keywords": ["明知", "徇私", "请托", "王静", "何晓初", "短信", "宴请", "送钱", "27万", "3万", "现金", "转账", "好处"],
            "positive": "如资金、短信、宴请、请托和案件处置节点能够前后呼应，可形成主观明知与徇私动机的间接证明链。",
            "gap": "当前仍需区分普通业务判断、程序瑕疵与明知故意；资金或请托线索必须与具体处置节点建立时间和对象对应。",
            "suggestion": "将短信、通话、银行流水、现金取存、证人证言与拘留、调解、释放、结案节点放在同一时间轴交叉验证。",
        },
        {
            "title": "结果与因果",
            "requirement": "枉法处置造成有罪人员逃避追诉、案件被错误处理、被害人权益受损或其他严重后果，并能证明结果与职务行为之间存在因果关系。",
            "keywords": ["逃避", "未追究", "释放", "解除", "赔偿", "11万", "结案", "火灾", "死亡", "受伤", "后果"],
            "positive": "如果材料显示相关人员被释放、调解结案或未被继续追究，可作为结果与因果分析的核心事实。",
            "gap": "仍需确认错误处置与未追究刑责之间的因果，而不是只证明后来发生了结果。",
            "suggestion": "补强原案应追责标准、实际处理结果、责任人员未被追究原因及后续检察机关立案材料。",
        },
    ]
    return [_format_element_item(spec, passages) for spec in specs]


def _format_element_item(spec: dict[str, Any], passages: list[dict[str, Any]]) -> str:
    supports = _find_supports(passages, spec["keywords"], limit=4)
    evidence_lines = [_support_line(item) for item in supports] or ["未找到高匹配证据片段。"]
    conclusion = f"✅ {spec['positive']}" if supports else "⚠️ 现有证据不足以形成稳定结论。"
    return "\n".join(
        [
            f"### {spec['title']}",
            f"法定要求：{spec['requirement']}",
            "当前证据：" + "；".join(evidence_lines),
            f"初步结论：{conclusion}",
            f"缺口：{spec['gap']}",
            f"建议：{spec['suggestion']}",
        ]
    )


def _build_behavior_items(passages: list[dict[str, Any]], clues) -> list[str]:
    items = []
    for title, keywords in [
        ("原案事实与处置节点", ["接警", "伤情", "鉴定", "立案", "拘留", "释放", "调解", "结案"]),
        ("请托与协调安排", ["王静", "何晓初", "请托", "刘力飚", "安排", "调解", "短信", "通话"]),
        ("资金与处置交叉", ["27万", "3万", "现金", "转账", "取现", "存入", "赔偿", "11万"]),
    ]:
        supports = _find_supports(passages, keywords, limit=3)
        if supports:
            items.append(f"{title}：" + "；".join(_support_line(item) for item in supports))
    return items or ["现有证据尚未形成完整行为链条；应优先补齐案发事实、处置文书、请托联系和资金时间线。"]


def _build_subjective_items(passages: list[dict[str, Any]], clues) -> list[str]:
    supports = _find_supports(passages, ["明知", "徇私", "请托", "短信", "送钱", "宴请", "王静", "何晓初", "刘力飚"], limit=5)
    if not supports:
        return ["主观方面尚不能直接下结论；需要从请托、异常联系、利益输送和处置方向变化之间建立间接证明链。"]
    return [
        "主观方面应采用间接证明：材料中出现的请托、短信、宴请、资金或协调安排，需要与调解、释放、结案等处置节点交叉验证。",
        "当前可用入口：" + "；".join(_support_line(item) for item in supports),
    ]


def _build_gap_items(passages: list[dict[str, Any]]) -> list[str]:
    gaps = [
        "任职与权限缺口：需要任职文件、岗位职责、审批权限、分工记录来支撑主体要件。",
        "时间线缺口：需要把接警、鉴定、拘留、请托、资金、调解、释放、立案侦查放在同一时间轴。",
        "主观证明缺口：需要证明杨周武明知案件事实和法律后果，且处置方向受到请托或利益输送影响。",
        "资金闭环缺口：现金取存、过桥账户、控制账户和处置节点之间需要形成可解释闭环。",
    ]
    if _find_supports(passages, ["任职", "批准人", "所长"], 1):
        gaps[0] = "任职与权限仍需补强：材料已有职务入口，但还缺正式任职文件、岗位职责或审批权限依据。"
    return gaps


def _find_supports(passages: list[dict[str, Any]], keywords: list[str], limit: int = 4) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in passages:
        text = item.get("passage", "")
        hits = sum(1 for word in keywords if word and word in text)
        if hits:
            scored.append((hits, item))
    scored.sort(key=lambda row: (row[0], len(row[1].get("passage", ""))), reverse=True)
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for _, item in scored:
        key = f"{item.get('evidence_id')}::{item.get('passage')}"
        if key in seen:
            continue
        seen.add(key)
        results.append(item)
        if len(results) >= limit:
            break
    return results


def _support_line(item: dict[str, Any]) -> str:
    title = item.get("evidence_title") or item.get("evidence_id") or "未命名证据"
    passage = str(item.get("passage") or "").strip()
    if len(passage) > 90:
        passage = passage[:90] + "..."
    return f"{title}：{passage}"


def _generate_grounded_claim_sections(
    *,
    case_id: str,
    case_title: str,
    sections: list[PortraitSection],
    evidence,
    raw_contents: dict[str, str],
    extractions: dict[str, Any],
    graph,
) -> tuple[list[PortraitSection], str]:
    passages, source = _select_report_passages_with_hipporag(case_id, case_title, evidence, raw_contents, extractions)
    if not passages:
        passages = _build_evidence_passages(evidence, raw_contents)
        source = "keyword_fallback"
    if settings.deepseek_analysis_enabled and getenv("DEEPSEEK_API_KEY") and passages:
        llm_claims = _try_deepseek_claims(case_title, sections, passages, graph)
        if llm_claims:
            return _attach_claims_to_sections(sections, llm_claims, passages), f"deepseek:{settings.deepseek_analysis_model}:{source}"
    fallback_claims = []
    for section in sections:
        for item in section.items:
            for sentence in _split_claim_sentences(item):
                fallback_claims.append({"section": section.title, "text": sentence, "element": section.title})
    return _attach_claims_to_sections(sections, fallback_claims, passages), f"template_fallback_verified:{source}"


def _try_deepseek_claims(case_title: str, sections: list[PortraitSection], passages: list[dict[str, Any]], graph) -> list[dict[str, Any]]:
    selected_passages = passages[:80]
    log_llm_context(
        "portrait_deepseek_claims",
        question=f"{case_title} 信息画像报告与要件核查",
        passages=selected_passages,
        extra={"model": settings.deepseek_analysis_model, "total_passages": len(passages)},
    )
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


def _select_report_passages_with_hipporag(
    case_id: str,
    case_title: str,
    evidence,
    raw_contents: dict[str, str],
    extractions: dict[str, Any],
    limit: int = 120,
) -> tuple[list[dict[str, Any]], str]:
    suspect = _guess_suspect(case_title, raw_contents)
    queries = [
        f"{suspect}的身份职务和任职单位",
        f"{suspect}与哪些人有利益往来或请托关系",
        f"{suspect}在案件中做了什么违规行为",
        f"{suspect}是否接受贿赂或好处",
        f"{suspect}是否明知应追究刑事责任而不追究",
        f"{suspect}的行为导致了什么后果",
        f"{case_title} 完整时间线 接警 鉴定 拘留 请托 资金 调解 释放 立案侦查",
        f"{case_title} 8月12日 8月16日 8月19日 8月21日 9月6日 9月20日 9月28日",
        f"{case_title} 火灾 死亡 受伤 事故调查 履职情况专报 严重后果",
        f"{case_title} 立案决定书 检察院 犯罪嫌疑人 涉嫌罪名",
        "案件中是否存在隐瞒规避、白手套、现金取存、倒签补录或反侦察行为",
    ]
    adapter = get_algorithm_adapter()
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    errors: list[str] = []
    for query in queries:
        passages, error = adapter.retrieve_trace(
            case_id=case_id,
            query=query,
            evidence=evidence,
            raw_contents=raw_contents,
            extractions=extractions,
            top_k=12,
        )
        if error:
            errors.append(error)
            continue
        for item in passages:
            if _is_raw_structured_passage({"evidence_title": item.evidence_title, "passage": item.passage}):
                continue
            key = f"{item.evidence_id}::{item.passage}"
            if key in seen:
                continue
            seen.add(key)
            selected.append(
                {
                    "evidence_id": item.evidence_id,
                    "evidence_title": item.evidence_title,
                    "passage": item.passage,
                    "score": item.score,
                    "query": query,
                }
            )
            if len(selected) >= limit:
                break
        if len(selected) >= limit:
            break
    log_llm_context(
        "portrait_hipporag_retrieved_passages",
        question=f"{case_title} / {suspect} / portrait passage selection",
        passages=selected,
        extra={"queries": queries, "errors": errors[:5], "selected": len(selected)},
    )
    return selected, "hipporag_retrieval" if selected else "hipporag_empty"


def _guess_suspect(case_title: str, raw_contents: dict[str, str]) -> str:
    if "杨周武" in case_title:
        return "杨周武"
    corpus = "\n".join(raw_contents.values())[:20000]
    match = re.search(r"([\u4e00-\u9fa5]{2,4})(?:徇私枉法|涉嫌|被告人|犯罪嫌疑人)", f"{case_title}\n{corpus}")
    return match.group(1) if match else "目标人员"


def _select_report_passages(passages: list[dict[str, Any]], limit: int = 80) -> list[dict[str, Any]]:
    priority = [
        "杨周武", "同乐派出所", "王静", "何晓初", "刘力飚", "立案", "拘留", "释放", "调解", "撤销", "结案",
        "徇私", "明知", "请托", "短信", "通话", "27万", "3万", "11万", "现金", "转账", "取现", "存入",
        "伤情", "鉴定", "火灾", "检察院", "立案侦查",
    ]
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, item in enumerate(passages):
        text = f"{item.get('evidence_title') or ''}\n{item.get('passage') or ''}"
        score = sum(1 for word in priority if word in text)
        scored.append((score, -index, item))
    ranked = [item for score, _, item in sorted(scored, reverse=True) if score > 0]
    ranked.extend(item for _, _, item in scored if item not in ranked)
    selected: list[dict[str, Any]] = []
    per_evidence: dict[str, int] = {}
    for item in ranked:
        evidence_id = str(item.get("evidence_id") or "")
        if per_evidence.get(evidence_id, 0) >= 5:
            continue
        selected.append(item)
        per_evidence[evidence_id] = per_evidence.get(evidence_id, 0) + 1
        if len(selected) >= limit:
            break
    return selected


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
    candidates = [p for p in passages if (not evidence_ids or p.get("evidence_id") in evidence_ids) and not _is_raw_structured_passage(p)]
    scored = sorted(
        ((_score_passage(text, p), index, p) for index, p in enumerate(candidates)),
        key=lambda item: (item[0], -item[1]),
        reverse=True,
    )
    top = [(score, p) for score, _, p in scored if score > 0][:5]
    support = [
        ClaimPassage(
            evidence_id=p.get("evidence_id") or "",
            evidence_title=p.get("evidence_title"),
            passage=p.get("passage") or "",
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
    if _is_raw_structured_passage(passage):
        return 0.0
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
    if _looks_like_raw_structured_text(label):
        return False
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


def _is_raw_structured_passage(item: dict[str, Any]) -> bool:
    return _looks_like_raw_structured_text(f"{item.get('evidence_title') or ''}\n{item.get('passage') or ''}")


def _looks_like_raw_structured_text(text: str) -> bool:
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return False
    if normalized.count(",") >= 5:
        return True
    markers = ("structured/", "synthetic/", ".csv", ".xlsx", "CALL00", "FLOW", "cdr.csv")
    return sum(1 for marker in markers if marker in normalized) >= 2


def _match_section_title(value: str, sections: list[PortraitSection]) -> str:
    if value and any(token in value for token in ["主体要件", "客观行为", "主观方面", "结果因果", "结果与因果", "要件"]):
        target = next((section.title for section in sections if "要件" in section.title), None)
        if target:
            return target
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

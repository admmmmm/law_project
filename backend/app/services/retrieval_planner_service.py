from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from os import getenv
from typing import Any

from app.adapters.algorithm import AlgorithmAdapter
from app.core.config import settings
from app.schemas.analysis import RetrievalSession, RetrievalSessionDetail, RetrievalStep, RetrievalToolCall, TracePassage
from app.services.analysis_skill_service import AnalysisSkillService
from app.services.document_mother_service import DocumentMotherService
from app.schemas.common import new_id, now_utc
from app.services.legal_knowledge_service import LegalKnowledgeService
from app.storage.memory_store import MemoryStore


class RetrievalPlannerService:
    def __init__(self, store: MemoryStore, algorithm: AlgorithmAdapter, legal_knowledge: LegalKnowledgeService | None = None) -> None:
        self.store = store
        self.algorithm = algorithm
        self.legal_knowledge = legal_knowledge or LegalKnowledgeService()

    def get_session_detail(self, case_id: str, session_id: str) -> RetrievalSessionDetail | None:
        with self.store.lock:
            session = next((item for item in self.store.retrieval_sessions.get(case_id, []) if item.session_id == session_id), None)
            if not session:
                return None
            steps = [item for item in self.store.retrieval_steps.get(case_id, []) if item.session_id == session_id]
        return RetrievalSessionDetail(session=session, steps=steps)

    def run(
        self,
        *,
        case_id: str,
        mode: str,
        question: str,
        case_title: str,
        offense_id: str | None,
        evidence: list[Any],
        raw_contents: dict[str, str],
        extractions: dict[str, Any],
        graph: Any,
        forced_evidence_ids: list[str] | None = None,
        initial_goals: list[str] | None = None,
    ) -> RetrievalSessionDetail:
        forced_evidence_ids = forced_evidence_ids or []
        now = now_utc()
        session = RetrievalSession(
            session_id=new_id("rsess"),
            case_id=case_id,
            mode=mode,
            question=question,
            planner_model=settings.deepseek_planner_model,
            analysis_model=settings.deepseek_analysis_model,
            created_at=now,
            updated_at=now,
        )
        with self.store.lock:
            self.store.retrieval_sessions.setdefault(case_id, []).append(session)
            self.store.retrieval_steps.setdefault(case_id, [])
            self.store.flush_case(case_id)

        artifacts_seen: set[str] = set()
        previous_summary = ""
        unresolved_gaps = _initial_gaps(mode, question, initial_goals)
        no_new_rounds = 0
        steps: list[RetrievalStep] = []

        for round_index in range(1, max(settings.agentic_rag_max_rounds, 1) + 1):
            plan = self._plan_next_round(
                case_title=case_title,
                mode=mode,
                question=question,
                graph=graph,
                evidence=evidence,
                previous_summary=previous_summary,
                unresolved_gaps=unresolved_gaps,
                forced_evidence_ids=forced_evidence_ids if round_index == 1 else [],
                initial_goals=initial_goals or [],
            )
            tool_specs = _sanitize_tool_specs(plan.get("tool_calls"), mode, question, forced_evidence_ids if round_index == 1 else [])
            tool_calls: list[RetrievalToolCall] = []
            new_count = 0
            for spec in tool_specs[: max(settings.agentic_rag_max_tool_calls_per_round, 1)]:
                call = self._execute_tool(
                    case_id=case_id,
                    spec=spec,
                    evidence=evidence,
                    raw_contents=raw_contents,
                    extractions=extractions,
                    graph=graph,
                    offense_id=offense_id,
                )
                tool_calls.append(call)
                for key in _artifact_keys(call):
                    if key not in artifacts_seen:
                        artifacts_seen.add(key)
                        new_count += 1

            if new_count == 0:
                no_new_rounds += 1
            else:
                no_new_rounds = 0

            evaluation = self._evaluate_round(
                case_title=case_title,
                mode=mode,
                question=question,
                planned_goals=[str(item) for item in _safe_list(plan.get("retrieval_goals"))],
                tool_calls=tool_calls,
                previous_summary=previous_summary,
                unresolved_gaps=unresolved_gaps,
            )
            coverage_summary = _compact_summary(str(evaluation.get("coverage_summary") or _summarize_tool_calls(tool_calls)), 360)
            unresolved_gaps = [str(item)[:120] for item in _safe_list(evaluation.get("unresolved_gaps")) if str(item).strip()]
            ready = bool(evaluation.get("ready_to_answer")) or no_new_rounds >= 1
            step = RetrievalStep(
                step_id=new_id("rstep"),
                session_id=session.session_id,
                round_index=round_index,
                retrieval_goals=[str(item)[:120] for item in _safe_list(plan.get("retrieval_goals")) if str(item).strip()],
                tool_calls=tool_calls,
                coverage_summary=coverage_summary,
                unresolved_gaps=unresolved_gaps,
                ready_to_answer=ready,
                created_at=now_utc(),
            )
            steps.append(step)
            previous_summary = _compact_summary("\n".join([previous_summary, coverage_summary, _summarize_tool_calls(tool_calls)]), 1200)
            with self.store.lock:
                self.store.retrieval_steps.setdefault(case_id, []).append(step)
                session = session.model_copy(update={
                    "updated_at": now_utc(),
                    "retrieval_steps_count": len(steps),
                    "tool_call_summary": _tool_call_summary(steps),
                    "status": "completed" if ready else "running",
                })
                _replace_session(self.store, case_id, session)
                self.store.flush_case(case_id)
            if ready:
                break

        if not steps:
            step = RetrievalStep(
                step_id=new_id("rstep"),
                session_id=session.session_id,
                round_index=1,
                retrieval_goals=initial_goals or [question],
                tool_calls=[],
                coverage_summary="未能生成检索计划。",
                unresolved_gaps=["planner 未返回可执行工具调用。"],
                ready_to_answer=True,
                created_at=now_utc(),
            )
            steps.append(step)
            with self.store.lock:
                self.store.retrieval_steps.setdefault(case_id, []).append(step)

        final_session = session.model_copy(update={
            "status": "completed",
            "updated_at": now_utc(),
            "retrieval_steps_count": len(steps),
            "tool_call_summary": _tool_call_summary(steps),
        })
        with self.store.lock:
            _replace_session(self.store, case_id, final_session)
            self.store.flush_case(case_id)
        return RetrievalSessionDetail(session=final_session, steps=steps)

    def _plan_next_round(
        self,
        *,
        case_title: str,
        mode: str,
        question: str,
        graph: Any,
        evidence: list[Any],
        previous_summary: str,
        unresolved_gaps: list[str],
        forced_evidence_ids: list[str],
        initial_goals: list[str],
    ) -> dict[str, Any]:
        fallback = _fallback_plan(mode, question, unresolved_gaps, forced_evidence_ids, initial_goals)
        api_key = getenv("DEEPSEEK_API_KEY")
        if not settings.deepseek_analysis_enabled or not api_key:
            return fallback
        prompt = {
            "case_title": case_title,
            "mode": mode,
            "question": question,
            "available_tools": _tool_descriptions(),
            "graph_summary": _graph_summary(graph),
            "evidence_titles": [{"evidence_id": item.evidence_id, "title": item.title} for item in evidence[:80]],
            "previous_summary": previous_summary,
            "unresolved_gaps": unresolved_gaps,
            "forced_evidence_ids": forced_evidence_ids,
            "initial_goals": initial_goals,
            "rules": [
                "必须输出 JSON object。",
                "只允许调用 search_documents、search_graph、expand_node、search_time_range、search_legal。",
                "也可以调用 list_rule_packs、run_rule_pack、get_document_mother_graph、find_documents_by_stage、find_documents_by_type。",
                "每轮最多 5 个工具调用。",
                "如果 forced_evidence_ids 非空，第一轮必须至少调用一次 search_documents，并在 query 中说明指定证据。",
                "不要输出隐藏推理，只输出检索目标、工具调用、覆盖摘要、缺口和是否可以回答。",
            ],
            "output_schema": {
                "retrieval_goals": ["本轮检索目标"],
                "tool_calls": [{"tool_name": "search_documents", "arguments": {"query": "检索词", "top_k": 8}}],
                "coverage_summary": "本轮希望覆盖什么",
                "unresolved_gaps": ["仍缺什么"],
                "ready_to_answer": False,
            },
        }
        body = {
            "model": settings.deepseek_planner_model,
            "messages": [
                {"role": "system", "content": "你是检察案件 RAG 检索计划器，只输出可执行 JSON，不输出分析正文。"},
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
                return fallback
            if not parsed.get("tool_calls"):
                parsed["tool_calls"] = fallback["tool_calls"]
            return parsed
        except Exception:
            return fallback

    def _evaluate_round(
        self,
        *,
        case_title: str,
        mode: str,
        question: str,
        planned_goals: list[str],
        tool_calls: list[RetrievalToolCall],
        previous_summary: str,
        unresolved_gaps: list[str],
    ) -> dict[str, Any]:
        fallback = _fallback_evaluation(tool_calls, unresolved_gaps)
        api_key = getenv("DEEPSEEK_API_KEY")
        if not settings.deepseek_analysis_enabled or not api_key:
            return fallback
        prompt = {
            "case_title": case_title,
            "mode": mode,
            "question": question,
            "planned_goals": planned_goals,
            "previous_summary": previous_summary,
            "previous_unresolved_gaps": unresolved_gaps,
            "tool_results": [_tool_result_for_model(call) for call in tool_calls],
            "rules": [
                "必须输出 JSON object。",
                "你只评估检索结果，不写最终分析正文。",
                "判断当前结果是否足以回答问题；如果不足，给出下一轮应检索的具体缺口。",
                "缺口要能被下一轮工具调用使用，例如具体人物、时间、文件、资金节点、法律要件。",
                "不要输出隐藏推理，只输出覆盖摘要、未解决缺口和 ready_to_answer。",
            ],
            "output_schema": {
                "coverage_summary": "本轮工具结果实际覆盖了哪些事实或规则",
                "unresolved_gaps": ["仍缺什么，下一轮应查什么"],
                "ready_to_answer": False,
            },
        }
        body = {
            "model": settings.deepseek_planner_model,
            "messages": [
                {"role": "system", "content": "你是检察案件 RAG 检索评估器，只输出 JSON。"},
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
            return parsed if isinstance(parsed, dict) else fallback
        except Exception:
            return fallback

    def _execute_tool(
        self,
        *,
        case_id: str,
        spec: dict[str, Any],
        evidence: list[Any],
        raw_contents: dict[str, str],
        extractions: dict[str, Any],
        graph: Any,
        offense_id: str | None,
    ) -> RetrievalToolCall:
        tool_name = str(spec.get("tool_name") or spec.get("name") or "")
        args = spec.get("arguments") if isinstance(spec.get("arguments"), dict) else {}
        call = RetrievalToolCall(tool_call_id=new_id("tcall"), tool_name=tool_name, arguments=_jsonable_args(args))
        try:
            if tool_name == "search_documents":
                query = str(args.get("query") or "")
                top_k = _bounded_int(args.get("top_k"), 8, 1, 12)
                passages, error = self.algorithm.retrieve_trace(case_id, query, evidence, raw_contents, extractions, top_k=top_k)
                call.passages = passages
                call.document_groups = _aggregate_passages_by_document(self.store, case_id, passages)
                call.summary = f"文档检索「{query}」返回 {len(passages)} 条 passage。"
                if error:
                    call.errors.append(error)
            elif tool_name == "search_graph":
                query = str(args.get("query") or "")
                k = _bounded_int(args.get("k"), 20, 1, 60)
                call.graph_facts = _search_graph(graph, query, k)
                call.summary = f"图谱检索「{query}」返回 {len(call.graph_facts)} 条关系。"
            elif tool_name == "expand_node":
                label = str(args.get("node_label") or args.get("label") or "")
                depth = _bounded_int(args.get("depth"), 2, 1, 3)
                relation_filter = str(args.get("relation_filter") or "")
                call.graph_facts = _expand_node(graph, label, depth, relation_filter, 60)
                call.summary = f"节点扩展「{label}」返回 {len(call.graph_facts)} 条关系。"
            elif tool_name == "search_time_range":
                start = str(args.get("start") or "")
                end = str(args.get("end") or "")
                keywords = [str(item) for item in _safe_list(args.get("keywords"))]
                call.graph_facts = _search_time_range(graph, start, end, keywords, 50)
                call.summary = f"时间范围检索 {start or '起点不限'} 至 {end or '终点不限'} 返回 {len(call.graph_facts)} 条关系。"
            elif tool_name == "search_legal":
                query = str(args.get("query") or "")
                top_k = _bounded_int(args.get("top_k"), 6, 1, 10)
                result = self.legal_knowledge.retrieve(query=query, offense_id=offense_id, top_k=top_k)
                call.legal_passages = result.passages
                call.summary = f"法律知识检索「{query}」返回 {len(result.passages)} 条。"
                if result.error:
                    call.errors.append(result.error)
            elif tool_name == "list_rule_packs":
                service = AnalysisSkillService(self.store)
                packs = service.list_rule_packs()
                call.document_groups = [item.model_dump() for item in packs]
                call.summary = f"列出 {len(packs)} 个规则包。"
            elif tool_name == "run_rule_pack":
                pack_name = str(args.get("pack_name") or args.get("rule_pack") or "")
                if not pack_name:
                    call.errors.append("缺少 pack_name")
                else:
                    result = AnalysisSkillService(self.store).run_rule_pack(case_id, pack_name)
                    call.rule_findings = result.findings
                    call.document_groups = [{"not_triggered": [item.model_dump() for item in result.not_triggered], "data_gaps": result.data_gaps}]
                    call.summary = f"规则包「{pack_name}」命中 {len(result.findings)} 条 finding，未命中 {len(result.not_triggered)} 条。"
            elif tool_name == "get_document_mother_graph":
                graph_result = DocumentMotherService(self.store).get_graph(case_id)
                if not graph_result.nodes:
                    graph_result = DocumentMotherService(self.store).rebuild(case_id)
                call.document_groups = [_doc_group(node) for node in graph_result.nodes[:40]]
                call.summary = f"读取文件母图 {len(graph_result.nodes)} 个文件节点。"
            elif tool_name == "find_documents_by_stage":
                stage = str(args.get("process_stage") or args.get("stage") or "")
                nodes = DocumentMotherService(self.store).get_graph(case_id).nodes
                rows = [node for node in nodes if stage in node.process_stage or node.process_stage in stage]
                call.document_groups = [_doc_group(node) for node in rows[:30]]
                call.summary = f"按流程阶段「{stage}」找到 {len(rows)} 个文件节点。"
            elif tool_name == "find_documents_by_type":
                doc_type = str(args.get("doc_type") or args.get("type") or "")
                nodes = DocumentMotherService(self.store).get_graph(case_id).nodes
                rows = [node for node in nodes if doc_type in node.doc_type or node.doc_type in doc_type]
                call.document_groups = [_doc_group(node) for node in rows[:30]]
                call.summary = f"按文书类型「{doc_type}」找到 {len(rows)} 个文件节点。"
            else:
                call.errors.append(f"未知工具：{tool_name}")
        except Exception as exc:  # noqa: BLE001
            call.errors.append(str(exc))
        call.new_entities = _extract_entities_from_call(call)[:20]
        return call


def collect_session_artifacts(detail: RetrievalSessionDetail) -> tuple[list[TracePassage], list[str], list[TracePassage]]:
    passages_by_key: dict[str, TracePassage] = {}
    graph_facts: list[str] = []
    legal_by_key: dict[str, TracePassage] = {}
    for step in detail.steps:
        for call in step.tool_calls:
            for passage in call.passages:
                key = f"{passage.evidence_id}::{passage.passage}"
                current = passages_by_key.get(key)
                if current is None or passage.score > current.score:
                    passages_by_key[key] = passage
            for fact in call.graph_facts:
                if fact not in graph_facts:
                    graph_facts.append(fact)
            for finding in call.rule_findings:
                text = f"规则Finding：{finding.title}；严重度：{finding.severity}；原因：{finding.reason}；缺失材料：{'、'.join(finding.missing_documents)}"
                if text not in graph_facts:
                    graph_facts.append(text)
            for group in call.document_groups:
                if isinstance(group, dict) and group.get("doc_id"):
                    text = f"文件母图：{group.get('doc_id')}；阶段：{group.get('process_stage')}；证明事项：{group.get('proof_purpose')}；摘要：{group.get('document_summary')}"
                    if text not in graph_facts:
                        graph_facts.append(text)
            for passage in call.legal_passages:
                key = f"{passage.evidence_title}::{passage.passage}"
                current = legal_by_key.get(key)
                if current is None or passage.score > current.score:
                    legal_by_key[key] = passage
    passages = sorted(passages_by_key.values(), key=lambda item: item.score, reverse=True)[:40]
    return passages, graph_facts[:80], sorted(legal_by_key.values(), key=lambda item: item.score, reverse=True)[:10]


def _tool_descriptions() -> list[dict[str, Any]]:
    return [
        {"name": "search_documents", "purpose": "HippoRAG PPR 检索案件证据 passage", "args": ["query", "top_k"]},
        {"name": "search_graph", "purpose": "按关键词搜索图谱节点/边", "args": ["query", "k"]},
        {"name": "expand_node", "purpose": "从节点出发扩展局部子图", "args": ["node_label", "depth", "relation_filter"]},
        {"name": "search_time_range", "purpose": "按时间范围搜索图谱边和事件", "args": ["start", "end", "keywords"]},
        {"name": "search_legal", "purpose": "检索法律知识库与罪名模板", "args": ["query", "top_k"]},
        {"name": "list_rule_packs", "purpose": "列出可用检察分析规则包", "args": []},
        {"name": "run_rule_pack", "purpose": "运行规则包并返回 findings/not_triggered/data_gaps", "args": ["pack_name"]},
        {"name": "get_document_mother_graph", "purpose": "读取案件文件母图摘要", "args": []},
        {"name": "find_documents_by_stage", "purpose": "按流程阶段读取文件母图节点", "args": ["process_stage"]},
        {"name": "find_documents_by_type", "purpose": "按文书类型读取文件母图节点", "args": ["doc_type"]},
    ]


def _fallback_plan(mode: str, question: str, gaps: list[str], forced_ids: list[str], goals: list[str]) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    if forced_ids:
        calls.append({"tool_name": "search_documents", "arguments": {"query": f"指定证据 {' '.join(forced_ids)} {question}", "top_k": 8}})
    calls.append({"tool_name": "search_documents", "arguments": {"query": question, "top_k": 8}})
    if mode == "financial_flow":
        calls.extend([
            {"tool_name": "search_documents", "arguments": {"query": f"{question} 资金流水 转账 取现 存入 现金 过桥账户", "top_k": 8}},
            {"tool_name": "search_graph", "arguments": {"query": "资金 转账 现金 账户 赔偿", "k": 30}},
            {"tool_name": "expand_node", "arguments": {"node_label": _guess_node_from_question(question), "depth": 2, "relation_filter": "转账"}},
        ])
    elif mode.startswith("portrait"):
        calls.extend([
            {"tool_name": "get_document_mother_graph", "arguments": {}},
            {"tool_name": "run_rule_pack", "arguments": {"pack_name": "process_turning_point"}},
            {"tool_name": "search_documents", "arguments": {"query": "立案决定书 犯罪嫌疑人 案件事实 人物关系", "top_k": 8}},
            {"tool_name": "search_documents", "arguments": {"query": "时间线 行为事实 处置结果 后果 事故 调查", "top_k": 8}},
            {"tool_name": "search_graph", "arguments": {"query": "请托 指派 调解 释放 立案 资金 通话", "k": 40}},
        ])
    else:
        calls.extend([
            {"tool_name": "list_rule_packs", "arguments": {}},
            {"tool_name": "run_rule_pack", "arguments": {"pack_name": "document_completeness"}},
            {"tool_name": "search_graph", "arguments": {"query": question, "k": 30}},
            {"tool_name": "search_documents", "arguments": {"query": f"{question} 反向证据 证据缺口", "top_k": 8}},
        ])
    return {
        "retrieval_goals": goals or gaps or [question],
        "tool_calls": calls[: max(settings.agentic_rag_max_tool_calls_per_round, 1)],
        "coverage_summary": "使用确定性后备计划覆盖文档、图谱和法律知识。",
        "unresolved_gaps": gaps[:4] or ["需要根据召回结果判断是否还有事实缺口。"],
        "ready_to_answer": False,
    }


def _fallback_evaluation(calls: list[RetrievalToolCall], gaps: list[str]) -> dict[str, Any]:
    total = sum(len(call.passages) + len(call.graph_facts) + len(call.legal_passages) for call in calls)
    errors = [error for call in calls for error in call.errors]
    next_gaps = gaps[:4]
    if total == 0:
        next_gaps = next_gaps or ["本轮未召回有效材料，需要换更具体的人名、时间、文件标题或关系词继续检索。"]
    elif not next_gaps:
        next_gaps = ["需要核查召回材料之间是否能形成完整事实链。"]
    return {
        "coverage_summary": _summarize_tool_calls(calls) or "本轮没有可用工具结果。",
        "unresolved_gaps": next_gaps,
        "ready_to_answer": total >= 8 and not errors,
    }


def _sanitize_tool_specs(raw: Any, mode: str, question: str, forced_ids: list[str]) -> list[dict[str, Any]]:
    specs = [item for item in _safe_list(raw) if isinstance(item, dict)]
    allowed = {"search_documents", "search_graph", "expand_node", "search_time_range", "search_legal", "list_rule_packs", "run_rule_pack", "get_document_mother_graph", "find_documents_by_stage", "find_documents_by_type"}
    cleaned = []
    for item in specs:
        name = str(item.get("tool_name") or item.get("name") or "")
        if name not in allowed:
            continue
        args = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
        cleaned.append({"tool_name": name, "arguments": args})
    if not cleaned:
        cleaned = _fallback_plan(mode, question, [], forced_ids, [])["tool_calls"]
    if forced_ids and not any(item["tool_name"] == "search_documents" for item in cleaned):
        cleaned.insert(0, {"tool_name": "search_documents", "arguments": {"query": f"指定证据 {' '.join(forced_ids)} {question}", "top_k": 8}})
    return cleaned


def _tool_result_for_model(call: RetrievalToolCall) -> dict[str, Any]:
    return {
        "tool_call_id": call.tool_call_id,
        "tool_name": call.tool_name,
        "arguments": call.arguments,
        "summary": call.summary,
        "errors": call.errors[:3],
        "passages": [
            {
                "rank": index + 1,
                "score": round(float(item.score), 4),
                "title": item.evidence_title,
                "text": _compact_summary(item.passage, 220),
            }
            for index, item in enumerate(call.passages[:5])
        ],
        "graph_facts": [_compact_summary(item, 160) for item in call.graph_facts[:8]],
        "legal_passages": [
            {
                "rank": index + 1,
                "title": item.evidence_title,
                "text": _compact_summary(item.passage, 180),
            }
            for index, item in enumerate(call.legal_passages[:4])
        ],
        "rule_findings": [
            {
                "title": item.title,
                "severity": item.severity,
                "reason": _compact_summary(item.reason, 180),
                "missing_documents": item.missing_documents,
                "next_actions": item.next_actions[:4],
            }
            for item in call.rule_findings[:6]
        ],
        "document_groups": call.document_groups[:8],
    }


def _search_graph(graph: Any, query: str, limit: int) -> list[str]:
    if not graph:
        return []
    labels = {node.node_id: node.label for node in graph.nodes}
    terms = [term for term in re.split(r"[\s，。；、,;]+", query) if len(term) >= 2]
    rows: list[tuple[int, str]] = []
    for edge in graph.edges:
        text = _edge_text(edge, labels)
        score = sum(1 for term in terms if term in text)
        if score > 0 or not terms:
            rows.append((score, text))
    rows.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [text for _, text in rows[:limit]]


def _expand_node(graph: Any, label: str, depth: int, relation_filter: str, limit: int) -> list[str]:
    if not graph or not label:
        return []
    labels = {node.node_id: node.label for node in graph.nodes}
    start_ids = {node.node_id for node in graph.nodes if label in node.label or node.label in label}
    if not start_ids:
        return []
    frontier = set(start_ids)
    visited = set(start_ids)
    results: list[str] = []
    for _ in range(depth):
        next_frontier: set[str] = set()
        for edge in graph.edges:
            if relation_filter and relation_filter not in edge.relation:
                continue
            if edge.source_id in frontier or edge.target_id in frontier:
                text = _edge_text(edge, labels)
                if text not in results:
                    results.append(text)
                other = edge.target_id if edge.source_id in frontier else edge.source_id
                if other not in visited:
                    next_frontier.add(other)
                    visited.add(other)
            if len(results) >= limit:
                return results
        frontier = next_frontier
        if not frontier:
            break
    return results


def _search_time_range(graph: Any, start: str, end: str, keywords: list[str], limit: int) -> list[str]:
    if not graph:
        return []
    labels = {node.node_id: node.label for node in graph.nodes}
    rows: list[str] = []
    start_key = _date_key(start)
    end_key = _date_key(end)
    for edge in graph.edges:
        text = _edge_text(edge, labels)
        times = [edge.timestamp, *edge.time_range, str(edge.properties.get("time") or ""), str(edge.properties.get("time_sample") or "")]
        time_keys = [_date_key(item) for item in times if item]
        in_range = not start_key and not end_key
        for key in time_keys:
            if key and (not start_key or key >= start_key) and (not end_key or key <= end_key):
                in_range = True
                break
        if not in_range:
            continue
        if keywords and not any(word and word in text for word in keywords):
            continue
        rows.append(text)
        if len(rows) >= limit:
            break
    return rows


def _edge_text(edge: Any, labels: dict[str, str]) -> str:
    source = labels.get(edge.source_id, edge.source_id)
    target = labels.get(edge.target_id, edge.target_id)
    time = edge.timestamp or edge.properties.get("time") or edge.properties.get("time_sample") or ""
    amount = edge.properties.get("amount") or edge.properties.get("amount_total") or ""
    suffix = "，".join(str(value) for value in [f"时间 {time}" if time else "", f"金额 {amount}" if amount else ""] if value)
    return f"{source} --{edge.relation}--> {target}" + (f"（{suffix}）" if suffix else "")


def _graph_summary(graph: Any) -> dict[str, Any]:
    if not graph:
        return {"nodes": 0, "edges": 0}
    type_counts: dict[str, int] = {}
    for node in graph.nodes:
        type_counts[node.type] = type_counts.get(node.type, 0) + 1
    return {"nodes": len(graph.nodes), "edges": len(graph.edges), "node_types": type_counts}


def _replace_session(store: MemoryStore, case_id: str, session: RetrievalSession) -> None:
    sessions = store.retrieval_sessions.setdefault(case_id, [])
    for idx, item in enumerate(sessions):
        if item.session_id == session.session_id:
            sessions[idx] = session
            return
    sessions.append(session)


def _artifact_keys(call: RetrievalToolCall) -> list[str]:
    keys = []
    keys.extend(f"p::{item.evidence_id}::{item.passage}" for item in call.passages)
    keys.extend(f"g::{item}" for item in call.graph_facts)
    keys.extend(f"l::{item.evidence_title}::{item.passage}" for item in call.legal_passages)
    keys.extend(f"f::{item.finding_id}" for item in call.rule_findings)
    keys.extend(f"d::{item.get('doc_id') or item.get('name') or item}" for item in call.document_groups)
    return keys


def _tool_call_summary(steps: list[RetrievalStep]) -> str:
    counts: dict[str, int] = {}
    for step in steps:
        for call in step.tool_calls:
            counts[call.tool_name] = counts.get(call.tool_name, 0) + 1
    label_map = {
        "search_documents": "文档检索",
        "search_graph": "图谱检索",
        "expand_node": "节点扩展",
        "search_time_range": "时间检索",
        "search_legal": "法律知识",
        "list_rule_packs": "规则包列表",
        "run_rule_pack": "规则包运行",
        "get_document_mother_graph": "文件母图",
        "find_documents_by_stage": "阶段文件",
        "find_documents_by_type": "类型文件",
    }
    parts = [f"{label_map.get(name, name)} {count} 次" for name, count in counts.items()]
    return f"本轮经过 {len(steps)} 轮检索，调用" + "、".join(parts) + "。" if parts else f"本轮经过 {len(steps)} 轮检索。"


def _summarize_tool_calls(calls: list[RetrievalToolCall]) -> str:
    return "\n".join(_compact_summary(call.summary, 120) for call in calls)


def _extract_entities_from_call(call: RetrievalToolCall) -> list[str]:
    text = "\n".join([*(p.passage for p in call.passages), *call.graph_facts, *(p.passage for p in call.legal_passages), *(f.title for f in call.rule_findings), *(json.dumps(d, ensure_ascii=False) for d in call.document_groups)])
    return list(dict.fromkeys(re.findall(r"[\u4e00-\u9fa5]{2,4}", text)))


def _doc_group(node: Any) -> dict[str, Any]:
    verified_claims = [claim for claim in node.key_claims if claim.status == "verified"]
    return {
        "doc_id": node.doc_id,
        "evidence_id": node.evidence_id,
        "title": node.title,
        "document_summary": node.summary,
        "proof_purpose": node.proof_purpose,
        "process_stage": node.process_stage,
        "risk_tags": node.risk_tags,
        "matched_claims": [claim.model_dump() for claim in verified_claims[:6]],
    }


def _aggregate_passages_by_document(store: MemoryStore, case_id: str, passages: list[TracePassage]) -> list[dict[str, Any]]:
    with store.lock:
        nodes = list(store.document_mother_nodes.get(case_id, []))
    by_evidence = {node.evidence_id: node for node in nodes}
    grouped: dict[str, dict[str, Any]] = {}
    for passage in passages:
        node = by_evidence.get(str(passage.evidence_id or ""))
        key = node.doc_id if node else str(passage.evidence_id or passage.evidence_title or "unknown")
        row = grouped.setdefault(
            key,
            {
                "doc_id": key,
                "evidence_id": passage.evidence_id,
                "title": node.title if node else passage.evidence_title,
                "document_summary": node.summary if node else "",
                "proof_purpose": node.proof_purpose if node else "",
                "process_stage": node.process_stage if node else "",
                "risk_tags": node.risk_tags if node else [],
                "matched_passages": [],
                "matched_claims": [],
            },
        )
        row["matched_passages"].append({"rank": passage.rank, "text": passage.passage[:500], "score": passage.score})
        if node:
            row["matched_claims"] = [claim.model_dump() for claim in node.key_claims if claim.status == "verified"][:6]
    return list(grouped.values())[:12]


def _initial_gaps(mode: str, question: str, goals: list[str] | None) -> list[str]:
    if goals:
        return goals
    if mode == "portrait":
        return ["人物关系", "行为事实", "时间线", "结果后果", "关键证据缺口"]
    if mode == "financial_flow":
        return ["资金路径", "现金化或过桥账户", "资金节点与处置节点的时间关系"]
    return [question, "支撑证据", "反向证据或证据缺口"]


def _date_key(value: str) -> str:
    text = str(value or "")
    match = re.search(r"(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    match = re.search(r"(20\d{2})[-年/.](\d{1,2})", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-00"
    return ""


def _guess_node_from_question(question: str) -> str:
    match = re.search(r"[\u4e00-\u9fa5]{2,4}", question)
    return match.group(0) if match else ""


def _bounded_int(value: Any, default: int, min_value: int, max_value: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(min_value, min(max_value, number))


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _jsonable_args(args: dict[str, Any]) -> dict[str, str | int | float | bool | list[str] | None]:
    clean: dict[str, str | int | float | bool | list[str] | None] = {}
    for key, value in args.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            clean[str(key)] = value
        elif isinstance(value, list):
            clean[str(key)] = [str(item) for item in value]
        else:
            clean[str(key)] = str(value)
    return clean


def _compact_summary(value: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit] + ("..." if len(text) > limit else "")

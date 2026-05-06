import json
import re
import urllib.error
import urllib.request
from os import getenv
from typing import Any

from app.adapters.algorithm import AlgorithmAdapter
from app.core.config import settings
from app.core.errors import not_found
from app.schemas.common import new_id, now_utc
from app.schemas.analysis import (
    AnalysisMessage,
    AnalysisRunRequest,
    AnalysisRunResult,
    AnalysisThread,
    AnalysisThreadCreate,
    AnalysisThreadDetail,
    AnalysisThreadMessageCreate,
    ChatRequest,
    ChatResult,
    GroundedSentence,
    PortraitFact,
    PortraitFactsResult,
    RagToolCall,
    SuspicionAnalysisRequest,
    SuspicionAnalysisResult,
    SuspicionCandidate,
    TracePassage,
    TracePath,
    TraceRequest,
    TraceResult,
)
from app.services.legal_knowledge_service import LegalKnowledgeService
from app.services.llm_context_debug import log_llm_context
from app.storage.memory_store import MemoryStore


class AnalysisService:
    def __init__(self, store: MemoryStore, algorithm: AlgorithmAdapter) -> None:
        self.store = store
        self.algorithm = algorithm
        self.legal_knowledge = LegalKnowledgeService()

    def run(self, case_id: str, payload: AnalysisRunRequest) -> AnalysisRunResult:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")

            evidence = self.store.evidence.get(case_id, [])
            graph = self.algorithm.build_graph(case_id, evidence, self.store.raw_contents, self.store.extractions)
            self.store.graphs[case_id] = graph
            self.store.portrait_facts.pop(case_id, None)
            self.store.cases[case_id] = case.model_copy(update={"status": "analyzed"})
            self.store.flush_case(case_id)

            scope_text = " / ".join(payload.scopes)
            summary = (
                f"已完成 {scope_text} 分析，"
                f"生成 {len(graph.nodes)} 个节点、{len(graph.edges)} 条关系、{len(graph.clues)} 条线索。"
            )
            return AnalysisRunResult(case_id=case_id, status="completed", summary=summary, graph=graph)

    def trace(self, case_id: str, payload: TraceRequest) -> TraceResult:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")
            evidence = list(self.store.evidence.get(case_id, []))
            raw_contents = dict(self.store.raw_contents)
            extractions = dict(self.store.extractions)
            graph = self.store.graphs.get(case_id)

        passages, error = self.algorithm.retrieve_trace(
            case_id=case_id,
            query=payload.query,
            evidence=evidence,
            raw_contents=raw_contents,
            extractions=extractions,
            top_k=payload.top_k,
        )
        return TraceResult(
            case_id=case_id,
            query=payload.query,
            provider=self.algorithm.provider,
            passages=passages,
            paths=_rank_graph_paths(payload.query, graph, payload.evidence_ids),
            error=error,
        )

    def chat(self, case_id: str, payload: ChatRequest) -> ChatResult:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")
            evidence = list(self.store.evidence.get(case_id, []))
            raw_contents = dict(self.store.raw_contents)
            extractions = dict(self.store.extractions)
            graph = self.store.graphs.get(case_id)

        answer, passages, error = self.algorithm.answer_question(
            case_id=case_id,
            question=payload.question,
            evidence=evidence,
            raw_contents=raw_contents,
            extractions=extractions,
            top_k=payload.top_k,
        )
        return ChatResult(
            case_id=case_id,
            question=payload.question,
            answer=answer,
            provider=self.algorithm.provider,
            passages=passages,
            paths=_rank_graph_paths(payload.question, graph, payload.evidence_ids),
            error=error,
        )

    def portrait_facts(self, case_id: str, force: bool = False) -> PortraitFactsResult:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")
            cached = self.store.portrait_facts.get(case_id)
            if cached and not force:
                return cached
            evidence = list(self.store.evidence.get(case_id, []))
            raw_contents = dict(self.store.raw_contents)
            extractions = dict(self.store.extractions)
            graph = self.store.graphs.get(case_id)

        suspect = _guess_focus_person(case.title, raw_contents)
        offense_name = _offense_name(self.legal_knowledge, case.offense_id)
        relationship_queries = _portrait_queries(case.title, suspect, offense_name, "relationship")
        behavior_queries = _portrait_queries(case.title, suspect, offense_name, "behavior")

        passages_by_key: dict[str, TracePassage] = {}
        errors: list[str] = []
        tool_calls: list[RagToolCall] = []
        for query in relationship_queries + behavior_queries:
            passages, error = self.algorithm.retrieve_trace(
                case_id=case_id,
                query=query,
                evidence=evidence,
                raw_contents=raw_contents,
                extractions=extractions,
                top_k=10,
            )
            mode = "time_oriented_ppr" if _query_has_time_signal(query) else "semantic_ppr"
            tool_calls.append(
                RagToolCall(
                    query=query,
                    mode=mode,
                    top_k=10,
                    returned=len(passages),
                    note=error,
                )
            )
            if error:
                errors.append(error)
            for passage in passages:
                key = f"{passage.evidence_id}::{passage.passage}"
                current = passages_by_key.get(key)
                if current is None or passage.score > current.score:
                    passages_by_key[key] = passage

        passages = sorted(passages_by_key.values(), key=lambda item: item.score, reverse=True)
        passages = _merge_required_filing_passages(passages, evidence, raw_contents)
        legal_passages = _retrieve_legal_context(
            self.legal_knowledge,
            case.offense_id,
            f"{offense_name or case.title} 人物关系 行为事实 证据缺口 办案模板",
            8,
        )
        graph_facts = _facts_from_graph(graph, "relationship") + _facts_from_graph(graph, "behavior") if graph else []
        llm_relationship_facts, llm_behavior_facts, relationship_narrative, behavior_narrative, llm_error = _deepseek_grounded_portrait_facts(
            case_title=case.title,
            suspect=suspect,
            offense_name=offense_name,
            passages=passages,
            legal_passages=legal_passages,
            graph_facts=graph_facts,
            tool_calls=tool_calls,
        )
        if llm_error:
            errors.append(llm_error)
        relationship_facts = llm_relationship_facts or _facts_from_hipporag_passages(passages, "relationship")
        behavior_facts = llm_behavior_facts or _facts_from_hipporag_passages(passages, "behavior")

        if graph:
            relationship_facts.extend(_facts_from_graph(graph, "relationship"))
            behavior_facts.extend(_facts_from_graph(graph, "behavior"))

        relationship_facts = _dedupe_facts(relationship_facts)[:18]
        behavior_facts = sorted(_dedupe_facts(behavior_facts), key=lambda item: (item.time or "9999", -item.confidence))[:24]

        result = PortraitFactsResult(
            case_id=case_id,
            provider=self.algorithm.provider,
            relationship_narrative=relationship_narrative or _narrative_from_facts(relationship_facts, "围绕嫌疑人的人物关系"),
            behavior_narrative=behavior_narrative or _narrative_from_facts(behavior_facts, "关键行为还原"),
            relationship_facts=relationship_facts,
            behavior_facts=behavior_facts,
            queries=relationship_queries + behavior_queries,
            tool_calls=tool_calls,
            tool_call_note=_tool_call_note(tool_calls),
            error="；".join(errors[:3]) if errors and not passages else None,
        )
        with self.store.lock:
            self.store.portrait_facts[case_id] = result
            self.store.flush_case(case_id)
        return result

    def suspicion_analysis(self, case_id: str, payload: SuspicionAnalysisRequest) -> SuspicionAnalysisResult:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")
            evidence = list(self.store.evidence.get(case_id, []))
            raw_contents = dict(self.store.raw_contents)
            extractions = dict(self.store.extractions)
            graph = self.store.graphs.get(case_id)
            selected_cases = {selected_id: self.store.cases[selected_id] for selected_id in payload.selected_case_ids if selected_id in self.store.cases}
            selected_graphs = {selected_id: self.store.graphs.get(selected_id) for selected_id in selected_cases}

        if not graph or (not graph.nodes and evidence):
            graph = self.algorithm.build_graph(case_id, evidence, raw_contents, extractions)
            with self.store.lock:
                self.store.graphs[case_id] = graph
                self.store.flush_case(case_id)

        if not graph:
            return SuspicionAnalysisResult(case_id=case_id, provider=self.algorithm.provider, summary="当前案件还没有可分析的图谱。")

        suspect = _guess_focus_person(case.title, raw_contents)
        if payload.mode == "cross_case":
            candidates, llm_error = _manual_cross_case_analysis(
                case_id=case_id,
                case_title=case.title,
                graph=graph,
                selected_cases=selected_cases,
                selected_graphs=selected_graphs,
                payload=payload,
                algorithm=self.algorithm,
                evidence=evidence,
                raw_contents=raw_contents,
                extractions=extractions,
            )
        elif payload.mode == "financial_flow":
            candidates, llm_error = _deepseek_multiround_analysis(
                case_id=case_id,
                case_title=case.title,
                suspect=suspect,
                mode="financial_flow",
                question=payload.hypothesis or "分析本案是否存在可疑资金流动、现金化、过桥账户、资金与处置节点前后呼应的问题。",
                graph=graph,
                evidence=evidence,
                raw_contents=raw_contents,
                extractions=extractions,
                algorithm=self.algorithm,
                legal_knowledge=self.legal_knowledge,
                offense_id=case.offense_id,
            )
        else:
            candidates, llm_error = _deepseek_multiround_analysis(
                case_id=case_id,
                case_title=case.title,
                suspect=suspect,
                mode="hypothesis",
                question=payload.hypothesis or f"围绕{suspect}提出并验证一个案件假设。",
                graph=graph,
                evidence=evidence,
                raw_contents=raw_contents,
                extractions=extractions,
                algorithm=self.algorithm,
                legal_knowledge=self.legal_knowledge,
                offense_id=case.offense_id,
            )

        summary = (
            f"完成 {payload.mode} 分析，生成 {len(candidates)} 条可采纳分析文本。"
        )
        return SuspicionAnalysisResult(
            case_id=case_id,
            provider=self.algorithm.provider,
            summary=summary,
            candidates=candidates,
            error=llm_error,
        )

    def list_threads(self, case_id: str, mode: str | None = None) -> list[AnalysisThread]:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            threads = list(self.store.analysis_threads.get(case_id, []))
        if mode:
            threads = [thread for thread in threads if thread.mode == mode]
        return sorted(threads, key=lambda item: item.updated_at, reverse=True)

    def get_thread(self, case_id: str, thread_id: str) -> AnalysisThreadDetail:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            thread = next((item for item in self.store.analysis_threads.get(case_id, []) if item.thread_id == thread_id), None)
            if not thread:
                raise not_found("analysis thread not found")
            messages = [item for item in self.store.analysis_messages.get(case_id, []) if item.thread_id == thread_id]
        return AnalysisThreadDetail(thread=thread, messages=messages)

    def create_thread(self, case_id: str, payload: AnalysisThreadCreate) -> AnalysisThreadDetail:
        title = payload.title or _thread_title(payload.initial_question, payload.mode)
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")
            now = now_utc()
            thread = AnalysisThread(
                thread_id=new_id("ath"),
                case_id=case_id,
                mode=payload.mode,
                title=title,
                created_at=now,
                updated_at=now,
                message_count=0,
            )
            self.store.analysis_threads.setdefault(case_id, []).append(thread)
            self.store.analysis_messages.setdefault(case_id, [])
            self.store.flush_case(case_id)
        return self.add_thread_message(case_id, thread.thread_id, AnalysisThreadMessageCreate(question=payload.initial_question))

    def add_thread_message(self, case_id: str, thread_id: str, payload: AnalysisThreadMessageCreate) -> AnalysisThreadDetail:
        with self.store.lock:
            case = self.store.cases.get(case_id)
            if not case:
                raise not_found("case not found")
            thread = next((item for item in self.store.analysis_threads.get(case_id, []) if item.thread_id == thread_id), None)
            if not thread:
                raise not_found("analysis thread not found")
            evidence = list(self.store.evidence.get(case_id, []))
            raw_contents = dict(self.store.raw_contents)
            extractions = dict(self.store.extractions)
            graph = self.store.graphs.get(case_id)
            history = [item for item in self.store.analysis_messages.get(case_id, []) if item.thread_id == thread_id]

        mentioned_ids, mention_errors = _resolve_evidence_mentions(payload.question, evidence)
        now = now_utc()
        user_message = AnalysisMessage(
            message_id=new_id("amsg"),
            thread_id=thread_id,
            role="user",
            content=payload.question,
            created_at=now,
            mentioned_evidence_ids=mentioned_ids,
            error="；".join(mention_errors) if mention_errors else None,
        )
        if mention_errors:
            assistant = AnalysisMessage(
                message_id=new_id("amsg"),
                thread_id=thread_id,
                role="assistant",
                content=f"无法继续分析：{'；'.join(mention_errors)}",
                created_at=now_utc(),
                error="；".join(mention_errors),
            )
            self._append_thread_messages(case_id, thread_id, [user_message, assistant])
            return self.get_thread(case_id, thread_id)

        if not graph and evidence:
            graph = self.algorithm.build_graph(case_id, evidence, raw_contents, extractions)
            with self.store.lock:
                self.store.graphs[case_id] = graph
                self.store.flush_case(case_id)

        evidence_subset = [item for item in evidence if not mentioned_ids or item.evidence_id in mentioned_ids]
        suspect = _guess_focus_person(case.title, raw_contents)
        graph_context = _select_graph_context_for_question(payload.question, graph, {node.node_id: node.label for node in graph.nodes}, thread.mode) if graph else []
        history_context = _thread_history_context(history)
        answer, passages, error = _deepseek_tool_loop_answer(
            case_id=case_id,
            case_title=case.title,
            mode=thread.mode,
            question=f"{history_context}\n本轮问题：{payload.question}".strip(),
            graph_context=graph_context,
            evidence=evidence_subset,
            raw_contents=raw_contents,
            extractions=extractions,
            algorithm=self.algorithm,
            legal_knowledge=self.legal_knowledge,
            offense_id=case.offense_id,
        )
        legal_passages = _retrieve_legal_context(
            self.legal_knowledge,
            case.offense_id,
            f"{case.legal_basis or ''} {payload.question} 证据要点 缺口",
            6,
        )
        claims = _ground_answer_sentences(answer, passages, graph_context)
        assistant_message = AnalysisMessage(
            message_id=new_id("amsg"),
            thread_id=thread_id,
            role="assistant",
            content=answer,
            created_at=now_utc(),
            claims=claims,
            retrievals=passages,
            graph_context=graph_context[:80],
            legal_context=legal_passages,
            mentioned_evidence_ids=mentioned_ids,
            error=error,
        )
        self._append_thread_messages(case_id, thread_id, [user_message, assistant_message], summary=_thread_summary(answer))
        return self.get_thread(case_id, thread_id)

    def delete_thread(self, case_id: str, thread_id: str) -> None:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            before = len(self.store.analysis_threads.get(case_id, []))
            self.store.analysis_threads[case_id] = [item for item in self.store.analysis_threads.get(case_id, []) if item.thread_id != thread_id]
            if len(self.store.analysis_threads[case_id]) == before:
                raise not_found("analysis thread not found")
            self.store.analysis_messages[case_id] = [item for item in self.store.analysis_messages.get(case_id, []) if item.thread_id != thread_id]
            self.store.flush_case(case_id)

    def _append_thread_messages(self, case_id: str, thread_id: str, messages: list[AnalysisMessage], summary: str | None = None) -> None:
        with self.store.lock:
            self.store.analysis_messages.setdefault(case_id, []).extend(messages)
            threads = self.store.analysis_threads.setdefault(case_id, [])
            for idx, thread in enumerate(threads):
                if thread.thread_id == thread_id:
                    count = len([item for item in self.store.analysis_messages.get(case_id, []) if item.thread_id == thread_id])
                    threads[idx] = thread.model_copy(update={
                        "updated_at": now_utc(),
                        "message_count": count,
                        "summary": summary if summary is not None else thread.summary,
                    })
                    break
            self.store.flush_case(case_id)


def _offense_name(service: LegalKnowledgeService, offense_id: str | None) -> str | None:
    if not offense_id:
        return None
    try:
        template = service.get_offense_template(offense_id)
    except Exception:  # noqa: BLE001
        return offense_id
    return str(template.get("name") or offense_id)


def _retrieve_legal_context(service: LegalKnowledgeService, offense_id: str | None, query: str, top_k: int) -> list[TracePassage]:
    result = service.retrieve(query=query, offense_id=offense_id, top_k=top_k)
    return result.passages if not result.error else []


def _portrait_queries(case_title: str, suspect: str, offense_name: str | None, kind: str) -> list[str]:
    prefix = f"{case_title} {offense_name or ''}".strip()
    focus = suspect if suspect and suspect != "杨周武" else "案件核心人物"
    if kind == "relationship":
        queries = [
            f"{prefix} 人物关系 核心人物 相关人 组织 账户 通话 转账 管理 控制",
            f"{prefix} {focus} 与其他人之间的关系、联系、请托、管理、指派、资金往来",
            f"{prefix} 谁和谁发生了联系、指挥、控制、帮助、利益往来或共同处置",
            f"{prefix} 立案决定书 犯罪嫌疑人 请托人 被害人 办案人员 关系网络",
        ]
    else:
        queries = [
            f"{prefix} 行为事实 时间线 谁做了什么 何时发生 结果如何",
            f"{prefix} {focus} 关键行为 处置节点 文书 通话 资金 结果",
            f"{prefix} 事件经过 证据材料中的动作、决定、安排、处理和后果",
            f"{prefix} 8月12日 8月16日 8月17日 8月18日 8月19日 8月21日 9月6日 9月20日 9月28日 时间线",
            f"{prefix} 火灾 死亡 受伤 事故 调查 履职 专报 严重后果",
            f"{prefix} 后续火灾 44人死亡 64人受伤 检察院立案侦查",
        ]
    if offense_name:
        queries.append(f"{offense_name} 本案相关事实 证据要点 缺口 补查方向")
    return list(dict.fromkeys([item.strip() for item in queries if item.strip()]))


def _query_has_time_signal(query: str) -> bool:
    return bool(re.search(r"\d{4}年|\d{1,2}月\d{1,2}日|时间线|后续|火灾", query))


def _tool_call_note(tool_calls: list[RagToolCall]) -> str:
    if not tool_calls:
        return ""
    labels: list[str] = []
    for call in tool_calls:
        text = call.query
        if "人物" in text or "关系" in text:
            label = "关系"
        elif "火灾" in text or "死亡" in text or "受伤" in text:
            label = "火灾后果"
        elif "8月" in text or "9月" in text or "时间线" in text:
            label = "时间线"
        elif "资金" in text or "转账" in text or "账户" in text:
            label = "资金"
        elif "立案" in text or "文书" in text:
            label = "文书"
        else:
            label = "事实"
        if label not in labels:
            labels.append(label)
    return f"本段依据后端代 DeepSeek 执行的 {len(tool_calls)} 次 HippoRAG PPR 检索，覆盖：{'、'.join(labels[:6])}。"


def _thread_title(question: str, mode: str) -> str:
    prefix = "资金" if mode == "financial_flow" else "假设"
    clean = re.sub(r"\s+", " ", question).strip()
    return f"{prefix}：{clean[:38]}" if clean else f"{prefix}分析"


def _thread_summary(answer: str) -> str:
    for sentence in _split_fact_sentences(answer):
        if sentence.strip():
            return sentence.strip()[:120]
    return answer.strip()[:120]


def _thread_history_context(history: list[AnalysisMessage]) -> str:
    if not history:
        return ""
    rows = []
    for item in history[-6:]:
        content = re.sub(r"\s+", " ", item.content).strip()
        rows.append(f"{item.role}: {content[:280]}")
    return "本会话历史：\n" + "\n".join(rows)


def _resolve_evidence_mentions(question: str, evidence: list[Any]) -> tuple[list[str], list[str]]:
    by_id = {str(item.evidence_id): item for item in evidence}
    by_title = {str(item.title): item for item in evidence}
    mentioned: list[str] = []
    errors: list[str] = []
    bracket_mentions = re.findall(r"@\[[^\]]+\]\(([^)]+)\)", question)
    loose_mentions = re.findall(r"@([^\s@，。；,;]+)", question)
    for raw in bracket_mentions + loose_mentions:
        token = raw.strip()
        if not token:
            continue
        item = by_id.get(token) or by_title.get(token)
        if not item:
            matches = [candidate for title, candidate in by_title.items() if token in title]
            if len(matches) == 1:
                item = matches[0]
        if not item:
            errors.append(f"未找到 @ 指定的证据：{token}")
            continue
        evidence_id = str(item.evidence_id)
        if evidence_id not in mentioned:
            mentioned.append(evidence_id)
    return mentioned, errors


def _ground_answer_sentences(answer: str, passages: list[TracePassage], graph_context: list[str]) -> list[GroundedSentence]:
    claims: list[GroundedSentence] = []
    cursor = 0
    for idx, sentence in enumerate(_split_fact_sentences(answer), start=1):
        text = sentence.strip()
        if not text:
            continue
        start = answer.find(sentence, cursor)
        if start < 0:
            start = cursor
        end = start + len(sentence)
        cursor = end
        scored = sorted(
            ((_score_sentence_against_passage(text, passage.passage), passage) for passage in passages),
            key=lambda item: item[0],
            reverse=True,
        )
        support = [passage for score, passage in scored[:4] if score > 0.08]
        confidence = min(0.95, scored[0][0]) if scored else 0.0
        if confidence >= 0.35:
            status = "supported"
        elif support:
            status = "weak"
        else:
            status = "unsupported"
        claims.append(
            GroundedSentence(
                sentence_id=f"sent_{idx}",
                text=text,
                start=start,
                end=end,
                status=status,
                confidence=round(float(confidence), 3),
                supporting_passages=support,
                supporting_graph_paths=[],
            )
        )
    return claims


def _score_sentence_against_passage(sentence: str, passage: str) -> float:
    terms = {term for term in re.findall(r"[\u4e00-\u9fa5]{2,}|\d+(?:\.\d+)?万?元?", sentence) if len(term) >= 2}
    if not terms:
        return 0.0
    hits = sum(1 for term in terms if term in passage)
    return hits / max(len(terms), 1)


def _manual_cross_case_analysis(
    case_id: str,
    case_title: str,
    graph,
    selected_cases: dict[str, Any],
    selected_graphs: dict[str, Any],
    payload: SuspicionAnalysisRequest,
    algorithm: AlgorithmAdapter,
    evidence: list[Any],
    raw_contents: dict[str, str],
    extractions: dict[str, Any],
) -> tuple[list[SuspicionCandidate], str | None]:
    if not selected_cases:
        return [
            SuspicionCandidate(
                candidate_id="cross_case_empty",
                title="请先选择要拉入临时合并态的案件",
                category="cross_case",
                method="manual_case_merge",
                risk_level="low",
                confidence=0,
                explanation="跨案件碰撞不会自动扫描全部案件。需要检察官指定一个或多个案件，系统才会进入临时合并态分析。",
                gaps=["未选择其他案件。"],
                suggestions=["在页面上选择一个或多个案件后重新运行跨案件碰撞。"],
            )
        ], None
    labels = {node.node_id: node.label for node in graph.nodes}
    selected_context: list[str] = []
    support_paths: list[str] = []
    evidence_ids: set[str] = set()
    current_nodes = _index_nodes_by_label(graph)
    for selected_id, selected_case in selected_cases.items():
        other_graph = selected_graphs.get(selected_id)
        if not other_graph:
            selected_context.append(f"案件「{selected_case.title}」尚无图谱，无法合并。")
            continue
        other_nodes = _index_nodes_by_label(other_graph)
        shared = [label for label in current_nodes if label in other_nodes and not _low_value_label(label)]
        selected_context.append(f"合并案件：{selected_case.title}（{selected_id}），共享实体 {len(shared)} 个：{', '.join(shared[:20])}")
        for label in shared[:12]:
            node = current_nodes[label]
            evidence_ids.update(node.evidence_ids[:3])
            support_paths.append(f"临时合并图：当前案件「{label}」 <-> 「{selected_case.title}」同名/同标识节点")
        selected_edges = [_edge_text(edge, {node.node_id: node.label for node in other_graph.nodes})["text"] for edge in other_graph.edges[:80]]
        selected_context.extend(selected_edges[:20])
    graph_context = [_edge_text(edge, labels)["text"] for edge in graph.edges[:120]]
    question = payload.hypothesis or "请分析这些被检察官拉入临时合并态的案件之间是否存在值得核查的交叉线索、共同人物、共同账户、共同机构或相似行为结构。"
    answer, passages, error = _deepseek_tool_loop_answer(
        case_id=case_id,
        case_title=case_title,
        mode="cross_case",
        question=question,
        graph_context=graph_context + selected_context,
        evidence=evidence,
        raw_contents=raw_contents,
        extractions=extractions,
        algorithm=algorithm,
    )
    candidate = SuspicionCandidate(
        candidate_id="cross_case_manual_merge",
        title="临时合并态跨案件碰撞分析",
        category="cross_case",
        method="manual_case_merge_deepseek_rag",
        risk_level="medium",
        status="candidate",
        confidence=0.65 if support_paths else 0.35,
        explanation=answer,
        support_paths=support_paths[:30],
        evidence_ids=sorted(evidence_ids),
        supporting_passages=passages,
        gaps=["当前是临时态合并，不会改写原案件图谱。", "同名实体尚未自动合并为同一自然人，需要人工确认。"],
        suggestions=["对共享实体逐一核查身份证号、手机号、账户号、地址和证据来源。", "如果确认同一实体，再将相关子图并入正式分析。"],
    )
    return [candidate], error


def _deepseek_multiround_analysis(
    case_id: str,
    case_title: str,
    suspect: str,
    mode: str,
    question: str,
    graph,
    evidence: list[Any],
    raw_contents: dict[str, str],
    extractions: dict[str, Any],
    algorithm: AlgorithmAdapter,
    legal_knowledge: LegalKnowledgeService,
    offense_id: str | None,
) -> tuple[list[SuspicionCandidate], str | None]:
    labels = {node.node_id: node.label for node in graph.nodes}
    graph_context = _select_graph_context_for_question(question, graph, labels, mode)
    answer, passages, error = _deepseek_tool_loop_answer(
        case_id=case_id,
        case_title=case_title,
        mode=mode,
        question=question,
        graph_context=graph_context,
        evidence=evidence,
        raw_contents=raw_contents,
        extractions=extractions,
        algorithm=algorithm,
        legal_knowledge=legal_knowledge,
        offense_id=offense_id,
    )
    category = "financial_flow" if mode == "financial_flow" else "hypothesis"
    title = "可疑资金流多轮 RAG 分析" if mode == "financial_flow" else "检察官假设多轮 RAG 验证"
    support_paths = graph_context[:30]
    candidate = SuspicionCandidate(
        candidate_id=f"{category}_deepseek_multiround",
        title=title,
        category=category,
        method="deepseek_multiround_rag",
        risk_level="medium",
        status="candidate",
        confidence=0.62 if passages else 0.35,
        explanation=answer,
        support_paths=support_paths,
        evidence_ids=sorted({passage.evidence_id for passage in passages if passage.evidence_id}),
        supporting_passages=passages,
        gaps=["当前版本由后端模拟 tool-use 多轮检索：先生成检索问题，再调用 HippoRAG，再让 DeepSeek 写分析。", "结论仍需检察官结合证据能力和合法性人工审查。"],
        suggestions=["点击 passage 回看证据原文。", "如果分析文本里出现无证据支撑的句子，应退回重问或缩小假设。"],
        gnn_note="资金流当前先用 DeepSeek + RAG + 图上下文分析；GNN 需要更多标注资金网络样本，暂不作为当前结论来源。" if mode == "financial_flow" else None,
    )
    return [candidate], error


def _deepseek_tool_loop_answer(
    case_id: str,
    case_title: str,
    mode: str,
    question: str,
    graph_context: list[str],
    evidence: list[Any],
    raw_contents: dict[str, str],
    extractions: dict[str, Any],
    algorithm: AlgorithmAdapter,
    legal_knowledge: LegalKnowledgeService | None = None,
    offense_id: str | None = None,
) -> tuple[str, list[TracePassage], str | None]:
    queries = _analysis_queries(mode, question)
    passages_by_key: dict[str, TracePassage] = {}
    errors: list[str] = []
    for query in queries:
        passages, error = algorithm.retrieve_trace(
            case_id=case_id,
            query=query,
            evidence=evidence,
            raw_contents=raw_contents,
            extractions=extractions,
            top_k=8,
        )
        if error:
            errors.append(error)
        for passage in passages:
            key = f"{passage.evidence_id}::{passage.passage}"
            if key not in passages_by_key or passage.score > passages_by_key[key].score:
                passages_by_key[key] = passage
    passages = sorted(passages_by_key.values(), key=lambda item: item.score, reverse=True)[:24]
    legal_knowledge = legal_knowledge or LegalKnowledgeService()
    offense_name = _offense_name(legal_knowledge, offense_id)
    legal_query = f"{offense_name or '司法工作人员职务犯罪'} {question} 证据要点 办案模板 证据缺口"
    legal_passages = _retrieve_legal_context(legal_knowledge, offense_id, legal_query, 8)
    answer, llm_error = _deepseek_write_analysis(case_title, mode, question, queries, passages, graph_context[:80], legal_passages, offense_name)
    if llm_error:
        errors.append(llm_error)
    return answer, passages, "；".join(errors[:2]) if errors else None


def _analysis_queries(mode: str, question: str) -> list[str]:
    base = [question]
    if mode == "financial_flow":
        base.extend([
            "本案资金流水 转账 取现 存入 现金 柜台 过桥账户 马甲账户",
            "资金时间线 与关键处置节点、通话节点、文书节点的先后关系",
            "核心人物 相关账户 资金往来 异常金额 现金化 过桥账户",
        ])
    elif mode == "cross_case":
        base.extend([
            "跨案件 共同人物 共同账户 共同机构 共同地址 共同电话",
            "多个案件之间 共享实体 相似行为结构 请托 资金 处置",
            "案件合并分析 共同线索 隐藏关系 多跳路径",
        ])
    else:
        base.extend([
            f"{question} 相关证据",
            f"{question} 是否有反向证据或证据缺口",
            "文书 修改 隐瞒 倒签 补录 删除 清理 通话 资金 处置 责任",
        ])
    return list(dict.fromkeys([item.strip() for item in base if item.strip()]))


def _select_graph_context_for_question(question: str, graph, labels: dict[str, str], mode: str) -> list[str]:
    if mode == "financial_flow":
        edges = [edge for edge in graph.edges if _is_fund_edge(edge)]
    else:
        terms = [term for term in re.split(r"[\s，。；、,;]+", question) if len(term) >= 2]
        edges = [
            edge
            for edge in graph.edges
            if any(term in _edge_text(edge, labels)["text"] for term in terms)
            or any(word in f"{edge.relation} {edge.properties}" for word in ["请托", "指派", "调解", "释放", "修改", "隐瞒", "倒签", "补录", "文书"])
        ]
    if not edges:
        edges = graph.edges[:80]
    return [_edge_text(edge, labels)["text"] for edge in edges[:120]]


def _deepseek_write_analysis(
    case_title: str,
    mode: str,
    question: str,
    queries: list[str],
    passages: list[TracePassage],
    graph_context: list[str],
    legal_passages: list[TracePassage] | None = None,
    offense_name: str | None = None,
) -> tuple[str, str | None]:
    api_key = getenv("DEEPSEEK_API_KEY")
    if not settings.deepseek_analysis_enabled or not api_key:
        return _fallback_analysis_text(mode, question, passages, graph_context), None
    prompt = {
        "case_title": case_title,
        "analysis_mode": mode,
        "selected_offense": offense_name or "未选择罪名，按证据事实分析",
        "prosecutor_question": question,
        "tool_use_description": "你不能直接调用工具。后端已经代你进行了多轮 HippoRAG 检索，下面给出每轮查询、召回 passage 和图谱三元组/边上下文。请像完成 tool-use 分析一样，先说明检索发现，再判断支撑、矛盾和缺口。",
        "queries": queries,
        "passages": [
            {
                "rank": index + 1,
                "score": item.score,
                "evidence_id": item.evidence_id,
                "evidence_title": item.evidence_title,
                "text": item.passage,
            }
            for index, item in enumerate(passages)
        ],
        "graph_context": graph_context,
        "legal_knowledge_passages": [
            {
                "rank": index + 1,
                "title": item.evidence_title,
                "text": item.passage,
                "score": item.score,
            }
            for index, item in enumerate((legal_passages or [])[:10])
        ],
        "requirements": [
            "用中文写成连续分析文本，不要写成碎卡片。",
            "如果 selected_offense 不是“未选择罪名”，可以参考 legal_knowledge_passages 组织分析框架；如果未选择罪名，不要强行套法条。",
            "法律知识只提供分析框架，不能当作本案事实来源。本案事实必须来自 passages 或 graph_context。",
            "明确区分：已由证据支持、仅为疑点、尚需补强。",
            "每个关键判断后用括号标注证据标题或 passage rank，例如（passage #3）。",
            "不得作定罪结论，不得编造证据。",
            "资金流分析必须说明当前 GNN 需要更多数据，现阶段只做 RAG+图谱解释。",
        ],
    }
    body = {
        "model": settings.deepseek_analysis_model,
        "messages": [
            {"role": "system", "content": "你是检察侦查分析助手。请基于给定 JSON 证据上下文完成严谨中文分析。"},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0.1,
    }
    request = urllib.request.Request(
        f"{settings.hipporag_llm_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.deepseek_analysis_timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data["choices"][0]["message"]["content"]).strip(), None
    except Exception as exc:  # noqa: BLE001
        return _fallback_analysis_text(mode, question, passages, graph_context), _format_llm_error(exc)


def _fallback_analysis_text(mode: str, question: str, passages: list[TracePassage], graph_context: list[str]) -> str:
    lines = [f"问题：{question}", "当前未能调用 DeepSeek，以下为检索上下文摘要。"]
    if passages:
        lines.append("召回证据：")
        for index, passage in enumerate(passages[:6], start=1):
            lines.append(f"{index}. {passage.evidence_title or passage.evidence_id or '未知证据'}：{passage.passage[:120]}")
    if graph_context:
        lines.append("图谱上下文：")
        lines.extend(graph_context[:8])
    if mode == "financial_flow":
        lines.append("资金流 GNN 模式需要更多标注交易网络样本，当前仅作为 RAG+图谱解释。")
    return "\n".join(lines)


def _cross_case_candidates(case_id: str, graph, other_graphs: dict[str, Any], other_cases: dict[str, str], limit: int) -> list[SuspicionCandidate]:
    current_nodes = _index_nodes_by_label(graph)
    candidates: list[SuspicionCandidate] = []
    for other_id, other_graph in other_graphs.items():
        other_nodes = _index_nodes_by_label(other_graph)
        shared_labels = [
            label
            for label, node in current_nodes.items()
            if label in other_nodes and _collision_node_type(node.type) and not _low_value_label(label)
        ]
        if not shared_labels:
            continue
        support_paths: list[str] = []
        evidence_ids: set[str] = set()
        for label in shared_labels[:8]:
            node = current_nodes[label]
            other_node = other_nodes[label]
            evidence_ids.update(node.evidence_ids[:3])
            support_paths.append(f"当前案件实体「{label}」与案件「{other_cases.get(other_id, other_id)}」存在同名/同标识节点（{node.type} / {other_node.type}）。")
        candidates.append(
            SuspicionCandidate(
                candidate_id=f"susp_cross_{other_id}",
                title=f"与案件「{other_cases.get(other_id, other_id)}」存在 {len(shared_labels)} 个共享实体",
                category="cross_case",
                method="exact_entity_linkage",
                risk_level="medium" if len(shared_labels) < 3 else "high",
                status="candidate",
                confidence=min(0.9, 0.35 + len(shared_labels) * 0.08),
                explanation="发现当前案件与其他案件存在共享实体，可能提示共同人员、共同账户、共同机构或重复出现的资源线索。需要进一步核查是否为同一自然人、同一账户或同一业务场景。",
                support_paths=support_paths,
                evidence_ids=sorted(evidence_ids),
                gaps=["当前版本先做同名/同标识碰撞，还没有做人名别名归一、地址相似度和子图同构。"],
                suggestions=["优先核查共享实体的身份证号、手机号、账户号、地址和证据来源。", "如果共享实体处于资金或请托路径中，应并入统一子图继续分析。"],
            )
        )
        if len(candidates) >= limit:
            break
    return candidates


def _hypothesis_candidates(graph, suspect: str, user_hypothesis: str | None) -> list[SuspicionCandidate]:
    labels = {node.node_id: node.label for node in graph.nodes}
    text_edges = [_edge_text(edge, labels) for edge in graph.edges]
    candidates: list[SuspicionCandidate] = []
    hypothesis_specs = [
        (
            "request_chain",
            user_hypothesis or f"{suspect}可能接受请托并影响案件处置",
            ["请托", "联系", "短信", "通话", "指派", "安排", "调解", "释放", "结案"],
            ["需要证明请托、职权动作和处置结果之间存在时间顺序。", "需要排除正常工作联系或程序性协调。"],
        ),
        (
            "procedure_anomaly",
            f"{suspect}可能通过异常程序处置使相关人员逃避追诉",
            ["拘留", "释放", "调解", "撤案", "结案", "批准", "指派", "非办案"],
            ["需要补强原案本应追究刑事责任的法律依据。", "需要核查批准、经办、执行人员之间的职责边界。"],
        ),
    ]
    for index, (kind, title, keywords, gaps) in enumerate(hypothesis_specs, start=1):
        matched_edges = [item for item in text_edges if any(word in item["text"] for word in keywords)]
        if not matched_edges:
            continue
        evidence_ids = sorted({evd for item in matched_edges[:10] for evd in item["evidence_ids"]})
        candidates.append(
            SuspicionCandidate(
                candidate_id=f"susp_hyp_{index}",
                title=title,
                category="hypothesis",
                method="graph_hypothesis_testing",
                risk_level="high" if len(matched_edges) >= 6 else "medium",
                status="plausible" if len(matched_edges) >= 4 else "candidate",
                confidence=min(0.88, 0.25 + len(matched_edges) * 0.07),
                explanation="该假设在图谱中找到了若干相关边，暂未发现明显与图谱相冲突的信息。当前只能说明值得核查，不能直接作为事实结论。",
                support_paths=[item["text"] for item in matched_edges[:8]],
                evidence_ids=evidence_ids,
                gaps=gaps,
                suggestions=["用 HippoRAG 针对每个关键动作检索原文 passage。", "把请托、资金、通话、文书处置放到同一时间轴验证先后关系。"],
            )
        )
    return candidates


def _financial_flow_candidates(graph) -> list[SuspicionCandidate]:
    labels = {node.node_id: node.label for node in graph.nodes}
    fund_edges = [
        edge
        for edge in graph.edges
        if _is_fund_edge(edge)
    ]
    candidates: list[SuspicionCandidate] = []
    if fund_edges:
        amount_total = sum(_edge_amount(edge) for edge in fund_edges)
        top_edges = sorted(fund_edges, key=_edge_amount, reverse=True)[:8]
        evidence_ids = sorted({evd for edge in top_edges for evd in edge.evidence_ids})
        candidates.append(
            SuspicionCandidate(
                candidate_id="susp_fund_paths",
                title=f"发现 {len(fund_edges)} 条资金相关边，金额合计约 {amount_total:.2f} 元",
                category="financial_flow",
                method="financial_flow_graph",
                risk_level="high" if amount_total >= 100000 else "medium",
                status="candidate",
                confidence=min(0.86, 0.3 + len(fund_edges) * 0.02),
                explanation="资金边显示当前案件存在转账、取现、存入或赔偿等资金动作。需要判断这些动作是否与请托、调解、释放等关键处置节点前后呼应。",
                support_paths=[_edge_text(edge, labels)["text"] for edge in top_edges],
                evidence_ids=evidence_ids,
                gaps=["当前版本没有足够跨案件和正常交易样本，暂不使用 GNN 判断异常。", "现金取存、过桥账户和备注性质仍需人工核对。"],
                suggestions=["优先追踪 2-5 跳资金路径。", "检查是否存在短期大额、拆分转账、现金化处理、过桥账户和处置节点临近交易。"],
                gnn_note="后续可接 GNN：需要大量标注资金网络样本、账户特征、交易边特征和异常路径标签。当前先用图算法和 LLM 解释。",
            )
        )
    cash_edges = [edge for edge in fund_edges if any(word in f"{edge.relation} {edge.properties}" for word in ["现金", "取现", "存入", "ATM", "柜台"])]
    if cash_edges:
        candidates.append(
            SuspicionCandidate(
                candidate_id="susp_cash_break",
                title=f"发现 {len(cash_edges)} 条现金化或柜台相关资金线索",
                category="financial_flow",
                method="cash_flow_break_detection",
                risk_level="high",
                status="candidate",
                confidence=min(0.82, 0.35 + len(cash_edges) * 0.08),
                explanation="现金取现、现金存入或柜台存款会切断账户间直接转账链条，适合作为规避留痕或利益输送的重点核查对象。",
                support_paths=[_edge_text(edge, labels)["text"] for edge in cash_edges[:8]],
                evidence_ids=sorted({evd for edge in cash_edges[:8] for evd in edge.evidence_ids}),
                gaps=["需要将取现人与存款人、时间间隔、地点和后续处置节点放在同一时间轴核对。"],
                suggestions=["核查 ATM/柜台监控、取存凭证、同日通话或短信记录。"],
                gnn_note="现金化模式后续可作为 GNN/规则混合模型的强特征，但当前样本不足，先用规则提示。",
            )
        )
    return candidates


def _rank_suspicion_candidates(candidates: list[SuspicionCandidate]) -> list[SuspicionCandidate]:
    priority = {"high": 3, "medium": 2, "low": 1}
    seen: set[str] = set()
    unique: list[SuspicionCandidate] = []
    for item in candidates:
        key = f"{item.category}:{item.title}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return sorted(unique, key=lambda item: (priority.get(item.risk_level, 0), item.confidence, len(item.evidence_ids)), reverse=True)


def _attach_suspicion_passages(
    candidates: list[SuspicionCandidate],
    case_id: str,
    evidence: list[Any],
    raw_contents: dict[str, str],
    extractions: dict[str, Any],
    algorithm: AlgorithmAdapter,
) -> None:
    for item in candidates:
        query = f"{item.title}\n{item.explanation}\n" + "\n".join(item.support_paths[:3])
        passages, _error = algorithm.retrieve_trace(
            case_id=case_id,
            query=query,
            evidence=evidence,
            raw_contents=raw_contents,
            extractions=extractions,
            top_k=5,
        )
        item.supporting_passages = passages[:5]
        for passage in passages:
            if passage.evidence_id and passage.evidence_id not in item.evidence_ids:
                item.evidence_ids.append(passage.evidence_id)


def _polish_suspicion_candidates_with_deepseek(case_title: str, suspect: str, candidates: list[SuspicionCandidate]) -> str | None:
    api_key = getenv("DEEPSEEK_API_KEY")
    if not settings.deepseek_analysis_enabled or not api_key or not candidates:
        return None
    payload_candidates = [
        {
            "candidate_id": item.candidate_id,
            "title": item.title,
            "category": item.category,
            "method": item.method,
            "support_paths": item.support_paths[:6],
            "gaps": item.gaps,
            "suggestions": item.suggestions,
        }
        for item in candidates[:8]
    ]
    system = "你是检察侦查辅助分析助手。请只基于给定疑点候选和支持路径，用简洁中文润色解释，不要新增事实。必须返回合法 JSON。"
    user = json.dumps(
        {
            "case_title": case_title,
            "focus_suspect": suspect,
            "task": "把每条疑点候选改写成更清楚的检察官工作提示。不得扩大事实，不得作定罪结论。",
            "return_schema": [{"candidate_id": "string", "explanation": "string", "gaps": ["string"], "suggestions": ["string"]}],
            "candidates": payload_candidates,
        },
        ensure_ascii=False,
    )
    try:
        data = json.dumps(
            {
                "model": settings.deepseek_analysis_model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = json.loads(response.read().decode("utf-8"))
        content = raw["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        rows = parsed.get("candidates", parsed.get("items", [])) if isinstance(parsed, dict) else []
        by_id = {str(item.get("candidate_id")): item for item in rows if isinstance(item, dict)}
        for item in candidates:
            row = by_id.get(item.candidate_id)
            if not row:
                continue
            if row.get("explanation"):
                item.explanation = str(row["explanation"])
            if isinstance(row.get("gaps"), list):
                item.gaps = [str(value) for value in row["gaps"] if value]
            if isinstance(row.get("suggestions"), list):
                item.suggestions = [str(value) for value in row["suggestions"] if value]
    except Exception as exc:  # noqa: BLE001
        return _format_llm_error(exc)
    return None


def _index_nodes_by_label(graph) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for node in graph.nodes:
        label = str(node.label or "").strip()
        if label and label not in result:
            result[label] = node
    return result


def _collision_node_type(node_type: str) -> bool:
    return node_type in {"person", "organization", "account", "money", "address", "device", "phone"}


def _low_value_label(label: str) -> bool:
    if len(label) <= 1:
        return True
    return label in {"证据", "未知对象", "记录", "现金", "ATM", "柜台", "文件", "案件", "事故"}


def _edge_text(edge, labels: dict[str, str]) -> dict[str, Any]:
    source = labels.get(edge.source_id, edge.source_id)
    target = labels.get(edge.target_id, edge.target_id)
    time = edge.timestamp or edge.properties.get("time") or edge.properties.get("time_sample") or ""
    amount = edge.properties.get("amount") or edge.properties.get("amount_total") or ""
    suffix = "，".join(str(value) for value in [f"时间 {time}" if time else "", f"金额 {amount}" if amount else ""] if value)
    return {
        "text": f"{source} --{edge.relation}--> {target}" + (f"（{suffix}）" if suffix else ""),
        "evidence_ids": list(edge.evidence_ids),
    }


def _is_fund_edge(edge) -> bool:
    text = f"{edge.relation} {' '.join(edge.tags or [])} {edge.properties}"
    return any(word in text for word in ["转账", "资金", "交易", "付款", "收款", "支出", "收入", "现金", "取现", "存入", "赔偿", "金额"])


def _edge_amount(edge) -> float:
    for key in ["amount", "amount_total", "金额", "交易金额"]:
        value = edge.properties.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = re.sub(r"[^0-9.]", "", value)
            if cleaned:
                try:
                    return float(cleaned)
                except ValueError:
                    return 0.0
    return 0.0


def _rank_graph_paths(query: str, graph, evidence_ids: list[str], limit: int = 12) -> list[TracePath]:
    if not graph:
        return []
    query_terms = [term for term in query.replace(",", " ").replace("，", " ").replace("。", " ").split() if term]
    evidence_set = set(evidence_ids)
    labels = {node.node_id: node.label for node in graph.nodes}
    paths: list[TracePath] = []
    for edge in graph.edges:
        source = labels.get(edge.source_id, edge.source_id)
        target = labels.get(edge.target_id, edge.target_id)
        text = f"{source} {edge.relation} {target} {' '.join(str(v) for v in edge.properties.values())}"
        term_score = sum(1 for term in query_terms if term and term in text)
        evidence_score = 2 if evidence_set and evidence_set.intersection(edge.evidence_ids) else 0
        count_score = min(float(edge.properties.get("count", 1) or 1), 5.0) / 5.0
        score = float(term_score + evidence_score + count_score)
        if score <= 0 and query_terms:
            continue
        paths.append(
            TracePath(
                source=source,
                relation=edge.relation,
                target=target,
                score=score,
                evidence_ids=edge.evidence_ids,
            )
        )
    return sorted(paths, key=lambda item: item.score, reverse=True)[:limit]


CASE_NAMES = ("杨周武", "王静", "何晓初", "刘力飚", "罗贤涛", "易承桂", "江军", "汪春蓉", "赵志高", "张夏天", "陈三一", "罗宇")


def _guess_focus_person(case_title: str, raw_contents: dict[str, str]) -> str:
    corpus = "\n".join(raw_contents.values())[:30000]
    for name in CASE_NAMES:
        if name in case_title or name in corpus:
            return name
    suspect_match = re.search(r"犯罪嫌疑人[：:\s]*([\u4e00-\u9fa5]{2,4})", corpus)
    if suspect_match:
        return suspect_match.group(1)
    title_match = re.search(r"([\u4e00-\u9fa5]{2,4})(?:涉嫌|案|案件)", case_title)
    if title_match:
        return title_match.group(1)
    return "案件核心人物"


def _merge_required_filing_passages(
    passages: list[TracePassage],
    evidence: list[Any],
    raw_contents: dict[str, str],
    limit: int = 6,
) -> list[TracePassage]:
    existing = {f"{item.evidence_id}::{item.passage}" for item in passages}
    required: list[TracePassage] = []
    for item in evidence:
        title = str(getattr(item, "title", "") or "")
        evidence_id = str(getattr(item, "evidence_id", "") or "")
        if not ("立案" in title or "检察院" in title):
            continue
        content = raw_contents.get(evidence_id, getattr(item, "content_preview", "") or "")
        for sentence in _split_fact_sentences(content):
            if not any(word in sentence for word in ("立案", "侦查", "犯罪嫌疑人", "涉嫌", "决定", "案件", "调查")):
                continue
            key = f"{evidence_id}::{sentence}"
            if key in existing:
                continue
            required.append(
                TracePassage(
                    rank=900 + len(required) + 1,
                    score=1.0,
                    passage=sentence,
                    evidence_id=evidence_id,
                    evidence_title=title,
                )
            )
            existing.add(key)
            if len(required) >= limit:
                return required + passages
    return required + passages


def _narrative_from_facts(facts: list[PortraitFact], title: str) -> str:
    if not facts:
        return ""
    lines = [f"{title}："]
    for fact in facts[:8]:
        lines.append(f"{fact.subject}{fact.relation}{fact.object}。{fact.text}")
    return "\n".join(lines)


def _deepseek_grounded_portrait_facts(
    case_title: str,
    suspect: str,
    offense_name: str | None,
    passages: list[TracePassage],
    legal_passages: list[TracePassage],
    graph_facts: list[PortraitFact],
    tool_calls: list[RagToolCall],
) -> tuple[list[PortraitFact], list[PortraitFact], str, str, str | None]:
    if not settings.deepseek_analysis_enabled or not getenv("DEEPSEEK_API_KEY") or not passages:
        return [], [], "", "", None

    selected_passages = passages[:36]
    passage_payload = [
        {
            "rank": item.rank,
            "evidence_id": item.evidence_id,
            "evidence_title": item.evidence_title,
            "score": round(float(item.score), 4),
            "text": item.passage,
        }
        for item in selected_passages
    ]
    triple_payload = [
        {
            "triple_id": f"t{idx + 1}",
            "category": item.category,
            "group": item.group,
            "subject": item.subject,
            "relation": item.relation,
            "object": item.object,
            "time": item.time,
            "evidence_ids": item.evidence_ids,
        }
        for idx, item in enumerate(graph_facts[:80])
    ]
    log_llm_context(
        "portrait_facts_deepseek_tool_context",
        question=f"{case_title}：人物关系与行为还原",
        passages=passage_payload,
        extra={"model": settings.deepseek_analysis_model, "triples": triple_payload[:40], "tool_calls": [item.model_dump() for item in tool_calls]},
    )
    tool_note = _tool_call_note(tool_calls)
    prompt = {
        "case_title": case_title,
        "suspect": suspect,
        "selected_offense": offense_name or "未选择罪名，按证据事实分析",
        "task": "基于 passages 和 triples，先写文段式分析，再输出可溯源 claims。只能输出 JSON。",
        "tool_call_note": tool_note,
        "available_tools": [
            "本轮已由后端代你执行 HippoRAG.retrieve_trace，多角度查询并返回 passages。",
            "passages 是证据原文片段；triples 是图谱关系摘要。你必须同时参考二者。",
            "legal_knowledge_passages 是法律知识库/办案模板片段，只能作为分析框架，不能作为本案事实依据。",
            "如果需要进一步查询，输出 next_queries 字段，后端后续版本会继续检索；本轮不要假装已经查到未提供的材料。",
        ],
        "tool_calls": [item.model_dump() for item in tool_calls],
        "rules": [
            "必须使用简体中文。",
            "第一目标是“还原人物关系”：围绕当前案件核心人物向外推分析相关人、组织、账户、处置人员、被害人/对象之间的关系。",
            "如果 selected_offense 不是“未选择罪名”，可以参考 legal_knowledge_passages 组织要点；如果未选择罪名，不要强行套法条或构成要件。",
            "开头先写 2 到 4 段自然文，不要堆列表。",
            "relationship_narrative 和 behavior_narrative 的最后各附一行极短的“检索说明”，使用 tool_call_note，不要超过 45 个汉字。",
            "文段只能写证据能支持的事实，不写宏大评价，不写套话。",
            "每条 claim 只表达一个事实。",
            "人物关系关注谁与谁之间发生了请托、收受、指派、通话、转账、亲属、上下级等关系。",
            "行为还原关注时间顺序和动作：接警、鉴定、拘留、请托、收钱、指派、调解、释放、后续火灾/事故后果、检察院立案侦查。",
            "如果 passages 中出现火灾、死亡、受伤、事故调查、履职专报，行为还原必须纳入；若未出现，明确写“本轮未召回后续火灾材料”。",
            "每条 claim 必须引用 source_passage_ranks 或 source_triple_ids；没有来源就不要输出。",
            "如果无法确定 passage rank，也必须填写 evidence_ids，且 evidence_ids 必须来自 passages 或 triples。",
            "不要把 passage 中的证明事项当成最终结论，除非有文书原文、证言、短信、流水或通话记录支撑。",
        ],
        "fewshot": {
            "input_hint": "嫌疑人甲；passage显示乙打电话找甲帮忙，丙称甲安排丁介入调解；triples显示乙 通话 甲、甲 指派 丁。",
            "good_output": {
                "relationship_narrative": "从现有材料看，甲处在关系网络中心。乙先通过电话向甲提出请托，随后甲把案件处置动作转交给丁执行，丁与调解节点发生直接联系。因此，乙是请托端，甲是权力处置端，丁是具体介入执行端。",
                "claims": [
                    {
                        "category": "relationship",
                        "group": "请托/协调",
                        "subject": "乙",
                        "relation": "请托",
                        "object": "甲",
                        "text": "乙通过电话向甲提出请托。",
                        "source_passage_ranks": [1],
                        "source_triple_ids": ["t1"],
                        "evidence_ids": ["evd_demo"],
                        "confidence": 0.86,
                    }
                ],
            },
        },
        "passages": passage_payload,
        "legal_knowledge_passages": [
            {
                "rank": index + 1,
                "title": item.evidence_title,
                "score": round(float(item.score), 4),
                "text": item.passage,
            }
            for index, item in enumerate(legal_passages[:10])
        ],
        "triples": triple_payload,
        "output_schema": {
            "relationship_narrative": "围绕嫌疑人向外扩展的人物关系分析文段",
            "behavior_narrative": "按事实顺序还原关键行为的文段",
            "next_queries": ["仍需进一步检索的问题，可为空"],
            "claims": [
                {
                    "category": "relationship 或 behavior",
                    "group": "请托/协调 或 职务/指派 或 资金/利益 或 案件处置 或 通话/联系",
                    "subject": "主体",
                    "relation": "关系/动作",
                    "object": "客体",
                    "text": "一句可核验事实",
                    "time": "可选时间",
                    "source_passage_ranks": [1, 2],
                    "source_triple_ids": ["t1"],
                    "evidence_ids": ["evd_xxx"],
                    "confidence": 0.0,
                }
            ]
        },
    }
    body = {
        "model": settings.deepseek_analysis_model,
        "messages": [
            {"role": "system", "content": "你是检察侦查事实分析助手。你只能基于给定证据片段和三元组输出可溯源事实。"},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{settings.hipporag_llm_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {getenv('DEEPSEEK_API_KEY')}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.deepseek_analysis_timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        raw_claims = parsed.get("claims", [])
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return [], [], "", "", f"DeepSeek facts generation failed: {_format_llm_error(exc)}"
    if not isinstance(raw_claims, list):
        return [], [], "", "", "DeepSeek facts generation failed: response claims is not a list"

    passage_by_rank = {item.rank: item for item in selected_passages}
    passages_by_evidence: dict[str, list[TracePassage]] = {}
    for item in selected_passages:
        if item.evidence_id:
            passages_by_evidence.setdefault(item.evidence_id, []).append(item)
    triple_by_id = {item["triple_id"]: item for item in triple_payload}
    relationship: list[PortraitFact] = []
    behavior: list[PortraitFact] = []
    for idx, raw in enumerate(raw_claims[:40]):
        fact = _claim_to_fact(raw, idx, passage_by_rank, passages_by_evidence, triple_by_id)
        if not fact:
            continue
        if fact.category == "behavior":
            behavior.append(fact)
        else:
            relationship.append(fact)
    relationship_text = _clean_fact_text(str(parsed.get("relationship_narrative") or ""))
    behavior_text = _clean_fact_text(str(parsed.get("behavior_narrative") or ""))
    return relationship, behavior, relationship_text, behavior_text, None


def _claim_to_fact(
    raw: Any,
    index: int,
    passage_by_rank: dict[int, TracePassage],
    passages_by_evidence: dict[str, list[TracePassage]],
    triple_by_id: dict[str, dict[str, Any]],
) -> PortraitFact | None:
    if not isinstance(raw, dict):
        return None
    text = _clean_fact_text(str(raw.get("text") or ""))
    subject = _clean_fact_text(str(raw.get("subject") or ""))
    relation = _clean_fact_text(str(raw.get("relation") or ""))
    obj = _clean_fact_text(str(raw.get("object") or ""))
    if not text or not subject or not relation or not obj:
        return None

    ranks = [int(rank) for rank in _safe_list(raw.get("source_passage_ranks")) if str(rank).isdigit()]
    triple_ids = [str(item) for item in _safe_list(raw.get("source_triple_ids")) if str(item) in triple_by_id]
    raw_evidence_ids = [str(item) for item in _safe_list(raw.get("evidence_ids")) if str(item)]
    source_passages = [passage_by_rank[rank] for rank in ranks if rank in passage_by_rank]
    if not source_passages and raw_evidence_ids:
        for evidence_id in raw_evidence_ids:
            source_passages.extend(passages_by_evidence.get(evidence_id, [])[:2])
    source_triples = [triple_by_id[item] for item in triple_ids]
    if not source_passages and not source_triples and not raw_evidence_ids:
        return None

    evidence_ids: list[str] = list(raw_evidence_ids)
    for item in source_passages:
        if item.evidence_id:
            evidence_ids.append(item.evidence_id)
    for item in source_triples:
        evidence_ids.extend(str(eid) for eid in item.get("evidence_ids", []) if eid)
    evidence_ids = list(dict.fromkeys(evidence_ids))
    if not evidence_ids:
        return None

    raw_category = str(raw.get("category") or "")
    category = "behavior" if raw_category in {"behavior", "行为还原", "行为事实"} else "relationship"
    group = str(raw.get("group") or _relation_group(relation))
    if group not in {"请托/协调", "职务/指派", "资金/利益", "案件处置", "通话/联系", "其他关系"}:
        group = _relation_group(relation)
    confidence = _safe_float(raw.get("confidence"), 0.78)
    if source_passages:
        joined = "\n".join(item.passage for item in source_passages)
        if not any(part and part in joined for part in (subject, obj, relation)):
            confidence = min(confidence, 0.55)
    fact_key = f"llm:{category}:{subject}:{relation}:{obj}:{index}:{','.join(evidence_ids)}"
    return PortraitFact(
        fact_id=f"pf_llm_{abs(hash(fact_key))}",
        category=category,
        group=group,
        subject=subject,
        relation=relation,
        object=obj,
        text=text,
        time=str(raw.get("time") or "") or None,
        evidence_ids=evidence_ids,
        passages=source_passages,
        confidence=max(0.0, min(confidence, 1.0)),
        source="deepseek",
    )


def _facts_from_hipporag_passages(passages: list[TracePassage], category: str) -> list[PortraitFact]:
    facts: list[PortraitFact] = []
    for passage in passages:
        for sentence in _split_fact_sentences(passage.passage):
            fact = _fact_from_sentence(sentence, passage, category)
            if fact:
                facts.append(fact)
    return facts


def _fact_from_sentence(sentence: str, passage: TracePassage, category: str) -> PortraitFact | None:
    text = _clean_fact_text(sentence)
    if not text or len(text) < 10 or _looks_like_structured_row(text):
        return None
    names = [name for name in CASE_NAMES if name in text]
    time = _extract_time(text)
    amount = _extract_amount(text)

    if _has_any(text, ("请托", "请求", "帮忙", "宴请")) and "杨周武" in text and _has_any(text, ("王静", "何晓初")):
        subject = "王静" if "王静" in text else "何晓初"
        return _make_fact(category, "请托/协调", subject, "请托", "杨周武", text, time, passage, 0.92)

    if _has_any(text, ("指派", "安排")) and "杨周武" in text and "刘力飚" in text:
        return _make_fact(category, "职务/指派", "杨周武", "指派/安排", "刘力飚", text, time, passage, 0.94)

    if _has_any(text, ("介入", "协调", "调解")) and "刘力飚" in text:
        relation = "介入调解" if "调解" in text else "介入"
        return _make_fact(category, "职务/指派", "刘力飚", relation, "案件处置", text, time, passage, 0.84)

    if _has_any(text, ("3万元", "30000", "现金")) and _has_any(text, ("王静", "何晓初", "杨周武")):
        subject = "王静" if "王静" in text else "何晓初" if "何晓初" in text else "杨周武"
        obj = "杨周武" if subject != "杨周武" and "杨周武" in text else amount or "3万元"
        return _make_fact(category, "资金/利益", subject, "资金往来", obj, text, time, passage, 0.88)

    if _has_any(text, ("27万", "270000")) and _has_any(text, ("王静", "何晓初", "杨周武")):
        return _make_fact(category, "资金/利益", "王静", "好处费/利益输送", "27万元", text, time, passage, 0.82)

    if _has_any(text, ("11万", "110000")) and _has_any(text, ("刘力飚", "杨周武", "江军")):
        subject = "刘力飚" if "刘力飚" in text else "杨周武"
        return _make_fact(category, "案件处置", subject, "促成赔偿", "11万元", text, time, passage, 0.84)

    if _has_any(text, ("释放", "解除刑事拘留", "调解结案", "撤销案件", "结案")) and _has_any(text, ("罗贤涛", "易承桂", "杨周武", "刘力飚")):
        subject = "杨周武" if "杨周武" in text else "刘力飚" if "刘力飚" in text else "同乐派出所"
        obj = next((name for name in ("罗贤涛", "易承桂") if name in text), "案件处置结果")
        relation = "促成释放" if _has_any(text, ("释放", "解除刑事拘留")) else "调解结案" if "调解" in text else "处置案件"
        return _make_fact(category, "案件处置", subject, relation, obj, text, time, passage, 0.82)

    if category == "behavior" and _has_any(text, ("火灾", "死亡", "受伤", "事故调查", "履职情况专报", "严重后果")):
        subject = "舞王俱乐部" if "舞王" in text else "案件后果"
        relation = "发生火灾/严重后果" if _has_any(text, ("火灾", "死亡", "受伤")) else "进入事故调查"
        obj = "火灾事故" if "火灾" in text else "事故调查"
        return _make_fact(category, "案件处置", subject, relation, obj, text, time, passage, 0.76)

    if category == "behavior" and len(names) >= 2 and _has_any(text, ("接警", "鉴定", "立案", "拘留", "释放", "调解", "请托", "指派", "赔偿", "侦查")):
        relation = _infer_relation(text)
        return _make_fact(category, _relation_group(relation), names[0], relation, names[1], text, time, passage, 0.66)

    return None


def _make_fact(
    category: str,
    group: str,
    subject: str,
    relation: str,
    obj: str,
    text: str,
    time: str | None,
    passage: TracePassage,
    confidence: float,
) -> PortraitFact:
    evidence_ids = [passage.evidence_id] if passage.evidence_id else []
    fact_key = f"{category}:{subject}:{relation}:{obj}:{text[:80]}"
    return PortraitFact(
        fact_id=f"pf_{abs(hash(fact_key))}",
        category=category,
        group=group,
        subject=subject,
        relation=relation,
        object=obj,
        text=text,
        time=time,
        evidence_ids=evidence_ids,
        passages=[passage],
        confidence=confidence,
        source="hipporag",
    )


def _facts_from_graph(graph, category: str) -> list[PortraitFact]:
    node_labels = {node.node_id: node.label for node in graph.nodes}
    facts: list[PortraitFact] = []
    for edge in graph.edges:
        subject = _clean_node_label(node_labels.get(edge.source_id, edge.source_id))
        obj = _clean_node_label(node_labels.get(edge.target_id, edge.target_id))
        relation = edge.relation
        group = _relation_group(relation)
        if group == "其他关系":
            continue
        if subject == obj or not (subject in CASE_NAMES or obj in CASE_NAMES):
            continue
        if category == "relationship" and group == "案件处置":
            continue
        if category == "behavior" and group not in {"职务/指派", "资金/利益", "案件处置", "请托/协调"}:
            continue
        text = f"{subject} {relation} {obj}"
        time = edge.timestamp or str(edge.properties.get("time") or edge.properties.get("time_sample") or "") or None
        facts.append(
            PortraitFact(
                fact_id=f"pf_graph_{edge.edge_id}",
                category=category,
                group=group,
                subject=subject,
                relation=relation,
                object=obj,
                text=text,
                time=time,
                evidence_ids=edge.evidence_ids,
                passages=[],
                confidence=float(edge.confidence or 0.5),
                source="graph",
            )
        )
    return facts


def _dedupe_facts(facts: list[PortraitFact]) -> list[PortraitFact]:
    best: dict[str, PortraitFact] = {}
    for fact in facts:
        key = f"{fact.category}:{fact.subject}:{fact.relation}:{fact.object}"
        current = best.get(key)
        if current is None or fact.confidence > current.confidence or (fact.passages and not current.passages):
            best[key] = fact
    return sorted(best.values(), key=lambda item: item.confidence, reverse=True)


def _split_fact_sentences(text: str) -> list[str]:
    return [
        _clean_fact_text(part)
        for part in re.split(r"\n+|(?<=[。！？；])\s*", text or "")
        if 8 <= len(_clean_fact_text(part)) <= 280
    ]


def _clean_fact_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lstrip("-*# "))


def _extract_time(text: str) -> str | None:
    match = re.search(r"\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2}|\d{4}年\d{1,2}月|\d{1,2}月\d{1,2}日", text)
    return match.group(0) if match else None


def _extract_amount(text: str) -> str:
    match = re.search(r"\d+(?:\.\d+)?\s*(?:万)?元", text)
    return match.group(0) if match else ""


def _infer_relation(text: str) -> str:
    for word in ("请托", "指派", "安排", "调解", "释放", "拘留", "赔偿", "立案", "侦查"):
        if word in text:
            return "指派/安排" if word == "安排" else word
    return "关联"


def _relation_group(relation: str) -> str:
    if _has_any(relation, ("请托", "协调", "通过")):
        return "请托/协调"
    if _has_any(relation, ("指派", "安排", "介入", "任职", "职务", "负责", "批准")):
        return "职务/指派"
    if _has_any(relation, ("资金", "转账", "收受", "行贿", "取现", "存入", "赔偿", "好处费")):
        return "资金/利益"
    if _has_any(relation, ("立案", "拘留", "释放", "调解", "撤案", "结案", "侦查", "处置")):
        return "案件处置"
    return "其他关系"


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_llm_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            detail = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            detail = ""
        return f"HTTP {exc.code} {detail[:240]}"
    return str(exc)[:240]


def _looks_like_structured_row(text: str) -> bool:
    return text.count(",") >= 5 or sum(1 for marker in ("synthetic/", ".csv", ".xlsx", "CALL00") if marker in text) >= 2


def _clean_node_label(value: str) -> str:
    return str(value or "").replace("entity:", "").strip()

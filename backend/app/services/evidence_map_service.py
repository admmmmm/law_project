from __future__ import annotations

import re
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

from app.core.errors import not_found
from app.schemas.analysis_skill import RuleFinding
from app.schemas.document_mother import DocumentMotherNode
from app.schemas.evidence_map import (
    EvidenceContainmentEdge,
    EvidenceDocumentEdge,
    EvidenceDocumentNode,
    EvidenceMap,
    EvidenceMapLayer,
    EvidenceMapLayerEdge,
    EvidenceMapLayerNode,
    EvidenceMapLayerStats,
    EvidenceMapLegend,
    EvidenceMapLegendItem,
    EvidenceMapStats,
    EvidencePassageEdge,
    EvidencePassageNode,
    EvidenceTripleNode,
)
from app.schemas.graph import InvestigationGraph
from app.schemas.ingestion import EvidenceRecord, ExtractedTriple, ExtractionResult, PassageRecord
from app.storage.memory_store import MemoryStore


ALLOWED_MAP_TAGS = {
    "立案阶段材料",
    "接警材料",
    "伤情材料",
    "强制措施材料",
    "释放材料",
    "调解/撤案材料",
    "履职监管材料",
    "事故后果材料",
    "资金往来线索",
    "通信联络线索",
    "审批人关联",
    "权限节点",
    "流程转向材料",
    "来源质量待核查",
    "需人工复核",
}

FORBIDDEN_WORDS = (
    "徇私枉法",
    "受贿",
    "行贿",
    "玩忽职守",
    "包庇",
    "构成犯罪",
    "枉法调解",
    "违规释放",
    "因果关系成立",
)

STAGE_ORDER = ["接警", "受案登记", "伤情鉴定/送检", "立案", "强制措施", "释放", "调解/撤案", "检察侦查"]
AUTHORITY_WORDS = ("审批", "批准", "指派", "安排", "同意", "释放", "签发", "决定")
GENERIC_ENTITIES = {"证据", "案件", "材料", "情况", "时间", "记录", "通知", "决定", "报告", "人员", "民警", "公安", "检察", "法院", "舞王俱乐部"}


class EvidenceMapService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def get_map(self, case_id: str) -> EvidenceMap:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            evidence = list(self.store.evidence.get(case_id, []))
            raw_contents = dict(self.store.raw_contents)
            extractions = {item.evidence_id: self.store.extractions.get(item.evidence_id) for item in evidence}
            mother_nodes = {node.evidence_id: node for node in self.store.document_mother_nodes.get(case_id, [])}
            rule_runs = list(self.store.rule_pack_runs.get(case_id, []))
            raw_graph = self.store.graphs.get(case_id)
        return EvidenceMapBuilder(case_id, evidence, raw_contents, extractions, mother_nodes, rule_runs, raw_graph).build()


class EvidenceMapBuilder:
    """Builds a graph-page evidence map without invoking LLMs.

    原始图谱过于碎片化，直接展示会导致线过多、用户无法理解证据结构。
    三层证据地图用于：文件层看全局，片段层看 HippoRAG passage，
    原始图谱层看实体与关系网络。
    """

    def __init__(
        self,
        case_id: str,
        evidence: list[EvidenceRecord],
        raw_contents: dict[str, str],
        extractions: dict[str, ExtractionResult | None],
        mother_nodes: dict[str, DocumentMotherNode],
        rule_runs: list[Any],
        raw_graph: InvestigationGraph | None = None,
    ) -> None:
        self.case_id = case_id
        self.evidence = evidence
        self.raw_contents = raw_contents
        self.extractions = extractions
        self.mother_nodes = mother_nodes
        self.raw_graph = raw_graph
        self.findings = [finding for run in rule_runs for finding in getattr(run, "findings", [])]
        self.doc_by_evidence: dict[str, str] = {}
        self.passages_by_doc: dict[str, list[EvidencePassageNode]] = defaultdict(list)
        self.triples_by_doc: dict[str, list[EvidenceTripleNode]] = defaultdict(list)
        self.triples_by_passage: dict[str, list[EvidenceTripleNode]] = defaultdict(list)

    def build(self) -> EvidenceMap:
        documents = self._build_documents()
        passages, triples, containment_edges = self._build_passages_and_triples()
        documents = [
            doc.model_copy(
                update={
                    "passage_count": len(self.passages_by_doc.get(doc.id, [])),
                    "triple_count": len(self.triples_by_doc.get(doc.id, [])),
                    "quality_status": doc.quality_status if self.passages_by_doc.get(doc.id) and self.triples_by_doc.get(doc.id) else "needs_review",
                }
            )
            for doc in documents
        ]
        document_edges = self._limit_document_edges(self._build_document_edges(documents, passages, triples))
        passage_edges = self._build_passage_edges(passages, triples)
        layers = self._build_layers(documents, passages, triples, document_edges, passage_edges)
        return EvidenceMap(
            case_id=self.case_id,
            documents=documents,
            passages=passages,
            triples=triples,
            document_edges=document_edges,
            passage_edges=passage_edges,
            containment_edges=containment_edges,
            layers=layers,
            stats=EvidenceMapStats(
                documents=len(documents),
                passages=len(passages),
                raw_nodes=len(layers.get("raw", EvidenceMapLayer(label="原始图谱层")).nodes),
                raw_edges=len(layers.get("raw", EvidenceMapLayer(label="原始图谱层")).edges),
            ),
        )

    def _build_layers(
        self,
        documents: list[EvidenceDocumentNode],
        passages: list[EvidencePassageNode],
        triples: list[EvidenceTripleNode],
        document_edges: list[EvidenceDocumentEdge],
        passage_edges: list[EvidencePassageEdge],
    ) -> dict[str, EvidenceMapLayer]:
        document_nodes = [
            EvidenceMapLayerNode(
                id=_layer_doc_id(doc.id),
                label=doc.title or doc.id,
                type="document",
                layer="document",
                summary=doc.summary,
                properties={
                    "doc_type": doc.doc_type,
                    "process_stage": doc.process_stage,
                    "proof_purpose": doc.proof_purpose,
                    "quality_status": doc.quality_status,
                    "passage_count": doc.passage_count,
                    "triple_count": doc.triple_count,
                    "finding_count": doc.finding_count,
                    "map_tags": ",".join(doc.map_tags),
                },
                source={"evidence_id": doc.evidence_id, "passage_id": None},
            )
            for doc in documents
        ]
        document_edges_layer = [
            EvidenceMapLayerEdge(
                id=edge.id,
                source=_layer_doc_id(edge.source),
                target=_layer_doc_id(edge.target),
                type=edge.type,
                label=edge.label,
                properties={
                    "reason": edge.reason,
                    "weight": edge.weight,
                    "shared_entities": ",".join(edge.shared_entities),
                    "visible_by_default": edge.visible_by_default,
                },
                source_refs=[{"evidence_id": None, "passage_id": pid} for pid in edge.supporting_passage_ids],
            )
            for edge in document_edges
        ]

        passage_nodes = [
            EvidenceMapLayerNode(
                id=passage.id,
                label=passage.summary or passage.text_preview or passage.id,
                type="passage",
                layer="passage",
                summary=passage.text_preview,
                properties={
                    "parent_doc_id": _layer_doc_id(passage.parent_doc_id),
                    "passage_index": passage.passage_index,
                    "triple_count": passage.triple_count,
                    "entities": ",".join(passage.entities),
                },
                source={"evidence_id": passage.evidence_id, "passage_id": passage.id},
            )
            for passage in passages
        ]
        passage_edges_layer = [
            EvidenceMapLayerEdge(
                id=edge.id,
                source=edge.source,
                target=edge.target,
                type=edge.type,
                label=edge.label,
                properties={
                    "weight": edge.weight,
                    "shared_entities": ",".join(edge.shared_entities),
                    "visible_by_default": edge.visible_by_default,
                },
                source_refs=[{"evidence_id": None, "passage_id": edge.source}, {"evidence_id": None, "passage_id": edge.target}],
            )
            for edge in passage_edges
        ]

        raw_nodes, raw_edges = self._raw_layer()
        layers = {
            "document": self._closed_layer("文件证据图", document_nodes, document_edges_layer, editable=False),
            "passage": self._closed_layer("片段证据图", passage_nodes, passage_edges_layer, editable=False),
            "raw": self._closed_layer("原始图谱层", raw_nodes, raw_edges, editable=True),
        }
        return layers

    def _raw_layer(self) -> tuple[list[EvidenceMapLayerNode], list[EvidenceMapLayerEdge]]:
        if not self.raw_graph:
            return [], []
        id_map = {node.node_id: _layer_raw_id(node.node_id, node.type) for node in self.raw_graph.nodes}
        nodes = [
            EvidenceMapLayerNode(
                id=id_map[node.node_id],
                label=node.label,
                type=node.type or "entity",
                layer="raw",
                summary="",
                properties={
                    **node.properties,
                    "raw_id": node.node_id,
                    "tags": ",".join(node.tags),
                    "manually_verified": node.manually_verified,
                    "timestamp": node.timestamp,
                },
                source={"evidence_id": node.evidence_ids[0] if node.evidence_ids else None, "passage_id": None},
            )
            for node in self.raw_graph.nodes
        ]
        edges = [
            EvidenceMapLayerEdge(
                id=edge.edge_id,
                source=id_map.get(edge.source_id, _layer_raw_id(edge.source_id, "entity")),
                target=id_map.get(edge.target_id, _layer_raw_id(edge.target_id, "entity")),
                type=edge.relation or "fact_relation",
                label=edge.relation,
                properties={
                    **edge.properties,
                    "raw_id": edge.edge_id,
                    "confidence": edge.confidence,
                    "tags": ",".join(edge.tags),
                    "manually_verified": edge.manually_verified,
                    "timestamp": edge.timestamp,
                },
                source_refs=[{"evidence_id": evidence_id, "passage_id": None} for evidence_id in edge.evidence_ids],
            )
            for edge in self.raw_graph.edges
        ]
        return nodes, edges

    def _closed_layer(
        self,
        label: str,
        nodes: list[EvidenceMapLayerNode],
        edges: list[EvidenceMapLayerEdge],
        editable: bool,
    ) -> EvidenceMapLayer:
        deduped_nodes = _dedupe_layer_nodes(nodes)
        node_ids = {node.id for node in deduped_nodes}
        closed_edges = _dedupe_layer_edges([edge for edge in edges if edge.source in node_ids and edge.target in node_ids])
        return EvidenceMapLayer(
            label=label,
            nodes=deduped_nodes,
            edges=closed_edges,
            legend=_legend_for(deduped_nodes, closed_edges),
            stats=EvidenceMapLayerStats(nodes=len(deduped_nodes), edges=len(closed_edges)),
            editable=editable,
        )

    def _build_documents(self) -> list[EvidenceDocumentNode]:
        finding_count_by_doc = Counter(
            self._resolve_doc_ref(doc_id) for finding in self.findings for doc_id in finding.supporting_documents
        )
        documents: list[EvidenceDocumentNode] = []
        for index, item in enumerate(self.evidence):
            mother = self.mother_nodes.get(item.evidence_id)
            doc_id = _doc_id(item, mother, index)
            self.doc_by_evidence[item.evidence_id] = doc_id
            content = self.raw_contents.get(item.evidence_id, item.content_preview)
            doc_type = mother.doc_type if mother else _infer_doc_type(item.title, content)
            process_stage = mother.process_stage if mother else _infer_process_stage(doc_type, item.title, content)
            summary = _neutral_text(mother.summary if mother else _shorten(content, 110))
            proof_purpose = _neutral_text(mother.proof_purpose if mother else f"用于展示该文件在“{process_stage}”阶段的材料留痕。")
            tags = _neutral_map_tags(doc_type, process_stage, item.title, content, mother)
            quality_status = mother.quality_status if mother else ("needs_review" if not self.extractions.get(item.evidence_id) else "ok")
            documents.append(
                EvidenceDocumentNode(
                    id=doc_id,
                    evidence_id=item.evidence_id,
                    title=_neutral_text(item.title),
                    doc_type=_neutral_text(doc_type),
                    process_stage=_neutral_text(process_stage),
                    summary=summary,
                    proof_purpose=proof_purpose,
                    map_tags=tags,
                    finding_count=finding_count_by_doc.get(doc_id, 0),
                    quality_status=quality_status,
                    event_time=mother.event_time if mother else _extract_time(content),
                    formation_time=mother.formation_time if mother else _extract_time(item.title + "\n" + content),
                )
            )
        return documents

    def _build_passages_and_triples(self) -> tuple[list[EvidencePassageNode], list[EvidenceTripleNode], list[EvidenceContainmentEdge]]:
        passages: list[EvidencePassageNode] = []
        triples: list[EvidenceTripleNode] = []
        containment: list[EvidenceContainmentEdge] = []
        for item in self.evidence:
            doc_id = self.doc_by_evidence[item.evidence_id]
            extraction = self.extractions.get(item.evidence_id)
            raw_passages = _passages(item, self.raw_contents.get(item.evidence_id, item.content_preview), extraction)
            raw_triples = extraction.triples if extraction else []
            for idx, passage in enumerate(raw_passages):
                passage_id = f"passage:{item.evidence_id}:{idx}"
                related = _triples_for_passage(idx, raw_passages, raw_triples)
                entities = _passage_entities(passage.text, related)
                node = EvidencePassageNode(
                    id=passage_id,
                    parent_doc_id=doc_id,
                    evidence_id=item.evidence_id,
                    passage_index=idx,
                    summary=_shorten(_sentence_summary(passage.text), 90),
                    text_preview=_shorten(passage.text, 50),
                    text=passage.text[:1200],
                    triple_count=len(related),
                    entities=entities[:12],
                )
                passages.append(node)
                self.passages_by_doc[doc_id].append(node)
                containment.append(EvidenceContainmentEdge(id=f"contains:{doc_id}:{passage_id}", source=doc_id, target=passage_id, type="CONTAINS"))
            if not raw_passages:
                passage_id = f"passage:{item.evidence_id}:0"
                node = EvidencePassageNode(
                    id=passage_id,
                    parent_doc_id=doc_id,
                    evidence_id=item.evidence_id,
                    passage_index=0,
                    summary="该文件暂无可用片段。",
                    text_preview=item.content_preview[:50],
                    text=item.content_preview,
                    triple_count=len(raw_triples),
                    entities=_passage_entities(item.content_preview, raw_triples)[:12],
                )
                passages.append(node)
                self.passages_by_doc[doc_id].append(node)
                containment.append(EvidenceContainmentEdge(id=f"contains:{doc_id}:{passage_id}", source=doc_id, target=passage_id, type="CONTAINS"))
                raw_passages = [PassageRecord(text=item.content_preview, evidence_id=item.evidence_id)]
            for triple_idx, triple in enumerate(raw_triples):
                passage_index = _triple_passage_index(triple_idx, triple, raw_passages)
                parent_passage_id = f"passage:{item.evidence_id}:{passage_index}"
                node = EvidenceTripleNode(
                    id=f"triple:{item.evidence_id}:{triple_idx}",
                    parent_passage_id=parent_passage_id,
                    subject=_neutral_text(triple.subject),
                    predicate=_neutral_text(triple.relation),
                    object=_neutral_text(triple.object),
                    confidence=_confidence_label(triple.properties.get("confidence")),
                    supporting_text=_supporting_text(triple, raw_passages[passage_index].text if passage_index < len(raw_passages) else ""),
                    source_doc_id=doc_id,
                    evidence_id=item.evidence_id,
                )
                triples.append(node)
                self.triples_by_doc[doc_id].append(node)
                self.triples_by_passage[parent_passage_id].append(node)
                containment.append(EvidenceContainmentEdge(id=f"extracts:{parent_passage_id}:{node.id}", source=parent_passage_id, target=node.id, type="EXTRACTS"))
        for doc in self.doc_by_evidence.values():
            pass
        return passages, triples, containment

    def _build_document_edges(self, documents: list[EvidenceDocumentNode], passages: list[EvidencePassageNode], triples: list[EvidenceTripleNode]) -> list[EvidenceDocumentEdge]:
        edges: dict[tuple[str, str, str], EvidenceDocumentEdge] = {}
        doc_map = {doc.id: doc for doc in documents}
        entity_docs = _entity_docs(passages, triples)
        entity_freq = Counter(entity for entity, docs in entity_docs.items() for _ in docs)

        for left, right in combinations(documents, 2):
            key_entities = _shared_key_entities(left.id, right.id, entity_docs, entity_freq)
            if key_entities:
                weight = min(0.9, 0.25 + sum(_entity_weight(entity, entity_freq) for entity in key_entities))
                self._add_document_edge(edges, left.id, right.id, "SHARED_ENTITY", f"共同关联{'、'.join(key_entities[:3])}", "两份文件出现相同关键实体。", key_entities, weight)

            if _adjacent_stage(left, right) and self._process_next_supported(left, right, key_entities):
                weight = 0.72 if key_entities else 0.55
                self._add_document_edge(edges, left.id, right.id, "PROCESS_NEXT", "流程相邻", "两份文件位于相邻流程阶段，并存在时间、实体或底层证据关联。", key_entities, weight)

        for finding in self.findings:
            doc_ids = [self._resolve_doc_ref(doc_id) for doc_id in finding.supporting_documents]
            doc_ids = [doc_id for doc_id in doc_ids if doc_id in doc_map]
            for left_id, right_id in combinations(sorted(set(doc_ids)), 2):
                self._add_document_edge(edges, left_id, right_id, "SUPPORTS_SAME_FINDING", "共同支撑同一核查项", "两份文件共同出现在同一规则核查结果的支撑文件中。", [], 0.82)

        authority_docs = self._authority_docs()
        for person, doc_ids in authority_docs.items():
            for left_id, right_id in combinations(sorted(doc_ids), 2):
                self._add_document_edge(edges, left_id, right_id, "AUTHORITY_CHAIN", f"{person}相关权限链", "多份文件共同体现同一人员的审批、批准、指派、同意或释放等权力动作。", [person], 0.86)

        return [edge for edge in edges.values() if edge.weight >= 0.35]

    def _resolve_doc_ref(self, value: str) -> str:
        if value in self.doc_by_evidence.values():
            return value
        if value in self.doc_by_evidence:
            return self.doc_by_evidence[value]
        for evidence_id, doc_id in self.doc_by_evidence.items():
            if value and (value in evidence_id or evidence_id in value):
                return doc_id
        return value

    def _add_document_edge(
        self,
        edges: dict[tuple[str, str, str], EvidenceDocumentEdge],
        source: str,
        target: str,
        edge_type: str,
        label: str,
        reason: str,
        shared_entities: list[str],
        weight: float,
    ) -> None:
        left, right = sorted([source, target])
        key = (left, right, edge_type)
        support_passages = [p.id for p in (self.passages_by_doc.get(left, []) + self.passages_by_doc.get(right, [])) if set(p.entities) & set(shared_entities)][:6]
        support_triples = [t.id for t in (self.triples_by_doc.get(left, []) + self.triples_by_doc.get(right, [])) if t.subject in shared_entities or t.object in shared_entities][:8]
        candidate = EvidenceDocumentEdge(
            id=f"doc-edge:{edge_type}:{left}:{right}",
            source=left,
            target=right,
            type=edge_type,
            label=_neutral_text(label),
            reason=_neutral_text(reason),
            supporting_passage_ids=support_passages,
            supporting_triple_ids=support_triples,
            shared_entities=shared_entities[:3],
            weight=round(min(weight, 1.0), 3),
            visible_by_default=weight >= 0.35,
        )
        if key not in edges or candidate.weight > edges[key].weight:
            edges[key] = candidate

    def _limit_document_edges(self, edges: list[EvidenceDocumentEdge]) -> list[EvidenceDocumentEdge]:
        result: list[EvidenceDocumentEdge] = []
        degree = Counter()
        for edge in sorted(edges, key=lambda item: (-item.weight, item.type, item.id)):
            if degree[edge.source] >= 8 or degree[edge.target] >= 8:
                continue
            result.append(edge)
            degree[edge.source] += 1
            degree[edge.target] += 1
        return sorted(result, key=lambda item: (item.source, item.target, item.type))

    def _process_next_supported(self, left: EvidenceDocumentNode, right: EvidenceDocumentNode, shared_entities: list[str]) -> bool:
        if _time_ordered(left, right):
            return True
        if shared_entities:
            return True
        if any({left.id, right.id}.issubset(set(f.supporting_documents)) for f in self.findings):
            return True
        left_entities = {entity for passage in self.passages_by_doc.get(left.id, []) for entity in passage.entities}
        right_entities = {entity for passage in self.passages_by_doc.get(right.id, []) for entity in passage.entities}
        return bool((left_entities & right_entities) - GENERIC_ENTITIES)

    def _authority_docs(self) -> dict[str, set[str]]:
        mapping: dict[str, set[str]] = defaultdict(set)
        for doc_id, triples in self.triples_by_doc.items():
            for triple in triples:
                text = f"{triple.subject} {triple.predicate} {triple.object}"
                if any(word in text for word in AUTHORITY_WORDS):
                    for entity in (triple.subject, triple.object):
                        if _looks_like_person(entity):
                            mapping[entity].add(doc_id)
        return mapping

    def _build_passage_edges(self, passages: list[EvidencePassageNode], triples: list[EvidenceTripleNode]) -> list[EvidencePassageEdge]:
        edges: dict[tuple[str, str, str], EvidencePassageEdge] = {}
        by_doc: dict[str, list[EvidencePassageNode]] = defaultdict(list)
        for passage in passages:
            by_doc[passage.parent_doc_id].append(passage)
        for rows in by_doc.values():
            ordered = sorted(rows, key=lambda item: item.passage_index)
            for left, right in zip(ordered, ordered[1:]):
                edges[(left.id, right.id, "SAME_DOCUMENT_ORDER")] = EvidencePassageEdge(
                    id=f"passage-edge:order:{left.id}:{right.id}",
                    source=left.id,
                    target=right.id,
                    type="SAME_DOCUMENT_ORDER",
                    label="同文件相邻片段",
                    supporting_triple_ids=[],
                    weight=0.5,
                )
        entity_passages: dict[str, list[EvidencePassageNode]] = defaultdict(list)
        for passage in passages:
            for entity in passage.entities:
                if entity not in GENERIC_ENTITIES:
                    entity_passages[entity].append(passage)
        for entity, rows in entity_passages.items():
            if len(rows) > 12:
                continue
            for left, right in combinations(rows[:8], 2):
                if left.id == right.id:
                    continue
                key = tuple(sorted([left.id, right.id]) + ["SHARED_ENTITY"])  # type: ignore[list-item]
                if key in edges:
                    continue
                related = [t.id for t in self.triples_by_passage.get(left.id, []) + self.triples_by_passage.get(right.id, []) if entity in (t.subject, t.object)][:6]
                edges[key] = EvidencePassageEdge(
                    id=f"passage-edge:shared:{key[0]}:{key[1]}:{entity}",
                    source=key[0],
                    target=key[1],
                    type="SHARED_ENTITY",
                    label=f"共同关联{entity}",
                    supporting_triple_ids=related,
                    shared_entities=[entity],
                    weight=0.45,
                )
        doc_to_passages = {doc_id: [p.id for p in rows] for doc_id, rows in by_doc.items()}
        for finding in self.findings:
            support_passages = [pid for doc_id in finding.supporting_documents for pid in doc_to_passages.get(doc_id, [])]
            for left_id, right_id in combinations(support_passages[:10], 2):
                key = tuple(sorted([left_id, right_id]) + ["SUPPORTS_SAME_FINDING"])  # type: ignore[list-item]
                edges.setdefault(
                    key,
                    EvidencePassageEdge(
                        id=f"passage-edge:finding:{key[0]}:{key[1]}",
                        source=key[0],
                        target=key[1],
                        type="SUPPORTS_SAME_FINDING",
                        label="共同支撑同一核查项",
                        weight=0.7,
                    ),
                )
        return [edge for edge in edges.values() if edge.weight >= 0.35]


def _doc_id(evidence: EvidenceRecord, mother: DocumentMotherNode | None, index: int) -> str:
    if mother:
        return mother.doc_id
    match = re.search(r"证据\d+(?:-\d+)?", evidence.title)
    return match.group(0) if match else f"doc:{index + 1}:{evidence.evidence_id}"


def _layer_doc_id(value: str) -> str:
    text = str(value or "").strip()
    return text if text.startswith("doc:") else f"doc:{text}"


def _layer_raw_id(value: str, node_type: str) -> str:
    text = str(value or "").strip()
    if ":" in text:
        return text
    prefix = {
        "person": "person",
        "organization": "org",
        "account": "account",
        "transaction": "fact",
        "event": "event",
        "time": "time",
        "evidence": "evidence",
        "document": "doc",
    }.get(str(node_type or "").lower(), "entity")
    return f"{prefix}:{text}"


def _dedupe_layer_nodes(nodes: list[EvidenceMapLayerNode]) -> list[EvidenceMapLayerNode]:
    result: dict[str, EvidenceMapLayerNode] = {}
    for node in nodes:
        if not node.id:
            continue
        if node.id not in result:
            result[node.id] = node
    return list(result.values())


def _dedupe_layer_edges(edges: list[EvidenceMapLayerEdge]) -> list[EvidenceMapLayerEdge]:
    result: dict[str, EvidenceMapLayerEdge] = {}
    for edge in edges:
        if not edge.id or not edge.source or not edge.target:
            continue
        if edge.id not in result:
            result[edge.id] = edge
    return list(result.values())


def _legend_for(nodes: list[EvidenceMapLayerNode], edges: list[EvidenceMapLayerEdge]) -> EvidenceMapLegend:
    node_types = sorted({node.type or "entity" for node in nodes})
    edge_types = sorted({edge.type or "related" for edge in edges})
    return EvidenceMapLegend(
        node_types=[EvidenceMapLegendItem(type=item, label=_node_type_label(item), description=_node_type_desc(item)) for item in node_types],
        edge_types=[EvidenceMapLegendItem(type=item, label=_edge_type_label(item), description=_edge_type_desc(item)) for item in edge_types],
    )


def _node_type_label(node_type: str) -> str:
    mapping = {
        "document": "文件节点",
        "passage": "片段节点",
        "person": "人物节点",
        "organization": "机构节点",
        "org": "机构节点",
        "event": "事件节点",
        "time": "时间节点",
        "account": "账户 / 资金节点",
        "transaction": "资金流水节点",
        "evidence": "证据节点",
        "fact": "事实节点",
        "entity": "实体节点",
        "call_record": "通信记录节点",
        "fund_flow": "资金往来节点",
    }
    return mapping.get(node_type, f"{node_type} 节点")


def _node_type_desc(node_type: str) -> str:
    mapping = {
        "document": "一份已导入证据材料。",
        "passage": "证据材料中的一个原文片段。",
        "person": "案件图谱中的人员对象。",
        "organization": "案件图谱中的机构或单位对象。",
        "account": "账户、现金柜台、ATM 等资金对象。",
        "transaction": "结构化资金流水或交易记录。",
        "event": "案情事件或程序节点。",
        "time": "时间点或时间段。",
    }
    return mapping.get(node_type, "当前图层中出现的节点类型。")


def _edge_type_label(edge_type: str) -> str:
    mapping = {
        "CONTAINS": "包含关系",
        "SAME_DOCUMENT_ORDER": "同文件相邻",
        "SHARED_ENTITY": "共享实体",
        "SUPPORTS_SAME_FINDING": "共同支撑核查项",
        "AUTHORITY_CHAIN": "权限链",
        "PROCESS_NEXT": "流程相邻",
        "contains": "包含关系",
        "supports": "支撑关系",
        "related": "关联关系",
        "fact_relation": "事实关系",
        "source_ref": "来源关系",
        "mentions": "提及关系",
    }
    return mapping.get(edge_type, edge_type)


def _edge_type_desc(edge_type: str) -> str:
    mapping = {
        "CONTAINS": "文件包含片段。",
        "SAME_DOCUMENT_ORDER": "同一文件内相邻片段。",
        "SHARED_ENTITY": "两端对象共享关键实体。",
        "SUPPORTS_SAME_FINDING": "两端对象共同支撑同一规则核查结果。",
        "AUTHORITY_CHAIN": "多份材料共同体现审批、批准、指派、同意或释放等权力动作。",
        "PROCESS_NEXT": "两个文件位于相邻流程阶段，且存在支撑依据。",
    }
    return mapping.get(edge_type, "当前图层中出现的关系类型。")


def _passages(evidence: EvidenceRecord, content: str, extraction: ExtractionResult | None) -> list[PassageRecord]:
    source_rows = [passage.text for passage in extraction.passages] if extraction and extraction.passages else []
    if not source_rows:
        source_rows = re.split(r"\n+|(?<=[。！？；])", content)
    chunks = _merge_passage_rows(source_rows)
    return [PassageRecord(text=chunk[:1000], evidence_id=evidence.evidence_id) for chunk in chunks[:40]]


def _merge_passage_rows(rows: list[str]) -> list[str]:
    chunks: list[str] = []
    buffer: list[str] = []
    size = 0
    for row in rows:
        text = _clean_passage_row(row)
        if not text:
            continue
        if len(text) >= 180:
            if buffer:
                chunks.append(" ".join(buffer))
                buffer = []
                size = 0
            chunks.append(text)
            continue
        buffer.append(text)
        size += len(text)
        if size >= 260:
            chunks.append(" ".join(buffer))
            buffer = []
            size = 0
    if buffer:
        chunks.append(" ".join(buffer))
    return [chunk for chunk in chunks if len(chunk) >= 18]


def _clean_passage_row(row: str) -> str:
    text = _neutral_text(str(row or "").strip())
    if not text:
        return ""
    text = re.sub(r"^[-*]\s*", "", text).strip()
    if re.fullmatch(r"#+\s*.*", text):
        return ""
    if re.fullmatch(r"(证据类型|案情时间|案情日期|对应案情|证明事项|来源文件|文书内容)[:：].*", text):
        return ""
    if re.fullmatch(r"证据\d+(?:-\d+)?[:：_].*", text):
        return ""
    if text.startswith(("可用于", "可与", "需要进一步核查", "备注", "说明")):
        return ""
    if text in {"中华人民共和国", "文书内容"}:
        return ""
    return text


def _triples_for_passage(index: int, passages: list[PassageRecord], triples: list[ExtractedTriple]) -> list[ExtractedTriple]:
    result = []
    for triple_index, triple in enumerate(triples):
        if _triple_passage_index(triple_index, triple, passages) == index:
            result.append(triple)
    if not result and index < len(passages) and passages[index].triple_index is not None and 0 <= passages[index].triple_index < len(triples):
        result.append(triples[passages[index].triple_index])
    return result


def _triple_passage_index(triple_index: int, triple: ExtractedTriple, passages: list[PassageRecord]) -> int:
    explicit = triple.properties.get("passage_index")
    if isinstance(explicit, int) and 0 <= explicit < len(passages):
        return explicit
    if isinstance(explicit, str) and explicit.isdigit() and 0 <= int(explicit) < len(passages):
        return int(explicit)
    for idx, passage in enumerate(passages):
        if triple.subject in passage.text and triple.object in passage.text:
            return idx
    return min(triple_index, max(len(passages) - 1, 0))


def _passage_entities(text: str, triples: list[ExtractedTriple]) -> list[str]:
    entities = []
    for triple in triples:
        entities.extend([triple.subject, triple.object])
    entities.extend(re.findall(r"[\u4e00-\u9fa5]{2,6}", text[:500]))
    return [item for item in dict.fromkeys(entities) if _is_key_entity(item)]


def _entity_docs(passages: list[EvidencePassageNode], triples: list[EvidenceTripleNode]) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = defaultdict(set)
    for passage in passages:
        for entity in passage.entities:
            if _is_key_entity(entity):
                mapping[entity].add(passage.parent_doc_id)
    for triple in triples:
        for entity in (triple.subject, triple.object):
            if _is_key_entity(entity):
                mapping[entity].add(triple.source_doc_id)
    return mapping


def _shared_key_entities(left_id: str, right_id: str, entity_docs: dict[str, set[str]], entity_freq: Counter[str]) -> list[str]:
    candidates = [entity for entity, doc_ids in entity_docs.items() if left_id in doc_ids and right_id in doc_ids and _is_key_entity(entity)]
    return sorted(candidates, key=lambda entity: (-_entity_weight(entity, entity_freq), entity))[:3]


def _entity_weight(entity: str, freq: Counter[str]) -> float:
    count = max(freq.get(entity, 1), 1)
    base = 0.22 if _looks_like_person(entity) else 0.16
    if entity in GENERIC_ENTITIES or count > 10:
        return 0.04
    if count > 5:
        return base / 2
    return base


def _is_key_entity(value: str) -> bool:
    text = str(value or "").strip()
    if len(text) < 2 or text in GENERIC_ENTITIES:
        return False
    if any(word in text for word in ("时间", "情况", "记录", "材料", "证明", "意见", "摘要")):
        return False
    return bool(re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", text))


def _looks_like_person(value: str) -> bool:
    return bool(re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", str(value or ""))) and value not in GENERIC_ENTITIES


def _adjacent_stage(left: EvidenceDocumentNode, right: EvidenceDocumentNode) -> bool:
    try:
        diff = abs(STAGE_ORDER.index(left.process_stage) - STAGE_ORDER.index(right.process_stage))
    except ValueError:
        return False
    return diff == 1


def _time_ordered(left: EvidenceDocumentNode, right: EvidenceDocumentNode) -> bool:
    left_time = _time_key(left.event_time or left.formation_time)
    right_time = _time_key(right.event_time or right.formation_time)
    return bool(left_time and right_time and left_time <= right_time)


def _time_key(value: str | None) -> str:
    if not value:
        return ""
    match = re.search(r"(19|20)\d{2}[-年/.]?\d{1,2}?[-月/.]?\d{0,2}", value)
    return match.group(0) if match else ""


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
        ("履职情况专报", "履职情况专报"),
        ("火灾", "事故材料"),
    ]
    for keyword, doc_type in mapping:
        if keyword in text:
            return doc_type
    return "未知文书"


def _infer_process_stage(doc_type: str, title: str, content: str) -> str:
    text = f"{title}\n{content[:500]}"
    if doc_type == "接警记录":
        return "接警"
    if doc_type == "受案登记":
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
    if doc_type == "履职情况专报" or any(word in text for word in ("巡查", "整改", "履职", "监管")):
        return "履职监管"
    if any(word in text for word in ("火灾", "死亡", "受伤", "事故")):
        return "事故后果"
    return "未归类"


def _neutral_map_tags(doc_type: str, process_stage: str, title: str, content: str, mother: DocumentMotherNode | None) -> list[str]:
    text = f"{doc_type} {process_stage} {title} {content[:500]} {' '.join(mother.risk_tags if mother else [])}"
    tags: list[str] = []
    mapping = [
        ("接警", "接警材料"),
        ("伤情", "伤情材料"),
        ("鉴定", "伤情材料"),
        ("立案", "立案阶段材料"),
        ("拘留", "强制措施材料"),
        ("强制措施", "强制措施材料"),
        ("释放", "释放材料"),
        ("调解", "调解/撤案材料"),
        ("撤案", "调解/撤案材料"),
        ("履职", "履职监管材料"),
        ("监管", "履职监管材料"),
        ("火灾", "事故后果材料"),
        ("死亡", "事故后果材料"),
        ("受伤", "事故后果材料"),
        ("银行", "资金往来线索"),
        ("流水", "资金往来线索"),
        ("转账", "资金往来线索"),
        ("通话", "通信联络线索"),
        ("短信", "通信联络线索"),
        ("批准", "审批人关联"),
        ("审批", "审批人关联"),
        ("指派", "权限节点"),
        ("同意", "权限节点"),
    ]
    for keyword, tag in mapping:
        if keyword in text and tag in ALLOWED_MAP_TAGS:
            tags.append(tag)
    if process_stage in {"释放", "调解/撤案"}:
        tags.append("流程转向材料")
    if mother and mother.quality_status != "ok":
        tags.append("需人工复核")
    if not tags:
        tags.append("需人工复核")
    return [tag for tag in dict.fromkeys(tags) if tag in ALLOWED_MAP_TAGS][:8]


def _extract_time(text: str) -> str | None:
    match = re.search(r"(19|20)\d{2}[-年/.]\d{1,2}[-月/.]\d{1,2}日?|(?:19|20)\d{2}年\d{1,2}月|(?:19|20)\d{2}-\d{1,2}-\d{1,2}", text)
    return match.group(0) if match else None


def _neutral_text(text: str) -> str:
    value = str(text or "")
    for word in FORBIDDEN_WORDS:
        value = value.replace(word, "")
    return re.sub(r"\s+", " ", value).strip()


def _shorten(text: str, length: int) -> str:
    value = _neutral_text(text)
    return value[:length] + ("..." if len(value) > length else "")


def _sentence_summary(text: str) -> str:
    return re.split(r"(?<=[。！？；])|\n", text.strip())[0] if text.strip() else ""


def _confidence_label(value: Any) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return "medium"
    if score >= 0.75:
        return "high"
    if score < 0.45:
        return "low"
    return "medium"


def _supporting_text(triple: ExtractedTriple, fallback: str) -> str:
    raw = triple.properties.get("supporting_text") or triple.properties.get("passage") or fallback
    return _shorten(str(raw), 180)

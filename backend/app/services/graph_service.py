from fastapi import HTTPException, status

from app.core.errors import bad_request, not_found
from app.adapters.algorithm import enrich_graph_tags
from app.schemas.graph import GraphEdge, GraphInterventionRequest, GraphNode, InvestigationGraph, RawGraphActionRequest, RawGraphActionResponse
from app.storage.memory_store import MemoryStore


class GraphService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def get_graph(self, case_id: str) -> InvestigationGraph:
        with self.store.lock:
            # The graph page may be opened before evidence import/analysis, or after an
            # in-memory reset while the frontend still holds the last case id.
            # Returning an empty graph keeps the UI usable instead of surfacing a 404.
            graph = self.store.graphs.setdefault(case_id, InvestigationGraph(case_id=case_id))
            return enrich_graph_tags(graph)

    def get_merged_graph(self, case_id: str, selected_case_ids: list[str]) -> InvestigationGraph:
        with self.store.lock:
            base = self.store.graphs.setdefault(case_id, InvestigationGraph(case_id=case_id))
            merged = InvestigationGraph(case_id=f"tmp:{case_id}:{','.join(selected_case_ids)}")
            node_map = {}
            for source_case_id, graph in [(case_id, base), *[(item, self.store.graphs.get(item)) for item in selected_case_ids]]:
                if not graph:
                    continue
                for node in graph.nodes:
                    existing = node_map.get(node.node_id)
                    props = dict(node.properties)
                    props.setdefault("source_case_ids", source_case_id)
                    if existing:
                        evidence_ids = sorted(set(existing.evidence_ids + node.evidence_ids))
                        source_ids = set(str(existing.properties.get("source_case_ids", "")).split(","))
                        source_ids.add(source_case_id)
                        existing.evidence_ids = evidence_ids
                        existing.properties["source_case_ids"] = ",".join(sorted(item for item in source_ids if item))
                    else:
                        copied = node.model_copy(update={"properties": props})
                        node_map[node.node_id] = copied
                for edge in graph.edges:
                    props = dict(edge.properties)
                    props.setdefault("source_case_id", source_case_id)
                    edge_id = edge.edge_id if source_case_id == case_id else f"{source_case_id}:{edge.edge_id}"
                    merged.edges.append(edge.model_copy(update={"edge_id": edge_id, "properties": props}))
                for clue in graph.clues:
                    merged.clues.append(clue.model_copy(update={"clue_id": f"{source_case_id}:{clue.clue_id}"}))
            merged.nodes = list(node_map.values())
            return enrich_graph_tags(merged)

    def apply_intervention(self, case_id: str, payload: GraphInterventionRequest) -> InvestigationGraph:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")

            graph = self.store.graphs.setdefault(case_id, InvestigationGraph(case_id=case_id))

            if payload.action == "upsert_node":
                if not payload.node:
                    raise bad_request("node is required")
                graph.nodes = [node for node in graph.nodes if node.node_id != payload.node.node_id]
                graph.nodes.append(payload.node.model_copy(update={"manually_verified": True}))
            elif payload.action == "upsert_edge":
                if not payload.edge:
                    raise bad_request("edge is required")
                graph.edges = [edge for edge in graph.edges if edge.edge_id != payload.edge.edge_id]
                graph.edges.append(payload.edge.model_copy(update={"manually_verified": True}))
            elif payload.action == "delete_node":
                if not payload.target_id:
                    raise bad_request("target_id is required")
                graph.nodes = [node for node in graph.nodes if node.node_id != payload.target_id]
                graph.edges = [edge for edge in graph.edges if edge.source_id != payload.target_id and edge.target_id != payload.target_id]
            elif payload.action == "delete_edge":
                if not payload.target_id:
                    raise bad_request("target_id is required")
                graph.edges = [edge for edge in graph.edges if edge.edge_id != payload.target_id]
            elif payload.action == "verify_node":
                graph.nodes = [
                    node.model_copy(update={"manually_verified": True}) if node.node_id == payload.target_id else node for node in graph.nodes
                ]
            elif payload.action == "verify_edge":
                graph.edges = [
                    edge.model_copy(update={"manually_verified": True}) if edge.edge_id == payload.target_id else edge for edge in graph.edges
                ]

            self.store.graphs[case_id] = graph
            enrich_graph_tags(graph)
            self.store.flush_case(case_id)
            return graph

    def apply_raw_action(self, case_id: str, payload: RawGraphActionRequest) -> RawGraphActionResponse:
        if payload.layer != "raw":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"detail": "文件证据图和片段证据图为只读图层，请在原始图谱层维护事实关系。", "code": "GRAPH_LAYER_READONLY"},
            )
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            graph = self.store.graphs.setdefault(case_id, InvestigationGraph(case_id=case_id))
            action = payload.action
            data = payload.payload or {}
            message = "操作成功"

            if action == "create_node":
                node = _node_from_payload(data)
                if any(item.node_id == node.node_id for item in graph.nodes):
                    raise _graph_error(status.HTTP_400_BAD_REQUEST, "节点已存在", "GRAPH_ACTION_FAILED")
                graph.nodes.append(node.model_copy(update={"manually_verified": True}))
            elif action == "update_node":
                node_id = _payload_id(data)
                updated = False
                graph.nodes = [
                    _merge_node(node, data) if node.node_id == node_id else node
                    for node in graph.nodes
                ]
                updated = any(node.node_id == node_id for node in graph.nodes)
                if not updated:
                    raise _graph_error(status.HTTP_404_NOT_FOUND, "节点不存在", "GRAPH_NODE_NOT_FOUND")
            elif action == "delete_node":
                node_id = _payload_id(data)
                before_nodes = len(graph.nodes)
                before_edges = len(graph.edges)
                graph.nodes = [node for node in graph.nodes if node.node_id != node_id]
                if len(graph.nodes) == before_nodes:
                    raise _graph_error(status.HTTP_404_NOT_FOUND, "节点不存在", "GRAPH_NODE_NOT_FOUND")
                graph.edges = [edge for edge in graph.edges if edge.source_id != node_id and edge.target_id != node_id]
                message = f"操作成功，已级联删除 {before_edges - len(graph.edges)} 条相关关系"
            elif action == "create_edge":
                edge = _edge_from_payload(data)
                _ensure_edge_endpoints(graph, edge.source_id, edge.target_id)
                if any(item.edge_id == edge.edge_id for item in graph.edges):
                    raise _graph_error(status.HTTP_400_BAD_REQUEST, "关系已存在", "GRAPH_ACTION_FAILED")
                graph.edges.append(edge.model_copy(update={"manually_verified": True}))
            elif action == "update_edge":
                edge_id = _payload_id(data)
                existing = next((edge for edge in graph.edges if edge.edge_id == edge_id), None)
                if not existing:
                    raise _graph_error(status.HTTP_404_NOT_FOUND, "关系不存在", "GRAPH_EDGE_NOT_FOUND")
                source_id = str(data.get("source") or data.get("source_id") or existing.source_id)
                target_id = str(data.get("target") or data.get("target_id") or existing.target_id)
                _ensure_edge_endpoints(graph, source_id, target_id)
                graph.edges = [_merge_edge(edge, data) if edge.edge_id == edge_id else edge for edge in graph.edges]
            elif action == "delete_edge":
                edge_id = _payload_id(data)
                before_edges = len(graph.edges)
                graph.edges = [edge for edge in graph.edges if edge.edge_id != edge_id]
                if len(graph.edges) == before_edges:
                    raise _graph_error(status.HTTP_404_NOT_FOUND, "关系不存在", "GRAPH_EDGE_NOT_FOUND")
            else:
                raise _graph_error(status.HTTP_400_BAD_REQUEST, "不支持的图谱操作", "GRAPH_ACTION_FAILED")

            self.store.graphs[case_id] = graph
            enrich_graph_tags(graph)
            self.store.flush_case(case_id)
            return RawGraphActionResponse(
                message=message,
                action=action,
                graph=_raw_graph_payload(graph),
            )


def _payload_id(data: dict) -> str:
    value = data.get("id") or data.get("node_id") or data.get("edge_id")
    if not value:
        raise _graph_error(status.HTTP_400_BAD_REQUEST, "缺少 id", "GRAPH_ACTION_FAILED")
    return str(value)


def _node_from_payload(data: dict) -> GraphNode:
    node_id = _payload_id(data)
    return GraphNode(
        node_id=node_id,
        label=str(data.get("label") or node_id),
        type=str(data.get("type") or "manual"),
        tags=list(data.get("tags") or ["manual"]),
        properties=dict(data.get("properties") or {}),
        evidence_ids=list(data.get("evidence_ids") or []),
    )


def _merge_node(node: GraphNode, data: dict) -> GraphNode:
    return node.model_copy(
        update={
            "label": str(data.get("label") or node.label),
            "type": str(data.get("type") or node.type),
            "tags": list(data.get("tags") or node.tags),
            "properties": dict(data.get("properties") or node.properties),
            "manually_verified": True,
        }
    )


def _edge_from_payload(data: dict) -> GraphEdge:
    edge_id = _payload_id(data)
    source = data.get("source") or data.get("source_id")
    target = data.get("target") or data.get("target_id")
    if not source or not target:
        raise _graph_error(status.HTTP_400_BAD_REQUEST, "关系必须包含 source 和 target", "GRAPH_INVALID_EDGE_ENDPOINT")
    relation = str(data.get("label") or data.get("relation") or data.get("type") or "关联")
    return GraphEdge(
        edge_id=edge_id,
        source_id=str(source),
        target_id=str(target),
        relation=relation,
        tags=list(data.get("tags") or ["manual"]),
        confidence=float(data.get("confidence") or 0.8),
        properties=dict(data.get("properties") or {}),
        evidence_ids=list(data.get("evidence_ids") or []),
    )


def _merge_edge(edge: GraphEdge, data: dict) -> GraphEdge:
    return edge.model_copy(
        update={
            "source_id": str(data.get("source") or data.get("source_id") or edge.source_id),
            "target_id": str(data.get("target") or data.get("target_id") or edge.target_id),
            "relation": str(data.get("label") or data.get("relation") or data.get("type") or edge.relation),
            "tags": list(data.get("tags") or edge.tags),
            "properties": dict(data.get("properties") or edge.properties),
            "manually_verified": True,
        }
    )


def _ensure_edge_endpoints(graph: InvestigationGraph, source_id: str, target_id: str) -> None:
    node_ids = {node.node_id for node in graph.nodes}
    if source_id not in node_ids or target_id not in node_ids:
        raise _graph_error(status.HTTP_400_BAD_REQUEST, "关系端点不存在", "GRAPH_INVALID_EDGE_ENDPOINT")


def _raw_graph_payload(graph: InvestigationGraph) -> dict:
    nodes = [
        {
            "id": node.node_id,
            "label": node.label,
            "type": node.type,
            "layer": "raw",
            "summary": "",
            "properties": node.properties,
            "source": {"evidence_id": node.evidence_ids[0] if node.evidence_ids else None, "passage_id": None},
        }
        for node in graph.nodes
    ]
    node_ids = {node["id"] for node in nodes}
    edges = [
        {
            "id": edge.edge_id,
            "source": edge.source_id,
            "target": edge.target_id,
            "type": edge.relation,
            "label": edge.relation,
            "properties": edge.properties,
            "source_refs": [{"evidence_id": evidence_id, "passage_id": None} for evidence_id in edge.evidence_ids],
        }
        for edge in graph.edges
        if edge.source_id in node_ids and edge.target_id in node_ids
    ]
    return {
        "nodes": nodes,
        "edges": edges,
        "legend": _legend(nodes, edges),
        "stats": {"nodes": len(nodes), "edges": len(edges)},
        "editable": True,
    }


def _legend(nodes: list[dict], edges: list[dict]) -> dict:
    return {
        "node_types": [{"type": item, "label": _label(item, "节点"), "description": "原始图谱层中的节点类型。"} for item in sorted({node["type"] for node in nodes})],
        "edge_types": [{"type": item, "label": _label(item, "关系"), "description": "原始图谱层中的关系类型。"} for item in sorted({edge["type"] for edge in edges})],
    }


def _label(value: str, suffix: str) -> str:
    mapping = {
        "person": "人物",
        "organization": "机构",
        "account": "账户 / 资金",
        "transaction": "资金流水",
        "manual": "人工添加",
        "entity": "实体",
    }
    return mapping.get(value, value) + suffix


def _graph_error(status_code: int, detail: str, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"detail": detail, "code": code})

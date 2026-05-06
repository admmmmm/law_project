from app.core.errors import bad_request, not_found
from app.adapters.algorithm import enrich_graph_tags
from app.schemas.graph import GraphInterventionRequest, InvestigationGraph
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

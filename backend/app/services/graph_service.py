from app.core.errors import bad_request, not_found
from app.schemas.graph import GraphInterventionRequest, InvestigationGraph
from app.storage.memory_store import MemoryStore


class GraphService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def get_graph(self, case_id: str) -> InvestigationGraph:
        with self.store.lock:
            if case_id not in self.store.cases:
                raise not_found("case not found")
            return self.store.graphs.setdefault(case_id, InvestigationGraph(case_id=case_id))

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
            return graph

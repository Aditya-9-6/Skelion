import networkx as nx
from typing import List, Dict, Any, Optional


class CausalityGraph:
    """
    Constructs a directed acyclic dependency graph from distributed trace spans
    to identify root causes in cascading failure and timeout scenarios.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_span(
        self,
        span_id: str,
        parent_span_id: Optional[str],
        service: str,
        name: str,
        duration_ms: float,
        status_code: int,
        error: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Adds a trace span node and links it to its parent span if specified."""
        self.graph.add_node(
            span_id,
            service=service,
            name=name,
            duration_ms=duration_ms,
            status_code=status_code,
            error=error,
            metadata=metadata or {},
        )
        if parent_span_id:
            # Directed edge from parent -> child representing invocation flow
            self.graph.add_edge(parent_span_id, span_id)

    def build_from_spans(self, spans: List[Dict[str, Any]]) -> None:
        """Builds the complete causality graph from a list of serialized span dicts."""
        for span in spans:
            self.add_span(
                span_id=span.get("span_id"),
                parent_span_id=span.get("parent_span_id"),
                service=span.get("service", "unknown"),
                name=span.get("name", "operation"),
                duration_ms=span.get("duration_ms", 0.0),
                status_code=span.get("status_code", 200),
                error=span.get("error", False),
                metadata=span.get("metadata"),
            )

    def find_root_cause(self) -> Optional[str]:
        """
        Traverses the graph to pinpoint the exact upstream root-cause node
        responsible for cascading failures (e.g. first node with error or timeout anomaly).
        """
        if not self.graph.nodes:
            return None

        # Find entry points (nodes with in-degree 0)
        roots = [n for n, d in self.graph.in_degree() if d == 0]
        if not roots:
            roots = list(self.graph.nodes)

        # Search for the earliest failing or slowest path
        error_nodes = [
            n
            for n, data in self.graph.nodes(data=True)
            if data.get("error") or data.get("status_code", 200) >= 500
        ]

        if error_nodes:
            # Return the upstream-most error node (shortest path from any root or topological order)
            try:
                sorted_nodes = list(nx.topological_sort(self.graph))
                for node in sorted_nodes:
                    if node in error_nodes:
                        return node
            except nx.NetworkXUnfeasible:
                pass
            return error_nodes[0]

        # If no explicit error status, return the node with maximum duration contributing to timeout
        max_node = max(
            self.graph.nodes,
            key=lambda n: self.graph.nodes[n].get("duration_ms", 0.0),
            default=None,
        )
        return max_node

    def get_upstream_path(self, span_id: str) -> List[str]:
        """Returns the lineage path from root to the specified span."""
        if span_id not in self.graph:
            return []

        roots = [n for n, d in self.graph.in_degree() if d == 0]
        for root in roots:
            try:
                path = nx.shortest_path(self.graph, source=root, target=span_id)
                return path
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        return [span_id]

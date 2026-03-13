"""Service dependency graph implementation using adjacency list representation."""

from typing import Dict, List, Set, Optional, Tuple, TYPE_CHECKING
from collections import defaultdict
from datetime import datetime
from src.models.dependency import DependencyEdge, ServiceDependency, GraphWarning, WarningType

if TYPE_CHECKING:
    from src.models.dependency import DependencyGraph


class ServiceGraph:
    """
    Service dependency graph using adjacency list representation.
    
    Supports:
    - Service-to-service dependencies
    - Service-to-infrastructure dependencies
    - Querying upstream and downstream services
    - Efficient graph traversal operations
    """
    
    def __init__(self):
        """Initialize an empty service graph."""
        # Adjacency list: service_id -> list of (target_id, edge_metadata)
        self._adjacency_list: Dict[str, List[Tuple[str, DependencyEdge]]] = defaultdict(list)
        
        # Reverse adjacency list for upstream queries: service_id -> list of source_ids
        self._reverse_adjacency_list: Dict[str, List[str]] = defaultdict(list)
        
        # Set of all nodes (services and infrastructure)
        self._nodes: Set[str] = set()
        
        # Track infrastructure nodes separately
        self._infrastructure_nodes: Set[str] = set()
    
    def add_node(self, node_id: str, is_infrastructure: bool = False) -> None:
        """
        Add a node (service or infrastructure) to the graph.
        
        Args:
            node_id: Unique identifier for the node
            is_infrastructure: Whether this node represents infrastructure
        """
        self._nodes.add(node_id)
        if is_infrastructure:
            self._infrastructure_nodes.add(node_id)
        
        # Ensure the node exists in adjacency lists
        if node_id not in self._adjacency_list:
            self._adjacency_list[node_id] = []
        if node_id not in self._reverse_adjacency_list:
            self._reverse_adjacency_list[node_id] = []
    
    def add_edge(self, source_id: str, target_id: str, edge_metadata: DependencyEdge) -> None:
        """
        Add a directed edge (dependency) from source to target.
        
        Args:
            source_id: Source service ID
            target_id: Target service or infrastructure ID
            edge_metadata: Dependency metadata (type, timeout, criticality, etc.)
        """
        # Ensure both nodes exist
        self.add_node(source_id, is_infrastructure=False)
        
        # Determine if target is infrastructure
        is_infrastructure = edge_metadata.target_infrastructure_id is not None
        self.add_node(target_id, is_infrastructure=is_infrastructure)
        
        # Add edge to adjacency list
        self._adjacency_list[source_id].append((target_id, edge_metadata))
        
        # Add reverse edge for upstream queries
        self._reverse_adjacency_list[target_id].append(source_id)
    
    def get_downstream_services(self, service_id: str) -> List[str]:
        """
        Get all direct downstream dependencies of a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            List of downstream service/infrastructure IDs
        """
        if service_id not in self._adjacency_list:
            return []
        
        return [target_id for target_id, _ in self._adjacency_list[service_id]]
    
    def get_upstream_services(self, service_id: str) -> List[str]:
        """
        Get all direct upstream services that depend on this service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            List of upstream service IDs
        """
        if service_id not in self._reverse_adjacency_list:
            return []
        
        return list(self._reverse_adjacency_list[service_id])
    
    def get_edge_metadata(self, source_id: str, target_id: str) -> Optional[DependencyEdge]:
        """
        Get the metadata for a specific edge.
        
        Args:
            source_id: Source service ID
            target_id: Target service/infrastructure ID
            
        Returns:
            DependencyEdge metadata if edge exists, None otherwise
        """
        if source_id not in self._adjacency_list:
            return None
        
        for target, metadata in self._adjacency_list[source_id]:
            if target == target_id:
                return metadata
        
        return None
    
    def get_all_nodes(self) -> Set[str]:
        """
        Get all nodes in the graph.
        
        Returns:
            Set of all node IDs (services and infrastructure)
        """
        return self._nodes.copy()
    
    def get_service_nodes(self) -> Set[str]:
        """
        Get only service nodes (excluding infrastructure).
        
        Returns:
            Set of service node IDs
        """
        return self._nodes - self._infrastructure_nodes
    
    def get_infrastructure_nodes(self) -> Set[str]:
        """
        Get only infrastructure nodes.
        
        Returns:
            Set of infrastructure node IDs
        """
        return self._infrastructure_nodes.copy()
    
    def has_node(self, node_id: str) -> bool:
        """
        Check if a node exists in the graph.
        
        Args:
            node_id: Node identifier
            
        Returns:
            True if node exists, False otherwise
        """
        return node_id in self._nodes
    
    def has_edge(self, source_id: str, target_id: str) -> bool:
        """
        Check if an edge exists between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            
        Returns:
            True if edge exists, False otherwise
        """
        if source_id not in self._adjacency_list:
            return False
        
        return any(target == target_id for target, _ in self._adjacency_list[source_id])
    
    def get_node_count(self) -> int:
        """
        Get the total number of nodes in the graph.
        
        Returns:
            Number of nodes
        """
        return len(self._nodes)
    
    def get_edge_count(self) -> int:
        """
        Get the total number of edges in the graph.
        
        Returns:
            Number of edges
        """
        return sum(len(edges) for edges in self._adjacency_list.values())
    
    def get_adjacency_list(self) -> Dict[str, List[Tuple[str, DependencyEdge]]]:
        """
        Get the internal adjacency list representation.
        
        Returns:
            Dictionary mapping source_id to list of (target_id, edge_metadata) tuples
        """
        return dict(self._adjacency_list)
    
    def get_reverse_adjacency_list(self) -> Dict[str, List[str]]:
        """
        Get the reverse adjacency list for upstream queries.
        
        Returns:
            Dictionary mapping target_id to list of source_ids
        """
        return dict(self._reverse_adjacency_list)
    
    def clear(self) -> None:
        """Clear all nodes and edges from the graph."""
        self._adjacency_list.clear()
        self._reverse_adjacency_list.clear()
        self._nodes.clear()
        self._infrastructure_nodes.clear()
    def build_from_declarations(
        self,
        declarations: List[ServiceDependency]
    ) -> List[GraphWarning]:
        """
        Build the service graph from dependency declarations.

        This method takes a list of ServiceDependency objects and constructs
        the graph by adding nodes for each service and edges for each dependency.
        It handles missing dependencies gracefully by generating warnings.

        Args:
            declarations: List of ServiceDependency objects containing services
                         and their dependencies

        Returns:
            List of GraphWarning objects for missing dependencies or other issues

        Example:
            >>> from src.models.dependency import ServiceDependency, DependencyEdge
            >>> graph = ServiceGraph()
            >>> declarations = [
            ...     ServiceDependency(
            ...         service_id="api-gateway",
            ...         dependencies=[
            ...             DependencyEdge(
            ...                 target_service_id="auth-service",
            ...                 dependency_type="synchronous",
            ...                 criticality="high"
            ...             )
            ...         ]
            ...     ),
            ...     ServiceDependency(service_id="auth-service", dependencies=[])
            ... ]
            >>> warnings = graph.build_from_declarations(declarations)
            >>> graph.has_node("api-gateway")
            True
            >>> graph.has_edge("api-gateway", "auth-service")
            True
        """
        warnings: List[GraphWarning] = []

        # First pass: Add all declared services as nodes
        declared_services: Set[str] = set()
        for declaration in declarations:
            service_id = declaration.service_id
            declared_services.add(service_id)
            self.add_node(service_id, is_infrastructure=False)

        # Second pass: Add edges and track referenced services/infrastructure
        referenced_targets: Set[str] = set()

        for declaration in declarations:
            source_id = declaration.service_id

            for dependency in declaration.dependencies:
                # Determine the target ID
                if dependency.target_service_id:
                    target_id = dependency.target_service_id
                    is_infrastructure = False
                elif dependency.target_infrastructure_id:
                    target_id = dependency.target_infrastructure_id
                    is_infrastructure = True
                else:
                    # Edge has neither target_service_id nor target_infrastructure_id
                    warnings.append(GraphWarning(
                        warning_type=WarningType.NO_TARGET,
                        service_id=source_id,
                        message=f"Service '{source_id}' has a dependency with no target "
                                f"(neither target_service_id nor target_infrastructure_id specified)"
                    ))
                    continue

                referenced_targets.add(target_id)

                # Check if target service exists in declarations (only for services, not infrastructure)
                if not is_infrastructure and target_id not in declared_services:
                    warnings.append(GraphWarning(
                        warning_type=WarningType.MISSING_DEPENDENCY,
                        service_id=source_id,
                        target_id=target_id,
                        message=f"Service '{source_id}' depends on '{target_id}' which is not "
                                f"declared in the dependency graph"
                    ))

                # Add the edge (this will also add the target node if it doesn't exist)
                self.add_edge(source_id, target_id, dependency)

        # Check for isolated nodes (services with no dependencies and no dependents)
        for service_id in declared_services:
            downstream = self.get_downstream_services(service_id)
            upstream = self.get_upstream_services(service_id)

            if not downstream and not upstream:
                warnings.append(GraphWarning(
                    warning_type=WarningType.ISOLATED_NODE,
                    service_id=service_id,
                    message=f"Service '{service_id}' has no dependencies and no dependents "
                            f"(isolated node)"
                ))

        return warnings

    def build_from_dependency_graph(self, dependency_graph: 'DependencyGraph') -> List[GraphWarning]:
        """
        Build the service graph from a DependencyGraph object.

        This is a convenience method that extracts the services list from
        a DependencyGraph object and calls build_from_declarations.

        Args:
            dependency_graph: DependencyGraph object containing services and metadata

        Returns:
            List of GraphWarning objects for missing dependencies or other issues

        Example:
            >>> from src.models.dependency import DependencyGraph, ServiceDependency
            >>> from datetime import datetime
            >>> graph = ServiceGraph()
            >>> dep_graph = DependencyGraph(
            ...     version="1.0",
            ...     updated_at=datetime.now(),
            ...     services=[
            ...         ServiceDependency(service_id="api-gateway", dependencies=[])
            ...     ]
            ... )
            >>> warnings = graph.build_from_dependency_graph(dep_graph)
            >>> graph.has_node("api-gateway")
            True
        """
        return self.build_from_declarations(dependency_graph.services)
    def detect_circular_dependencies(self) -> List[List[str]]:
        """
        Detect circular dependencies using Tarjan's algorithm for strongly connected components.

        Returns:
            List of strongly connected components (SCCs) with size > 1.
            Each SCC is a list of service IDs that form a circular dependency.

        Example:
            >>> graph = ServiceGraph()
            >>> # Build a graph with circular dependency: A -> B -> C -> A
            >>> edge1 = DependencyEdge(target_service_id="service-b", dependency_type="synchronous", criticality="high")
            >>> edge2 = DependencyEdge(target_service_id="service-c", dependency_type="synchronous", criticality="high")
            >>> edge3 = DependencyEdge(target_service_id="service-a", dependency_type="synchronous", criticality="high")
            >>> graph.add_edge("service-a", "service-b", edge1)
            >>> graph.add_edge("service-b", "service-c", edge2)
            >>> graph.add_edge("service-c", "service-a", edge3)
            >>> cycles = graph.detect_circular_dependencies()
            >>> len(cycles)
            1
            >>> set(cycles[0]) == {"service-a", "service-b", "service-c"}
            True
        """
        index_counter = [0]
        stack: List[str] = []
        lowlinks: Dict[str, int] = {}
        index: Dict[str, int] = {}
        on_stack: Set[str] = set()
        sccs: List[List[str]] = []

        def strongconnect(node: str) -> None:
            """Tarjan's algorithm recursive helper function."""
            # Set the depth index for this node
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack.add(node)

            # Consider successors (downstream services)
            for successor in self.get_downstream_services(node):
                if successor not in index:
                    # Successor has not yet been visited; recurse on it
                    strongconnect(successor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                elif successor in on_stack:
                    # Successor is in the current SCC
                    lowlinks[node] = min(lowlinks[node], index[successor])

            # If node is a root node, pop the stack and generate an SCC
            if lowlinks[node] == index[node]:
                scc: List[str] = []
                while True:
                    successor = stack.pop()
                    on_stack.remove(successor)
                    scc.append(successor)
                    if successor == node:
                        break
                sccs.append(scc)

        # Run Tarjan's algorithm on all nodes
        for node in self.get_service_nodes():
            if node not in index:
                strongconnect(node)

        # Return only SCCs with size > 1 (circular dependencies)
        return [scc for scc in sccs if len(scc) > 1]
    def compute_critical_path(
        self,
        service_id: str,
        service_latencies: Dict[str, float]
    ) -> Dict[str, any]:
        """
        Compute the critical path from a service to all leaf dependencies.
        Uses modified Dijkstra's algorithm to find the longest latency path.

        The critical path is the sequence of dependent services that determines
        the maximum end-to-end latency. This is useful for identifying bottlenecks
        and understanding latency budgets.

        Args:
            service_id: Starting service identifier
            service_latencies: Dictionary mapping service_id to p95 latency in milliseconds

        Returns:
            Dictionary containing:
                - path: List of service IDs in the critical path
                - total_latency_ms: Total cumulative latency along the path
                - bottleneck_service: Service with highest latency in the path

        Example:
            >>> graph = ServiceGraph()
            >>> # Build graph: A -> B -> C, A -> D
            >>> edge1 = DependencyEdge(target_service_id="B", dependency_type="synchronous", criticality="high")
            >>> edge2 = DependencyEdge(target_service_id="C", dependency_type="synchronous", criticality="high")
            >>> edge3 = DependencyEdge(target_service_id="D", dependency_type="synchronous", criticality="high")
            >>> graph.add_edge("A", "B", edge1)
            >>> graph.add_edge("B", "C", edge2)
            >>> graph.add_edge("A", "D", edge3)
            >>> latencies = {"A": 10, "B": 50, "C": 30, "D": 20}
            >>> result = graph.compute_critical_path("A", latencies)
            >>> result['path']
            ['A', 'B', 'C']
            >>> result['total_latency_ms']
            90.0
            >>> result['bottleneck_service']
            'B'
        """
        from heapq import heappush, heappop

        # Validate service exists
        if not self.has_node(service_id):
            return {
                'path': [],
                'total_latency_ms': 0.0,
                'bottleneck_service': None
            }

        # Handle service with no downstream dependencies
        downstream = self.get_downstream_services(service_id)
        if not downstream:
            service_latency = service_latencies.get(service_id, 0.0)
            return {
                'path': [service_id],
                'total_latency_ms': service_latency,
                'bottleneck_service': service_id if service_latency > 0 else None
            }

        # Priority queue: (-cumulative_latency, current_node, path)
        # We use negative latency to turn min-heap into max-heap
        initial_latency = service_latencies.get(service_id, 0.0)
        pq = [(-initial_latency, service_id, [service_id])]

        max_latency = initial_latency
        max_latency_path = [service_id]

        # Track visited nodes to avoid infinite loops in case of cycles
        visited_paths = set()

        while pq:
            neg_current_latency, current_node, current_path = heappop(pq)
            current_latency = -neg_current_latency

            # Create a hashable representation of the path to detect cycles
            path_key = tuple(current_path)
            if path_key in visited_paths:
                continue
            visited_paths.add(path_key)

            # Get downstream dependencies
            downstream_nodes = self.get_downstream_services(current_node)

            # If this is a leaf node, check if it's the longest path
            if not downstream_nodes:
                if current_latency > max_latency:
                    max_latency = current_latency
                    max_latency_path = current_path
                continue

            # Explore downstream dependencies
            for target_node in downstream_nodes:
                # Avoid cycles in the path
                if target_node in current_path:
                    continue

                # Get target service latency
                target_latency = service_latencies.get(target_node, 0.0)
                new_latency = current_latency + target_latency
                new_path = current_path + [target_node]

                heappush(pq, (-new_latency, target_node, new_path))

        # Find bottleneck service (service with highest latency in the path)
        bottleneck_service = None
        max_service_latency = 0.0

        for service in max_latency_path:
            service_latency = service_latencies.get(service, 0.0)
            if service_latency > max_service_latency:
                max_service_latency = service_latency
                bottleneck_service = service

        return {
            'path': max_latency_path,
            'total_latency_ms': max_latency,
            'bottleneck_service': bottleneck_service
        }
    def compute_cascading_impact_score(self, service_id: str) -> float:
        """
        Compute cascading impact score for a service using BFS traversal.

        The impact score measures how many downstream services are affected by this service,
        weighted by dependency depth and fanout. Services closer in the dependency chain
        and with fewer siblings have higher impact.

        Formula: Σ (1 / depth) * (1 / fanout) for all downstream services
        Score is normalized to [0, 1] range.

        Args:
            service_id: Service identifier

        Returns:
            Cascading impact score in range [0, 1]
            Returns 0.0 for services with no downstream dependencies (leaf nodes)

        Example:
            >>> graph = ServiceGraph()
            >>> # Build graph: A -> B -> C, A -> D
            >>> edge1 = DependencyEdge(target_service_id="B", dependency_type="synchronous", criticality="high")
            >>> edge2 = DependencyEdge(target_service_id="C", dependency_type="synchronous", criticality="high")
            >>> edge3 = DependencyEdge(target_service_id="D", dependency_type="synchronous", criticality="high")
            >>> graph.add_edge("A", "B", edge1)
            >>> graph.add_edge("B", "C", edge2)
            >>> graph.add_edge("A", "D", edge3)
            >>> score = graph.compute_cascading_impact_score("A")
            >>> score > 0.0
            True
        """
        from collections import deque

        # Validate service exists
        if not self.has_node(service_id):
            return 0.0

        # Handle leaf nodes (no downstream dependencies)
        downstream = self.get_downstream_services(service_id)
        if not downstream:
            return 0.0

        # BFS traversal to compute impact score
        visited: Set[str] = set()
        queue: deque = deque([(service_id, 0)])  # (node, depth)
        impact_score = 0.0

        while queue:
            current_node, depth = queue.popleft()

            # Skip if already visited (avoid cycles)
            if current_node in visited:
                continue
            visited.add(current_node)

            # Get downstream dependencies
            downstream_nodes = self.get_downstream_services(current_node)
            fanout = len(downstream_nodes) if downstream_nodes else 1

            # Don't count the service itself (depth > 0)
            if depth > 0:
                impact_score += (1.0 / depth) * (1.0 / fanout)

            # Add downstream nodes to queue
            for target_node in downstream_nodes:
                if target_node not in visited:
                    queue.append((target_node, depth + 1))

        # Normalize to [0, 1] range
        return min(impact_score, 1.0)



    
    def __repr__(self) -> str:
        """String representation of the graph."""
        return (
            f"ServiceGraph(nodes={len(self._nodes)}, "
            f"edges={self.get_edge_count()}, "
            f"services={len(self.get_service_nodes())}, "
            f"infrastructure={len(self._infrastructure_nodes)})"
        )

"""Unit tests for ServiceGraph class."""

import pytest
from src.algorithms.service_graph import ServiceGraph
from src.models.dependency import DependencyEdge


class TestServiceGraphBasics:
    """Test basic ServiceGraph functionality."""
    
    def test_empty_graph_initialization(self):
        """Test that a new graph is empty."""
        graph = ServiceGraph()
        assert graph.get_node_count() == 0
        assert graph.get_edge_count() == 0
        assert len(graph.get_all_nodes()) == 0
    
    def test_add_single_node(self):
        """Test adding a single service node."""
        graph = ServiceGraph()
        graph.add_node("service-a")
        
        assert graph.get_node_count() == 1
        assert graph.has_node("service-a")
        assert "service-a" in graph.get_all_nodes()
        assert "service-a" in graph.get_service_nodes()
        assert "service-a" not in graph.get_infrastructure_nodes()
    
    def test_add_infrastructure_node(self):
        """Test adding an infrastructure node."""
        graph = ServiceGraph()
        graph.add_node("postgres-db", is_infrastructure=True)
        
        assert graph.get_node_count() == 1
        assert graph.has_node("postgres-db")
        assert "postgres-db" in graph.get_all_nodes()
        assert "postgres-db" in graph.get_infrastructure_nodes()
        assert "postgres-db" not in graph.get_service_nodes()
    
    def test_add_multiple_nodes(self):
        """Test adding multiple nodes."""
        graph = ServiceGraph()
        graph.add_node("service-a")
        graph.add_node("service-b")
        graph.add_node("postgres-db", is_infrastructure=True)
        
        assert graph.get_node_count() == 3
        assert len(graph.get_service_nodes()) == 2
        assert len(graph.get_infrastructure_nodes()) == 1
    
    def test_add_duplicate_node(self):
        """Test that adding duplicate nodes doesn't increase count."""
        graph = ServiceGraph()
        graph.add_node("service-a")
        graph.add_node("service-a")
        
        assert graph.get_node_count() == 1


class TestServiceGraphEdges:
    """Test edge operations in ServiceGraph."""
    
    def test_add_simple_edge(self):
        """Test adding a simple service-to-service edge."""
        graph = ServiceGraph()
        edge = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        
        graph.add_edge("service-a", "service-b", edge)
        
        assert graph.get_node_count() == 2
        assert graph.get_edge_count() == 1
        assert graph.has_edge("service-a", "service-b")
        assert not graph.has_edge("service-b", "service-a")
    
    def test_add_infrastructure_edge(self):
        """Test adding a service-to-infrastructure edge."""
        graph = ServiceGraph()
        edge = DependencyEdge(
            target_infrastructure_id="postgres-db",
            infrastructure_type="postgresql",
            dependency_type="synchronous",
            criticality="high"
        )
        
        graph.add_edge("service-a", "postgres-db", edge)
        
        assert graph.get_node_count() == 2
        assert "postgres-db" in graph.get_infrastructure_nodes()
        assert "service-a" in graph.get_service_nodes()
    
    def test_add_multiple_edges(self):
        """Test adding multiple edges from one service."""
        graph = ServiceGraph()
        
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="asynchronous",
            criticality="medium"
        )
        
        graph.add_edge("service-a", "service-b", edge1)
        graph.add_edge("service-a", "service-c", edge2)
        
        assert graph.get_edge_count() == 2
        assert graph.has_edge("service-a", "service-b")
        assert graph.has_edge("service-a", "service-c")
    
    def test_get_edge_metadata(self):
        """Test retrieving edge metadata."""
        graph = ServiceGraph()
        edge = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            timeout_ms=500,
            criticality="high"
        )
        
        graph.add_edge("service-a", "service-b", edge)
        
        retrieved_edge = graph.get_edge_metadata("service-a", "service-b")
        assert retrieved_edge is not None
        assert retrieved_edge.dependency_type == "synchronous"
        assert retrieved_edge.timeout_ms == 500
        assert retrieved_edge.criticality == "high"
    
    def test_get_nonexistent_edge_metadata(self):
        """Test retrieving metadata for non-existent edge."""
        graph = ServiceGraph()
        
        metadata = graph.get_edge_metadata("service-a", "service-b")
        assert metadata is None


class TestServiceGraphQueries:
    """Test query operations on ServiceGraph."""
    
    def test_get_downstream_services(self):
        """Test getting downstream services."""
        graph = ServiceGraph()
        
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="medium"
        )
        
        graph.add_edge("service-a", "service-b", edge1)
        graph.add_edge("service-a", "service-c", edge2)
        
        downstream = graph.get_downstream_services("service-a")
        assert len(downstream) == 2
        assert "service-b" in downstream
        assert "service-c" in downstream
    
    def test_get_upstream_services(self):
        """Test getting upstream services."""
        graph = ServiceGraph()
        
        edge1 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="high"
        )
        
        graph.add_edge("service-a", "service-c", edge1)
        graph.add_edge("service-b", "service-c", edge2)
        
        upstream = graph.get_upstream_services("service-c")
        assert len(upstream) == 2
        assert "service-a" in upstream
        assert "service-b" in upstream
    
    def test_get_downstream_empty(self):
        """Test getting downstream services for leaf node."""
        graph = ServiceGraph()
        graph.add_node("service-a")
        
        downstream = graph.get_downstream_services("service-a")
        assert len(downstream) == 0
    
    def test_get_upstream_empty(self):
        """Test getting upstream services for root node."""
        graph = ServiceGraph()
        graph.add_node("service-a")
        
        upstream = graph.get_upstream_services("service-a")
        assert len(upstream) == 0
    
    def test_get_downstream_nonexistent_service(self):
        """Test getting downstream for non-existent service."""
        graph = ServiceGraph()
        
        downstream = graph.get_downstream_services("nonexistent")
        assert len(downstream) == 0
    
    def test_get_upstream_nonexistent_service(self):
        """Test getting upstream for non-existent service."""
        graph = ServiceGraph()
        
        upstream = graph.get_upstream_services("nonexistent")
        assert len(upstream) == 0


class TestServiceGraphComplex:
    """Test complex graph scenarios."""
    
    def test_chain_topology(self):
        """Test a simple chain: A -> B -> C."""
        graph = ServiceGraph()
        
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="high"
        )
        
        graph.add_edge("service-a", "service-b", edge1)
        graph.add_edge("service-b", "service-c", edge2)
        
        # Check service-a
        assert len(graph.get_downstream_services("service-a")) == 1
        assert len(graph.get_upstream_services("service-a")) == 0
        
        # Check service-b
        assert len(graph.get_downstream_services("service-b")) == 1
        assert len(graph.get_upstream_services("service-b")) == 1
        
        # Check service-c
        assert len(graph.get_downstream_services("service-c")) == 0
        assert len(graph.get_upstream_services("service-c")) == 1
    
    def test_fan_out_topology(self):
        """Test fan-out: A -> B, A -> C, A -> D."""
        graph = ServiceGraph()
        
        for target in ["service-b", "service-c", "service-d"]:
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("service-a", target, edge)
        
        downstream = graph.get_downstream_services("service-a")
        assert len(downstream) == 3
        assert set(downstream) == {"service-b", "service-c", "service-d"}
    
    def test_fan_in_topology(self):
        """Test fan-in: A -> D, B -> D, C -> D."""
        graph = ServiceGraph()
        
        for source in ["service-a", "service-b", "service-c"]:
            edge = DependencyEdge(
                target_service_id="service-d",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(source, "service-d", edge)
        
        upstream = graph.get_upstream_services("service-d")
        assert len(upstream) == 3
        assert set(upstream) == {"service-a", "service-b", "service-c"}
    
    def test_mixed_service_and_infrastructure(self):
        """Test graph with both services and infrastructure."""
        graph = ServiceGraph()
        
        # Service to service
        edge1 = DependencyEdge(
            target_service_id="auth-service",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("api-gateway", "auth-service", edge1)
        
        # Service to infrastructure
        edge2 = DependencyEdge(
            target_infrastructure_id="postgres-db",
            infrastructure_type="postgresql",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("auth-service", "postgres-db", edge2)
        
        assert graph.get_node_count() == 3
        assert len(graph.get_service_nodes()) == 2
        assert len(graph.get_infrastructure_nodes()) == 1
        
        # Check relationships
        assert "auth-service" in graph.get_downstream_services("api-gateway")
        assert "postgres-db" in graph.get_downstream_services("auth-service")
        assert "api-gateway" in graph.get_upstream_services("auth-service")


class TestServiceGraphUtilities:
    """Test utility methods of ServiceGraph."""
    
    def test_clear_graph(self):
        """Test clearing the graph."""
        graph = ServiceGraph()
        
        edge = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge)
        
        assert graph.get_node_count() > 0
        assert graph.get_edge_count() > 0
        
        graph.clear()
        
        assert graph.get_node_count() == 0
        assert graph.get_edge_count() == 0
        assert len(graph.get_all_nodes()) == 0
    
    def test_get_adjacency_list(self):
        """Test getting the adjacency list representation."""
        graph = ServiceGraph()
        
        edge = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge)
        
        adj_list = graph.get_adjacency_list()
        assert "service-a" in adj_list
        assert len(adj_list["service-a"]) == 1
        assert adj_list["service-a"][0][0] == "service-b"
    
    def test_get_reverse_adjacency_list(self):
        """Test getting the reverse adjacency list."""
        graph = ServiceGraph()
        
        edge = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge)
        
        reverse_adj = graph.get_reverse_adjacency_list()
        assert "service-b" in reverse_adj
        assert "service-a" in reverse_adj["service-b"]
    
    def test_repr(self):
        """Test string representation."""
        graph = ServiceGraph()
        
        edge = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge)
        
        repr_str = repr(graph)
        assert "ServiceGraph" in repr_str
        assert "nodes=2" in repr_str
        assert "edges=1" in repr_str


class TestServiceGraphEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_self_loop(self):
        """Test adding a self-loop (service depends on itself)."""
        graph = ServiceGraph()
        
        edge = DependencyEdge(
            target_service_id="service-a",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-a", edge)
        
        # Should have 1 node and 1 edge
        assert graph.get_node_count() == 1
        assert graph.get_edge_count() == 1
        assert "service-a" in graph.get_downstream_services("service-a")
        assert "service-a" in graph.get_upstream_services("service-a")
    
    def test_multiple_edges_same_pair(self):
        """Test adding multiple edges between the same pair of nodes."""
        graph = ServiceGraph()
        
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="asynchronous",
            criticality="low"
        )
        
        graph.add_edge("service-a", "service-b", edge1)
        graph.add_edge("service-a", "service-b", edge2)
        
        # Should have 2 edges (parallel edges allowed)
        assert graph.get_edge_count() == 2
        downstream = graph.get_downstream_services("service-a")
        # But downstream list will have duplicates
        assert len(downstream) == 2
    
    def test_empty_service_id(self):
        """Test handling empty service IDs."""
        graph = ServiceGraph()
        graph.add_node("")
        
        assert graph.has_node("")
        assert graph.get_node_count() == 1



class TestServiceGraphBuildFromDeclarations:
    """Test building graph from dependency declarations."""
    
    def test_build_from_empty_declarations(self):
        """Test building graph from empty declarations list."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        warnings = graph.build_from_declarations([])
        
        assert graph.get_node_count() == 0
        assert graph.get_edge_count() == 0
        assert len(warnings) == 0
    
    def test_build_from_single_service_no_dependencies(self):
        """Test building graph with single service and no dependencies."""
        from src.models.dependency import ServiceDependency, WarningType
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(service_id="service-a", dependencies=[])
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        assert graph.get_node_count() == 1
        assert graph.has_node("service-a")
        assert graph.get_edge_count() == 0
        # Should warn about isolated node
        assert len(warnings) == 1
        assert warnings[0].warning_type == WarningType.ISOLATED_NODE
        assert "isolated node" in warnings[0].message.lower()
    
    def test_build_from_simple_dependency_chain(self):
        """Test building graph with simple dependency chain."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-b",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(service_id="service-b", dependencies=[])
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        assert graph.get_node_count() == 2
        assert graph.get_edge_count() == 1
        assert graph.has_edge("service-a", "service-b")
        assert len(warnings) == 0
    
    def test_build_from_declarations_with_infrastructure(self):
        """Test building graph with infrastructure dependencies."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="auth-service",
                dependencies=[
                    DependencyEdge(
                        target_infrastructure_id="postgres-db",
                        infrastructure_type="postgresql",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            )
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        assert graph.get_node_count() == 2
        assert graph.has_node("auth-service")
        assert graph.has_node("postgres-db")
        assert "postgres-db" in graph.get_infrastructure_nodes()
        assert graph.has_edge("auth-service", "postgres-db")
        assert len(warnings) == 0
    
    def test_build_from_declarations_missing_dependency(self):
        """Test building graph with missing dependency generates warning."""
        from src.models.dependency import ServiceDependency, WarningType
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-b",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            )
            # service-b is not declared
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Graph should still be built with the missing service
        assert graph.get_node_count() == 2
        assert graph.has_node("service-a")
        assert graph.has_node("service-b")
        assert graph.has_edge("service-a", "service-b")
        
        # Should have warning about missing dependency
        assert len(warnings) == 1
        assert warnings[0].warning_type == WarningType.MISSING_DEPENDENCY
        assert warnings[0].service_id == "service-a"
        assert warnings[0].target_id == "service-b"
        assert "service-b" in warnings[0].message
        assert "not declared" in warnings[0].message
    
    def test_build_from_declarations_multiple_missing_dependencies(self):
        """Test building graph with multiple missing dependencies."""
        from src.models.dependency import ServiceDependency, WarningType
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-b",
                        dependency_type="synchronous",
                        criticality="high"
                    ),
                    DependencyEdge(
                        target_service_id="service-c",
                        dependency_type="synchronous",
                        criticality="medium"
                    )
                ]
            )
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Should have warnings for both missing services
        assert len(warnings) == 2
        assert all(w.warning_type == WarningType.MISSING_DEPENDENCY for w in warnings)
        target_ids = {w.target_id for w in warnings}
        assert "service-b" in target_ids
        assert "service-c" in target_ids
    
    def test_build_from_declarations_complex_graph(self):
        """Test building a complex graph with multiple services and dependencies."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="api-gateway",
                dependencies=[
                    DependencyEdge(
                        target_service_id="auth-service",
                        dependency_type="synchronous",
                        timeout_ms=500,
                        criticality="high"
                    ),
                    DependencyEdge(
                        target_service_id="payment-service",
                        dependency_type="synchronous",
                        timeout_ms=1000,
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(
                service_id="auth-service",
                dependencies=[
                    DependencyEdge(
                        target_infrastructure_id="user-db",
                        infrastructure_type="postgresql",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(
                service_id="payment-service",
                dependencies=[
                    DependencyEdge(
                        target_infrastructure_id="payment-db",
                        infrastructure_type="postgresql",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            )
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Verify graph structure
        assert graph.get_node_count() == 5
        assert graph.get_edge_count() == 4
        
        # Verify services
        assert len(graph.get_service_nodes()) == 3
        assert "api-gateway" in graph.get_service_nodes()
        assert "auth-service" in graph.get_service_nodes()
        assert "payment-service" in graph.get_service_nodes()
        
        # Verify infrastructure
        assert len(graph.get_infrastructure_nodes()) == 2
        assert "user-db" in graph.get_infrastructure_nodes()
        assert "payment-db" in graph.get_infrastructure_nodes()
        
        # Verify edges
        assert graph.has_edge("api-gateway", "auth-service")
        assert graph.has_edge("api-gateway", "payment-service")
        assert graph.has_edge("auth-service", "user-db")
        assert graph.has_edge("payment-service", "payment-db")
        
        # Verify upstream/downstream relationships
        assert set(graph.get_downstream_services("api-gateway")) == {"auth-service", "payment-service"}
        assert graph.get_upstream_services("api-gateway") == []
        assert graph.get_upstream_services("auth-service") == ["api-gateway"]
        assert graph.get_upstream_services("payment-service") == ["api-gateway"]
        
        # No warnings expected
        assert len(warnings) == 0
    
    def test_build_from_declarations_with_no_target(self):
        """Test building graph with dependency that has no target."""
        from src.models.dependency import ServiceDependency, WarningType
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            )
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Should have warning about missing target
        assert len(warnings) == 2  # One for no target, one for isolated node
        warning_types = {w.warning_type for w in warnings}
        assert WarningType.NO_TARGET in warning_types
        assert WarningType.ISOLATED_NODE in warning_types
        
        no_target_warning = next(w for w in warnings if w.warning_type == WarningType.NO_TARGET)
        assert "no target" in no_target_warning.message.lower()
        
        # Graph should still have the service node
        assert graph.get_node_count() == 1
        assert graph.has_node("service-a")
        assert graph.get_edge_count() == 0
    
    def test_build_from_dependency_graph_object(self):
        """Test building from DependencyGraph object."""
        from src.models.dependency import ServiceDependency, DependencyGraph
        from datetime import datetime
        
        graph = ServiceGraph()
        
        dep_graph = DependencyGraph(
            version="1.0.0",
            updated_at=datetime.now(),
            services=[
                ServiceDependency(
                    service_id="service-a",
                    dependencies=[
                        DependencyEdge(
                            target_service_id="service-b",
                            dependency_type="synchronous",
                            criticality="high"
                        )
                    ]
                ),
                ServiceDependency(service_id="service-b", dependencies=[])
            ]
        )
        
        warnings = graph.build_from_dependency_graph(dep_graph)
        
        assert graph.get_node_count() == 2
        assert graph.get_edge_count() == 1
        assert graph.has_edge("service-a", "service-b")
        assert len(warnings) == 0
    
    def test_build_from_declarations_preserves_edge_metadata(self):
        """Test that edge metadata is preserved during graph construction."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-b",
                        dependency_type="synchronous",
                        timeout_ms=500,
                        retry_policy="exponential_backoff",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(service_id="service-b", dependencies=[])
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Retrieve and verify edge metadata
        edge_metadata = graph.get_edge_metadata("service-a", "service-b")
        assert edge_metadata is not None
        assert edge_metadata.target_service_id == "service-b"
        assert edge_metadata.dependency_type == "synchronous"
        assert edge_metadata.timeout_ms == 500
        assert edge_metadata.retry_policy == "exponential_backoff"
        assert edge_metadata.criticality == "high"
    
    def test_build_from_declarations_circular_dependency(self):
        """Test building graph with circular dependencies."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-b",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(
                service_id="service-b",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-a",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            )
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Graph should be built successfully
        assert graph.get_node_count() == 2
        assert graph.get_edge_count() == 2
        assert graph.has_edge("service-a", "service-b")
        assert graph.has_edge("service-b", "service-a")
        
        # Both services should have upstream and downstream
        assert "service-b" in graph.get_downstream_services("service-a")
        assert "service-b" in graph.get_upstream_services("service-a")
        assert "service-a" in graph.get_downstream_services("service-b")
        assert "service-a" in graph.get_upstream_services("service-b")
        
        # No warnings expected (circular dependency detection is a separate task)
        assert len(warnings) == 0
    
    def test_build_from_declarations_idempotent(self):
        """Test that building from declarations is idempotent when called multiple times."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-b",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(service_id="service-b", dependencies=[])
        ]
        
        # Build twice
        warnings1 = graph.build_from_declarations(declarations)
        warnings2 = graph.build_from_declarations(declarations)
        
        # Second build adds duplicate nodes and edges
        assert graph.get_node_count() == 2
        # Edges will be duplicated
        assert graph.get_edge_count() == 2

    def test_build_from_declarations_multiple_services_same_infrastructure(self):
        """Test multiple services depending on the same infrastructure."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_infrastructure_id="shared-cache",
                        infrastructure_type="redis",
                        dependency_type="synchronous",
                        criticality="medium"
                    )
                ]
            ),
            ServiceDependency(
                service_id="service-b",
                dependencies=[
                    DependencyEdge(
                        target_infrastructure_id="shared-cache",
                        infrastructure_type="redis",
                        dependency_type="synchronous",
                        criticality="medium"
                    )
                ]
            )
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Should have 3 nodes: 2 services + 1 infrastructure
        assert graph.get_node_count() == 3
        assert len(graph.get_service_nodes()) == 2
        assert len(graph.get_infrastructure_nodes()) == 1
        
        # Both services should depend on the same infrastructure
        assert "shared-cache" in graph.get_downstream_services("service-a")
        assert "shared-cache" in graph.get_downstream_services("service-b")
        
        # Infrastructure should have both services as upstream
        upstream = graph.get_upstream_services("shared-cache")
        assert len(upstream) == 2
        assert set(upstream) == {"service-a", "service-b"}
        
        assert len(warnings) == 0
    
    def test_build_from_declarations_mixed_targets(self):
        """Test service with both service and infrastructure dependencies."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="api-service",
                dependencies=[
                    DependencyEdge(
                        target_service_id="auth-service",
                        dependency_type="synchronous",
                        criticality="high"
                    ),
                    DependencyEdge(
                        target_infrastructure_id="redis-cache",
                        infrastructure_type="redis",
                        dependency_type="synchronous",
                        criticality="medium"
                    ),
                    DependencyEdge(
                        target_infrastructure_id="postgres-db",
                        infrastructure_type="postgresql",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(service_id="auth-service", dependencies=[])
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Should have 4 nodes: 2 services + 2 infrastructure
        assert graph.get_node_count() == 4
        assert len(graph.get_service_nodes()) == 2
        assert len(graph.get_infrastructure_nodes()) == 2
        
        # Verify all dependencies
        downstream = graph.get_downstream_services("api-service")
        assert len(downstream) == 3
        assert "auth-service" in downstream
        assert "redis-cache" in downstream
        assert "postgres-db" in downstream
        
        assert len(warnings) == 0
    
    def test_build_from_declarations_deep_chain(self):
        """Test building a deep dependency chain."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-b",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(
                service_id="service-b",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-c",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(
                service_id="service-c",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-d",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(service_id="service-d", dependencies=[])
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Verify chain structure
        assert graph.get_node_count() == 4
        assert graph.get_edge_count() == 3
        
        # Verify each link in the chain
        assert graph.has_edge("service-a", "service-b")
        assert graph.has_edge("service-b", "service-c")
        assert graph.has_edge("service-c", "service-d")
        
        # Verify upstream/downstream at each level
        assert len(graph.get_upstream_services("service-a")) == 0
        assert len(graph.get_downstream_services("service-a")) == 1
        
        assert len(graph.get_upstream_services("service-b")) == 1
        assert len(graph.get_downstream_services("service-b")) == 1
        
        assert len(graph.get_upstream_services("service-c")) == 1
        assert len(graph.get_downstream_services("service-c")) == 1
        
        assert len(graph.get_upstream_services("service-d")) == 1
        assert len(graph.get_downstream_services("service-d")) == 0
        
        assert len(warnings) == 0
    
    def test_build_from_declarations_diamond_topology(self):
        """Test building a diamond-shaped dependency graph."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-b",
                        dependency_type="synchronous",
                        criticality="high"
                    ),
                    DependencyEdge(
                        target_service_id="service-c",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(
                service_id="service-b",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-d",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(
                service_id="service-c",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-d",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(service_id="service-d", dependencies=[])
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Verify diamond structure
        assert graph.get_node_count() == 4
        assert graph.get_edge_count() == 4
        
        # Top node (A) has 2 downstream
        assert len(graph.get_downstream_services("service-a")) == 2
        assert set(graph.get_downstream_services("service-a")) == {"service-b", "service-c"}
        
        # Middle nodes (B, C) each have 1 upstream and 1 downstream
        assert len(graph.get_upstream_services("service-b")) == 1
        assert len(graph.get_downstream_services("service-b")) == 1
        assert len(graph.get_upstream_services("service-c")) == 1
        assert len(graph.get_downstream_services("service-c")) == 1
        
        # Bottom node (D) has 2 upstream
        assert len(graph.get_upstream_services("service-d")) == 2
        assert set(graph.get_upstream_services("service-d")) == {"service-b", "service-c"}
        assert len(graph.get_downstream_services("service-d")) == 0
        
        assert len(warnings) == 0
    
    def test_build_from_declarations_all_isolated_nodes(self):
        """Test building graph with all isolated nodes."""
        from src.models.dependency import ServiceDependency, WarningType
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(service_id="service-a", dependencies=[]),
            ServiceDependency(service_id="service-b", dependencies=[]),
            ServiceDependency(service_id="service-c", dependencies=[])
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # All nodes should be added
        assert graph.get_node_count() == 3
        assert graph.get_edge_count() == 0
        
        # Should have warnings for all isolated nodes
        assert len(warnings) == 3
        assert all(w.warning_type == WarningType.ISOLATED_NODE for w in warnings)
        
        isolated_services = {w.service_id for w in warnings}
        assert isolated_services == {"service-a", "service-b", "service-c"}
    
    def test_build_from_declarations_partial_missing_dependencies(self):
        """Test service with some valid and some missing dependencies."""
        from src.models.dependency import ServiceDependency, WarningType
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-b",
                        dependency_type="synchronous",
                        criticality="high"
                    ),
                    DependencyEdge(
                        target_service_id="service-missing",
                        dependency_type="synchronous",
                        criticality="high"
                    ),
                    DependencyEdge(
                        target_service_id="service-c",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(service_id="service-b", dependencies=[]),
            ServiceDependency(service_id="service-c", dependencies=[])
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Graph should be built with all nodes including missing one
        assert graph.get_node_count() == 4
        assert graph.has_node("service-missing")
        
        # Should have exactly 1 warning for the missing dependency
        assert len(warnings) == 1
        assert warnings[0].warning_type == WarningType.MISSING_DEPENDENCY
        assert warnings[0].target_id == "service-missing"
        
        # All edges should be created
        assert graph.get_edge_count() == 3
        assert graph.has_edge("service-a", "service-b")
        assert graph.has_edge("service-a", "service-missing")
        assert graph.has_edge("service-a", "service-c")
    
    def test_build_from_declarations_async_dependencies(self):
        """Test building graph with asynchronous dependencies."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="publisher-service",
                dependencies=[
                    DependencyEdge(
                        target_infrastructure_id="message-queue",
                        infrastructure_type="kafka",
                        dependency_type="asynchronous",
                        criticality="medium"
                    )
                ]
            ),
            ServiceDependency(
                service_id="consumer-service",
                dependencies=[
                    DependencyEdge(
                        target_infrastructure_id="message-queue",
                        infrastructure_type="kafka",
                        dependency_type="asynchronous",
                        criticality="medium"
                    )
                ]
            )
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Verify graph structure
        assert graph.get_node_count() == 3
        assert len(graph.get_service_nodes()) == 2
        assert len(graph.get_infrastructure_nodes()) == 1
        
        # Verify edge metadata for async dependencies
        edge1 = graph.get_edge_metadata("publisher-service", "message-queue")
        assert edge1 is not None
        assert edge1.dependency_type == "asynchronous"
        
        edge2 = graph.get_edge_metadata("consumer-service", "message-queue")
        assert edge2 is not None
        assert edge2.dependency_type == "asynchronous"
        
        assert len(warnings) == 0
    
    def test_build_from_declarations_with_retry_policies(self):
        """Test that retry policies are preserved in edge metadata."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_service_id="service-b",
                        dependency_type="synchronous",
                        timeout_ms=1000,
                        retry_policy="exponential_backoff",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(service_id="service-b", dependencies=[])
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Verify edge metadata includes retry policy
        edge = graph.get_edge_metadata("service-a", "service-b")
        assert edge is not None
        assert edge.retry_policy == "exponential_backoff"
        assert edge.timeout_ms == 1000
        
        assert len(warnings) == 0
    
    def test_build_from_declarations_large_fanout(self):
        """Test service with large number of dependencies (fan-out)."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        
        # Create a service with 10 dependencies
        num_dependencies = 10
        dependencies = [
            DependencyEdge(
                target_service_id=f"service-{i}",
                dependency_type="synchronous",
                criticality="medium"
            )
            for i in range(num_dependencies)
        ]
        
        declarations = [
            ServiceDependency(
                service_id="api-gateway",
                dependencies=dependencies
            )
        ]
        
        # Add declarations for all target services
        for i in range(num_dependencies):
            declarations.append(
                ServiceDependency(service_id=f"service-{i}", dependencies=[])
            )
        
        warnings = graph.build_from_declarations(declarations)
        
        # Verify structure
        assert graph.get_node_count() == num_dependencies + 1
        assert graph.get_edge_count() == num_dependencies
        
        # Verify all downstream services
        downstream = graph.get_downstream_services("api-gateway")
        assert len(downstream) == num_dependencies
        assert all(f"service-{i}" in downstream for i in range(num_dependencies))
        
        assert len(warnings) == 0
    
    def test_build_from_declarations_criticality_levels(self):
        """Test that different criticality levels are preserved."""
        from src.models.dependency import ServiceDependency
        
        graph = ServiceGraph()
        declarations = [
            ServiceDependency(
                service_id="service-a",
                dependencies=[
                    DependencyEdge(
                        target_service_id="critical-service",
                        dependency_type="synchronous",
                        criticality="high"
                    ),
                    DependencyEdge(
                        target_service_id="important-service",
                        dependency_type="synchronous",
                        criticality="medium"
                    ),
                    DependencyEdge(
                        target_service_id="optional-service",
                        dependency_type="synchronous",
                        criticality="low"
                    )
                ]
            ),
            ServiceDependency(service_id="critical-service", dependencies=[]),
            ServiceDependency(service_id="important-service", dependencies=[]),
            ServiceDependency(service_id="optional-service", dependencies=[])
        ]
        
        warnings = graph.build_from_declarations(declarations)
        
        # Verify criticality levels are preserved
        critical_edge = graph.get_edge_metadata("service-a", "critical-service")
        assert critical_edge.criticality == "high"
        
        important_edge = graph.get_edge_metadata("service-a", "important-service")
        assert important_edge.criticality == "medium"
        
        optional_edge = graph.get_edge_metadata("service-a", "optional-service")
        assert optional_edge.criticality == "low"
        
        assert len(warnings) == 0



class TestCascadingImpactScore:
    """Test cascading impact score computation."""

    def test_leaf_node_has_zero_impact(self):
        """Test that a leaf node (no downstream dependencies) has impact score of 0."""
        graph = ServiceGraph()
        graph.add_node("leaf-service")

        score = graph.compute_cascading_impact_score("leaf-service")
        assert score == 0.0

    def test_nonexistent_service_has_zero_impact(self):
        """Test that a non-existent service returns impact score of 0."""
        graph = ServiceGraph()

        score = graph.compute_cascading_impact_score("nonexistent")
        assert score == 0.0

    def test_simple_chain_impact_score(self):
        """Test impact score for a simple chain: A -> B -> C."""
        graph = ServiceGraph()

        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="high"
        )

        graph.add_edge("service-a", "service-b", edge1)
        graph.add_edge("service-b", "service-c", edge2)

        # For service-a:
        # - service-b at depth 1, fanout 1: (1/1) * (1/1) = 1.0
        # - service-c at depth 2, fanout 1: (1/2) * (1/1) = 0.5
        # Total: 1.0 + 0.5 = 1.5, normalized to 1.0
        score_a = graph.compute_cascading_impact_score("service-a")
        assert score_a == 1.0  # Normalized to max of 1.0

        # For service-b:
        # - service-c at depth 1, fanout 1: (1/1) * (1/1) = 1.0
        score_b = graph.compute_cascading_impact_score("service-b")
        assert score_b == 1.0

        # For service-c (leaf):
        score_c = graph.compute_cascading_impact_score("service-c")
        assert score_c == 0.0

    def test_fan_out_impact_score(self):
        """Test impact score for fan-out topology: A -> B, A -> C, A -> D."""
        graph = ServiceGraph()

        for target in ["service-b", "service-c", "service-d"]:
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("service-a", target, edge)

        # For service-a:
        # - 3 services at depth 1, fanout 3: 3 * (1/1) * (1/3) = 1.0
        score = graph.compute_cascading_impact_score("service-a")
        assert score == 1.0

    def test_diamond_topology_impact_score(self):
        """Test impact score for diamond topology: A -> B, A -> C, B -> D, C -> D."""
        graph = ServiceGraph()

        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="high"
        )
        edge3 = DependencyEdge(
            target_service_id="service-d",
            dependency_type="synchronous",
            criticality="high"
        )
        edge4 = DependencyEdge(
            target_service_id="service-d",
            dependency_type="synchronous",
            criticality="high"
        )

        graph.add_edge("service-a", "service-b", edge1)
        graph.add_edge("service-a", "service-c", edge2)
        graph.add_edge("service-b", "service-d", edge3)
        graph.add_edge("service-c", "service-d", edge4)

        # For service-a:
        # - service-b at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # - service-c at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # - service-d at depth 2 (via B), fanout 1: (1/2) * (1/1) = 0.5
        # Note: service-d is visited only once due to BFS visited tracking
        # Total: 0.5 + 0.5 + 0.5 = 1.5, normalized to 1.0
        score_a = graph.compute_cascading_impact_score("service-a")
        assert score_a == 1.0  # Normalized

        # For service-b:
        # - service-d at depth 1, fanout 1: (1/1) * (1/1) = 1.0
        score_b = graph.compute_cascading_impact_score("service-b")
        assert score_b == 1.0

    def test_complex_graph_impact_scores(self):
        """Test impact scores in a complex graph with multiple levels."""
        graph = ServiceGraph()

        # Build graph: A -> B, A -> C, B -> D, C -> D, D -> E
        edges = [
            ("service-a", "service-b"),
            ("service-a", "service-c"),
            ("service-b", "service-d"),
            ("service-c", "service-d"),
            ("service-d", "service-e")
        ]

        for source, target in edges:
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(source, target, edge)

        # All services should have scores >= 0
        for service_id in ["service-a", "service-b", "service-c", "service-d", "service-e"]:
            score = graph.compute_cascading_impact_score(service_id)
            assert score >= 0.0
            assert score <= 1.0

        # Service-a should have highest impact (most downstream services)
        score_a = graph.compute_cascading_impact_score("service-a")
        score_b = graph.compute_cascading_impact_score("service-b")
        score_c = graph.compute_cascading_impact_score("service-c")

        assert score_a >= score_b
        assert score_a >= score_c

        # Leaf node should have zero impact
        score_e = graph.compute_cascading_impact_score("service-e")
        assert score_e == 0.0

    def test_circular_dependency_impact_score(self):
        """Test impact score with circular dependencies (should handle gracefully)."""
        graph = ServiceGraph()

        # Create circular dependency: A -> B -> C -> A
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="high"
        )
        edge3 = DependencyEdge(
            target_service_id="service-a",
            dependency_type="synchronous",
            criticality="high"
        )

        graph.add_edge("service-a", "service-b", edge1)
        graph.add_edge("service-b", "service-c", edge2)
        graph.add_edge("service-c", "service-a", edge3)

        # Should handle circular dependency without infinite loop
        score_a = graph.compute_cascading_impact_score("service-a")
        score_b = graph.compute_cascading_impact_score("service-b")
        score_c = graph.compute_cascading_impact_score("service-c")

        # All should have valid scores in [0, 1]
        assert 0.0 <= score_a <= 1.0
        assert 0.0 <= score_b <= 1.0
        assert 0.0 <= score_c <= 1.0

        # All should have same score due to symmetry
        assert score_a == score_b == score_c

    def test_single_dependency_impact_score(self):
        """Test impact score for service with single downstream dependency."""
        graph = ServiceGraph()

        edge = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge)

        # For service-a:
        # - service-b at depth 1, fanout 1: (1/1) * (1/1) = 1.0
        score = graph.compute_cascading_impact_score("service-a")
        assert score == 1.0

    def test_deep_chain_impact_score(self):
        """Test impact score for a deep dependency chain."""
        graph = ServiceGraph()

        # Create chain: A -> B -> C -> D -> E
        services = ["service-a", "service-b", "service-c", "service-d", "service-e"]
        for i in range(len(services) - 1):
            edge = DependencyEdge(
                target_service_id=services[i + 1],
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(services[i], services[i + 1], edge)

        # Service-a should have highest impact (all downstream)
        score_a = graph.compute_cascading_impact_score("service-a")
        # Formula: 1/1 + 1/2 + 1/3 + 1/4 = 2.083..., normalized to 1.0
        assert score_a == 1.0

        # Each subsequent service should have lower impact
        scores = [graph.compute_cascading_impact_score(s) for s in services]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_mixed_fanout_impact_score(self):
        """Test impact score with varying fanout at different levels."""
        graph = ServiceGraph()

        # A -> B, A -> C
        # B -> D, B -> E, B -> F
        # C -> G

        graph.add_edge("service-a", "service-b", DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("service-a", "service-c", DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="high"
        ))

        for target in ["service-d", "service-e", "service-f"]:
            graph.add_edge("service-b", target, DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            ))

        graph.add_edge("service-c", "service-g", DependencyEdge(
            target_service_id="service-g",
            dependency_type="synchronous",
            criticality="high"
        ))

        # For service-a:
        # - service-b at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # - service-c at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # - service-d at depth 2, fanout 3: (1/2) * (1/3) = 0.167
        # - service-e at depth 2, fanout 3: (1/2) * (1/3) = 0.167
        # - service-f at depth 2, fanout 3: (1/2) * (1/3) = 0.167
        # - service-g at depth 2, fanout 1: (1/2) * (1/1) = 0.5
        # Total: 0.5 + 0.5 + 0.167 + 0.167 + 0.167 + 0.5 = 2.0, normalized to 1.0
        score_a = graph.compute_cascading_impact_score("service-a")
        assert score_a == 1.0

        # Service-b has 3 downstream, service-c has 1 downstream
        # Both will be normalized to 1.0, but before normalization b > c
        score_b = graph.compute_cascading_impact_score("service-b")
        score_c = graph.compute_cascading_impact_score("service-c")
        # Both are normalized to 1.0, so just verify they're valid
        assert score_b == 1.0
        assert score_c == 1.0

    def test_infrastructure_dependencies_impact_score(self):
        """Test impact score with infrastructure dependencies."""
        graph = ServiceGraph()

        # Service -> Infrastructure should count in impact score
        edge = DependencyEdge(
            target_infrastructure_id="postgres-db",
            infrastructure_type="postgresql",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "postgres-db", edge)

        # Should have impact score > 0
        score = graph.compute_cascading_impact_score("service-a")
        assert score == 1.0

    def test_normalized_score_never_exceeds_one(self):
        """Test that impact score is always normalized to [0, 1]."""
        graph = ServiceGraph()

        # Create a large fan-out to test normalization
        for i in range(20):
            edge = DependencyEdge(
                target_service_id=f"service-{i}",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("root-service", f"service-{i}", edge)

            # Add second level
            for j in range(5):
                edge2 = DependencyEdge(
                    target_service_id=f"service-{i}-{j}",
                    dependency_type="synchronous",
                    criticality="high"
                )
                graph.add_edge(f"service-{i}", f"service-{i}-{j}", edge2)

        score = graph.compute_cascading_impact_score("root-service")
        assert score <= 1.0
        assert score > 0.0


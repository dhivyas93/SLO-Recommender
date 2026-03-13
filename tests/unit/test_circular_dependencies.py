"""Unit tests for circular dependency detection using Tarjan's algorithm."""

import pytest
from src.algorithms.service_graph import ServiceGraph
from src.models.dependency import DependencyEdge


class TestCircularDependencyDetection:
    """Test Tarjan's algorithm for detecting circular dependencies."""
    
    def test_no_circular_dependencies_empty_graph(self):
        """Test that empty graph has no circular dependencies."""
        graph = ServiceGraph()
        cycles = graph.detect_circular_dependencies()
        assert len(cycles) == 0
    
    def test_no_circular_dependencies_single_node(self):
        """Test that single node with no edges has no circular dependencies."""
        graph = ServiceGraph()
        graph.add_node("service-a")
        cycles = graph.detect_circular_dependencies()
        assert len(cycles) == 0
    
    def test_no_circular_dependencies_chain(self):
        """Test that simple chain has no circular dependencies."""
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
        
        cycles = graph.detect_circular_dependencies()
        assert len(cycles) == 0
    
    def test_simple_two_node_cycle(self):
        """Test detection of simple two-node cycle: A -> B -> A."""
        graph = ServiceGraph()
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="service-a",
            dependency_type="synchronous",
            criticality="high"
        )
        
        graph.add_edge("service-a", "service-b", edge1)
        graph.add_edge("service-b", "service-a", edge2)
        
        cycles = graph.detect_circular_dependencies()
        assert len(cycles) == 1
        assert len(cycles[0]) == 2
        assert set(cycles[0]) == {"service-a", "service-b"}
    
    def test_three_node_cycle(self):
        """Test detection of three-node cycle: A -> B -> C -> A."""
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
            target_service_id="service-a",
            dependency_type="synchronous",
            criticality="high"
        )
        
        graph.add_edge("service-a", "service-b", edge1)
        graph.add_edge("service-b", "service-c", edge2)
        graph.add_edge("service-c", "service-a", edge3)
        
        cycles = graph.detect_circular_dependencies()
        assert len(cycles) == 1
        assert len(cycles[0]) == 3
        assert set(cycles[0]) == {"service-a", "service-b", "service-c"}
    
    def test_self_loop(self):
        """Test that self-loop is NOT considered a circular dependency.
        
        According to the design, only SCCs with size > 1 are circular dependencies.
        A self-loop creates an SCC of size 1, so it should not be reported.
        """
        graph = ServiceGraph()
        edge = DependencyEdge(
            target_service_id="service-a",
            dependency_type="synchronous",
            criticality="high"
        )
        
        graph.add_edge("service-a", "service-a", edge)
        
        cycles = graph.detect_circular_dependencies()
        # Self-loops are not considered circular dependencies (SCC size = 1)
        assert len(cycles) == 0
    
    def test_multiple_separate_cycles(self):
        """Test detection of multiple separate cycles."""
        graph = ServiceGraph()
        
        # First cycle: A -> B -> A
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="service-a",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge1)
        graph.add_edge("service-b", "service-a", edge2)
        
        # Second cycle: C -> D -> E -> C
        edge3 = DependencyEdge(
            target_service_id="service-d",
            dependency_type="synchronous",
            criticality="high"
        )
        edge4 = DependencyEdge(
            target_service_id="service-e",
            dependency_type="synchronous",
            criticality="high"
        )
        edge5 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-c", "service-d", edge3)
        graph.add_edge("service-d", "service-e", edge4)
        graph.add_edge("service-e", "service-c", edge5)
        
        cycles = graph.detect_circular_dependencies()
        assert len(cycles) == 2
        
        # Check that we have one 2-node cycle and one 3-node cycle
        cycle_sizes = sorted([len(cycle) for cycle in cycles])
        assert cycle_sizes == [2, 3]
        
        # Check cycle contents
        cycle_sets = [set(cycle) for cycle in cycles]
        assert {"service-a", "service-b"} in cycle_sets
        assert {"service-c", "service-d", "service-e"} in cycle_sets
    
    def test_cycle_with_external_nodes(self):
        """Test cycle detection when there are nodes outside the cycle."""
        graph = ServiceGraph()
        
        # External node pointing to cycle
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge1)
        
        # Cycle: B -> C -> D -> B
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
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-b", "service-c", edge2)
        graph.add_edge("service-c", "service-d", edge3)
        graph.add_edge("service-d", "service-b", edge4)
        
        # Cycle pointing to external node
        edge5 = DependencyEdge(
            target_service_id="service-e",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-d", "service-e", edge5)
        
        cycles = graph.detect_circular_dependencies()
        assert len(cycles) == 1
        assert len(cycles[0]) == 3
        assert set(cycles[0]) == {"service-b", "service-c", "service-d"}
    
    def test_complex_graph_with_multiple_cycles(self):
        """Test complex graph with nested and overlapping structures."""
        graph = ServiceGraph()
        
        # Create a more complex structure:
        # A -> B -> C -> A (cycle 1)
        # B -> D -> E -> B (cycle 2, shares B with cycle 1)
        
        # Cycle 1: A -> B -> C -> A
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
        
        # Additional edges from B: B -> D -> E -> B
        edge4 = DependencyEdge(
            target_service_id="service-d",
            dependency_type="synchronous",
            criticality="high"
        )
        edge5 = DependencyEdge(
            target_service_id="service-e",
            dependency_type="synchronous",
            criticality="high"
        )
        edge6 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-b", "service-d", edge4)
        graph.add_edge("service-d", "service-e", edge5)
        graph.add_edge("service-e", "service-b", edge6)
        
        cycles = graph.detect_circular_dependencies()
        
        # Tarjan's algorithm will find one large SCC containing all nodes
        # because they're all strongly connected through the shared node B
        assert len(cycles) == 1
        assert len(cycles[0]) == 5
        assert set(cycles[0]) == {"service-a", "service-b", "service-c", "service-d", "service-e"}
    
    def test_infrastructure_not_included_in_cycles(self):
        """Test that infrastructure nodes are not included in cycle detection."""
        graph = ServiceGraph()
        
        # Create a cycle with services
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="service-a",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge1)
        graph.add_edge("service-b", "service-a", edge2)
        
        # Add infrastructure dependency (should not affect cycle detection)
        edge3 = DependencyEdge(
            target_infrastructure_id="postgres-db",
            infrastructure_type="postgresql",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "postgres-db", edge3)
        
        cycles = graph.detect_circular_dependencies()
        assert len(cycles) == 1
        assert len(cycles[0]) == 2
        assert set(cycles[0]) == {"service-a", "service-b"}
        # Infrastructure should not be in the cycle
        assert "postgres-db" not in cycles[0]
    
    def test_large_cycle(self):
        """Test detection of a large cycle with many nodes."""
        graph = ServiceGraph()
        
        # Create a cycle with 10 nodes: 0 -> 1 -> 2 -> ... -> 9 -> 0
        num_nodes = 10
        for i in range(num_nodes):
            next_i = (i + 1) % num_nodes
            edge = DependencyEdge(
                target_service_id=f"service-{next_i}",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(f"service-{i}", f"service-{next_i}", edge)
        
        cycles = graph.detect_circular_dependencies()
        assert len(cycles) == 1
        assert len(cycles[0]) == num_nodes
        expected_services = {f"service-{i}" for i in range(num_nodes)}
        assert set(cycles[0]) == expected_services
    
    def test_diamond_with_cycle_at_bottom(self):
        """Test diamond topology with a cycle at the bottom."""
        graph = ServiceGraph()
        
        # Diamond: A -> B, A -> C, B -> D, C -> D
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
        
        # Add cycle at D: D -> E -> F -> D
        edge5 = DependencyEdge(
            target_service_id="service-e",
            dependency_type="synchronous",
            criticality="high"
        )
        edge6 = DependencyEdge(
            target_service_id="service-f",
            dependency_type="synchronous",
            criticality="high"
        )
        edge7 = DependencyEdge(
            target_service_id="service-d",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-d", "service-e", edge5)
        graph.add_edge("service-e", "service-f", edge6)
        graph.add_edge("service-f", "service-d", edge7)
        
        cycles = graph.detect_circular_dependencies()
        assert len(cycles) == 1
        assert len(cycles[0]) == 3
        assert set(cycles[0]) == {"service-d", "service-e", "service-f"}

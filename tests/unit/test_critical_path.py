"""Unit tests for critical path computation."""

import pytest
from src.algorithms.service_graph import ServiceGraph
from src.models.dependency import DependencyEdge


class TestCriticalPath:
    """Test suite for critical path algorithm."""
    
    def test_critical_path_linear_chain(self):
        """Test critical path with a simple linear chain: A -> B -> C."""
        graph = ServiceGraph()
        
        # Build graph: A -> B -> C
        edge1 = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="C",
            dependency_type="synchronous",
            criticality="high"
        )
        
        graph.add_edge("A", "B", edge1)
        graph.add_edge("B", "C", edge2)
        
        # Service latencies
        latencies = {
            "A": 10.0,
            "B": 50.0,
            "C": 30.0
        }
        
        # Compute critical path from A
        result = graph.compute_critical_path("A", latencies)
        
        assert result['path'] == ["A", "B", "C"]
        assert result['total_latency_ms'] == 90.0
        assert result['bottleneck_service'] == "B"
    
    def test_critical_path_branching(self):
        """Test critical path with branching: A -> B -> C and A -> D."""
        graph = ServiceGraph()
        
        # Build graph: A -> B -> C, A -> D
        edge1 = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="C",
            dependency_type="synchronous",
            criticality="high"
        )
        edge3 = DependencyEdge(
            target_service_id="D",
            dependency_type="synchronous",
            criticality="high"
        )
        
        graph.add_edge("A", "B", edge1)
        graph.add_edge("B", "C", edge2)
        graph.add_edge("A", "D", edge3)
        
        # Service latencies - longer path through B->C
        latencies = {
            "A": 10.0,
            "B": 50.0,
            "C": 30.0,
            "D": 20.0
        }
        
        # Compute critical path from A
        result = graph.compute_critical_path("A", latencies)
        
        # Should choose the longer path A -> B -> C
        assert result['path'] == ["A", "B", "C"]
        assert result['total_latency_ms'] == 90.0
        assert result['bottleneck_service'] == "B"
    
    def test_critical_path_no_dependencies(self):
        """Test critical path for a service with no downstream dependencies."""
        graph = ServiceGraph()
        
        # Add a single service with no dependencies
        graph.add_node("A", is_infrastructure=False)
        
        latencies = {"A": 25.0}
        
        result = graph.compute_critical_path("A", latencies)
        
        assert result['path'] == ["A"]
        assert result['total_latency_ms'] == 25.0
        assert result['bottleneck_service'] == "A"
    
    def test_critical_path_nonexistent_service(self):
        """Test critical path for a service that doesn't exist in the graph."""
        graph = ServiceGraph()
        
        result = graph.compute_critical_path("nonexistent", {})
        
        assert result['path'] == []
        assert result['total_latency_ms'] == 0.0
        assert result['bottleneck_service'] is None
    
    def test_critical_path_missing_latency_data(self):
        """Test critical path when some services have no latency data."""
        graph = ServiceGraph()
        
        # Build graph: A -> B -> C
        edge1 = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        edge2 = DependencyEdge(
            target_service_id="C",
            dependency_type="synchronous",
            criticality="high"
        )
        
        graph.add_edge("A", "B", edge1)
        graph.add_edge("B", "C", edge2)
        
        # Only provide latency for A and C, not B
        latencies = {
            "A": 10.0,
            "C": 30.0
        }
        
        result = graph.compute_critical_path("A", latencies)
        
        # Should still compute path, treating missing latency as 0
        assert result['path'] == ["A", "B", "C"]
        assert result['total_latency_ms'] == 40.0  # 10 + 0 + 30
        assert result['bottleneck_service'] == "C"
    
    def test_critical_path_complex_graph(self):
        """Test critical path in a more complex graph with multiple paths."""
        graph = ServiceGraph()
        
        # Build graph:
        #     A
        #    / \
        #   B   C
        #  / \   \
        # D   E   F
        
        graph.add_edge("A", "B", DependencyEdge(
            target_service_id="B", dependency_type="synchronous", criticality="high"
        ))
        graph.add_edge("A", "C", DependencyEdge(
            target_service_id="C", dependency_type="synchronous", criticality="high"
        ))
        graph.add_edge("B", "D", DependencyEdge(
            target_service_id="D", dependency_type="synchronous", criticality="high"
        ))
        graph.add_edge("B", "E", DependencyEdge(
            target_service_id="E", dependency_type="synchronous", criticality="high"
        ))
        graph.add_edge("C", "F", DependencyEdge(
            target_service_id="F", dependency_type="synchronous", criticality="high"
        ))
        
        latencies = {
            "A": 5.0,
            "B": 20.0,
            "C": 15.0,
            "D": 10.0,
            "E": 50.0,  # Highest latency leaf
            "F": 25.0
        }
        
        result = graph.compute_critical_path("A", latencies)
        
        # Should choose path A -> B -> E (total: 75)
        assert result['path'] == ["A", "B", "E"]
        assert result['total_latency_ms'] == 75.0
        assert result['bottleneck_service'] == "E"
    
    def test_critical_path_with_cycle(self):
        """Test critical path handles cycles gracefully."""
        graph = ServiceGraph()
        
        # Build graph with cycle: A -> B -> C -> B
        graph.add_edge("A", "B", DependencyEdge(
            target_service_id="B", dependency_type="synchronous", criticality="high"
        ))
        graph.add_edge("B", "C", DependencyEdge(
            target_service_id="C", dependency_type="synchronous", criticality="high"
        ))
        graph.add_edge("C", "B", DependencyEdge(
            target_service_id="B", dependency_type="synchronous", criticality="high"
        ))
        
        latencies = {
            "A": 10.0,
            "B": 20.0,
            "C": 30.0
        }
        
        # Should handle cycle without infinite loop
        result = graph.compute_critical_path("A", latencies)
        
        # Should find a path without revisiting nodes
        assert len(result['path']) > 0
        assert result['total_latency_ms'] > 0
        # Path should not contain duplicates (no infinite loop)
        assert len(result['path']) == len(set(result['path']))
    
    def test_critical_path_zero_latencies(self):
        """Test critical path when all services have zero latency."""
        graph = ServiceGraph()
        
        graph.add_edge("A", "B", DependencyEdge(
            target_service_id="B", dependency_type="synchronous", criticality="high"
        ))
        graph.add_edge("B", "C", DependencyEdge(
            target_service_id="C", dependency_type="synchronous", criticality="high"
        ))
        
        latencies = {
            "A": 0.0,
            "B": 0.0,
            "C": 0.0
        }
        
        result = graph.compute_critical_path("A", latencies)
        
        # When all latencies are zero, any path is valid
        # The algorithm should still return a valid path
        assert len(result['path']) > 0
        assert result['path'][0] == "A"
        assert result['total_latency_ms'] == 0.0
        assert result['bottleneck_service'] is None
    
    def test_critical_path_single_high_latency_service(self):
        """Test that bottleneck correctly identifies the highest latency service."""
        graph = ServiceGraph()
        
        # Build chain where middle service has highest latency
        graph.add_edge("A", "B", DependencyEdge(
            target_service_id="B", dependency_type="synchronous", criticality="high"
        ))
        graph.add_edge("B", "C", DependencyEdge(
            target_service_id="C", dependency_type="synchronous", criticality="high"
        ))
        graph.add_edge("C", "D", DependencyEdge(
            target_service_id="D", dependency_type="synchronous", criticality="high"
        ))
        
        latencies = {
            "A": 5.0,
            "B": 100.0,  # Bottleneck
            "C": 10.0,
            "D": 5.0
        }
        
        result = graph.compute_critical_path("A", latencies)
        
        assert result['path'] == ["A", "B", "C", "D"]
        assert result['total_latency_ms'] == 120.0
        assert result['bottleneck_service'] == "B"
    
    def test_critical_path_realistic_api_gateway_scenario(self):
        """
        Test critical path with realistic API gateway scenario.
        
        Known topology:
            api-gateway (5ms)
                ├─> auth-service (20ms)
                │   └─> user-db (45ms)
                └─> payment-service (120ms)
                    └─> payment-db (80ms)
        
        Known critical path: api-gateway -> payment-service -> payment-db
        Expected total latency: 5 + 120 + 80 = 205ms
        Expected bottleneck: payment-service (120ms)
        """
        graph = ServiceGraph()
        
        # Build the graph
        graph.add_edge("api-gateway", "auth-service", DependencyEdge(
            target_service_id="auth-service",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("api-gateway", "payment-service", DependencyEdge(
            target_service_id="payment-service",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("auth-service", "user-db", DependencyEdge(
            target_service_id="user-db",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("payment-service", "payment-db", DependencyEdge(
            target_service_id="payment-db",
            dependency_type="synchronous",
            criticality="high"
        ))
        
        latencies = {
            "api-gateway": 5.0,
            "auth-service": 20.0,
            "user-db": 45.0,
            "payment-service": 120.0,
            "payment-db": 80.0
        }
        
        result = graph.compute_critical_path("api-gateway", latencies)
        
        # Verify known critical path
        assert result['path'] == ["api-gateway", "payment-service", "payment-db"]
        assert result['total_latency_ms'] == 205.0
        assert result['bottleneck_service'] == "payment-service"
    
    def test_critical_path_realistic_multi_tier_scenario(self):
        """
        Test critical path with realistic multi-tier application.
        
        Known topology:
            frontend (10ms)
                └─> backend-api (30ms)
                    ├─> cache (5ms)
                    ├─> database (100ms)
                    │   └─> replica (50ms)
                    └─> external-api (200ms)
        
        Known critical path: frontend -> backend-api -> external-api
        Expected total latency: 10 + 30 + 200 = 240ms
        Expected bottleneck: external-api (200ms)
        """
        graph = ServiceGraph()
        
        # Build the graph
        graph.add_edge("frontend", "backend-api", DependencyEdge(
            target_service_id="backend-api",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("backend-api", "cache", DependencyEdge(
            target_service_id="cache",
            dependency_type="synchronous",
            criticality="medium"
        ))
        graph.add_edge("backend-api", "database", DependencyEdge(
            target_service_id="database",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("backend-api", "external-api", DependencyEdge(
            target_service_id="external-api",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("database", "replica", DependencyEdge(
            target_service_id="replica",
            dependency_type="synchronous",
            criticality="medium"
        ))
        
        latencies = {
            "frontend": 10.0,
            "backend-api": 30.0,
            "cache": 5.0,
            "database": 100.0,
            "replica": 50.0,
            "external-api": 200.0
        }
        
        result = graph.compute_critical_path("frontend", latencies)
        
        # Verify known critical path
        assert result['path'] == ["frontend", "backend-api", "external-api"]
        assert result['total_latency_ms'] == 240.0
        assert result['bottleneck_service'] == "external-api"
    
    def test_critical_path_realistic_microservices_mesh(self):
        """
        Test critical path with realistic microservices mesh.
        
        Known topology:
            order-service (15ms)
                ├─> inventory-service (25ms)
                │   └─> inventory-db (40ms)
                ├─> pricing-service (35ms)
                │   ├─> pricing-db (30ms)
                │   └─> discount-service (60ms)
                └─> shipping-service (20ms)
                    └─> shipping-db (35ms)
        
        Known critical path: order-service -> pricing-service -> discount-service
        Expected total latency: 15 + 35 + 60 = 110ms
        Expected bottleneck: discount-service (60ms)
        """
        graph = ServiceGraph()
        
        # Build the graph
        graph.add_edge("order-service", "inventory-service", DependencyEdge(
            target_service_id="inventory-service",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("order-service", "pricing-service", DependencyEdge(
            target_service_id="pricing-service",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("order-service", "shipping-service", DependencyEdge(
            target_service_id="shipping-service",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("inventory-service", "inventory-db", DependencyEdge(
            target_service_id="inventory-db",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("pricing-service", "pricing-db", DependencyEdge(
            target_service_id="pricing-db",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("pricing-service", "discount-service", DependencyEdge(
            target_service_id="discount-service",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("shipping-service", "shipping-db", DependencyEdge(
            target_service_id="shipping-db",
            dependency_type="synchronous",
            criticality="high"
        ))
        
        latencies = {
            "order-service": 15.0,
            "inventory-service": 25.0,
            "inventory-db": 40.0,
            "pricing-service": 35.0,
            "pricing-db": 30.0,
            "discount-service": 60.0,
            "shipping-service": 20.0,
            "shipping-db": 35.0
        }
        
        result = graph.compute_critical_path("order-service", latencies)
        
        # Verify known critical path
        assert result['path'] == ["order-service", "pricing-service", "discount-service"]
        assert result['total_latency_ms'] == 110.0
        assert result['bottleneck_service'] == "discount-service"
    
    def test_critical_path_deep_dependency_chain(self):
        """
        Test critical path with deep dependency chain (6 levels).
        
        Known topology: A -> B -> C -> D -> E -> F
        Known critical path: A -> B -> C -> D -> E -> F
        Expected total latency: 10 + 20 + 15 + 30 + 25 + 40 = 140ms
        Expected bottleneck: F (40ms)
        """
        graph = ServiceGraph()
        
        # Build deep chain
        services = ["A", "B", "C", "D", "E", "F"]
        for i in range(len(services) - 1):
            graph.add_edge(services[i], services[i+1], DependencyEdge(
                target_service_id=services[i+1],
                dependency_type="synchronous",
                criticality="high"
            ))
        
        latencies = {
            "A": 10.0,
            "B": 20.0,
            "C": 15.0,
            "D": 30.0,
            "E": 25.0,
            "F": 40.0
        }
        
        result = graph.compute_critical_path("A", latencies)
        
        # Verify known critical path
        assert result['path'] == ["A", "B", "C", "D", "E", "F"]
        assert result['total_latency_ms'] == 140.0
        assert result['bottleneck_service'] == "F"
    
    def test_critical_path_wide_fanout_scenario(self):
        """
        Test critical path with wide fanout (one service calling many).
        
        Known topology:
            aggregator (5ms)
                ├─> service-1 (10ms)
                ├─> service-2 (20ms)
                ├─> service-3 (50ms)  <- Longest
                ├─> service-4 (15ms)
                └─> service-5 (25ms)
        
        Known critical path: aggregator -> service-3
        Expected total latency: 5 + 50 = 55ms
        Expected bottleneck: service-3 (50ms)
        """
        graph = ServiceGraph()
        
        # Build wide fanout
        for i in range(1, 6):
            graph.add_edge("aggregator", f"service-{i}", DependencyEdge(
                target_service_id=f"service-{i}",
                dependency_type="synchronous",
                criticality="high"
            ))
        
        latencies = {
            "aggregator": 5.0,
            "service-1": 10.0,
            "service-2": 20.0,
            "service-3": 50.0,
            "service-4": 15.0,
            "service-5": 25.0
        }
        
        result = graph.compute_critical_path("aggregator", latencies)
        
        # Verify known critical path
        assert result['path'] == ["aggregator", "service-3"]
        assert result['total_latency_ms'] == 55.0
        assert result['bottleneck_service'] == "service-3"
    
    def test_critical_path_balanced_tree_scenario(self):
        """
        Test critical path with balanced tree structure.
        
        Known topology:
                    root (10ms)
                   /    \\
            left (20ms)  right (15ms)
             /    \\        /      \\
        ll(30ms) lr(25ms) rl(40ms) rr(35ms)
        
        Known critical path: root -> right -> rl
        Expected total latency: 10 + 15 + 40 = 65ms
        Expected bottleneck: rl (40ms)
        """
        graph = ServiceGraph()
        
        # Build balanced tree
        graph.add_edge("root", "left", DependencyEdge(
            target_service_id="left",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("root", "right", DependencyEdge(
            target_service_id="right",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("left", "ll", DependencyEdge(
            target_service_id="ll",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("left", "lr", DependencyEdge(
            target_service_id="lr",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("right", "rl", DependencyEdge(
            target_service_id="rl",
            dependency_type="synchronous",
            criticality="high"
        ))
        graph.add_edge("right", "rr", DependencyEdge(
            target_service_id="rr",
            dependency_type="synchronous",
            criticality="high"
        ))
        
        latencies = {
            "root": 10.0,
            "left": 20.0,
            "right": 15.0,
            "ll": 30.0,
            "lr": 25.0,
            "rl": 40.0,
            "rr": 35.0
        }
        
        result = graph.compute_critical_path("root", latencies)
        
        # Verify known critical path
        assert result['path'] == ["root", "right", "rl"]
        assert result['total_latency_ms'] == 65.0
        assert result['bottleneck_service'] == "rl"

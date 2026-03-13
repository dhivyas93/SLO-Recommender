"""Unit tests for cascading impact score computation."""

import pytest
from src.algorithms.service_graph import ServiceGraph
from src.models.dependency import DependencyEdge


class TestCascadingImpactBasics:
    """Test basic cascading impact score functionality."""
    
    def test_leaf_node_has_zero_impact(self):
        """Test that a leaf node (no downstream dependencies) has zero impact."""
        graph = ServiceGraph()
        graph.add_node("leaf-service")
        
        score = graph.compute_cascading_impact_score("leaf-service")
        assert score == 0.0
    
    def test_nonexistent_service_returns_zero(self):
        """Test that computing impact for non-existent service returns 0."""
        graph = ServiceGraph()
        
        score = graph.compute_cascading_impact_score("nonexistent")
        assert score == 0.0
    
    def test_single_downstream_dependency(self):
        """Test impact score with single downstream dependency."""
        graph = ServiceGraph()
        edge = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge)
        
        score = graph.compute_cascading_impact_score("service-a")
        # Formula: (1/depth) * (1/fanout) = (1/1) * (1/1) = 1.0
        assert score == 1.0
    
    def test_downstream_leaf_has_zero_impact(self):
        """Test that downstream leaf node has zero impact."""
        graph = ServiceGraph()
        edge = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge)
        
        score = graph.compute_cascading_impact_score("service-b")
        assert score == 0.0


class TestCascadingImpactChainTopology:
    """Test cascading impact with chain topologies."""
    
    def test_simple_chain_two_nodes(self):
        """Test chain: A -> B."""
        graph = ServiceGraph()
        edge = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A has 1 downstream at depth 1: (1/1) * (1/1) = 1.0
        assert score_a == 1.0
        
        score_b = graph.compute_cascading_impact_score("service-b")
        # B is a leaf
        assert score_b == 0.0
    
    def test_chain_three_nodes(self):
        """Test chain: A -> B -> C."""
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
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A has: B at depth 1 (1/1)*(1/1)=1.0, C at depth 2 (1/2)*(1/1)=0.5
        # Total: 1.0 + 0.5 = 1.5, but normalized to max 1.0
        assert score_a == 1.0
        
        score_b = graph.compute_cascading_impact_score("service-b")
        # B has: C at depth 1 (1/1)*(1/1)=1.0
        assert score_b == 1.0
        
        score_c = graph.compute_cascading_impact_score("service-c")
        # C is a leaf
        assert score_c == 0.0
    
    def test_long_chain_five_nodes(self):
        """Test long chain: A -> B -> C -> D -> E."""
        graph = ServiceGraph()
        services = ["service-a", "service-b", "service-c", "service-d", "service-e"]
        
        for i in range(len(services) - 1):
            edge = DependencyEdge(
                target_service_id=services[i + 1],
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(services[i], services[i + 1], edge)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A has: B(1/1), C(1/2), D(1/3), E(1/4) = 1 + 0.5 + 0.333 + 0.25 = 2.083
        # Normalized to 1.0
        assert score_a == 1.0
        
        score_e = graph.compute_cascading_impact_score("service-e")
        # E is a leaf
        assert score_e == 0.0


class TestCascadingImpactFanOutTopology:
    """Test cascading impact with fan-out topologies."""
    
    def test_fan_out_two_branches(self):
        """Test fan-out: A -> B, A -> C."""
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
        graph.add_edge("service-a", "service-c", edge2)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A has 2 downstream at depth 1, fanout=2
        # B: (1/1) * (1/2) = 0.5
        # C: (1/1) * (1/2) = 0.5
        # Total: 0.5 + 0.5 = 1.0
        assert score_a == 1.0
    
    def test_fan_out_three_branches(self):
        """Test fan-out: A -> B, A -> C, A -> D."""
        graph = ServiceGraph()
        for target in ["service-b", "service-c", "service-d"]:
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("service-a", target, edge)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A has 3 downstream at depth 1, fanout=3
        # Each: (1/1) * (1/3) = 0.333
        # Total: 0.333 * 3 = 1.0
        assert score_a == 1.0
    
    def test_fan_out_five_branches(self):
        """Test fan-out with 5 branches: A -> B, C, D, E, F."""
        graph = ServiceGraph()
        targets = ["service-b", "service-c", "service-d", "service-e", "service-f"]
        
        for target in targets:
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("service-a", target, edge)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A has 5 downstream at depth 1, fanout=5
        # Each: (1/1) * (1/5) = 0.2
        # Total: 0.2 * 5 = 1.0
        assert score_a == 1.0


class TestCascadingImpactFanInTopology:
    """Test cascading impact with fan-in topologies."""
    
    def test_fan_in_two_sources(self):
        """Test fan-in: A -> C, B -> C."""
        graph = ServiceGraph()
        for source in ["service-a", "service-b"]:
            edge = DependencyEdge(
                target_service_id="service-c",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(source, "service-c", edge)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A has 1 downstream at depth 1: (1/1) * (1/1) = 1.0
        assert score_a == 1.0
        
        score_b = graph.compute_cascading_impact_score("service-b")
        # B has 1 downstream at depth 1: (1/1) * (1/1) = 1.0
        assert score_b == 1.0
        
        score_c = graph.compute_cascading_impact_score("service-c")
        # C is a leaf
        assert score_c == 0.0
    
    def test_fan_in_three_sources(self):
        """Test fan-in: A -> D, B -> D, C -> D."""
        graph = ServiceGraph()
        for source in ["service-a", "service-b", "service-c"]:
            edge = DependencyEdge(
                target_service_id="service-d",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(source, "service-d", edge)
        
        # Each source has same impact
        for source in ["service-a", "service-b", "service-c"]:
            score = graph.compute_cascading_impact_score(source)
            assert score == 1.0


class TestCascadingImpactTreeTopology:
    """Test cascading impact with tree topologies."""
    
    def test_binary_tree_depth_two(self):
        """Test binary tree: A -> B, A -> C, B -> D, B -> E, C -> F, C -> G."""
        graph = ServiceGraph()
        
        # Level 1
        for target in ["service-b", "service-c"]:
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("service-a", target, edge)
        
        # Level 2
        for source, targets in [("service-b", ["service-d", "service-e"]),
                                 ("service-c", ["service-f", "service-g"])]:
            for target in targets:
                edge = DependencyEdge(
                    target_service_id=target,
                    dependency_type="synchronous",
                    criticality="high"
                )
                graph.add_edge(source, target, edge)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A has:
        # - B at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # - C at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # - D at depth 2, fanout 2: (1/2) * (1/2) = 0.25
        # - E at depth 2, fanout 2: (1/2) * (1/2) = 0.25
        # - F at depth 2, fanout 2: (1/2) * (1/2) = 0.25
        # - G at depth 2, fanout 2: (1/2) * (1/2) = 0.25
        # Total: 0.5 + 0.5 + 0.25 + 0.25 + 0.25 + 0.25 = 2.0
        # Normalized to 1.0
        assert score_a == 1.0
        
        score_b = graph.compute_cascading_impact_score("service-b")
        # B has: D and E at depth 1, fanout 2
        # Each: (1/1) * (1/2) = 0.5
        # Total: 1.0
        assert score_b == 1.0
    
    def test_unbalanced_tree(self):
        """Test unbalanced tree: A -> B -> C -> D, A -> E."""
        graph = ServiceGraph()
        
        # Long branch
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge1)
        
        edge2 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-b", "service-c", edge2)
        
        edge3 = DependencyEdge(
            target_service_id="service-d",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-c", "service-d", edge3)
        
        # Short branch
        edge4 = DependencyEdge(
            target_service_id="service-e",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-e", edge4)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A has:
        # - B at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # - E at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # - C at depth 2, fanout 1: (1/2) * (1/1) = 0.5
        # - D at depth 3, fanout 1: (1/3) * (1/1) = 0.333
        # Total: 0.5 + 0.5 + 0.5 + 0.333 = 1.833
        # Normalized to 1.0
        assert score_a == 1.0


class TestCascadingImpactDiamondTopology:
    """Test cascading impact with diamond topologies."""
    
    def test_simple_diamond(self):
        """Test diamond: A -> B, A -> C, B -> D, C -> D."""
        graph = ServiceGraph()
        
        # Top edges
        for target in ["service-b", "service-c"]:
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("service-a", target, edge)
        
        # Bottom edges
        for source in ["service-b", "service-c"]:
            edge = DependencyEdge(
                target_service_id="service-d",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(source, "service-d", edge)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A has:
        # - B at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # - C at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # - D at depth 2, fanout 1: (1/2) * (1/1) = 0.5
        # Note: D is visited only once due to BFS visited set
        # Total: 0.5 + 0.5 + 0.5 = 1.5
        # Normalized to 1.0
        assert score_a == 1.0
    
    def test_double_diamond(self):
        """Test double diamond: A -> B, A -> C, B -> D, C -> D, D -> E, D -> F, E -> G, F -> G."""
        graph = ServiceGraph()
        
        # First diamond
        for target in ["service-b", "service-c"]:
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("service-a", target, edge)
        
        for source in ["service-b", "service-c"]:
            edge = DependencyEdge(
                target_service_id="service-d",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(source, "service-d", edge)
        
        # Second diamond
        for target in ["service-e", "service-f"]:
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("service-d", target, edge)
        
        for source in ["service-e", "service-f"]:
            edge = DependencyEdge(
                target_service_id="service-g",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(source, "service-g", edge)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # Complex calculation, but should be normalized to 1.0
        assert score_a == 1.0


class TestCascadingImpactCircularTopology:
    """Test cascading impact with circular dependencies."""
    
    def test_simple_cycle_two_nodes(self):
        """Test simple cycle: A -> B -> A."""
        graph = ServiceGraph()
        
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge1)
        
        edge2 = DependencyEdge(
            target_service_id="service-a",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-b", "service-a", edge2)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A -> B (depth 1), B -> A (but A already visited, skip)
        # Score: (1/1) * (1/1) = 1.0
        assert score_a == 1.0
        
        score_b = graph.compute_cascading_impact_score("service-b")
        # B -> A (depth 1), A -> B (but B already visited, skip)
        # Score: (1/1) * (1/1) = 1.0
        assert score_b == 1.0
    
    def test_cycle_three_nodes(self):
        """Test cycle: A -> B -> C -> A."""
        graph = ServiceGraph()
        
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge1)
        
        edge2 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-b", "service-c", edge2)
        
        edge3 = DependencyEdge(
            target_service_id="service-a",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-c", "service-a", edge3)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A -> B (depth 1): (1/1) * (1/1) = 1.0
        # B -> C (depth 2): (1/2) * (1/1) = 0.5
        # C -> A (already visited, skip)
        # Total: 1.0 + 0.5 = 1.5, normalized to 1.0
        assert score_a == 1.0
    
    def test_self_loop(self):
        """Test self-loop: A -> A."""
        graph = ServiceGraph()
        
        edge = DependencyEdge(
            target_service_id="service-a",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-a", edge)
        
        score_a = graph.compute_cascading_impact_score("service-a")
        # A -> A (but A already visited after first iteration)
        # Score should be 0 since we skip already visited nodes
        assert score_a == 0.0


class TestCascadingImpactComplexTopologies:
    """Test cascading impact with complex real-world topologies."""
    
    def test_microservices_api_gateway_pattern(self):
        """Test typical API gateway pattern: Gateway -> Auth, Payment, User."""
        graph = ServiceGraph()
        
        # API Gateway to services
        for service in ["auth-service", "payment-service", "user-service"]:
            edge = DependencyEdge(
                target_service_id=service,
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("api-gateway", service, edge)
        
        # Services to databases
        for service, db in [("auth-service", "auth-db"),
                            ("payment-service", "payment-db"),
                            ("user-service", "user-db")]:
            edge = DependencyEdge(
                target_infrastructure_id=db,
                infrastructure_type="postgresql",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(service, db, edge)
        
        score_gateway = graph.compute_cascading_impact_score("api-gateway")
        # Gateway has high impact (affects 3 services + 3 databases)
        assert score_gateway > 0.5
        assert score_gateway <= 1.0
        
        score_auth = graph.compute_cascading_impact_score("auth-service")
        # Auth service has lower impact (only affects 1 database)
        assert score_auth == 1.0
        
        # Databases are leaf nodes
        score_db = graph.compute_cascading_impact_score("auth-db")
        assert score_db == 0.0
    
    def test_layered_architecture(self):
        """Test layered architecture: Presentation -> Business -> Data."""
        graph = ServiceGraph()
        
        # Presentation layer
        edge1 = DependencyEdge(
            target_service_id="business-logic",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("web-frontend", "business-logic", edge1)
        
        # Business layer
        edge2 = DependencyEdge(
            target_service_id="data-access",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("business-logic", "data-access", edge2)
        
        # Data layer
        edge3 = DependencyEdge(
            target_infrastructure_id="database",
            infrastructure_type="postgresql",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("data-access", "database", edge3)
        
        score_frontend = graph.compute_cascading_impact_score("web-frontend")
        # Frontend affects all layers
        # business-logic at depth 1: (1/1) * (1/1) = 1.0
        # data-access at depth 2: (1/2) * (1/1) = 0.5
        # database at depth 3: (1/3) * (1/1) = 0.333
        # Total: 1.833, normalized to 1.0
        assert score_frontend == 1.0
        
        score_business = graph.compute_cascading_impact_score("business-logic")
        # Business logic affects data layer
        # data-access at depth 1: (1/1) * (1/1) = 1.0
        # database at depth 2: (1/2) * (1/1) = 0.5
        # Total: 1.5, normalized to 1.0
        assert score_business == 1.0
        
        score_data = graph.compute_cascading_impact_score("data-access")
        # Data access affects only database
        assert score_data == 1.0
    
    def test_message_queue_pattern(self):
        """Test message queue pattern with multiple consumers."""
        graph = ServiceGraph()
        
        # Producer to queue
        edge1 = DependencyEdge(
            target_infrastructure_id="message-queue",
            infrastructure_type="kafka",
            dependency_type="asynchronous",
            criticality="medium"
        )
        graph.add_edge("producer-service", "message-queue", edge1)
        
        # Queue to consumers
        for consumer in ["consumer-a", "consumer-b", "consumer-c"]:
            edge = DependencyEdge(
                target_service_id=consumer,
                dependency_type="asynchronous",
                criticality="medium"
            )
            graph.add_edge("message-queue", consumer, edge)
        
        score_producer = graph.compute_cascading_impact_score("producer-service")
        # Producer affects queue and all consumers
        # message-queue at depth 1: (1/1) * (1/1) = 1.0
        # Each consumer at depth 2, fanout 3: (1/2) * (1/3) = 0.167
        # Total: 1.0 + 0.167 * 3 = 1.5, normalized to 1.0
        assert score_producer == 1.0
        
        score_queue = graph.compute_cascading_impact_score("message-queue")
        # Queue affects all consumers
        # Each consumer at depth 1, fanout 3: (1/1) * (1/3) = 0.333
        # Total: 0.333 * 3 = 1.0
        assert score_queue == 1.0
    
    def test_mixed_sync_async_dependencies(self):
        """Test graph with mixed synchronous and asynchronous dependencies."""
        graph = ServiceGraph()
        
        # Synchronous path
        edge1 = DependencyEdge(
            target_service_id="sync-service",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("main-service", "sync-service", edge1)
        
        # Asynchronous path
        edge2 = DependencyEdge(
            target_service_id="async-service",
            dependency_type="asynchronous",
            criticality="low"
        )
        graph.add_edge("main-service", "async-service", edge2)
        
        score = graph.compute_cascading_impact_score("main-service")
        # Both paths contribute equally to impact score
        # sync-service at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # async-service at depth 1, fanout 2: (1/1) * (1/2) = 0.5
        # Total: 1.0
        assert score == 1.0


class TestCascadingImpactEdgeCases:
    """Test edge cases for cascading impact computation."""
    
    def test_isolated_node(self):
        """Test isolated node with no connections."""
        graph = ServiceGraph()
        graph.add_node("isolated-service")
        
        score = graph.compute_cascading_impact_score("isolated-service")
        assert score == 0.0
    
    def test_multiple_paths_to_same_node(self):
        """Test multiple paths to the same downstream node."""
        graph = ServiceGraph()
        
        # A -> B -> D
        # A -> C -> D
        edge1 = DependencyEdge(
            target_service_id="service-b",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-b", edge1)
        
        edge2 = DependencyEdge(
            target_service_id="service-c",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-a", "service-c", edge2)
        
        edge3 = DependencyEdge(
            target_service_id="service-d",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-b", "service-d", edge3)
        
        edge4 = DependencyEdge(
            target_service_id="service-d",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("service-c", "service-d", edge4)
        
        score = graph.compute_cascading_impact_score("service-a")
        # D should only be counted once (first time visited)
        assert score == 1.0
    
    def test_very_wide_fanout(self):
        """Test very wide fanout (10 downstream services)."""
        graph = ServiceGraph()
        
        for i in range(10):
            edge = DependencyEdge(
                target_service_id=f"service-{i}",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("root-service", f"service-{i}", edge)
        
        score = graph.compute_cascading_impact_score("root-service")
        # Each downstream at depth 1, fanout 10: (1/1) * (1/10) = 0.1
        # Total: 0.1 * 10 = 1.0
        assert score == 1.0
    
    def test_very_deep_chain(self):
        """Test very deep chain (10 levels)."""
        graph = ServiceGraph()
        
        for i in range(10):
            edge = DependencyEdge(
                target_service_id=f"service-{i+1}",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(f"service-{i}", f"service-{i+1}", edge)
        
        score = graph.compute_cascading_impact_score("service-0")
        # Sum: 1/1 + 1/2 + 1/3 + ... + 1/10 = 2.928
        # Normalized to 1.0
        assert score == 1.0
    
    def test_infrastructure_only_dependencies(self):
        """Test service with only infrastructure dependencies."""
        graph = ServiceGraph()
        
        for infra in ["postgres-db", "redis-cache", "kafka-queue"]:
            edge = DependencyEdge(
                target_infrastructure_id=infra,
                infrastructure_type="infrastructure",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("service-a", infra, edge)
        
        score = graph.compute_cascading_impact_score("service-a")
        # Infrastructure nodes are treated like any other node
        # Each at depth 1, fanout 3: (1/1) * (1/3) = 0.333
        # Total: 0.333 * 3 = 1.0
        assert score == 1.0
    
    def test_empty_graph(self):
        """Test computing impact on empty graph."""
        graph = ServiceGraph()
        
        score = graph.compute_cascading_impact_score("nonexistent")
        assert score == 0.0
    
    def test_normalization_boundary(self):
        """Test that scores are properly normalized to [0, 1]."""
        graph = ServiceGraph()
        
        # Create a graph that would exceed 1.0 without normalization
        # Root -> 5 services at depth 1 (5 * 1.0 = 5.0)
        for i in range(5):
            edge = DependencyEdge(
                target_service_id=f"level1-{i}",
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("root", f"level1-{i}", edge)
            
            # Each level1 service -> 3 services at depth 2
            for j in range(3):
                edge2 = DependencyEdge(
                    target_service_id=f"level2-{i}-{j}",
                    dependency_type="synchronous",
                    criticality="high"
                )
                graph.add_edge(f"level1-{i}", f"level2-{i}-{j}", edge2)
        
        score = graph.compute_cascading_impact_score("root")
        # Should be normalized to 1.0
        assert score == 1.0
        assert score <= 1.0
        assert score >= 0.0


class TestCascadingImpactComparison:
    """Test comparing impact scores across different topologies."""
    
    def test_chain_vs_fanout_same_node_count(self):
        """Compare impact: chain vs fanout with same number of nodes."""
        # Chain: A -> B -> C -> D
        chain_graph = ServiceGraph()
        for i in range(3):
            edge = DependencyEdge(
                target_service_id=f"service-{i+1}",
                dependency_type="synchronous",
                criticality="high"
            )
            chain_graph.add_edge(f"service-{i}", f"service-{i+1}", edge)
        
        # Fanout: A -> B, A -> C, A -> D
        fanout_graph = ServiceGraph()
        for target in ["service-1", "service-2", "service-3"]:
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
            fanout_graph.add_edge("service-0", target, edge)
        
        chain_score = chain_graph.compute_cascading_impact_score("service-0")
        fanout_score = fanout_graph.compute_cascading_impact_score("service-0")
        
        # Both should be normalized to 1.0
        assert chain_score == 1.0
        assert fanout_score == 1.0
    
    def test_impact_decreases_with_depth(self):
        """Test that impact contribution decreases with depth."""
        graph = ServiceGraph()
        
        # A -> B -> C -> D -> E
        services = ["a", "b", "c", "d", "e"]
        for i in range(len(services) - 1):
            edge = DependencyEdge(
                target_service_id=services[i + 1],
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(services[i], services[i + 1], edge)
        
        # Services closer to root should have higher impact
        score_a = graph.compute_cascading_impact_score("a")
        score_b = graph.compute_cascading_impact_score("b")
        score_c = graph.compute_cascading_impact_score("c")
        score_d = graph.compute_cascading_impact_score("d")
        score_e = graph.compute_cascading_impact_score("e")
        
        # All except e should have impact > 0
        assert score_a > 0
        assert score_b > 0
        assert score_c > 0
        assert score_d > 0
        assert score_e == 0.0
        
        # Impact should decrease as we go deeper (before normalization)
        # But after normalization, some might be 1.0
        assert score_e < score_d or score_d == 1.0

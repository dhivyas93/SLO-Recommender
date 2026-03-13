"""Unit tests for cascading impact computation engine."""

import pytest
from src.algorithms.service_graph import ServiceGraph
from src.models.dependency import DependencyEdge
from src.engines.cascading_impact_computation import (
    CascadingImpactComputation,
    SLOChange,
    AffectedService,
    CriticalPathImpact,
    RiskAssessment,
    CascadingImpactResult
)


class TestCascadingImpactComputationBasics:
    """Test basic cascading impact computation functionality."""

    def test_single_change_direct_impact(self):
        """Test computing impact for a single service change with direct downstream."""
        # Build graph: A -> B -> C
        graph = ServiceGraph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_node("C")
        
        edge_ab = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        edge_bc = DependencyEdge(
            target_service_id="C",
            dependency_type="synchronous",
            criticality="high"
        )
        
        graph.add_edge("A", "B", edge_ab)
        graph.add_edge("B", "C", edge_bc)
        
        # Create computation engine
        engine = CascadingImpactComputation(graph)
        
        # Propose change to A
        changes = [SLOChange(
            service_id="A",
            new_availability=99.9,
            new_latency_p95_ms=100
        )]
        
        # Compute impact
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        # Verify result
        assert result.proposed_changes_count == 1
        assert result.analysis_depth == 3
        assert result.affected_services_count == 2  # B and C
        
        # Check affected services
        affected_ids = {s.service_id for s in result.affected_services}
        assert affected_ids == {"B", "C"}
        
        # Check impact depths
        b_service = next(s for s in result.affected_services if s.service_id == "B")
        c_service = next(s for s in result.affected_services if s.service_id == "C")
        
        assert b_service.impact_depth == 1
        assert c_service.impact_depth == 2
        
        # Check risk levels
        assert b_service.risk_level == "high"
        assert c_service.risk_level == "medium"

    def test_multiple_changes_combined_impact(self):
        """Test computing impact for multiple service changes."""
        # Build graph: A -> B -> C, D -> B
        graph = ServiceGraph()
        for node in ["A", "B", "C", "D"]:
            graph.add_node(node)
        
        edge = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("A", "B", edge)
        graph.add_edge("D", "B", edge)
        
        edge_bc = DependencyEdge(
            target_service_id="C",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("B", "C", edge_bc)
        
        # Create computation engine
        engine = CascadingImpactComputation(graph)
        
        # Propose changes to both A and D
        changes = [
            SLOChange(service_id="A", new_availability=99.9),
            SLOChange(service_id="D", new_availability=99.5)
        ]
        
        # Compute impact
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        # Verify result
        assert result.proposed_changes_count == 2
        assert result.affected_services_count == 2  # B and C
        
        # B should be directly affected by both changes
        b_service = next(s for s in result.affected_services if s.service_id == "B")
        assert b_service.impact_depth == 1

    def test_empty_proposed_changes_raises_error(self):
        """Test that empty proposed changes raises ValueError."""
        graph = ServiceGraph()
        graph.add_node("A")
        
        engine = CascadingImpactComputation(graph)
        
        with pytest.raises(ValueError, match="proposed_changes cannot be empty"):
            engine.compute_cascading_impact([], analysis_depth=3)

    def test_invalid_analysis_depth_raises_error(self):
        """Test that invalid analysis depth raises ValueError."""
        graph = ServiceGraph()
        graph.add_node("A")
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_availability=99.9)]
        
        with pytest.raises(ValueError, match="analysis_depth must be >= 1"):
            engine.compute_cascading_impact(changes, analysis_depth=0)

    def test_nonexistent_service_in_graph(self):
        """Test handling of service not in graph."""
        graph = ServiceGraph()
        graph.add_node("A")
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_availability=99.9)]
        
        # Should not raise error, just return no affected services
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        assert result.affected_services_count == 0


class TestCascadingImpactComputationRecommendedAdjustments:
    """Test recommended adjustments computation."""

    def test_availability_adjustment_single_level(self):
        """Test availability adjustment for direct downstream service."""
        graph = ServiceGraph()
        graph.add_node("A")
        graph.add_node("B")
        
        edge = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("A", "B", edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_availability=99.9)]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        b_service = next(s for s in result.affected_services if s.service_id == "B")
        assert "recommended_availability" in b_service.recommended_adjustments
        
        # Should be 0.5% less than upstream (99.9 - 0.5 = 99.4)
        recommended = b_service.recommended_adjustments["recommended_availability"]
        assert recommended == 99.4

    def test_latency_adjustment_increases_with_depth(self):
        """Test that latency adjustments increase with impact depth."""
        # Build chain: A -> B -> C -> D
        graph = ServiceGraph()
        for node in ["A", "B", "C", "D"]:
            graph.add_node(node)
        
        edge = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("A", "B", edge)
        
        edge = DependencyEdge(
            target_service_id="C",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("B", "C", edge)
        
        edge = DependencyEdge(
            target_service_id="D",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("C", "D", edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_latency_p95_ms=100)]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        # Get adjustments for B, C, D
        b_service = next(s for s in result.affected_services if s.service_id == "B")
        c_service = next(s for s in result.affected_services if s.service_id == "C")
        d_service = next(s for s in result.affected_services if s.service_id == "D")
        
        b_latency = b_service.recommended_adjustments.get("recommended_latency_p95_ms", 0)
        c_latency = c_service.recommended_adjustments.get("recommended_latency_p95_ms", 0)
        d_latency = d_service.recommended_adjustments.get("recommended_latency_p95_ms", 0)
        
        # Buffers should increase with depth: 50ms * depth
        assert b_latency == 150  # 100 + 50*1
        assert c_latency == 200  # 100 + 50*2
        assert d_latency == 250  # 100 + 50*3

    def test_error_rate_adjustment(self):
        """Test error rate adjustment for affected services."""
        graph = ServiceGraph()
        graph.add_node("A")
        graph.add_node("B")
        
        edge = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("A", "B", edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_error_rate_percent=0.5)]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        b_service = next(s for s in result.affected_services if s.service_id == "B")
        assert "recommended_error_rate_percent" in b_service.recommended_adjustments
        
        # Should be 1% higher than upstream (0.5 + 1.0 = 1.5)
        recommended = b_service.recommended_adjustments["recommended_error_rate_percent"]
        assert recommended == 1.5


class TestCascadingImpactComputationRiskAssessment:
    """Test risk assessment computation."""

    def test_risk_levels_by_depth(self):
        """Test that risk levels are correctly assigned by depth."""
        # Build chain: A -> B -> C -> D -> E
        graph = ServiceGraph()
        for node in ["A", "B", "C", "D", "E"]:
            graph.add_node(node)
        
        nodes = ["A", "B", "C", "D", "E"]
        for i in range(len(nodes) - 1):
            edge = DependencyEdge(
                target_service_id=nodes[i + 1],
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(nodes[i], nodes[i + 1], edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_availability=99.9)]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=5)
        
        # Check risk levels
        b_service = next(s for s in result.affected_services if s.service_id == "B")
        c_service = next(s for s in result.affected_services if s.service_id == "C")
        d_service = next(s for s in result.affected_services if s.service_id == "D")
        
        assert b_service.risk_level == "high"  # depth 1
        assert c_service.risk_level == "medium"  # depth 2
        assert d_service.risk_level == "low"  # depth 3+

    def test_overall_risk_assessment(self):
        """Test overall risk assessment computation."""
        # Build graph with multiple branches
        graph = ServiceGraph()
        for node in ["A", "B", "C", "D"]:
            graph.add_node(node)
        
        edge = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("A", "B", edge)
        
        edge = DependencyEdge(
            target_service_id="C",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("B", "C", edge)
        
        edge = DependencyEdge(
            target_service_id="D",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("C", "D", edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_availability=99.9)]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        # Check risk assessment
        assert result.risk_assessment.high_risk_count == 1  # B
        assert result.risk_assessment.medium_risk_count == 1  # C
        assert result.risk_assessment.low_risk_count == 1  # D
        assert result.risk_assessment.overall_risk == "high"  # Has high-risk services


class TestCascadingImpactComputationAnalysisDepth:
    """Test analysis depth limiting."""

    def test_analysis_depth_limits_traversal(self):
        """Test that analysis depth limits BFS traversal."""
        # Build long chain: A -> B -> C -> D -> E -> F
        graph = ServiceGraph()
        nodes = ["A", "B", "C", "D", "E", "F"]
        for node in nodes:
            graph.add_node(node)
        
        for i in range(len(nodes) - 1):
            edge = DependencyEdge(
                target_service_id=nodes[i + 1],
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge(nodes[i], nodes[i + 1], edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_availability=99.9)]
        
        # Test with depth 2
        result = engine.compute_cascading_impact(changes, analysis_depth=2)
        affected_ids = {s.service_id for s in result.affected_services}
        
        # Should only include B and C (depth 1 and 2)
        assert affected_ids == {"B", "C"}
        assert result.affected_services_count == 2

    def test_analysis_depth_one_direct_only(self):
        """Test that depth 1 only includes direct downstream."""
        graph = ServiceGraph()
        for node in ["A", "B", "C"]:
            graph.add_node(node)
        
        edge = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("A", "B", edge)
        
        edge = DependencyEdge(
            target_service_id="C",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("B", "C", edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_availability=99.9)]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=1)
        affected_ids = {s.service_id for s in result.affected_services}
        
        # Should only include B
        assert affected_ids == {"B"}
        assert result.affected_services_count == 1


class TestCascadingImpactComputationFanOut:
    """Test fan-out topology handling."""

    def test_fan_out_multiple_branches(self):
        """Test impact computation with fan-out topology."""
        # Build graph: A -> B, A -> C, A -> D
        graph = ServiceGraph()
        for node in ["A", "B", "C", "D"]:
            graph.add_node(node)
        
        for target in ["B", "C", "D"]:
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
            graph.add_edge("A", target, edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_availability=99.9)]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        # All three should be affected at depth 1
        affected_ids = {s.service_id for s in result.affected_services}
        assert affected_ids == {"B", "C", "D"}
        
        # All should have high risk (depth 1)
        for service in result.affected_services:
            assert service.risk_level == "high"
            assert service.impact_depth == 1


class TestCascadingImpactComputationDirectUpstream:
    """Test direct_upstream field tracking."""

    def test_direct_upstream_for_depth_one(self):
        """Test that direct_upstream is set for depth 1 services."""
        graph = ServiceGraph()
        graph.add_node("A")
        graph.add_node("B")
        
        edge = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("A", "B", edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_availability=99.9)]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        b_service = next(s for s in result.affected_services if s.service_id == "B")
        assert b_service.direct_upstream == "A"

    def test_direct_upstream_none_for_deeper_levels(self):
        """Test that direct_upstream is None for depth > 1 services."""
        graph = ServiceGraph()
        for node in ["A", "B", "C"]:
            graph.add_node(node)
        
        edge = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("A", "B", edge)
        
        edge = DependencyEdge(
            target_service_id="C",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("B", "C", edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_availability=99.9)]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        c_service = next(s for s in result.affected_services if s.service_id == "C")
        assert c_service.direct_upstream is None


class TestCascadingImpactComputationEdgeCases:
    """Test edge cases and special scenarios."""

    def test_isolated_service_no_impact(self):
        """Test that isolated services have no impact."""
        graph = ServiceGraph()
        graph.add_node("A")
        graph.add_node("B")  # Isolated
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(service_id="A", new_availability=99.9)]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        # B should not be affected
        affected_ids = {s.service_id for s in result.affected_services}
        assert "B" not in affected_ids

    def test_all_slo_metrics_in_single_change(self):
        """Test change with all SLO metrics specified."""
        graph = ServiceGraph()
        graph.add_node("A")
        graph.add_node("B")
        
        edge = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("A", "B", edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(
            service_id="A",
            new_availability=99.9,
            new_latency_p95_ms=100,
            new_latency_p99_ms=200,
            new_error_rate_percent=0.5
        )]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        b_service = next(s for s in result.affected_services if s.service_id == "B")
        adjustments = b_service.recommended_adjustments
        
        # All metrics should have recommendations
        assert "recommended_availability" in adjustments
        assert "recommended_latency_p95_ms" in adjustments
        assert "recommended_latency_p99_ms" in adjustments
        assert "recommended_error_rate_percent" in adjustments

    def test_partial_slo_metrics_in_change(self):
        """Test change with only some SLO metrics specified."""
        graph = ServiceGraph()
        graph.add_node("A")
        graph.add_node("B")
        
        edge = DependencyEdge(
            target_service_id="B",
            dependency_type="synchronous",
            criticality="high"
        )
        graph.add_edge("A", "B", edge)
        
        engine = CascadingImpactComputation(graph)
        changes = [SLOChange(
            service_id="A",
            new_availability=99.9
            # Only availability specified
        )]
        
        result = engine.compute_cascading_impact(changes, analysis_depth=3)
        
        b_service = next(s for s in result.affected_services if s.service_id == "B")
        adjustments = b_service.recommended_adjustments
        
        # Only availability should have recommendation
        assert "recommended_availability" in adjustments
        assert "recommended_latency_p95_ms" not in adjustments
        assert "recommended_latency_p99_ms" not in adjustments
        assert "recommended_error_rate_percent" not in adjustments

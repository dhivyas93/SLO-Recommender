"""
Unit tests for dependency constraint application in RecommendationEngine.
"""

import pytest
from datetime import datetime
from src.engines.recommendation_engine import RecommendationEngine
from src.storage.file_storage import FileStorage


@pytest.fixture
def storage(tmp_path):
    """Create a temporary FileStorage instance."""
    return FileStorage(base_path=str(tmp_path / "data"))


@pytest.fixture
def recommendation_engine(storage):
    """Create a RecommendationEngine instance."""
    return RecommendationEngine(storage=storage)


@pytest.fixture
def base_recommendations():
    """Sample base recommendations."""
    return {
        "availability": 99.5,
        "latency_p95_ms": 200.0,
        "latency_p99_ms": 400.0,
        "error_rate_percent": 1.0
    }


@pytest.fixture
def analyzed_graph_no_dependencies(storage):
    """Create an analyzed graph with a service that has no dependencies."""
    graph_data = {
        "version": "1.0.0",
        "analyzed_at": datetime.utcnow().isoformat(),
        "services": [
            {
                "service_id": "independent-service",
                "upstream_services": [],
                "downstream_services": [],
                "upstream_count": 0,
                "downstream_count": 0,
                "depth_from_root": 0,
                "fanout": 0,
                "cascading_impact_score": 0.0,
                "critical_paths": [],
                "is_in_circular_dependency": False
            }
        ],
        "graph_statistics": {
            "total_services": 1,
            "total_edges": 0,
            "max_depth": 0,
            "circular_dependency_count": 0
        }
    }
    storage.write_json("dependencies/analyzed_graph.json", graph_data)
    return graph_data


@pytest.fixture
def analyzed_graph_with_upstream(storage):
    """Create an analyzed graph with upstream dependencies."""
    graph_data = {
        "version": "1.0.0",
        "analyzed_at": datetime.utcnow().isoformat(),
        "services": [
            {
                "service_id": "downstream-service",
                "upstream_services": ["upstream-service-1", "upstream-service-2"],
                "downstream_services": [],
                "upstream_count": 2,
                "downstream_count": 0,
                "depth_from_root": 1,
                "fanout": 0,
                "cascading_impact_score": 0.3,
                "critical_paths": [],
                "is_in_circular_dependency": False
            }
        ],
        "graph_statistics": {
            "total_services": 3,
            "total_edges": 2,
            "max_depth": 1,
            "circular_dependency_count": 0
        }
    }
    storage.write_json("dependencies/analyzed_graph.json", graph_data)
    return graph_data


@pytest.fixture
def upstream_service_slo(storage):
    """Create SLO recommendations for upstream service."""
    upstream_rec = {
        "service_id": "upstream-service-1",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "recommendations": {
            "aggressive": {
                "availability": 99.9,
                "latency_p95_ms": 100.0,
                "latency_p99_ms": 200.0,
                "error_rate_percent": 0.5
            },
            "balanced": {
                "availability": 99.5,
                "latency_p95_ms": 150.0,
                "latency_p99_ms": 300.0,
                "error_rate_percent": 1.0
            },
            "conservative": {
                "availability": 99.0,
                "latency_p95_ms": 200.0,
                "latency_p99_ms": 400.0,
                "error_rate_percent": 2.0
            }
        }
    }
    storage.write_json("recommendations/upstream-service-1/latest.json", upstream_rec)
    return upstream_rec


@pytest.fixture
def analyzed_graph_with_critical_path(storage):
    """Create an analyzed graph with critical path."""
    graph_data = {
        "version": "1.0.0",
        "analyzed_at": datetime.utcnow().isoformat(),
        "services": [
            {
                "service_id": "service-in-path",
                "upstream_services": [],
                "downstream_services": ["downstream-1"],
                "upstream_count": 0,
                "downstream_count": 1,
                "depth_from_root": 0,
                "fanout": 1,
                "cascading_impact_score": 0.5,
                "critical_paths": [
                    {
                        "path": ["service-in-path", "downstream-1", "downstream-2"],
                        "total_latency_budget_ms": 450.0,
                        "bottleneck_service": "downstream-2"
                    }
                ],
                "is_in_circular_dependency": False
            }
        ],
        "graph_statistics": {
            "total_services": 3,
            "total_edges": 2,
            "max_depth": 2,
            "circular_dependency_count": 0
        }
    }
    storage.write_json("dependencies/analyzed_graph.json", graph_data)
    return graph_data


@pytest.fixture
def analyzed_graph_circular_dependency(storage):
    """Create an analyzed graph with circular dependency."""
    graph_data = {
        "version": "1.0.0",
        "analyzed_at": datetime.utcnow().isoformat(),
        "services": [
            {
                "service_id": "service-in-cycle",
                "upstream_services": ["service-b"],
                "downstream_services": ["service-b"],
                "upstream_count": 1,
                "downstream_count": 1,
                "depth_from_root": 0,
                "fanout": 1,
                "cascading_impact_score": 0.5,
                "critical_paths": [],
                "is_in_circular_dependency": True
            }
        ],
        "graph_statistics": {
            "total_services": 2,
            "total_edges": 2,
            "max_depth": 0,
            "circular_dependency_count": 1
        }
    }
    storage.write_json("dependencies/analyzed_graph.json", graph_data)
    return graph_data


class TestApplyDependencyConstraintsValidation:
    """Test input validation for apply_dependency_constraints."""
    
    def test_missing_required_keys(self, recommendation_engine):
        """Test error when base_recommendations is missing required keys."""
        incomplete_recs = {
            "availability": 99.5,
            "latency_p95_ms": 200.0
            # Missing latency_p99_ms and error_rate_percent
        }
        
        with pytest.raises(ValueError, match="missing required keys"):
            recommendation_engine.apply_dependency_constraints(
                service_id="test-service",
                base_recommendations=incomplete_recs
            )


class TestApplyDependencyConstraintsNoDependencies:
    """Test apply_dependency_constraints with no dependencies."""
    
    def test_no_dependency_graph(self, recommendation_engine, base_recommendations):
        """Test when no dependency graph exists."""
        result = recommendation_engine.apply_dependency_constraints(
            service_id="test-service",
            base_recommendations=base_recommendations
        )
        
        # Should return base recommendations unchanged
        assert result["constrained_recommendations"] == base_recommendations
        assert "No dependency graph available" in result["constraints_applied"][0]
        assert result["metadata"]["note"] == "No analyzed dependency graph found"
    
    def test_service_not_in_graph(
        self,
        recommendation_engine,
        base_recommendations,
        analyzed_graph_no_dependencies
    ):
        """Test when service is not found in dependency graph."""
        result = recommendation_engine.apply_dependency_constraints(
            service_id="nonexistent-service",
            base_recommendations=base_recommendations
        )
        
        # Should return base recommendations unchanged
        assert result["constrained_recommendations"] == base_recommendations
        assert "Service not found in dependency graph" in result["constraints_applied"][0]
    
    def test_independent_service(
        self,
        recommendation_engine,
        base_recommendations,
        analyzed_graph_no_dependencies
    ):
        """Test service with no upstream or downstream dependencies."""
        result = recommendation_engine.apply_dependency_constraints(
            service_id="independent-service",
            base_recommendations=base_recommendations
        )
        
        # Should return base recommendations unchanged
        assert result["constrained_recommendations"] == base_recommendations
        assert "No dependency constraints applied" in result["constraints_applied"][0]
        assert result["metadata"]["upstream_services_checked"] == []


class TestApplyDependencyConstraintsAvailability:
    """Test availability constraint application."""
    
    def test_availability_constrained_by_upstream(
        self,
        recommendation_engine,
        base_recommendations,
        analyzed_graph_with_upstream,
        upstream_service_slo
    ):
        """Test availability is constrained by upstream service SLO."""
        # Base recommendation: 99.5%
        # Upstream service: 99.5%
        # Expected constraint: 99.5% - 0.5% = 99.0%
        
        result = recommendation_engine.apply_dependency_constraints(
            service_id="downstream-service",
            base_recommendations=base_recommendations,
            availability_margin=0.5
        )
        
        constrained = result["constrained_recommendations"]
        
        # Availability should be constrained
        assert constrained["availability"] == 99.0
        assert constrained["availability"] < base_recommendations["availability"]
        
        # Other metrics should remain unchanged
        assert constrained["latency_p95_ms"] == base_recommendations["latency_p95_ms"]
        assert constrained["latency_p99_ms"] == base_recommendations["latency_p99_ms"]
        assert constrained["error_rate_percent"] == base_recommendations["error_rate_percent"]
        
        # Check constraints_applied
        assert len(result["constraints_applied"]) > 0
        assert "upstream-service-1" in result["constraints_applied"][0]
        assert "Availability constrained" in result["constraints_applied"][0]
        
        # Check metadata
        assert len(result["metadata"]["availability_constraints"]) > 0
        constraint = result["metadata"]["availability_constraints"][0]
        assert constraint["upstream_service"] == "upstream-service-1"
        assert constraint["upstream_availability"] == 99.5
        assert constraint["margin"] == 0.5
        assert constraint["original_value"] == 99.5
        assert constraint["constrained_value"] == 99.0
    
    def test_availability_not_constrained_when_below_upstream(
        self,
        recommendation_engine,
        analyzed_graph_with_upstream,
        upstream_service_slo
    ):
        """Test availability is not constrained when already below upstream."""
        # Base recommendation: 98.0% (already below upstream - 0.5%)
        # Upstream service: 99.5%
        # Expected: No constraint applied
        
        low_base_recs = {
            "availability": 98.0,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.apply_dependency_constraints(
            service_id="downstream-service",
            base_recommendations=low_base_recs,
            availability_margin=0.5
        )
        
        constrained = result["constrained_recommendations"]
        
        # Availability should remain unchanged
        assert constrained["availability"] == 98.0
    
    def test_upstream_service_no_slo(
        self,
        recommendation_engine,
        base_recommendations,
        analyzed_graph_with_upstream
    ):
        """Test when upstream service has no SLO defined."""
        # Don't create upstream SLO - it's missing
        
        result = recommendation_engine.apply_dependency_constraints(
            service_id="downstream-service",
            base_recommendations=base_recommendations
        )
        
        # Should note the missing upstream SLO
        assert any("has no SLO defined" in c for c in result["constraints_applied"])
        
        # Check metadata
        constraint = result["metadata"]["availability_constraints"][0]
        assert constraint["upstream_service"] == "upstream-service-1"
        assert constraint["upstream_availability"] is None
        assert "No SLO defined" in constraint["note"]
    
    def test_custom_availability_margin(
        self,
        recommendation_engine,
        base_recommendations,
        analyzed_graph_with_upstream,
        upstream_service_slo
    ):
        """Test custom availability margin."""
        # Custom margin: 1.0%
        result = recommendation_engine.apply_dependency_constraints(
            service_id="downstream-service",
            base_recommendations=base_recommendations,
            availability_margin=1.0
        )
        
        constrained = result["constrained_recommendations"]
        
        # Expected: 99.5% - 1.0% = 98.5%
        assert constrained["availability"] == 98.5
        
        # Check metadata
        constraint = result["metadata"]["availability_constraints"][0]
        assert constraint["margin"] == 1.0


class TestApplyDependencyConstraintsLatency:
    """Test latency constraint application."""
    
    def test_latency_constrained_by_critical_path(
        self,
        recommendation_engine,
        base_recommendations,
        analyzed_graph_with_critical_path
    ):
        """Test latency is constrained by critical path budget."""
        # Base recommendation: 200ms p95
        # Critical path: 450ms total, 3 services
        # Per-service budget: 450 / 3 = 150ms (with 10% margin: 135ms)
        
        result = recommendation_engine.apply_dependency_constraints(
            service_id="service-in-path",
            base_recommendations=base_recommendations,
            latency_margin_percent=0.1
        )
        
        constrained = result["constrained_recommendations"]
        
        # Latency should be constrained
        expected_budget = (450.0 / 3) * 0.9  # 135ms
        assert constrained["latency_p95_ms"] == pytest.approx(expected_budget, rel=0.01)
        assert constrained["latency_p95_ms"] < base_recommendations["latency_p95_ms"]
        
        # p99 should be adjusted to maintain ratio
        assert constrained["latency_p99_ms"] >= constrained["latency_p95_ms"]
        
        # Check constraints_applied
        assert any("critical path budget" in c for c in result["constraints_applied"])
        
        # Check metadata
        assert result["metadata"]["critical_path_analyzed"] is True
        assert len(result["metadata"]["latency_constraints"]) > 0
        constraint = result["metadata"]["latency_constraints"][0]
        assert constraint["constraint_type"] == "critical_path_budget"
        assert constraint["total_budget_ms"] == 450.0
        assert constraint["path_length"] == 3
        assert constraint["margin_percent"] == 0.1
    
    def test_latency_not_constrained_when_below_budget(
        self,
        recommendation_engine,
        analyzed_graph_with_critical_path
    ):
        """Test latency is not constrained when already below budget."""
        # Base recommendation: 100ms p95 (below budget)
        low_latency_recs = {
            "availability": 99.5,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.apply_dependency_constraints(
            service_id="service-in-path",
            base_recommendations=low_latency_recs
        )
        
        constrained = result["constrained_recommendations"]
        
        # Latency should remain unchanged
        assert constrained["latency_p95_ms"] == 100.0
        assert constrained["latency_p99_ms"] == 200.0
    
    def test_custom_latency_margin(
        self,
        recommendation_engine,
        base_recommendations,
        analyzed_graph_with_critical_path
    ):
        """Test custom latency margin."""
        # Custom margin: 20%
        result = recommendation_engine.apply_dependency_constraints(
            service_id="service-in-path",
            base_recommendations=base_recommendations,
            latency_margin_percent=0.2
        )
        
        constrained = result["constrained_recommendations"]
        
        # Expected: (450 / 3) * 0.8 = 120ms
        expected_budget = (450.0 / 3) * 0.8
        assert constrained["latency_p95_ms"] == pytest.approx(expected_budget, rel=0.01)
        
        # Check metadata
        constraint = result["metadata"]["latency_constraints"][0]
        assert constraint["margin_percent"] == 0.2


class TestApplyDependencyConstraintsCircularDependency:
    """Test handling of circular dependencies."""
    
    def test_circular_dependency_noted(
        self,
        recommendation_engine,
        base_recommendations,
        analyzed_graph_circular_dependency
    ):
        """Test that circular dependencies are noted in constraints."""
        result = recommendation_engine.apply_dependency_constraints(
            service_id="service-in-cycle",
            base_recommendations=base_recommendations
        )
        
        # Should note the circular dependency
        assert any("circular dependency" in c.lower() for c in result["constraints_applied"])
        assert result["metadata"]["circular_dependency_detected"] is True


class TestApplyDependencyConstraintsCombined:
    """Test combined availability and latency constraints."""
    
    def test_both_constraints_applied(
        self,
        recommendation_engine,
        base_recommendations,
        storage
    ):
        """Test when both availability and latency constraints are applied."""
        # Create a graph with both upstream service and critical path
        graph_data = {
            "version": "1.0.0",
            "analyzed_at": datetime.utcnow().isoformat(),
            "services": [
                {
                    "service_id": "complex-service",
                    "upstream_services": ["upstream-service-1"],
                    "downstream_services": ["downstream-1"],
                    "upstream_count": 1,
                    "downstream_count": 1,
                    "depth_from_root": 1,
                    "fanout": 1,
                    "cascading_impact_score": 0.6,
                    "critical_paths": [
                        {
                            "path": ["upstream-service-1", "complex-service", "downstream-1"],
                            "total_latency_budget_ms": 300.0,
                            "bottleneck_service": "downstream-1"
                        }
                    ],
                    "is_in_circular_dependency": False
                }
            ],
            "graph_statistics": {
                "total_services": 3,
                "total_edges": 2,
                "max_depth": 2,
                "circular_dependency_count": 0
            }
        }
        storage.write_json("dependencies/analyzed_graph.json", graph_data)
        
        # Create upstream SLO
        upstream_rec = {
            "service_id": "upstream-service-1",
            "recommendations": {
                "balanced": {
                    "availability": 99.5,
                    "latency_p95_ms": 150.0,
                    "latency_p99_ms": 300.0,
                    "error_rate_percent": 1.0
                }
            }
        }
        storage.write_json("recommendations/upstream-service-1/latest.json", upstream_rec)
        
        result = recommendation_engine.apply_dependency_constraints(
            service_id="complex-service",
            base_recommendations=base_recommendations
        )
        
        constrained = result["constrained_recommendations"]
        
        # Both constraints should be applied
        assert constrained["availability"] < base_recommendations["availability"]
        assert constrained["latency_p95_ms"] < base_recommendations["latency_p95_ms"]
        
        # Should have multiple constraints in the list
        assert len(result["constraints_applied"]) >= 2
        assert any("Availability constrained" in c for c in result["constraints_applied"])
        assert any("Latency p95 constrained" in c for c in result["constraints_applied"])



class TestApplyDependencyConstraintsEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_multiple_upstream_services_most_restrictive_wins(
        self,
        recommendation_engine,
        base_recommendations,
        storage
    ):
        """Test that the most restrictive upstream constraint is applied."""
        # Create graph with multiple upstream services
        graph_data = {
            "version": "1.0.0",
            "analyzed_at": datetime.utcnow().isoformat(),
            "services": [
                {
                    "service_id": "multi-upstream-service",
                    "upstream_services": ["upstream-high", "upstream-low"],
                    "downstream_services": [],
                    "upstream_count": 2,
                    "downstream_count": 0,
                    "depth_from_root": 1,
                    "fanout": 0,
                    "cascading_impact_score": 0.4,
                    "critical_paths": [],
                    "is_in_circular_dependency": False
                }
            ],
            "graph_statistics": {
                "total_services": 3,
                "total_edges": 2,
                "max_depth": 1,
                "circular_dependency_count": 0
            }
        }
        storage.write_json("dependencies/analyzed_graph.json", graph_data)
        
        # Create upstream SLOs with different availability
        upstream_high = {
            "recommendations": {
                "balanced": {"availability": 99.9}
            }
        }
        upstream_low = {
            "recommendations": {
                "balanced": {"availability": 98.5}
            }
        }
        storage.write_json("recommendations/upstream-high/latest.json", upstream_high)
        storage.write_json("recommendations/upstream-low/latest.json", upstream_low)
        
        result = recommendation_engine.apply_dependency_constraints(
            service_id="multi-upstream-service",
            base_recommendations=base_recommendations,
            availability_margin=0.5
        )
        
        constrained = result["constrained_recommendations"]
        
        # Should be constrained by the lower upstream (98.5% - 0.5% = 98.0%)
        assert constrained["availability"] == 98.0
        
        # Should have constraints from both upstream services
        assert len(result["metadata"]["availability_constraints"]) == 2
    
    def test_zero_margin(
        self,
        recommendation_engine,
        base_recommendations,
        analyzed_graph_with_upstream,
        upstream_service_slo
    ):
        """Test with zero availability margin."""
        result = recommendation_engine.apply_dependency_constraints(
            service_id="downstream-service",
            base_recommendations=base_recommendations,
            availability_margin=0.0
        )
        
        constrained = result["constrained_recommendations"]
        
        # With zero margin, should equal upstream availability
        assert constrained["availability"] == 99.5
    
    def test_very_high_latency_margin(
        self,
        recommendation_engine,
        base_recommendations,
        analyzed_graph_with_critical_path
    ):
        """Test with very high latency margin (50%)."""
        result = recommendation_engine.apply_dependency_constraints(
            service_id="service-in-path",
            base_recommendations=base_recommendations,
            latency_margin_percent=0.5
        )
        
        constrained = result["constrained_recommendations"]
        
        # Expected: (450 / 3) * 0.5 = 75ms
        expected_budget = (450.0 / 3) * 0.5
        assert constrained["latency_p95_ms"] == pytest.approx(expected_budget, rel=0.01)
    
    def test_empty_critical_path(
        self,
        recommendation_engine,
        base_recommendations,
        storage
    ):
        """Test when critical_paths list is empty."""
        graph_data = {
            "version": "1.0.0",
            "analyzed_at": datetime.utcnow().isoformat(),
            "services": [
                {
                    "service_id": "no-path-service",
                    "upstream_services": [],
                    "downstream_services": [],
                    "upstream_count": 0,
                    "downstream_count": 0,
                    "depth_from_root": 0,
                    "fanout": 0,
                    "cascading_impact_score": 0.0,
                    "critical_paths": [],
                    "is_in_circular_dependency": False
                }
            ],
            "graph_statistics": {
                "total_services": 1,
                "total_edges": 0,
                "max_depth": 0,
                "circular_dependency_count": 0
            }
        }
        storage.write_json("dependencies/analyzed_graph.json", graph_data)
        
        result = recommendation_engine.apply_dependency_constraints(
            service_id="no-path-service",
            base_recommendations=base_recommendations
        )
        
        # Should not apply latency constraints
        assert result["constrained_recommendations"]["latency_p95_ms"] == base_recommendations["latency_p95_ms"]
        assert result["metadata"]["critical_path_analyzed"] is False
    
    def test_critical_path_with_missing_budget(
        self,
        recommendation_engine,
        base_recommendations,
        storage
    ):
        """Test when critical path exists but budget is None."""
        graph_data = {
            "version": "1.0.0",
            "analyzed_at": datetime.utcnow().isoformat(),
            "services": [
                {
                    "service_id": "no-budget-service",
                    "upstream_services": [],
                    "downstream_services": [],
                    "upstream_count": 0,
                    "downstream_count": 0,
                    "depth_from_root": 0,
                    "fanout": 0,
                    "cascading_impact_score": 0.0,
                    "critical_paths": [
                        {
                            "path": ["service-a", "service-b"],
                            "total_latency_budget_ms": None,  # Missing budget
                            "bottleneck_service": "service-b"
                        }
                    ],
                    "is_in_circular_dependency": False
                }
            ],
            "graph_statistics": {
                "total_services": 2,
                "total_edges": 1,
                "max_depth": 1,
                "circular_dependency_count": 0
            }
        }
        storage.write_json("dependencies/analyzed_graph.json", graph_data)
        
        result = recommendation_engine.apply_dependency_constraints(
            service_id="no-budget-service",
            base_recommendations=base_recommendations
        )
        
        # Should not apply latency constraints when budget is None
        assert result["constrained_recommendations"]["latency_p95_ms"] == base_recommendations["latency_p95_ms"]
    
    def test_p99_adjustment_when_p95_constrained(
        self,
        recommendation_engine,
        base_recommendations,
        analyzed_graph_with_critical_path
    ):
        """Test that p99 is adjusted when p95 is constrained and p99 becomes < p95."""
        # Set p99 lower than what p95 will be constrained to
        tight_recs = {
            "availability": 99.5,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 120.0,  # Lower than constrained p95 (~135ms)
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.apply_dependency_constraints(
            service_id="service-in-path",
            base_recommendations=tight_recs,
            latency_margin_percent=0.1
        )
        
        constrained = result["constrained_recommendations"]
        
        # p95 should be constrained to ~135ms
        expected_p95 = (450.0 / 3) * 0.9
        assert constrained["latency_p95_ms"] == pytest.approx(expected_p95, rel=0.01)
        
        # p99 should be adjusted to maintain 1.5x ratio since it was < p95
        expected_p99 = expected_p95 * 1.5
        assert constrained["latency_p99_ms"] == pytest.approx(expected_p99, rel=0.01)
        assert constrained["latency_p99_ms"] > constrained["latency_p95_ms"]
    
    def test_recommendations_already_meet_all_constraints(
        self,
        recommendation_engine,
        analyzed_graph_with_upstream,
        upstream_service_slo,
        storage
    ):
        """Test when base recommendations already meet all constraints."""
        # Create very conservative base recommendations
        conservative_recs = {
            "availability": 95.0,  # Well below upstream
            "latency_p95_ms": 50.0,  # Well below any budget
            "latency_p99_ms": 100.0,
            "error_rate_percent": 5.0
        }
        
        result = recommendation_engine.apply_dependency_constraints(
            service_id="downstream-service",
            base_recommendations=conservative_recs
        )
        
        # Should return unchanged recommendations
        assert result["constrained_recommendations"] == conservative_recs

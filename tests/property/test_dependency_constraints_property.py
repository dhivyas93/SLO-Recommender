"""
Property-based tests for dependency constraint application in RecommendationEngine.

This module uses property-based testing to verify that dependency constraints
are correctly applied to SLO recommendations across various dependency graphs
and recommendation scenarios.

**Validates: Requirements 4.4** (dependency constraints)
**Validates: Property 14** (conservative recommendations for unknown dependencies)
**Validates: Property 27** (dependency chain consistency)
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize

from src.engines.recommendation_engine import RecommendationEngine
from src.storage.file_storage import FileStorage


# ============================================================================
# Strategy Definitions
# ============================================================================

# Generate valid service IDs
service_id_strategy = st.text(
    min_size=3,
    max_size=30,
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
)

# Generate valid SLO values
availability_strategy = st.floats(min_value=90.0, max_value=99.999, allow_nan=False, allow_infinity=False)
latency_strategy = st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
error_rate_strategy = st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)

# Generate base recommendations
base_recommendations_strategy = st.fixed_dictionaries({
    "availability": availability_strategy,
    "latency_p95_ms": latency_strategy,
    "latency_p99_ms": latency_strategy,
    "error_rate_percent": error_rate_strategy
}).filter(lambda x: x["latency_p99_ms"] >= x["latency_p95_ms"])


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_storage():
    """Create a temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp()
    return FileStorage(base_path=temp_dir), temp_dir

def cleanup_test_storage(temp_dir):
    """Clean up temporary storage directory."""
    shutil.rmtree(temp_dir, ignore_errors=True)

def write_analyzed_graph(storage: FileStorage, services: List[Dict[str, Any]]):
    """Write analyzed graph to storage."""
    graph_data = {
        "version": "1.0.0",
        "analyzed_at": datetime.utcnow().isoformat(),
        "services": services,
        "graph_statistics": {
            "total_services": len(services),
            "total_edges": sum(len(s.get("upstream_services", [])) for s in services),
            "max_depth": max(s.get("depth_from_root", 0) for s in services),
            "circular_dependency_count": sum(1 for s in services if s.get("is_in_circular_dependency", False))
        }
    }
    storage.write_json("dependencies/analyzed_graph.json", graph_data)
    return graph_data

def write_upstream_slo(storage: FileStorage, service_id: str, availability: float):
    """Write upstream SLO recommendation to storage."""
    upstream_rec = {
        "service_id": service_id,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "recommendations": {
            "balanced": {
                "availability": availability,
                "latency_p95_ms": 150.0,
                "latency_p99_ms": 300.0,
                "error_rate_percent": 1.0
            }
        }
    }
    storage.write_json(f"recommendations/{service_id}/latest.json", upstream_rec)
    return upstream_rec


# ============================================================================
# Property Tests for Dependency Constraints
# ============================================================================

class TestDependencyConstraintProperties:
    """Property-based tests for dependency constraint application."""
    
    @given(
        service_id=service_id_strategy,
        base_recs=base_recommendations_strategy,
        upstream_services=st.lists(service_id_strategy, min_size=1, max_size=3),
        upstream_availability=availability_strategy,
        availability_margin=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20, deadline=5000, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_availability_constrained_by_upstream(
        self,
        service_id,
        base_recs,
        upstream_services,
        upstream_availability,
        availability_margin
    ):
        """
        Property 27: Dependency Chain Consistency
        
        *For any* service with upstream dependencies, if the service's base
        availability recommendation exceeds the upstream availability minus margin,
        it should be constrained to that value.
        
        Validates: Requirements 4.4, Property 27
        """
        # Create temporary storage
        temp_dir = tempfile.mkdtemp()
        try:
            storage = FileStorage(base_path=temp_dir)
            
            # Create analyzed graph with upstream dependencies
            service_analysis = {
                "service_id": service_id,
                "upstream_services": upstream_services,
                "downstream_services": [],
                "upstream_count": len(upstream_services),
                "downstream_count": 0,
                "depth_from_root": 1,
                "fanout": 0,
                "cascading_impact_score": 0.3,
                "critical_paths": [],
                "is_in_circular_dependency": False
            }
            write_analyzed_graph(storage, [service_analysis])
            
            # Write SLO for the first upstream service
            if upstream_services:
                write_upstream_slo(storage, upstream_services[0], upstream_availability)
            
            # Create recommendation engine
            engine = RecommendationEngine(storage=storage)
            
            # Apply dependency constraints
            result = engine.apply_dependency_constraints(
                service_id=service_id,
                base_recommendations=base_recs,
                availability_margin=availability_margin
            )
            
            constrained = result["constrained_recommendations"]
            
            # Property 1: If base availability > upstream - margin, it should be constrained
            if upstream_services and base_recs["availability"] > upstream_availability - availability_margin:
                expected_availability = upstream_availability - availability_margin
                assert constrained["availability"] == pytest.approx(expected_availability, rel=0.01), \
                    f"Availability should be constrained to upstream - margin: {expected_availability}"
                
                # Should have constraint applied
                assert len(result["constraints_applied"]) > 0
                assert any("Availability constrained" in c for c in result["constraints_applied"])
                
                # Metadata should contain constraint details
                assert len(result["metadata"]["availability_constraints"]) > 0
                constraint = result["metadata"]["availability_constraints"][0]
                assert constraint["upstream_service"] == upstream_services[0]
                assert constraint["upstream_availability"] == upstream_availability
                assert constraint["margin"] == availability_margin
            else:
                # If base availability already meets constraint, it should remain unchanged
                assert constrained["availability"] == pytest.approx(base_recs["availability"], rel=0.01)
            
            # Property 2: Other metrics should remain unchanged (unless also constrained)
            assert constrained["latency_p95_ms"] == pytest.approx(base_recs["latency_p95_ms"], rel=0.01)
            assert constrained["latency_p99_ms"] == pytest.approx(base_recs["latency_p99_ms"], rel=0.01)
            assert constrained["error_rate_percent"] == pytest.approx(base_recs["error_rate_percent"], rel=0.01)
            
            # Property 3: p99 should always be >= p95
            assert constrained["latency_p99_ms"] >= constrained["latency_p95_ms"]
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        service_id=service_id_strategy,
        base_recs=base_recommendations_strategy,
        upstream_services=st.lists(service_id_strategy, min_size=1, max_size=3)
    )
    @settings(max_examples=20, deadline=5000, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_unknown_dependencies_get_conservative_handling(
        self,
        service_id,
        base_recs,
        upstream_services
    ):
        """
        Property 14: Conservative Recommendations for Unknown Dependencies
        
        *For any* service with dependencies that have unknown SLOs, the system
        should handle them conservatively and note the uncertainty.
        
        Validates: Requirements 12.2, Property 14
        """
        # Create temporary storage
        temp_dir = tempfile.mkdtemp()
        try:
            storage = FileStorage(base_path=temp_dir)
            
            # Create analyzed graph with upstream dependencies
            service_analysis = {
                "service_id": service_id,
                "upstream_services": upstream_services,
                "downstream_services": [],
                "upstream_count": len(upstream_services),
                "downstream_count": 0,
                "depth_from_root": 1,
                "fanout": 0,
                "cascading_impact_score": 0.3,
                "critical_paths": [],
                "is_in_circular_dependency": False
            }
            write_analyzed_graph(storage, [service_analysis])
            
            # DO NOT write upstream SLOs - they should be unknown
            
            # Create recommendation engine
            engine = RecommendationEngine(storage=storage)
            
            # Apply dependency constraints
            result = engine.apply_dependency_constraints(
                service_id=service_id,
                base_recommendations=base_recs
            )
            
            # Property 1: Should note missing upstream SLOs
            assert len(result["constraints_applied"]) > 0
            assert any("has no SLO defined" in c for c in result["constraints_applied"])
            
            # Property 2: Metadata should contain information about unknown dependencies
            assert len(result["metadata"]["availability_constraints"]) == len(upstream_services)
            for constraint in result["metadata"]["availability_constraints"]:
                assert constraint["upstream_availability"] is None
                assert "No SLO defined" in constraint.get("note", "")
            
            # Property 3: Recommendations should remain unchanged (conservative handling)
            constrained = result["constrained_recommendations"]
            assert constrained["availability"] == pytest.approx(base_recs["availability"], rel=0.01)
            assert constrained["latency_p95_ms"] == pytest.approx(base_recs["latency_p95_ms"], rel=0.01)
            assert constrained["latency_p99_ms"] == pytest.approx(base_recs["latency_p99_ms"], rel=0.01)
            assert constrained["error_rate_percent"] == pytest.approx(base_recs["error_rate_percent"], rel=0.01)
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        service_id=service_id_strategy,
        base_recs=base_recommendations_strategy,
        critical_path_budget=st.floats(min_value=100.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
        path_length=st.integers(min_value=2, max_value=5),
        latency_margin_percent=st.floats(min_value=0.0, max_value=0.5, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20, deadline=5000, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_latency_constrained_by_critical_path(
        self,
        service_id,
        base_recs,
        critical_path_budget,
        path_length,
        latency_margin_percent
    ):
        """
        Property: Latency Constraint by Critical Path
        
        *For any* service in a critical path, if its base latency recommendation
        exceeds the per-service budget (with margin), it should be constrained.
        
        Validates: Requirements 4.4
        """
        # Create temporary storage
        temp_dir = tempfile.mkdtemp()
        try:
            storage = FileStorage(base_path=temp_dir)
            
            # Create a critical path that includes the service
            path = [f"service-{i}" for i in range(path_length)]
            # Ensure our service is in the path (e.g., at position 1)
            if path_length > 1:
                path[1] = service_id
            
            # Create analyzed graph with critical path
            service_analysis = {
                "service_id": service_id,
                "upstream_services": [],
                "downstream_services": [],
                "upstream_count": 0,
                "downstream_count": 0,
                "depth_from_root": 0,
                "fanout": 0,
                "cascading_impact_score": 0.0,
                "critical_paths": [
                    {
                        "path": path,
                        "total_latency_budget_ms": critical_path_budget,
                        "bottleneck_service": path[-1]
                    }
                ],
                "is_in_circular_dependency": False
            }
            write_analyzed_graph(storage, [service_analysis])
            
            # Create recommendation engine
            engine = RecommendationEngine(storage=storage)
            
            # Apply dependency constraints
            result = engine.apply_dependency_constraints(
                service_id=service_id,
                base_recommendations=base_recs,
                latency_margin_percent=latency_margin_percent
            )
            
            constrained = result["constrained_recommendations"]
            per_service_budget = (critical_path_budget / path_length) * (1 - latency_margin_percent)
            
            # Property 1: If base latency > per-service budget, it should be constrained
            if base_recs["latency_p95_ms"] > per_service_budget:
                assert constrained["latency_p95_ms"] == pytest.approx(per_service_budget, rel=0.01), \
                    f"Latency should be constrained to per-service budget: {per_service_budget}"
                
                # Should have constraint applied
                assert len(result["constraints_applied"]) > 0
                assert any("critical path budget" in c for c in result["constraints_applied"])
                
                # Metadata should contain constraint details
                assert len(result["metadata"]["latency_constraints"]) > 0
                constraint = result["metadata"]["latency_constraints"][0]
                assert constraint["constraint_type"] == "critical_path_budget"
                assert constraint["total_budget_ms"] == critical_path_budget
                assert constraint["path_length"] == path_length
                assert constraint["margin_percent"] == latency_margin_percent
            else:
                # If base latency already meets constraint, it should remain unchanged
                assert constrained["latency_p95_ms"] == pytest.approx(base_recs["latency_p95_ms"], rel=0.01)
            
            # Property 2: p99 should always be >= p95
            assert constrained["latency_p99_ms"] >= constrained["latency_p95_ms"]
            
            # Property 3: If p99 < p95 after constraint, it should be adjusted
            if base_recs["latency_p99_ms"] < constrained["latency_p95_ms"]:
                assert constrained["latency_p99_ms"] > constrained["latency_p95_ms"]
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        service_id=service_id_strategy,
        base_recs=base_recommendations_strategy
    )
    @settings(max_examples=10, deadline=5000, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_no_dependencies_no_constraints(
        self,
        service_id,
        base_recs
    ):
        """
        Property: No Dependencies - No Constraints
        
        *For any* service with no dependencies, recommendations should remain
        unchanged and no constraints should be applied.
        
        Validates: Requirements 12.1
        """
        # Create temporary storage
        temp_dir = tempfile.mkdtemp()
        try:
            storage = FileStorage(base_path=temp_dir)
            
            # Create analyzed graph with no dependencies
            service_analysis = {
                "service_id": service_id,
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
            write_analyzed_graph(storage, [service_analysis])
            
            # Create recommendation engine
            engine = RecommendationEngine(storage=storage)
            
            # Apply dependency constraints
            result = engine.apply_dependency_constraints(
                service_id=service_id,
                base_recommendations=base_recs
            )
            
            constrained = result["constrained_recommendations"]
            
            # Property 1: Recommendations should remain unchanged
            assert constrained["availability"] == pytest.approx(base_recs["availability"], rel=0.01)
            assert constrained["latency_p95_ms"] == pytest.approx(base_recs["latency_p95_ms"], rel=0.01)
            assert constrained["latency_p99_ms"] == pytest.approx(base_recs["latency_p99_ms"], rel=0.01)
            assert constrained["error_rate_percent"] == pytest.approx(base_recs["error_rate_percent"], rel=0.01)
            
            # Property 2: Should note no constraints applied
            assert any("No dependency constraints applied" in c for c in result["constraints_applied"])
            
            # Property 3: Metadata should show no upstream services checked
            assert result["metadata"]["upstream_services_checked"] == []
            assert result["metadata"]["critical_path_analyzed"] is False
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# Summary
# ============================================================================

"""
Property-Based Test Coverage Summary:

1. test_availability_constrained_by_upstream (Property 27):
   - Verifies dependency chain consistency: A.availability <= B.availability - margin
   - Tests with randomly generated upstream services and availability values
   - Validates constraint metadata and error handling

2. test_unknown_dependencies_get_conservative_handling (Property 14):
   - Verifies conservative handling of services with unknown upstream SLOs
   - Ensures uncertainty is noted in constraints and metadata
   - Tests with varying numbers of unknown dependencies

3. test_latency_constrained_by_critical_path:
   - Verifies latency constraints based on critical path budgets
   - Tests with randomly generated budgets, path lengths, and margins
   - Ensures p99 is adjusted when p95 is constrained

4. test_no_dependencies_no_constraints:
   - Verifies independent services have no constraints applied
   - Tests edge case of services with no dependencies
   - Ensures metadata correctly reflects no constraints

These properties complement the unit tests by:
- Testing with randomly generated dependency graphs and SLO values
- Verifying mathematical properties hold across all inputs
- Testing edge cases that are hard to cover with example-based tests
- Providing broader coverage of the dependency constraint logic
- Validating both Property 14 and Property 27 from the design document
"""

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
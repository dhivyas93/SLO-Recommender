"""
Unit tests for the Fault Tolerance Engine.

Tests component failure detection and graceful degradation.
"""

import pytest
from datetime import datetime
from src.engines.fault_tolerance import (
    FaultToleranceEngine,
    ComponentStatus,
    ComponentHealth
)


@pytest.fixture
def fault_tolerance_engine():
    """Create a FaultToleranceEngine instance."""
    return FaultToleranceEngine()


class TestComponentHealthTracking:
    """Test component health tracking."""
    
    def test_initial_component_status(self, fault_tolerance_engine):
        """Test that all components start as healthy."""
        health = fault_tolerance_engine.get_component_status("knowledge_layer")
        
        assert health is not None
        assert health.status == ComponentStatus.HEALTHY
        assert health.error_message is None
        assert health.recovery_attempts == 0
    
    def test_all_components_initialized(self, fault_tolerance_engine):
        """Test that all expected components are initialized."""
        expected_components = [
            "knowledge_layer",
            "dependency_analyzer",
            "metrics_ingestion",
            "llm_service",
            "file_storage"
        ]
        
        for component in expected_components:
            health = fault_tolerance_engine.get_component_status(component)
            assert health is not None
            assert health.component_name == component


class TestComponentErrorReporting:
    """Test reporting component errors."""
    
    def test_report_transient_error(self, fault_tolerance_engine):
        """Test reporting a transient error."""
        error = Exception("Connection timeout")
        fault_tolerance_engine.report_component_error(
            "knowledge_layer",
            error,
            is_transient=True
        )
        
        health = fault_tolerance_engine.get_component_status("knowledge_layer")
        
        assert health.status == ComponentStatus.DEGRADED
        assert health.error_message == "Connection timeout"
        assert health.recovery_attempts == 1
        assert health.last_error_time is not None
    
    def test_report_permanent_error(self, fault_tolerance_engine):
        """Test reporting a permanent error."""
        error = Exception("Configuration error")
        fault_tolerance_engine.report_component_error(
            "file_storage",
            error,
            is_transient=False
        )
        
        health = fault_tolerance_engine.get_component_status("file_storage")
        
        assert health.status == ComponentStatus.UNAVAILABLE
        assert health.error_message == "Configuration error"
    
    def test_multiple_error_reports(self, fault_tolerance_engine):
        """Test reporting multiple errors for the same component."""
        for i in range(3):
            error = Exception(f"Error {i}")
            fault_tolerance_engine.report_component_error(
                "llm_service",
                error,
                is_transient=True
            )
        
        health = fault_tolerance_engine.get_component_status("llm_service")
        
        assert health.recovery_attempts == 3
        assert health.status == ComponentStatus.DEGRADED


class TestComponentRecovery:
    """Test component recovery."""
    
    def test_report_recovery(self, fault_tolerance_engine):
        """Test reporting component recovery."""
        # First report an error
        error = Exception("Connection timeout")
        fault_tolerance_engine.report_component_error(
            "knowledge_layer",
            error,
            is_transient=True
        )
        
        # Then report recovery
        fault_tolerance_engine.report_component_recovery("knowledge_layer")
        
        health = fault_tolerance_engine.get_component_status("knowledge_layer")
        
        assert health.status == ComponentStatus.HEALTHY
        assert health.error_message is None
        assert health.recovery_attempts == 0
    
    def test_recovery_resets_state(self, fault_tolerance_engine):
        """Test that recovery resets component state."""
        # Report multiple errors
        for i in range(3):
            error = Exception(f"Error {i}")
            fault_tolerance_engine.report_component_error(
                "metrics_ingestion",
                error,
                is_transient=True
            )
        
        # Report recovery
        fault_tolerance_engine.report_component_recovery("metrics_ingestion")
        
        health = fault_tolerance_engine.get_component_status("metrics_ingestion")
        
        assert health.recovery_attempts == 0
        assert health.status == ComponentStatus.HEALTHY


class TestComponentAvailabilityCheck:
    """Test component availability checking."""
    
    def test_healthy_component_available(self, fault_tolerance_engine):
        """Test that healthy components are available."""
        available = fault_tolerance_engine.is_component_available("knowledge_layer")
        assert available is True
    
    def test_degraded_component_available(self, fault_tolerance_engine):
        """Test that degraded components are still available."""
        error = Exception("Connection timeout")
        fault_tolerance_engine.report_component_error(
            "knowledge_layer",
            error,
            is_transient=True
        )
        
        available = fault_tolerance_engine.is_component_available("knowledge_layer")
        assert available is True
    
    def test_unavailable_component(self, fault_tolerance_engine):
        """Test that unavailable components are not available."""
        error = Exception("Configuration error")
        fault_tolerance_engine.report_component_error(
            "file_storage",
            error,
            is_transient=False
        )
        
        available = fault_tolerance_engine.is_component_available("file_storage")
        assert available is False
    
    def test_unknown_component(self, fault_tolerance_engine):
        """Test checking availability of unknown component."""
        available = fault_tolerance_engine.is_component_available("unknown_component")
        assert available is False


class TestSystemHealthStatus:
    """Test overall system health status."""
    
    def test_healthy_system(self, fault_tolerance_engine):
        """Test system health when all components are healthy."""
        health = fault_tolerance_engine.get_system_health()
        
        assert health["overall_status"] == "healthy"
        assert health["healthy_components"] == 5
        assert health["degraded_components"] == 0
        assert health["unavailable_components"] == 0
    
    def test_degraded_system(self, fault_tolerance_engine):
        """Test system health when some components are degraded."""
        error = Exception("Connection timeout")
        fault_tolerance_engine.report_component_error(
            "knowledge_layer",
            error,
            is_transient=True
        )
        
        health = fault_tolerance_engine.get_system_health()
        
        assert health["overall_status"] == "degraded"
        assert health["healthy_components"] == 4
        assert health["degraded_components"] == 1
        assert health["unavailable_components"] == 0
    
    def test_unavailable_system(self, fault_tolerance_engine):
        """Test system health when components are unavailable."""
        error = Exception("Configuration error")
        fault_tolerance_engine.report_component_error(
            "file_storage",
            error,
            is_transient=False
        )
        
        health = fault_tolerance_engine.get_system_health()
        
        assert health["overall_status"] == "degraded"
        assert health["unavailable_components"] == 1


class TestRetryDecision:
    """Test retry decision logic."""
    
    def test_should_retry_healthy_component(self, fault_tolerance_engine):
        """Test that healthy components should be retried."""
        should_retry = fault_tolerance_engine.should_retry("knowledge_layer")
        assert should_retry is True
    
    def test_should_retry_degraded_component(self, fault_tolerance_engine):
        """Test that degraded components should be retried."""
        error = Exception("Connection timeout")
        fault_tolerance_engine.report_component_error(
            "knowledge_layer",
            error,
            is_transient=True
        )
        
        should_retry = fault_tolerance_engine.should_retry("knowledge_layer", max_retries=3)
        assert should_retry is True
    
    def test_should_not_retry_unavailable_component(self, fault_tolerance_engine):
        """Test that unavailable components should not be retried."""
        error = Exception("Configuration error")
        fault_tolerance_engine.report_component_error(
            "file_storage",
            error,
            is_transient=False
        )
        
        should_retry = fault_tolerance_engine.should_retry("file_storage")
        assert should_retry is False
    
    def test_should_not_retry_max_attempts_exceeded(self, fault_tolerance_engine):
        """Test that components with max retries exceeded should not be retried."""
        for i in range(3):
            error = Exception(f"Error {i}")
            fault_tolerance_engine.report_component_error(
                "llm_service",
                error,
                is_transient=True
            )
        
        should_retry = fault_tolerance_engine.should_retry("llm_service", max_retries=3)
        assert should_retry is False


class TestFallbackRecommendations:
    """Test fallback recommendation generation."""
    
    def test_fallback_recommendations_structure(self, fault_tolerance_engine):
        """Test that fallback recommendations have correct structure."""
        fallback = fault_tolerance_engine.get_fallback_recommendations("payment-api")
        
        assert fallback["service_id"] == "payment-api"
        assert "recommendations" in fallback
        assert "aggressive" in fallback["recommendations"]
        assert "balanced" in fallback["recommendations"]
        assert "conservative" in fallback["recommendations"]
        assert fallback["is_fallback"] is True
        assert fallback["confidence_score"] == 0.3
    
    def test_fallback_recommendations_values(self, fault_tolerance_engine):
        """Test that fallback recommendations have reasonable values."""
        fallback = fault_tolerance_engine.get_fallback_recommendations("payment-api")
        
        aggressive = fallback["recommendations"]["aggressive"]
        balanced = fallback["recommendations"]["balanced"]
        conservative = fallback["recommendations"]["conservative"]
        
        # Check that values are ordered correctly
        assert aggressive["availability"] >= balanced["availability"]
        assert balanced["availability"] >= conservative["availability"]
        
        assert aggressive["latency_p95_ms"] <= balanced["latency_p95_ms"]
        assert balanced["latency_p95_ms"] <= conservative["latency_p95_ms"]
    
    def test_fallback_with_metrics(self, fault_tolerance_engine):
        """Test fallback recommendations with available metrics."""
        metrics = {
            "availability": 99.5,
            "latency_p95_ms": 200
        }
        
        fallback = fault_tolerance_engine.get_fallback_recommendations(
            "payment-api",
            metrics=metrics
        )
        
        assert "Adjusted based on available metrics" in fallback["warnings"]


class TestDegradationWarnings:
    """Test degradation warning generation."""
    
    def test_no_warnings_healthy_system(self, fault_tolerance_engine):
        """Test that no warnings are generated for healthy system."""
        warnings = fault_tolerance_engine.get_degradation_warnings()
        assert warnings == []
    
    def test_degradation_warnings(self, fault_tolerance_engine):
        """Test that warnings are generated for degraded components."""
        error = Exception("Connection timeout")
        fault_tolerance_engine.report_component_error(
            "knowledge_layer",
            error,
            is_transient=True
        )
        
        warnings = fault_tolerance_engine.get_degradation_warnings()
        
        assert len(warnings) == 1
        assert "knowledge_layer" in warnings[0]
        assert "degraded" in warnings[0]
    
    def test_multiple_warnings(self, fault_tolerance_engine):
        """Test warnings for multiple degraded components."""
        error1 = Exception("Connection timeout")
        fault_tolerance_engine.report_component_error(
            "knowledge_layer",
            error1,
            is_transient=True
        )
        
        error2 = Exception("Configuration error")
        fault_tolerance_engine.report_component_error(
            "file_storage",
            error2,
            is_transient=False
        )
        
        warnings = fault_tolerance_engine.get_degradation_warnings()
        
        assert len(warnings) == 2

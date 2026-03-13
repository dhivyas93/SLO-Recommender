"""
Unit tests for the Evaluation Engine.

Tests backtesting and accuracy computation.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from src.engines.evaluation_engine import (
    EvaluationEngine,
    BacktestResult,
    AccuracyMetrics
)


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def evaluation_engine(temp_data_dir):
    """Create an EvaluationEngine instance with temporary storage."""
    return EvaluationEngine(base_path=temp_data_dir)


class TestBacktestResultCreation:
    """Test creation and validation of backtest results."""
    
    def test_create_backtest_result(self):
        """Test creating a backtest result."""
        result = BacktestResult(
            service_id="payment-api",
            backtest_date="2024-01-15T00:00:00Z",
            recommendation_version="v1.0.0",
            recommended_availability=99.5,
            recommended_latency_p95_ms=200,
            recommended_latency_p99_ms=400,
            recommended_error_rate_percent=1.0,
            actual_availability=99.6,
            actual_latency_p95_ms=180,
            actual_latency_p99_ms=380,
            actual_error_rate_percent=0.9,
            availability_met=True,
            latency_p95_met=True,
            latency_p99_met=True,
            error_rate_met=True,
            overall_accuracy=True
        )
        
        assert result.service_id == "payment-api"
        assert result.overall_accuracy is True
        assert result.availability_met is True


class TestAvailabilityCheck:
    """Test availability constraint checking."""
    
    def test_availability_met(self, evaluation_engine):
        """Test when actual availability meets recommendation."""
        result = evaluation_engine._check_availability_met(99.5, 99.6)
        assert result is True
    
    def test_availability_not_met(self, evaluation_engine):
        """Test when actual availability doesn't meet recommendation."""
        result = evaluation_engine._check_availability_met(99.5, 98.9)
        assert result is False
    
    def test_availability_with_margin(self, evaluation_engine):
        """Test availability check with allowed margin."""
        # 0.5% margin allowed
        result = evaluation_engine._check_availability_met(99.5, 99.0)
        assert result is True
    
    def test_availability_none_values(self, evaluation_engine):
        """Test availability check with None values."""
        result = evaluation_engine._check_availability_met(None, 99.5)
        assert result is True
        
        result = evaluation_engine._check_availability_met(99.5, None)
        assert result is True


class TestLatencyCheck:
    """Test latency constraint checking."""
    
    def test_latency_met(self, evaluation_engine):
        """Test when actual latency meets recommendation."""
        result = evaluation_engine._check_latency_met(200, 180)
        assert result is True
    
    def test_latency_not_met(self, evaluation_engine):
        """Test when actual latency doesn't meet recommendation."""
        result = evaluation_engine._check_latency_met(200, 220)
        assert result is False
    
    def test_latency_with_margin(self, evaluation_engine):
        """Test latency check with allowed margin."""
        # 10ms margin allowed
        result = evaluation_engine._check_latency_met(200, 209)
        assert result is True
    
    def test_latency_none_values(self, evaluation_engine):
        """Test latency check with None values."""
        result = evaluation_engine._check_latency_met(None, 200)
        assert result is True
        
        result = evaluation_engine._check_latency_met(200, None)
        assert result is True


class TestErrorRateCheck:
    """Test error rate constraint checking."""
    
    def test_error_rate_met(self, evaluation_engine):
        """Test when actual error rate meets recommendation."""
        result = evaluation_engine._check_error_rate_met(1.0, 0.9)
        assert result is True
    
    def test_error_rate_not_met(self, evaluation_engine):
        """Test when actual error rate doesn't meet recommendation."""
        result = evaluation_engine._check_error_rate_met(1.0, 1.8)
        assert result is False
    
    def test_error_rate_with_margin(self, evaluation_engine):
        """Test error rate check with allowed margin."""
        # 0.5% margin allowed
        result = evaluation_engine._check_error_rate_met(1.0, 1.4)
        assert result is True
    
    def test_error_rate_none_values(self, evaluation_engine):
        """Test error rate check with None values."""
        result = evaluation_engine._check_error_rate_met(None, 1.0)
        assert result is True
        
        result = evaluation_engine._check_error_rate_met(1.0, None)
        assert result is True


class TestAccuracyMetricsComputation:
    """Test accuracy metrics computation."""
    
    def test_compute_accuracy_all_met(self, evaluation_engine):
        """Test accuracy computation when all recommendations are met."""
        results = [
            BacktestResult(
                service_id="payment-api",
                backtest_date="2024-01-15T00:00:00Z",
                recommendation_version="v1.0.0",
                recommended_availability=99.5,
                recommended_latency_p95_ms=200,
                recommended_latency_p99_ms=400,
                recommended_error_rate_percent=1.0,
                actual_availability=99.6,
                actual_latency_p95_ms=180,
                actual_latency_p99_ms=380,
                actual_error_rate_percent=0.9,
                availability_met=True,
                latency_p95_met=True,
                latency_p99_met=True,
                error_rate_met=True,
                overall_accuracy=True
            ),
            BacktestResult(
                service_id="payment-api",
                backtest_date="2024-01-16T00:00:00Z",
                recommendation_version="v1.1.0",
                recommended_availability=99.5,
                recommended_latency_p95_ms=200,
                recommended_latency_p99_ms=400,
                recommended_error_rate_percent=1.0,
                actual_availability=99.5,
                actual_latency_p95_ms=200,
                actual_latency_p99_ms=400,
                actual_error_rate_percent=1.0,
                availability_met=True,
                latency_p95_met=True,
                latency_p99_met=True,
                error_rate_met=True,
                overall_accuracy=True
            )
        ]
        
        metrics = evaluation_engine.compute_accuracy_metrics(results)
        
        assert metrics.overall_accuracy == 1.0
        assert metrics.total_recommendations == 2
        assert metrics.accurate_recommendations == 2
    
    def test_compute_accuracy_partial_met(self, evaluation_engine):
        """Test accuracy computation when some recommendations are met."""
        results = [
            BacktestResult(
                service_id="payment-api",
                backtest_date="2024-01-15T00:00:00Z",
                recommendation_version="v1.0.0",
                recommended_availability=99.5,
                recommended_latency_p95_ms=200,
                recommended_latency_p99_ms=400,
                recommended_error_rate_percent=1.0,
                actual_availability=99.6,
                actual_latency_p95_ms=180,
                actual_latency_p99_ms=380,
                actual_error_rate_percent=0.9,
                availability_met=True,
                latency_p95_met=True,
                latency_p99_met=True,
                error_rate_met=True,
                overall_accuracy=True
            ),
            BacktestResult(
                service_id="payment-api",
                backtest_date="2024-01-16T00:00:00Z",
                recommendation_version="v1.1.0",
                recommended_availability=99.5,
                recommended_latency_p95_ms=200,
                recommended_latency_p99_ms=400,
                recommended_error_rate_percent=1.0,
                actual_availability=98.9,
                actual_latency_p95_ms=250,
                actual_latency_p99_ms=500,
                actual_error_rate_percent=2.0,
                availability_met=False,
                latency_p95_met=False,
                latency_p99_met=False,
                error_rate_met=False,
                overall_accuracy=False
            )
        ]
        
        metrics = evaluation_engine.compute_accuracy_metrics(results)
        
        assert metrics.overall_accuracy == pytest.approx(0.5, rel=0.01)
        assert metrics.total_recommendations == 2
        assert metrics.accurate_recommendations == 1
    
    def test_compute_accuracy_empty_results(self, evaluation_engine):
        """Test accuracy computation with empty results."""
        metrics = evaluation_engine.compute_accuracy_metrics([])
        
        assert metrics.overall_accuracy == 0.0
        assert metrics.total_recommendations == 0
        assert metrics.accurate_recommendations == 0


class TestBacktestResultStorage:
    """Test storage of backtest results."""
    
    def test_store_backtest_results(self, evaluation_engine):
        """Test storing backtest results."""
        results = [
            BacktestResult(
                service_id="payment-api",
                backtest_date="2024-01-15T00:00:00Z",
                recommendation_version="v1.0.0",
                recommended_availability=99.5,
                recommended_latency_p95_ms=200,
                recommended_latency_p99_ms=400,
                recommended_error_rate_percent=1.0,
                actual_availability=99.6,
                actual_latency_p95_ms=180,
                actual_latency_p99_ms=380,
                actual_error_rate_percent=0.9,
                availability_met=True,
                latency_p95_met=True,
                latency_p99_met=True,
                error_rate_met=True,
                overall_accuracy=True
            )
        ]
        
        backtest_date = datetime(2024, 1, 15)
        evaluation_engine.store_backtest_results(results, backtest_date)
        
        # Verify file was created
        import os
        results_file = os.path.join(
            evaluation_engine.base_path,
            "evaluation/backtest_results_2024-01-15.json"
        )
        assert os.path.exists(results_file)


class TestAccuracyReportStorage:
    """Test storage of accuracy reports."""
    
    def test_store_accuracy_report(self, evaluation_engine):
        """Test storing accuracy report."""
        metrics = AccuracyMetrics(
            overall_accuracy=0.87,
            aggressive_precision=0.72,
            balanced_precision=0.91,
            conservative_precision=0.98,
            acceptance_rate=0.83,
            total_recommendations=150,
            accurate_recommendations=130,
            modified_recommendations=15,
            rejected_recommendations=5
        )
        
        report_date = datetime(2024, 1, 15)
        evaluation_engine.store_accuracy_report(metrics, report_date)
        
        # Verify file was created
        import os
        report_file = os.path.join(
            evaluation_engine.base_path,
            "evaluation/accuracy_report_2024-01-15.json"
        )
        assert os.path.exists(report_file)

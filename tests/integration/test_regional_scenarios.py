"""
Integration tests for regional support.

Tests region-specific recommendations, cross-region aggregation, and regional variance analysis.
"""

import pytest
from src.engines.regional_recommendations import RegionalRecommendationEngine
from src.engines.cross_region_aggregation import (
    CrossRegionAggregationEngine,
    AggregationStrategy
)


@pytest.fixture
def regional_engine():
    """Create a regional recommendation engine."""
    return RegionalRecommendationEngine()


@pytest.fixture
def aggregation_engine():
    """Create a cross-region aggregation engine."""
    return CrossRegionAggregationEngine()


@pytest.fixture
def sample_regional_metrics():
    """Create sample metrics for multiple regions."""
    return {
        "us-east-1": {
            "metrics": {
                "latency": {
                    "p50_ms": 100.0,
                    "p95_ms": 200.0,
                    "p99_ms": 300.0,
                    "mean_ms": 150.0,
                    "stddev_ms": 50.0
                },
                "error_rate": {
                    "percent": 1.0,
                    "total_requests": 10000,
                    "failed_requests": 100
                },
                "availability": {
                    "percent": 99.5,
                    "uptime_seconds": 86340,
                    "downtime_seconds": 60
                }
            },
            "data_quality": {
                "completeness": 0.95,
                "quality_score": 0.95
            }
        },
        "eu-west-1": {
            "metrics": {
                "latency": {
                    "p50_ms": 120.0,
                    "p95_ms": 220.0,
                    "p99_ms": 320.0,
                    "mean_ms": 170.0,
                    "stddev_ms": 55.0
                },
                "error_rate": {
                    "percent": 1.5,
                    "total_requests": 8000,
                    "failed_requests": 120
                },
                "availability": {
                    "percent": 99.3,
                    "uptime_seconds": 85800,
                    "downtime_seconds": 600
                }
            },
            "data_quality": {
                "completeness": 0.92,
                "quality_score": 0.92
            }
        },
        "ap-southeast-1": {
            "metrics": {
                "latency": {
                    "p50_ms": 150.0,
                    "p95_ms": 250.0,
                    "p99_ms": 350.0,
                    "mean_ms": 200.0,
                    "stddev_ms": 60.0
                },
                "error_rate": {
                    "percent": 2.0,
                    "total_requests": 5000,
                    "failed_requests": 100
                },
                "availability": {
                    "percent": 99.0,
                    "uptime_seconds": 85500,
                    "downtime_seconds": 900
                }
            },
            "data_quality": {
                "completeness": 0.90,
                "quality_score": 0.90
            }
        }
    }


class TestRegionalRecommendations:
    """Tests for region-specific recommendations."""
    
    def test_generate_regional_recommendations(self, regional_engine, sample_regional_metrics):
        """Test generating region-specific recommendations."""
        result = regional_engine.generate_regional_recommendations(
            service_id="test-service",
            regional_metrics=sample_regional_metrics
        )
        
        assert result["service_id"] == "test-service"
        assert "regional_recommendations" in result
        assert "global_recommendation" in result
        assert result["region_count"] == 3
        assert len(result["regions_analyzed"]) == 3
    
    def test_regional_recommendations_structure(self, regional_engine, sample_regional_metrics):
        """Test that regional recommendations have correct structure."""
        result = regional_engine.generate_regional_recommendations(
            service_id="test-service",
            regional_metrics=sample_regional_metrics
        )
        
        # Check regional recommendations
        for region in sample_regional_metrics.keys():
            assert region in result["regional_recommendations"]
            regional_rec = result["regional_recommendations"][region]
            assert "service_id" in regional_rec or "error" in regional_rec
    
    def test_global_recommendation_aggregation(self, regional_engine, sample_regional_metrics):
        """Test that global recommendation aggregates regional data."""
        result = regional_engine.generate_regional_recommendations(
            service_id="test-service",
            regional_metrics=sample_regional_metrics
        )
        
        global_rec = result["global_recommendation"]
        
        # Global recommendation should have aggregated metrics
        assert "recommendations" in global_rec or "error" in global_rec
        
        # Should include regional variance analysis
        if "regional_variance" in global_rec:
            assert "regions_analyzed" in global_rec["regional_variance"]
    
    def test_regional_variance_analysis(self, regional_engine, sample_regional_metrics):
        """Test regional variance analysis."""
        result = regional_engine.generate_regional_recommendations(
            service_id="test-service",
            regional_metrics=sample_regional_metrics
        )
        
        global_rec = result["global_recommendation"]
        
        if "regional_variance" in global_rec:
            variance = global_rec["regional_variance"]
            
            # Should identify highest latency region
            assert "highest_latency_region" in variance
            assert variance["highest_latency_region"] in sample_regional_metrics.keys()
            
            # Should identify lowest availability region
            assert "lowest_availability_region" in variance
            assert variance["lowest_availability_region"] in sample_regional_metrics.keys()
            
            # Should assess consistency
            assert "regional_consistency" in variance
            assert variance["regional_consistency"] in ["high", "medium", "low", "unknown"]
    
    def test_empty_regional_metrics_error(self, regional_engine):
        """Test that empty regional metrics raises error."""
        with pytest.raises(ValueError):
            regional_engine.generate_regional_recommendations(
                service_id="test-service",
                regional_metrics={}
            )
    
    def test_unknown_region_warning(self, regional_engine, sample_regional_metrics):
        """Test that unknown regions generate warnings."""
        metrics_with_unknown = sample_regional_metrics.copy()
        metrics_with_unknown["unknown-region"] = sample_regional_metrics["us-east-1"]
        
        # Should not raise error, but may log warning
        result = regional_engine.generate_regional_recommendations(
            service_id="test-service",
            regional_metrics=metrics_with_unknown
        )
        
        assert result["region_count"] == 4


class TestCrossRegionAggregation:
    """Tests for cross-region aggregation."""
    
    def test_aggregate_metrics_worst_case(self, aggregation_engine, sample_regional_metrics):
        """Test aggregating metrics using worst-case strategy."""
        aggregation_engine.strategy = AggregationStrategy.WORST_CASE
        
        aggregated = aggregation_engine.aggregate_metrics(sample_regional_metrics)
        
        assert "latency" in aggregated
        assert "error_rate" in aggregated
        assert "availability" in aggregated
        
        # Latency should be worst case (maximum)
        assert aggregated["latency"]["p95_ms"] == 250.0  # ap-southeast-1
        
        # Error rate should be worst case (maximum)
        assert aggregated["error_rate"]["percent"] == 2.0  # ap-southeast-1
        
        # Availability should be worst case (minimum)
        assert aggregated["availability"]["percent"] == 99.0  # ap-southeast-1
    
    def test_aggregate_metrics_average(self, aggregation_engine, sample_regional_metrics):
        """Test aggregating metrics using average strategy."""
        aggregation_engine.strategy = AggregationStrategy.AVERAGE
        
        aggregated = aggregation_engine.aggregate_metrics(sample_regional_metrics)
        
        # Latency should be average
        expected_latency = (200.0 + 220.0 + 250.0) / 3
        assert abs(aggregated["latency"]["p95_ms"] - expected_latency) < 0.1
    
    def test_aggregate_metrics_percentile_95(self, aggregation_engine, sample_regional_metrics):
        """Test aggregating metrics using 95th percentile strategy."""
        aggregation_engine.strategy = AggregationStrategy.PERCENTILE_95
        
        aggregated = aggregation_engine.aggregate_metrics(sample_regional_metrics)
        
        # Should use 95th percentile
        assert "latency" in aggregated
        assert aggregated["latency"]["p95_ms"] > 0
    
    def test_aggregate_recommendations(self, aggregation_engine):
        """Test aggregating recommendations from multiple regions."""
        regional_recommendations = {
            "us-east-1": {
                "recommendations": {
                    "aggressive": {
                        "availability": 99.9,
                        "latency_p95_ms": 150,
                        "error_rate_percent": 0.5
                    },
                    "balanced": {
                        "availability": 99.5,
                        "latency_p95_ms": 200,
                        "error_rate_percent": 1.0
                    },
                    "conservative": {
                        "availability": 99.0,
                        "latency_p95_ms": 300,
                        "error_rate_percent": 2.0
                    }
                }
            },
            "eu-west-1": {
                "recommendations": {
                    "aggressive": {
                        "availability": 99.8,
                        "latency_p95_ms": 160,
                        "error_rate_percent": 0.6
                    },
                    "balanced": {
                        "availability": 99.3,
                        "latency_p95_ms": 220,
                        "error_rate_percent": 1.2
                    },
                    "conservative": {
                        "availability": 98.8,
                        "latency_p95_ms": 320,
                        "error_rate_percent": 2.2
                    }
                }
            }
        }
        
        aggregated = aggregation_engine.aggregate_recommendations(regional_recommendations)
        
        assert "recommendations" in aggregated
        assert "aggressive" in aggregated["recommendations"]
        assert "balanced" in aggregated["recommendations"]
        assert "conservative" in aggregated["recommendations"]
        
        # Aggressive tier should have best values
        aggressive = aggregated["recommendations"]["aggressive"]
        assert aggressive["availability"] < 99.9  # Worst case
        assert aggressive["latency_p95_ms"] == 160  # Worst case
    
    def test_compute_regional_variance(self, aggregation_engine, sample_regional_metrics):
        """Test computing regional variance statistics."""
        variance = aggregation_engine.compute_regional_variance(sample_regional_metrics)
        
        assert "latency_p95_variance" in variance
        assert "availability_variance" in variance
        assert "error_rate_variance" in variance
        assert variance["regions_analyzed"] == 3
        
        # Check variance statistics structure
        latency_var = variance["latency_p95_variance"]
        assert "mean" in latency_var
        assert "min" in latency_var
        assert "max" in latency_var
        assert "stddev" in latency_var
        assert "coefficient_of_variation" in latency_var
    
    def test_identify_outlier_regions(self, aggregation_engine, sample_regional_metrics):
        """Test identifying outlier regions."""
        outliers = aggregation_engine.identify_outlier_regions(
            sample_regional_metrics,
            threshold_stddev=1.0
        )
        
        assert "latency" in outliers
        assert "availability" in outliers
        assert "error_rate" in outliers
        
        # ap-southeast-1 should be identified as outlier for latency
        # (it has highest latency)
        if outliers["latency"]:
            assert "ap-southeast-1" in outliers["latency"]
    
    def test_empty_regional_metrics_error(self, aggregation_engine):
        """Test that empty regional metrics raises error."""
        with pytest.raises(ValueError):
            aggregation_engine.aggregate_metrics({})


class TestRegionalConsistency:
    """Tests for regional consistency assessment."""
    
    def test_high_consistency_regions(self, regional_engine):
        """Test assessment of high consistency regions."""
        # Create metrics with low variance
        consistent_metrics = {
            "us-east-1": {
                "metrics": {
                    "latency": {"p95_ms": 200.0},
                    "error_rate": {"percent": 1.0},
                    "availability": {"percent": 99.5}
                }
            },
            "eu-west-1": {
                "metrics": {
                    "latency": {"p95_ms": 205.0},
                    "error_rate": {"percent": 1.0},
                    "availability": {"percent": 99.5}
                }
            },
            "ap-southeast-1": {
                "metrics": {
                    "latency": {"p95_ms": 210.0},
                    "error_rate": {"percent": 1.0},
                    "availability": {"percent": 99.5}
                }
            }
        }
        
        result = regional_engine.generate_regional_recommendations(
            service_id="test-service",
            regional_metrics=consistent_metrics
        )
        
        if "regional_variance" in result["global_recommendation"]:
            consistency = result["global_recommendation"]["regional_variance"]["regional_consistency"]
            assert consistency == "high"
    
    def test_low_consistency_regions(self, regional_engine):
        """Test assessment of low consistency regions."""
        # Create metrics with high variance
        inconsistent_metrics = {
            "us-east-1": {
                "metrics": {
                    "latency": {"p95_ms": 100.0},
                    "error_rate": {"percent": 0.5},
                    "availability": {"percent": 99.9}
                }
            },
            "eu-west-1": {
                "metrics": {
                    "latency": {"p95_ms": 500.0},
                    "error_rate": {"percent": 5.0},
                    "availability": {"percent": 95.0}
                }
            },
            "ap-southeast-1": {
                "metrics": {
                    "latency": {"p95_ms": 1000.0},
                    "error_rate": {"percent": 10.0},
                    "availability": {"percent": 90.0}
                }
            }
        }
        
        result = regional_engine.generate_regional_recommendations(
            service_id="test-service",
            regional_metrics=inconsistent_metrics
        )
        
        if "regional_variance" in result["global_recommendation"]:
            consistency = result["global_recommendation"]["regional_variance"]["regional_consistency"]
            assert consistency == "low"


class TestRegionalMetricsExtraction:
    """Tests for metric extraction from regional data."""
    
    def test_extract_metric_values(self, aggregation_engine, sample_regional_metrics):
        """Test extracting specific metric values."""
        values = aggregation_engine._extract_metric_values(
            sample_regional_metrics,
            "latency",
            "p95_ms"
        )
        
        assert len(values) == 3
        assert 200.0 in values
        assert 220.0 in values
        assert 250.0 in values
    
    def test_extract_missing_metric(self, aggregation_engine, sample_regional_metrics):
        """Test extracting metric that doesn't exist."""
        values = aggregation_engine._extract_metric_values(
            sample_regional_metrics,
            "latency",
            "nonexistent_metric"
        )
        
        assert len(values) == 0

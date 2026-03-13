"""
Integration test for per-region statistics computation.

Demonstrates end-to-end functionality of Task 11.2.
"""

import pytest
from datetime import datetime, timedelta
from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage


def test_regional_statistics_end_to_end(tmp_path):
    """
    End-to-end test demonstrating per-region statistics computation.
    
    This test:
    1. Ingests metrics with regional breakdown for multiple regions
    2. Computes per-region aggregated statistics
    3. Verifies statistics are computed correctly for each region
    4. Verifies statistics are stored and can be retrieved
    """
    # Setup
    storage = FileStorage(base_path=str(tmp_path))
    engine = MetricsIngestionEngine(storage=storage)
    
    # Ingest metrics for a multi-region service over 10 days
    now = datetime.utcnow()
    service_id = "payment-api"
    
    for day in range(10):
        timestamp = now - timedelta(days=day)
        
        # Simulate varying performance across regions
        result = engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            timestamp=timestamp,
            latency={
                "p50_ms": 50.0,
                "p95_ms": 100.0,
                "p99_ms": 150.0,
                "mean_ms": 60.0,
                "stddev_ms": 20.0
            },
            error_rate={
                "percent": 1.0,
                "total_requests": 10000,
                "failed_requests": 100
            },
            availability={
                "percent": 99.5,
                "uptime_seconds": 86100,
                "downtime_seconds": 300
            },
            regional_breakdown={
                "us-east-1": {
                    "latency_p95_ms": 90.0 + day * 2,  # Gradually increasing
                    "availability": 99.9 - day * 0.01   # Gradually decreasing
                },
                "us-west-2": {
                    "latency_p95_ms": 95.0 + day * 2,
                    "availability": 99.8 - day * 0.01
                },
                "eu-west-1": {
                    "latency_p95_ms": 110.0 + day * 2,
                    "availability": 99.7 - day * 0.01
                }
            }
        )
        
        assert result["status"] == "ingested"
    
    # Compute per-region aggregated statistics
    regional_stats = engine.compute_regional_aggregated_metrics(
        service_id=service_id,
        time_windows=["1d", "7d"]
    )
    
    # Verify structure
    assert regional_stats["service_id"] == service_id
    assert regional_stats["has_regional_data"] is True
    assert len(regional_stats["regions"]) == 3
    
    # Verify all regions are present
    assert "us-east-1" in regional_stats["regions"]
    assert "us-west-2" in regional_stats["regions"]
    assert "eu-west-1" in regional_stats["regions"]
    
    # Verify statistics for us-east-1 in 7d window
    us_east_stats = regional_stats["regions"]["us-east-1"]["7d"]
    
    assert us_east_stats["data_available"] is True
    assert us_east_stats["sample_count"] == 7  # 7 days of data
    
    # Verify latency statistics
    latency_stats = us_east_stats["latency_p95_ms"]
    assert "mean" in latency_stats
    assert "median" in latency_stats
    assert "p50" in latency_stats
    assert "p95" in latency_stats
    assert "p99" in latency_stats
    assert "min" in latency_stats
    assert "max" in latency_stats
    assert "stddev" in latency_stats
    
    # Verify availability statistics
    availability_stats = us_east_stats["availability"]
    assert "mean" in availability_stats
    assert "median" in availability_stats
    assert "p50" in availability_stats
    assert "p95" in availability_stats
    assert "p99" in availability_stats
    
    # Verify latency increases over time (as we ingested increasing values)
    assert latency_stats["min"] < latency_stats["max"]
    
    # Verify availability decreases over time (as we ingested decreasing values)
    assert availability_stats["min"] < availability_stats["max"]
    
    # Verify storage and retrieval
    retrieved = engine.get_regional_aggregated_metrics(service_id)
    assert retrieved is not None
    assert retrieved["service_id"] == service_id
    assert retrieved["has_regional_data"] is True
    
    # Verify regional differences
    # eu-west-1 should have higher latency than us-east-1
    eu_west_stats = regional_stats["regions"]["eu-west-1"]["7d"]
    assert eu_west_stats["latency_p95_ms"]["mean"] > us_east_stats["latency_p95_ms"]["mean"]
    
    print("\n=== Regional Statistics Summary ===")
    print(f"Service: {service_id}")
    print(f"Regions: {list(regional_stats['regions'].keys())}")
    print(f"\nUS-East-1 (7d window):")
    print(f"  Latency p95 mean: {latency_stats['mean']}ms")
    print(f"  Latency p95 range: {latency_stats['min']}ms - {latency_stats['max']}ms")
    print(f"  Availability mean: {availability_stats['mean']}%")
    print(f"  Sample count: {us_east_stats['sample_count']}")
    
    print("\n✅ Per-region statistics computation working correctly!")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_regional_statistics_end_to_end(tmpdir)

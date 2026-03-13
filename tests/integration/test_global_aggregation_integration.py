"""
Integration test for global aggregation across regions.

Tests the complete workflow: ingest metrics with regional data,
compute per-region statistics, and compute global aggregated statistics.
"""

import pytest
from datetime import datetime, timedelta
from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage


def test_global_aggregation_end_to_end(tmp_path):
    """
    End-to-end test demonstrating global aggregation across regions.
    
    This test validates the complete workflow:
    1. Ingest metrics with regional breakdown
    2. Compute per-region statistics
    3. Compute global aggregated statistics
    4. Verify both regional and global stats are correct
    """
    # Setup
    storage = FileStorage(base_path=str(tmp_path))
    engine = MetricsIngestionEngine(storage=storage)
    
    # Ingest metrics for a multi-region service
    now = datetime.utcnow()
    service_id = "payment-api"
    
    # Simulate 10 days of metrics with 3 regions
    for day in range(10):
        for hour in range(24):
            timestamp = now - timedelta(days=day, hours=hour)
            
            # Simulate different performance characteristics per region
            metrics_data = {
                "service_id": service_id,
                "timestamp": timestamp,
                "time_window": "1d",
                "latency": {
                    "p50_ms": 50.0,
                    "p95_ms": 100.0,
                    "p99_ms": 150.0,
                    "mean_ms": 60.0,
                    "stddev_ms": 20.0
                },
                "error_rate": {
                    "percent": 1.0,
                    "total_requests": 10000,
                    "failed_requests": 100
                },
                "availability": {
                    "percent": 99.5,
                    "uptime_seconds": 3600,
                    "downtime_seconds": 18
                },
                "regional_breakdown": {
                    "us-east-1": {
                        "latency_p95_ms": 90.0 + (day * 2),  # Gradually increasing
                        "availability": 99.9 - (day * 0.01)
                    },
                    "eu-west-1": {
                        "latency_p95_ms": 110.0 + (day * 2),  # Higher latency
                        "availability": 99.8 - (day * 0.01)
                    },
                    "ap-south-1": {
                        "latency_p95_ms": 130.0 + (day * 2),  # Highest latency
                        "availability": 99.7 - (day * 0.01)
                    }
                }
            }
            
            result = engine.ingest_metrics(**metrics_data)
            assert result["status"] == "ingested"
    
    # Compute per-region statistics
    regional_stats = engine.compute_regional_aggregated_metrics(
        service_id=service_id,
        time_windows=["1d", "7d"]
    )
    
    # Verify regional statistics
    assert regional_stats["has_regional_data"] is True
    assert "us-east-1" in regional_stats["regions"]
    assert "eu-west-1" in regional_stats["regions"]
    assert "ap-south-1" in regional_stats["regions"]
    
    # Check 1d window for us-east-1
    us_east_1d = regional_stats["regions"]["us-east-1"]["1d"]
    assert us_east_1d["data_available"] is True
    assert us_east_1d["sample_count"] == 24  # 24 hours
    
    # Compute global aggregated statistics
    global_stats = engine.compute_global_aggregated_metrics(
        service_id=service_id,
        time_windows=["1d", "7d"]
    )
    
    # Verify global statistics
    assert global_stats["has_regional_data"] is True
    assert "1d" in global_stats["global_stats"]
    assert "7d" in global_stats["global_stats"]
    
    # Check 1d window global stats
    global_1d = global_stats["global_stats"]["1d"]
    assert global_1d["data_available"] is True
    assert global_1d["sample_count"] == 24
    
    # Global latency should be average of all regions
    # us-east-1: 90, eu-west-1: 110, ap-south-1: 130
    # Average: (90 + 110 + 130) / 3 = 110
    latency_stats = global_1d["latency_p95_ms"]
    assert latency_stats["mean"] == 110.0
    
    # Global availability should be average of all regions
    # us-east-1: 99.9, eu-west-1: 99.8, ap-south-1: 99.7
    # Average: (99.9 + 99.8 + 99.7) / 3 = 99.8
    availability_stats = global_1d["availability"]
    assert availability_stats["mean"] == 99.8
    
    # Verify 7d window has more samples
    global_7d = global_stats["global_stats"]["7d"]
    assert global_7d["sample_count"] > global_1d["sample_count"]
    
    # Verify storage and retrieval
    retrieved_regional = engine.get_regional_aggregated_metrics(service_id)
    assert retrieved_regional is not None
    assert retrieved_regional["service_id"] == service_id
    
    retrieved_global = engine.get_global_aggregated_metrics(service_id)
    assert retrieved_global is not None
    assert retrieved_global["service_id"] == service_id
    
    # Verify global stats show variation over time
    # Since latency increases over days in the 7d window, we should see variation there
    global_7d_latency = global_7d["latency_p95_ms"]
    assert global_7d_latency["stddev"] > 0
    assert global_7d_latency["min"] < global_7d_latency["max"]
    
    print("\n=== Integration Test Results ===")
    print(f"Service: {service_id}")
    print(f"Regions: {list(regional_stats['regions'].keys())}")
    print(f"\nRegional Stats (1d window):")
    for region in ["us-east-1", "eu-west-1", "ap-south-1"]:
        region_data = regional_stats["regions"][region]["1d"]
        print(f"  {region}:")
        print(f"    Latency p95 mean: {region_data['latency_p95_ms']['mean']} ms")
        print(f"    Availability mean: {region_data['availability']['mean']}%")
    
    print(f"\nGlobal Stats (1d window):")
    print(f"  Latency p95 mean: {latency_stats['mean']} ms")
    print(f"  Latency p95 stddev: {latency_stats['stddev']} ms")
    print(f"  Availability mean: {availability_stats['mean']}%")
    print(f"  Sample count: {global_1d['sample_count']}")
    
    print("\n✅ Global aggregation integration test passed!")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_global_aggregation_end_to_end(tmpdir)

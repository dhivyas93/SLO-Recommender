"""
Demonstration of explanation generation functionality.

This script shows how to use the generate_explanation method to create
human-readable explanations for SLO recommendations.
"""

from datetime import datetime, timedelta
from src.engines.recommendation_engine import RecommendationEngine
from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage
import json


def main():
    """Demonstrate explanation generation."""
    
    # Initialize components
    storage = FileStorage(base_path="data/demo")
    metrics_engine = MetricsIngestionEngine(storage=storage)
    recommendation_engine = RecommendationEngine(storage=storage, metrics_engine=metrics_engine)
    
    # Create a sample service with metrics
    service_id = "demo-payment-api"
    
    print(f"Creating sample service: {service_id}")
    print("-" * 60)
    
    # Ingest historical metrics
    base_time = datetime.utcnow() - timedelta(days=29)
    
    for i in range(30):
        timestamp = base_time + timedelta(days=i)
        
        metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="30d",
            latency={
                "p50_ms": 85 + (i % 5),
                "p95_ms": 180 + (i % 10),
                "p99_ms": 350 + (i % 15),
                "mean_ms": 95 + (i % 5),
                "stddev_ms": 45
            },
            error_rate={
                "percent": 0.8 + (i % 3) * 0.1,
                "total_requests": 1000000,
                "failed_requests": 8000 + (i % 3) * 1000
            },
            availability={
                "percent": 99.6 - (i % 3) * 0.1,
                "uptime_seconds": 86054,
                "downtime_seconds": 346
            },
            timestamp=timestamp
        )
    
    # Compute aggregated metrics
    metrics_engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
    
    print(f"✓ Ingested 30 days of metrics")
    print()
    
    # Generate recommendations
    print("Generating recommendations...")
    print("-" * 60)
    
    # Step 1: Compute base recommendations
    base_result = recommendation_engine.compute_base_recommendations(service_id)
    base_recommendations = base_result["base_recommendations"]
    
    print("Base recommendations (statistical baseline):")
    print(f"  Availability: {base_recommendations['availability']:.2f}%")
    print(f"  Latency p95: {base_recommendations['latency_p95_ms']:.2f}ms")
    print(f"  Latency p99: {base_recommendations['latency_p99_ms']:.2f}ms")
    print(f"  Error rate: {base_recommendations['error_rate_percent']:.2f}%")
    print()
    
    # Step 2: Apply dependency constraints
    dep_result = recommendation_engine.apply_dependency_constraints(
        service_id=service_id,
        base_recommendations=base_recommendations
    )
    constrained_recommendations = dep_result["constrained_recommendations"]
    dependency_metadata = dep_result["metadata"]
    
    print("After dependency constraints:")
    print(f"  Availability: {constrained_recommendations['availability']:.2f}%")
    print(f"  Latency p95: {constrained_recommendations['latency_p95_ms']:.2f}ms")
    print()
    
    # Step 3: Apply infrastructure constraints
    infra_result = recommendation_engine.apply_infrastructure_constraints(
        service_id=service_id,
        constrained_recommendations=constrained_recommendations
    )
    infrastructure_constrained_recommendations = infra_result["infrastructure_constrained_recommendations"]
    infrastructure_metadata = infra_result["metadata"]
    
    print("After infrastructure constraints:")
    print(f"  Availability: {infrastructure_constrained_recommendations['availability']:.2f}%")
    print(f"  Latency p95: {infrastructure_constrained_recommendations['latency_p95_ms']:.2f}ms")
    print()
    
    # Step 4: Generate explanation
    print("Generating explanation...")
    print("-" * 60)
    
    explanation = recommendation_engine.generate_explanation(
        service_id=service_id,
        base_recommendations=base_recommendations,
        constrained_recommendations=constrained_recommendations,
        infrastructure_constrained_recommendations=infrastructure_constrained_recommendations,
        dependency_metadata=dependency_metadata,
        infrastructure_metadata=infrastructure_metadata,
        confidence_score=0.85,
        time_window="30d"
    )
    
    # Display explanation
    print("\n" + "=" * 60)
    print("RECOMMENDATION EXPLANATION")
    print("=" * 60)
    print()
    
    print("Summary:")
    print(f"  {explanation['summary']}")
    print()
    
    print("Top 3 Influencing Factors:")
    for i, factor in enumerate(explanation['top_factors'], 1):
        print(f"  {i}. {factor}")
    print()
    
    if explanation['dependency_constraints']:
        print("Dependency Constraints:")
        for constraint in explanation['dependency_constraints']:
            print(f"  • {constraint}")
        print()
    else:
        print("Dependency Constraints: None")
        print()
    
    if explanation['infrastructure_bottlenecks']:
        print("Infrastructure Bottlenecks:")
        for bottleneck in explanation['infrastructure_bottlenecks']:
            print(f"  • {bottleneck}")
        print()
    else:
        print("Infrastructure Bottlenecks: None")
        print()
    
    if explanation['similar_services']:
        print("Similar Services:")
        for service in explanation['similar_services']:
            print(f"  • {service}")
        print()
    else:
        print("Similar Services: (placeholder - not yet implemented)")
        print()
    
    print("=" * 60)
    print()
    
    # Save explanation to file
    output_file = f"data/demo/explanations/{service_id}_explanation.json"
    storage.write_json(output_file, explanation)
    print(f"✓ Explanation saved to: {output_file}")
    print()


if __name__ == "__main__":
    main()

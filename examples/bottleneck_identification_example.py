"""
Example demonstrating bottleneck identification functionality.

This example shows how the identify_infrastructure_bottlenecks method
identifies which infrastructure components are limiting factors for SLO
recommendations.
"""

import json
from src.engines.recommendation_engine import RecommendationEngine
from src.storage.file_storage import FileStorage


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print('=' * 80)


def print_bottleneck_analysis(analysis):
    """Pretty print bottleneck analysis results."""
    print(f"\nSummary: {analysis['summary']}")
    print(f"Total components analyzed: {analysis['total_count']}")
    
    if analysis['bottlenecks']:
        print(f"\n🔴 Active Bottlenecks ({len(analysis['bottlenecks'])}):")
        for bottleneck in analysis['bottlenecks']:
            print(f"  - {bottleneck['description']}")
            print(f"    Severity: {bottleneck['severity']}")
            if 'impact' in bottleneck:
                impact = bottleneck['impact']
                print(f"    Impact: {impact['metric']} changed from {impact['original_value']} "
                      f"to {impact['constrained_value']}")
    
    if analysis['near_bottlenecks']:
        print(f"\n🟡 Near-Bottlenecks ({len(analysis['near_bottlenecks'])}):")
        for near_bottleneck in analysis['near_bottlenecks']:
            print(f"  - {near_bottleneck['description']}")
            print(f"    Severity: {near_bottleneck['severity']}")
            print(f"    Headroom: {near_bottleneck['headroom']:.2f}")
    
    if analysis['risks']:
        print(f"\n⚠️  Potential Risks ({len(analysis['risks'])}):")
        for risk in analysis['risks']:
            print(f"  - {risk['description']}")
            print(f"    Severity: {risk['severity']}")


def example_1_active_bottleneck():
    """Example 1: Active bottleneck - datastore limits availability."""
    print_section("Example 1: Active Bottleneck - Datastore Limits Availability")
    
    engine = RecommendationEngine()
    
    infrastructure = {
        "datastores": [
            {
                "name": "postgres-primary",
                "type": "postgresql",
                "availability_slo": 99.0,  # Lower than desired service availability
                "latency_p95_ms": 50.0
            }
        ],
        "caches": [],
        "message_queues": []
    }
    
    # Service wanted 99.5% availability, but datastore only provides 99.0%
    original_recommendations = {
        "availability": 99.5,
        "latency_p95_ms": 100.0,
        "latency_p99_ms": 200.0,
        "error_rate_percent": 1.0
    }
    
    # After applying constraints, availability is reduced
    constrained_recommendations = {
        "availability": 98.5,  # 99.0 - 0.5 margin
        "latency_p95_ms": 100.0,
        "latency_p99_ms": 200.0,
        "error_rate_percent": 1.0
    }
    
    print("\nInfrastructure:")
    print(json.dumps(infrastructure, indent=2))
    
    print("\nOriginal Recommendations:")
    print(f"  Availability: {original_recommendations['availability']}%")
    
    print("\nConstrained Recommendations:")
    print(f"  Availability: {constrained_recommendations['availability']}%")
    
    analysis = engine.identify_infrastructure_bottlenecks(
        service_id="payment-api",
        infrastructure_constrained_recommendations=constrained_recommendations,
        original_recommendations=original_recommendations,
        infrastructure=infrastructure,
        availability_margin=0.5
    )
    
    print_bottleneck_analysis(analysis)


def example_2_latency_bottleneck():
    """Example 2: Active bottleneck - slow datastore sets minimum latency."""
    print_section("Example 2: Active Bottleneck - Slow Datastore Sets Minimum Latency")
    
    engine = RecommendationEngine()
    
    infrastructure = {
        "datastores": [
            {
                "name": "legacy-db",
                "type": "mysql",
                "availability_slo": 99.9,
                "latency_p95_ms": 200.0  # High latency
            }
        ],
        "caches": [],
        "message_queues": []
    }
    
    # Service wanted aggressive 50ms latency, but datastore is too slow
    original_recommendations = {
        "availability": 99.5,
        "latency_p95_ms": 50.0,  # Too aggressive
        "latency_p99_ms": 100.0,
        "error_rate_percent": 1.0
    }
    
    # After applying constraints, latency is raised
    constrained_recommendations = {
        "availability": 99.5,
        "latency_p95_ms": 205.0,  # 200 + 5 network overhead
        "latency_p99_ms": 307.5,
        "error_rate_percent": 1.0
    }
    
    print("\nInfrastructure:")
    print(json.dumps(infrastructure, indent=2))
    
    print("\nOriginal Recommendations:")
    print(f"  Latency p95: {original_recommendations['latency_p95_ms']}ms")
    
    print("\nConstrained Recommendations:")
    print(f"  Latency p95: {constrained_recommendations['latency_p95_ms']}ms")
    
    analysis = engine.identify_infrastructure_bottlenecks(
        service_id="api-gateway",
        infrastructure_constrained_recommendations=constrained_recommendations,
        original_recommendations=original_recommendations,
        infrastructure=infrastructure,
        network_overhead_ms=5.0
    )
    
    print_bottleneck_analysis(analysis)


def example_3_near_bottleneck():
    """Example 3: Near-bottleneck - component close to becoming a constraint."""
    print_section("Example 3: Near-Bottleneck - Component Close to Limiting")
    
    engine = RecommendationEngine()
    
    infrastructure = {
        "datastores": [
            {
                "name": "postgres-db",
                "type": "postgresql",
                "availability_slo": 99.5,
                "latency_p95_ms": 100.0
            }
        ],
        "caches": [],
        "message_queues": []
    }
    
    # Service availability is close to datastore limit (within 1% headroom)
    recommendations = {
        "availability": 98.6,  # Close to 99.5 - 0.5 = 99.0
        "latency_p95_ms": 110.0,  # Close to 100 + 5 = 105
        "latency_p99_ms": 200.0,
        "error_rate_percent": 1.0
    }
    
    print("\nInfrastructure:")
    print(json.dumps(infrastructure, indent=2))
    
    print("\nRecommendations:")
    print(f"  Availability: {recommendations['availability']}%")
    print(f"  Latency p95: {recommendations['latency_p95_ms']}ms")
    
    analysis = engine.identify_infrastructure_bottlenecks(
        service_id="user-service",
        infrastructure_constrained_recommendations=recommendations,
        original_recommendations=recommendations,
        infrastructure=infrastructure,
        availability_margin=0.5,
        network_overhead_ms=5.0
    )
    
    print_bottleneck_analysis(analysis)


def example_4_message_queue_risk():
    """Example 4: Message queue identified as potential risk."""
    print_section("Example 4: Message Queue Risk")
    
    engine = RecommendationEngine()
    
    infrastructure = {
        "datastores": [],
        "caches": [],
        "message_queues": [
            {
                "name": "kafka-events",
                "type": "kafka"
            },
            {
                "name": "rabbitmq-tasks",
                "type": "rabbitmq"
            }
        ]
    }
    
    recommendations = {
        "availability": 99.5,
        "latency_p95_ms": 100.0,
        "latency_p99_ms": 200.0,
        "error_rate_percent": 1.0
    }
    
    print("\nInfrastructure:")
    print(json.dumps(infrastructure, indent=2))
    
    analysis = engine.identify_infrastructure_bottlenecks(
        service_id="event-processor",
        infrastructure_constrained_recommendations=recommendations,
        original_recommendations=recommendations,
        infrastructure=infrastructure
    )
    
    print_bottleneck_analysis(analysis)


def example_5_complex_scenario():
    """Example 5: Complex scenario with multiple bottlenecks and risks."""
    print_section("Example 5: Complex Scenario - Multiple Components")
    
    engine = RecommendationEngine()
    
    infrastructure = {
        "datastores": [
            {
                "name": "postgres-primary",
                "type": "postgresql",
                "availability_slo": 99.0,  # Active bottleneck
                "latency_p95_ms": 50.0
            },
            {
                "name": "redis-cache-db",
                "type": "redis",
                "availability_slo": 99.5,  # Near-bottleneck
                "latency_p95_ms": 100.0
            }
        ],
        "caches": [],
        "message_queues": [
            {
                "name": "kafka-queue",
                "type": "kafka"
            }
        ]
    }
    
    original_recommendations = {
        "availability": 99.5,
        "latency_p95_ms": 50.0,
        "latency_p99_ms": 100.0,
        "error_rate_percent": 1.0
    }
    
    constrained_recommendations = {
        "availability": 98.5,  # Constrained by postgres-primary
        "latency_p95_ms": 105.0,  # Constrained by redis-cache-db
        "latency_p99_ms": 157.5,
        "error_rate_percent": 1.0
    }
    
    print("\nInfrastructure:")
    print(json.dumps(infrastructure, indent=2))
    
    print("\nOriginal Recommendations:")
    print(f"  Availability: {original_recommendations['availability']}%")
    print(f"  Latency p95: {original_recommendations['latency_p95_ms']}ms")
    
    print("\nConstrained Recommendations:")
    print(f"  Availability: {constrained_recommendations['availability']}%")
    print(f"  Latency p95: {constrained_recommendations['latency_p95_ms']}ms")
    
    analysis = engine.identify_infrastructure_bottlenecks(
        service_id="complex-service",
        infrastructure_constrained_recommendations=constrained_recommendations,
        original_recommendations=original_recommendations,
        infrastructure=infrastructure,
        availability_margin=0.5,
        network_overhead_ms=5.0
    )
    
    print_bottleneck_analysis(analysis)


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("  BOTTLENECK IDENTIFICATION EXAMPLES")
    print("=" * 80)
    print("\nThis demonstrates how the system identifies infrastructure components")
    print("that limit or constrain SLO recommendations.")
    
    example_1_active_bottleneck()
    example_2_latency_bottleneck()
    example_3_near_bottleneck()
    example_4_message_queue_risk()
    example_5_complex_scenario()
    
    print("\n" + "=" * 80)
    print("  Examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

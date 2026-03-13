#!/usr/bin/env python3
"""
Generate comprehensive sample data for the SLO Recommendation System POC.

This script creates:
1. 20-30 sample services with realistic metadata
2. Realistic dependency graph with various topologies
3. Historical metrics for multiple time windows
4. Sample knowledge base content
5. Sample API keys for testing
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import random
import statistics

# Service types and their characteristics
SERVICE_TYPES = {
    "api_gateway": {
        "description": "Entry point for API requests",
        "typical_latency_p95": 100,
        "typical_availability": 99.95,
        "typical_error_rate": 0.1,
    },
    "auth_service": {
        "description": "Authentication and authorization",
        "typical_latency_p95": 50,
        "typical_availability": 99.99,
        "typical_error_rate": 0.05,
    },
    "payment_service": {
        "description": "Payment processing",
        "typical_latency_p95": 200,
        "typical_availability": 99.9,
        "typical_error_rate": 0.2,
    },
    "user_service": {
        "description": "User profile and data management",
        "typical_latency_p95": 80,
        "typical_availability": 99.9,
        "typical_error_rate": 0.1,
    },
    "database": {
        "description": "Primary data store",
        "typical_latency_p95": 45,
        "typical_availability": 99.99,
        "typical_error_rate": 0.01,
    },
    "cache": {
        "description": "In-memory cache layer",
        "typical_latency_p95": 5,
        "typical_availability": 99.95,
        "typical_error_rate": 0.05,
    },
    "message_queue": {
        "description": "Asynchronous message processing",
        "typical_latency_p95": 150,
        "typical_availability": 99.9,
        "typical_error_rate": 0.1,
    },
    "search_service": {
        "description": "Full-text search and indexing",
        "typical_latency_p95": 300,
        "typical_availability": 99.8,
        "typical_error_rate": 0.2,
    },
}

# Sample services to create
SAMPLE_SERVICES = [
    ("api-gateway", "api_gateway", "Platform", "critical"),
    ("auth-service", "auth_service", "Security", "critical"),
    ("user-service", "user_service", "Platform", "high"),
    ("payment-api", "payment_service", "Payments", "critical"),
    ("order-service", "api_gateway", "Orders", "high"),
    ("inventory-service", "api_gateway", "Inventory", "high"),
    ("notification-service", "message_queue", "Notifications", "medium"),
    ("search-service", "search_service", "Search", "medium"),
    ("analytics-service", "message_queue", "Analytics", "low"),
    ("recommendation-engine", "api_gateway", "ML", "medium"),
    ("user-db", "database", "Data", "critical"),
    ("payment-db", "database", "Data", "critical"),
    ("cache-layer", "cache", "Infrastructure", "high"),
    ("message-broker", "message_queue", "Infrastructure", "high"),
    ("logging-service", "message_queue", "Observability", "medium"),
    ("metrics-service", "database", "Observability", "medium"),
    ("config-service", "api_gateway", "Platform", "high"),
    ("rate-limiter", "cache", "Platform", "high"),
    ("cdn-service", "api_gateway", "Infrastructure", "high"),
    ("webhook-service", "message_queue", "Integration", "medium"),
    ("email-service", "message_queue", "Notifications", "medium"),
    ("sms-service", "message_queue", "Notifications", "medium"),
    ("fraud-detection", "api_gateway", "Security", "high"),
    ("compliance-service", "database", "Compliance", "medium"),
    ("backup-service", "database", "Infrastructure", "medium"),
]

# Dependency relationships (realistic topology)
DEPENDENCIES = {
    "api-gateway": ["auth-service", "rate-limiter", "cdn-service"],
    "auth-service": ["user-db", "cache-layer"],
    "user-service": ["user-db", "cache-layer", "auth-service"],
    "payment-api": ["auth-service", "payment-db", "fraud-detection"],
    "order-service": ["api-gateway", "inventory-service", "payment-api"],
    "inventory-service": ["api-gateway", "user-db"],
    "notification-service": ["message-broker", "email-service", "sms-service"],
    "search-service": ["user-db", "cache-layer"],
    "analytics-service": ["message-broker", "metrics-service"],
    "recommendation-engine": ["user-db", "search-service", "cache-layer"],
    "user-db": ["backup-service"],
    "payment-db": ["backup-service"],
    "cache-layer": [],
    "message-broker": [],
    "logging-service": ["message-broker"],
    "metrics-service": ["message-broker"],
    "config-service": ["cache-layer"],
    "rate-limiter": ["cache-layer"],
    "cdn-service": [],
    "webhook-service": ["message-broker"],
    "email-service": ["message-broker"],
    "sms-service": ["message-broker"],
    "fraud-detection": ["user-db", "cache-layer"],
    "compliance-service": ["user-db"],
    "backup-service": [],
}


def generate_service_metadata(service_id, service_type, team, criticality):
    """Generate metadata for a service."""
    type_info = SERVICE_TYPES[service_type]
    return {
        "service_id": service_id,
        "service_type": service_type,
        "team": team,
        "criticality": criticality,
        "description": type_info["description"],
        "owner_email": f"{team.lower().replace(' ', '_')}@company.com",
        "slack_channel": f"#team-{team.lower().replace(' ', '-')}",
        "runbook_url": f"https://wiki.company.com/runbooks/{service_id}",
        "created_at": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
        "last_updated": datetime.now().isoformat(),
        "tags": [service_type, team.lower(), criticality],
    }


def generate_metrics_for_window(service_id, service_type, days_back=0):
    """Generate realistic metrics for a time window."""
    type_info = SERVICE_TYPES[service_type]
    base_latency = type_info["typical_latency_p95"]
    base_availability = type_info["typical_availability"]
    base_error_rate = type_info["typical_error_rate"]

    # Add some variation
    latency_variation = random.uniform(0.8, 1.2)
    availability_variation = random.uniform(-0.5, 0.3)
    error_variation = random.uniform(0.5, 2.0)

    p50_latency = int(base_latency * 0.6 * latency_variation)
    p95_latency = int(base_latency * latency_variation)
    p99_latency = int(base_latency * 1.8 * latency_variation)

    availability = min(99.99, max(90.0, base_availability + availability_variation))
    error_rate = min(10.0, max(0.01, base_error_rate * error_variation))

    return {
        "timestamp": (datetime.now() - timedelta(days=days_back)).isoformat(),
        "time_window": f"{days_back}d",
        "metrics": {
            "latency": {
                "p50_ms": p50_latency,
                "p95_ms": p95_latency,
                "p99_ms": p99_latency,
                "mean_ms": int((p50_latency + p95_latency) / 2),
                "stddev_ms": int((p95_latency - p50_latency) / 2),
            },
            "error_rate": {
                "percent": round(error_rate, 2),
                "total_requests": random.randint(100000, 10000000),
                "failed_requests": random.randint(100, 100000),
            },
            "availability": {
                "percent": round(availability, 2),
                "uptime_seconds": int(86400 * (availability / 100)),
                "downtime_seconds": int(86400 * ((100 - availability) / 100)),
            },
        },
    }


def generate_aggregated_metrics(service_id, service_type):
    """Generate aggregated metrics for multiple time windows."""
    windows = [1, 7, 30, 90]
    aggregated = {}

    for window in windows:
        metrics_list = [generate_metrics_for_window(service_id, service_type, i) for i in range(window)]

        # Aggregate
        latencies_p95 = [m["metrics"]["latency"]["p95_ms"] for m in metrics_list]
        latencies_p99 = [m["metrics"]["latency"]["p99_ms"] for m in metrics_list]
        availabilities = [m["metrics"]["availability"]["percent"] for m in metrics_list]
        error_rates = [m["metrics"]["error_rate"]["percent"] for m in metrics_list]

        aggregated[f"{window}d"] = {
            "time_window": f"{window}d",
            "data_points": len(metrics_list),
            "latency": {
                "p50_ms": int(statistics.mean([m["metrics"]["latency"]["p50_ms"] for m in metrics_list])),
                "p95_ms": int(statistics.mean(latencies_p95)),
                "p99_ms": int(statistics.mean(latencies_p99)),
                "p95_stddev": int(statistics.stdev(latencies_p95)) if len(latencies_p95) > 1 else 0,
                "p99_stddev": int(statistics.stdev(latencies_p99)) if len(latencies_p99) > 1 else 0,
            },
            "error_rate": {
                "percent": round(statistics.mean(error_rates), 2),
                "stddev": round(statistics.stdev(error_rates), 2) if len(error_rates) > 1 else 0,
            },
            "availability": {
                "percent": round(statistics.mean(availabilities), 2),
                "stddev": round(statistics.stdev(availabilities), 2) if len(availabilities) > 1 else 0,
            },
        }

    return aggregated


def create_sample_services(data_dir):
    """Create sample service metadata and metrics."""
    services_dir = Path(data_dir) / "services"
    services_dir.mkdir(parents=True, exist_ok=True)

    print(f"Creating {len(SAMPLE_SERVICES)} sample services...")

    for service_id, service_type, team, criticality in SAMPLE_SERVICES:
        service_dir = services_dir / service_id
        service_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata
        metadata = generate_service_metadata(service_id, service_type, team, criticality)
        metadata_file = service_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"  ✓ {service_id}: metadata")

        # Create aggregated metrics
        aggregated_metrics = generate_aggregated_metrics(service_id, service_type)
        metrics_file = service_dir / "metrics_aggregated.json"
        with open(metrics_file, "w") as f:
            json.dump(aggregated_metrics, f, indent=2)
        print(f"  ✓ {service_id}: aggregated metrics")

        # Create raw metrics directory
        metrics_dir = service_dir / "metrics"
        metrics_dir.mkdir(exist_ok=True)


def create_dependency_graph(data_dir):
    """Create realistic dependency graph."""
    deps_dir = Path(data_dir) / "dependencies"
    deps_dir.mkdir(parents=True, exist_ok=True)

    print("\nCreating dependency graph...")

    # Build graph structure
    graph = {
        "services": [],
        "dependencies": [],
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "total_services": len(SAMPLE_SERVICES),
            "total_edges": sum(len(deps) for deps in DEPENDENCIES.values()),
        },
    }

    # Add services
    for service_id, _, _, _ in SAMPLE_SERVICES:
        graph["services"].append({"service_id": service_id})

    # Add dependencies
    for source, targets in DEPENDENCIES.items():
        for target in targets:
            graph["dependencies"].append(
                {
                    "source": source,
                    "target": target,
                    "dependency_type": "synchronous" if random.random() > 0.3 else "asynchronous",
                    "timeout_ms": random.randint(100, 5000),
                    "criticality": random.choice(["high", "medium", "low"]),
                }
            )

    # Save graph
    graph_file = deps_dir / "graph.json"
    with open(graph_file, "w") as f:
        json.dump(graph, f, indent=2)
    print(f"  ✓ Dependency graph: {len(graph['services'])} services, {len(graph['dependencies'])} edges")


def create_knowledge_base(data_dir):
    """Create sample knowledge base content."""
    kb_dir = Path(data_dir) / "knowledge"
    kb_dir.mkdir(parents=True, exist_ok=True)

    print("\nCreating knowledge base...")

    # Create runbooks
    runbooks_dir = kb_dir / "runbooks"
    runbooks_dir.mkdir(exist_ok=True)

    runbooks = {
        "api-gateway-slos.md": """# API Gateway SLO Recommendations

## Overview
API gateways are critical entry points that aggregate multiple downstream services.
Their SLOs must account for the weakest link in the dependency chain.

## Recommended Ranges
- **Availability**: 99.9% - 99.99%
- **Latency p95**: 50ms - 200ms (excluding downstream calls)
- **Latency p99**: 100ms - 500ms
- **Error Rate**: 0.1% - 0.5%

## Key Considerations
1. **Dependency Aggregation**: If calling N services in parallel, availability = product of all availabilities
2. **Timeout Strategy**: Set timeouts to 2x p99 latency of slowest dependency
3. **Circuit Breakers**: Implement for all downstream calls
4. **Rate Limiting**: Protect downstream services from overload

## Common Pitfalls
- Setting availability higher than any downstream service
- Not accounting for network latency (add 5-10ms overhead)
- Ignoring authentication service latency
""",
        "database-slos.md": """# Database SLO Recommendations

## Overview
Databases are critical infrastructure components that support multiple services.
Their SLOs directly impact all dependent services.

## Recommended Ranges
- **Availability**: 99.95% - 99.99%
- **Latency p95**: 10ms - 100ms
- **Latency p99**: 50ms - 500ms
- **Error Rate**: 0.01% - 0.1%

## Key Considerations
1. **Replication**: Multi-region replication improves availability
2. **Backup Strategy**: Regular backups don't impact SLO but enable recovery
3. **Connection Pooling**: Reduces latency variance
4. **Query Optimization**: Critical for maintaining latency SLOs

## Common Pitfalls
- Underestimating query latency at scale
- Not accounting for backup windows
- Insufficient connection pool size
""",
        "message-queue-slos.md": """# Message Queue SLO Recommendations

## Overview
Message queues enable asynchronous processing and decouple services.
Their SLOs affect both throughput and latency of async workflows.

## Recommended Ranges
- **Availability**: 99.9% - 99.95%
- **Latency p95**: 100ms - 500ms
- **Latency p99**: 500ms - 2000ms
- **Error Rate**: 0.1% - 0.5%

## Key Considerations
1. **Throughput**: Ensure queue can handle peak load
2. **Message Retention**: Balance between durability and performance
3. **Consumer Lag**: Monitor to detect processing bottlenecks
4. **Dead Letter Queues**: Handle failed messages gracefully

## Common Pitfalls
- Underestimating message volume
- Not implementing dead letter queue handling
- Insufficient consumer scaling
""",
    }

    for filename, content in runbooks.items():
        with open(runbooks_dir / filename, "w") as f:
            f.write(content)
    print(f"  ✓ Created {len(runbooks)} runbooks")

    # Create best practices
    best_practices = {
        "service_types": {
            "api_gateway": {
                "availability": {"min": 99.9, "typical": 99.95, "max": 99.99},
                "latency_p95_ms": {"min": 50, "typical": 100, "max": 200},
                "error_rate_percent": {"max": 0.5, "typical": 0.1},
            },
            "database": {
                "availability": {"min": 99.95, "typical": 99.99, "max": 99.99},
                "latency_p95_ms": {"min": 10, "typical": 50, "max": 100},
                "error_rate_percent": {"max": 0.1, "typical": 0.01},
            },
            "cache": {
                "availability": {"min": 99.9, "typical": 99.95, "max": 99.99},
                "latency_p95_ms": {"min": 1, "typical": 5, "max": 20},
                "error_rate_percent": {"max": 0.5, "typical": 0.05},
            },
            "message_queue": {
                "availability": {"min": 99.9, "typical": 99.95, "max": 99.99},
                "latency_p95_ms": {"min": 100, "typical": 200, "max": 500},
                "error_rate_percent": {"max": 0.5, "typical": 0.1},
            },
        },
        "general_principles": [
            "SLOs should be based on historical performance, not aspirational targets",
            "Always account for dependencies when setting SLOs",
            "Conservative SLOs are better than aggressive ones that are frequently missed",
            "Review and adjust SLOs quarterly based on actual performance",
            "Communicate SLOs clearly to all stakeholders",
        ],
    }

    with open(kb_dir / "best_practices.json", "w") as f:
        json.dump(best_practices, f, indent=2)
    print(f"  ✓ Created best practices")

    # Create historical patterns
    patterns = {
        "successful_patterns": [
            {
                "service_type": "api_gateway",
                "availability": 99.95,
                "latency_p95_ms": 120,
                "error_rate_percent": 0.15,
                "notes": "Stable performance with good dependency management",
            },
            {
                "service_type": "database",
                "availability": 99.99,
                "latency_p95_ms": 45,
                "error_rate_percent": 0.02,
                "notes": "Excellent performance with proper indexing",
            },
        ],
        "common_issues": [
            {
                "issue": "Latency spike",
                "cause": "Unoptimized query",
                "resolution": "Add database index",
                "prevention": "Regular query analysis",
            },
            {
                "issue": "Availability drop",
                "cause": "Dependency failure",
                "resolution": "Implement circuit breaker",
                "prevention": "Chaos engineering tests",
            },
        ],
    }

    with open(kb_dir / "historical_patterns.json", "w") as f:
        json.dump(patterns, f, indent=2)
    print(f"  ✓ Created historical patterns")


def create_api_keys(data_dir):
    """Create sample API keys for testing."""
    api_keys = {
        "api_keys": [
            {
                "key": "test-key-demo-tenant",
                "tenant_id": "demo-tenant",
                "created_at": datetime.now().isoformat(),
                "rate_limit": 100,
                "description": "Demo tenant for testing",
            },
            {
                "key": "test-key-acme-corp",
                "tenant_id": "acme-corp",
                "created_at": datetime.now().isoformat(),
                "rate_limit": 500,
                "description": "ACME Corporation production key",
            },
            {
                "key": "test-key-startup-inc",
                "tenant_id": "startup-inc",
                "created_at": datetime.now().isoformat(),
                "rate_limit": 100,
                "description": "Startup Inc development key",
            },
        ]
    }

    api_keys_file = Path(data_dir) / "api_keys.json"
    with open(api_keys_file, "w") as f:
        json.dump(api_keys, f, indent=2)
    print(f"\nCreated {len(api_keys['api_keys'])} sample API keys")


def main():
    """Generate all sample data."""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SLO Recommendation System - Sample Data Generator")
    print("=" * 60)

    create_sample_services(str(data_dir))
    create_dependency_graph(str(data_dir))
    create_knowledge_base(str(data_dir))
    create_api_keys(str(data_dir))

    print("\n" + "=" * 60)
    print("✓ Sample data generation complete!")
    print("=" * 60)
    print(f"\nData directory: {data_dir}")
    print(f"Services: {len(SAMPLE_SERVICES)}")
    print(f"Dependencies: {sum(len(deps) for deps in DEPENDENCIES.values())}")
    print("\nNext steps:")
    print("1. Start Ollama: ollama serve")
    print("2. Run the API: uvicorn src.api.gateway:app --reload")
    print("3. Test the API: curl http://localhost:8000/health")


if __name__ == "__main__":
    main()

"""Example demonstrating critical path computation."""

from src.algorithms.service_graph import ServiceGraph
from src.models.dependency import DependencyEdge


def main():
    """Demonstrate critical path computation with a realistic service graph."""
    
    # Create a service graph
    graph = ServiceGraph()
    
    # Build a realistic microservices graph:
    # API Gateway -> Auth Service -> User DB
    #             -> Payment Service -> Payment DB
    #             -> Notification Service
    
    print("Building service dependency graph...")
    
    # API Gateway dependencies
    graph.add_edge("api-gateway", "auth-service", DependencyEdge(
        target_service_id="auth-service",
        dependency_type="synchronous",
        criticality="high",
        timeout_ms=500
    ))
    graph.add_edge("api-gateway", "payment-service", DependencyEdge(
        target_service_id="payment-service",
        dependency_type="synchronous",
        criticality="high",
        timeout_ms=1000
    ))
    graph.add_edge("api-gateway", "notification-service", DependencyEdge(
        target_service_id="notification-service",
        dependency_type="asynchronous",
        criticality="low",
        timeout_ms=200
    ))
    
    # Auth Service dependencies
    graph.add_edge("auth-service", "user-db", DependencyEdge(
        target_infrastructure_id="user-db",
        infrastructure_type="postgresql",
        dependency_type="synchronous",
        criticality="high",
        timeout_ms=100
    ))
    
    # Payment Service dependencies
    graph.add_edge("payment-service", "payment-db", DependencyEdge(
        target_infrastructure_id="payment-db",
        infrastructure_type="postgresql",
        dependency_type="synchronous",
        criticality="high",
        timeout_ms=150
    ))
    
    print(f"Graph: {graph}")
    print()
    
    # Define service latencies (p95 in milliseconds)
    latencies = {
        "api-gateway": 10.0,
        "auth-service": 50.0,
        "payment-service": 120.0,
        "notification-service": 30.0,
        "user-db": 45.0,
        "payment-db": 80.0
    }
    
    print("Service Latencies (p95 ms):")
    for service, latency in sorted(latencies.items()):
        print(f"  {service}: {latency}ms")
    print()
    
    # Compute critical path from API Gateway
    print("Computing critical path from api-gateway...")
    result = graph.compute_critical_path("api-gateway", latencies)
    
    print("\nCritical Path Analysis:")
    print(f"  Path: {' -> '.join(result['path'])}")
    print(f"  Total Latency: {result['total_latency_ms']}ms")
    print(f"  Bottleneck Service: {result['bottleneck_service']}")
    print()
    
    # Compute critical paths for other services
    print("Critical paths for other services:")
    for service in ["auth-service", "payment-service", "notification-service"]:
        result = graph.compute_critical_path(service, latencies)
        if result['path']:
            print(f"\n  {service}:")
            print(f"    Path: {' -> '.join(result['path'])}")
            print(f"    Total Latency: {result['total_latency_ms']}ms")
            print(f"    Bottleneck: {result['bottleneck_service']}")
    
    print("\n" + "="*60)
    print("Analysis Summary:")
    print("="*60)
    print("The critical path from api-gateway is through payment-service")
    print("to payment-db, with a total latency of 210ms.")
    print("The payment-service is the bottleneck with 120ms latency.")
    print("\nThis information can be used to:")
    print("  1. Set realistic SLO targets for the API Gateway")
    print("  2. Identify optimization opportunities (payment-service)")
    print("  3. Allocate latency budgets across the dependency chain")


if __name__ == "__main__":
    main()

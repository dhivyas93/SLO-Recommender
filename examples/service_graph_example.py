"""Example usage of ServiceGraph class."""

from src.algorithms.service_graph import ServiceGraph
from src.models.dependency import DependencyEdge


def main():
    """Demonstrate ServiceGraph usage with a realistic microservices example."""
    
    # Create a new service graph
    graph = ServiceGraph()
    
    print("Building service dependency graph...")
    print()
    
    # Example: API Gateway -> Auth Service -> User DB
    #                      -> Payment Service -> Payment DB
    
    # Add edge: API Gateway -> Auth Service
    auth_edge = DependencyEdge(
        target_service_id="auth-service",
        dependency_type="synchronous",
        timeout_ms=500,
        retry_policy="exponential_backoff",
        criticality="high"
    )
    graph.add_edge("api-gateway", "auth-service", auth_edge)
    
    # Add edge: API Gateway -> Payment Service
    payment_edge = DependencyEdge(
        target_service_id="payment-service",
        dependency_type="synchronous",
        timeout_ms=1000,
        criticality="high"
    )
    graph.add_edge("api-gateway", "payment-service", payment_edge)
    
    # Add edge: Auth Service -> User DB (infrastructure)
    user_db_edge = DependencyEdge(
        target_infrastructure_id="user-db",
        infrastructure_type="postgresql",
        dependency_type="synchronous",
        criticality="high"
    )
    graph.add_edge("auth-service", "user-db", user_db_edge)
    
    # Add edge: Payment Service -> Payment DB (infrastructure)
    payment_db_edge = DependencyEdge(
        target_infrastructure_id="payment-db",
        infrastructure_type="postgresql",
        dependency_type="synchronous",
        criticality="high"
    )
    graph.add_edge("payment-service", "payment-db", payment_db_edge)
    
    # Add edge: Payment Service -> Fraud Detection (async)
    fraud_edge = DependencyEdge(
        target_service_id="fraud-detection",
        dependency_type="asynchronous",
        criticality="medium"
    )
    graph.add_edge("payment-service", "fraud-detection", fraud_edge)
    
    # Print graph statistics
    print(f"Graph: {graph}")
    print()
    
    print(f"Total nodes: {graph.get_node_count()}")
    print(f"Total edges: {graph.get_edge_count()}")
    print(f"Service nodes: {len(graph.get_service_nodes())}")
    print(f"Infrastructure nodes: {len(graph.get_infrastructure_nodes())}")
    print()
    
    # Query downstream dependencies
    print("Downstream dependencies:")
    for service in ["api-gateway", "auth-service", "payment-service"]:
        downstream = graph.get_downstream_services(service)
        print(f"  {service} -> {downstream}")
    print()
    
    # Query upstream dependencies
    print("Upstream dependencies:")
    for service in ["auth-service", "payment-service", "user-db", "payment-db"]:
        upstream = graph.get_upstream_services(service)
        print(f"  {service} <- {upstream}")
    print()
    
    # Get edge metadata
    print("Edge metadata example:")
    metadata = graph.get_edge_metadata("api-gateway", "auth-service")
    if metadata:
        print(f"  api-gateway -> auth-service:")
        print(f"    Type: {metadata.dependency_type}")
        print(f"    Timeout: {metadata.timeout_ms}ms")
        print(f"    Criticality: {metadata.criticality}")
    print()
    
    # List all services and infrastructure
    print("All services:")
    for service in sorted(graph.get_service_nodes()):
        print(f"  - {service}")
    print()
    
    print("All infrastructure:")
    for infra in sorted(graph.get_infrastructure_nodes()):
        print(f"  - {infra}")


if __name__ == "__main__":
    main()

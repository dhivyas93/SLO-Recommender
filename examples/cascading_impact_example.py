"""
Example demonstrating cascading impact score computation.

This example shows how to compute cascading impact scores for services
in a microservices dependency graph.
"""

from src.algorithms.service_graph import ServiceGraph
from src.models.dependency import DependencyEdge


def main():
    """Demonstrate cascading impact score computation."""
    
    # Create a realistic microservices architecture
    graph = ServiceGraph()
    
    print("Building Microservices Dependency Graph")
    print("=" * 70)
    
    # Architecture:
    # api-gateway -> auth-service -> user-db
    #             -> payment-service -> payment-db
    #             -> order-service -> order-db
    #                              -> inventory-service -> inventory-db
    
    dependencies = [
        ("api-gateway", "auth-service", "service"),
        ("api-gateway", "payment-service", "service"),
        ("api-gateway", "order-service", "service"),
        ("auth-service", "user-db", "infrastructure"),
        ("payment-service", "payment-db", "infrastructure"),
        ("order-service", "order-db", "infrastructure"),
        ("order-service", "inventory-service", "service"),
        ("inventory-service", "inventory-db", "infrastructure"),
    ]
    
    for source, target, target_type in dependencies:
        if target_type == "service":
            edge = DependencyEdge(
                target_service_id=target,
                dependency_type="synchronous",
                criticality="high"
            )
        else:
            edge = DependencyEdge(
                target_infrastructure_id=target,
                infrastructure_type="postgresql",
                dependency_type="synchronous",
                criticality="high"
            )
        graph.add_edge(source, target, edge)
        print(f"  {source} -> {target}")
    
    print(f"\nGraph Statistics:")
    print(f"  Total nodes: {graph.get_node_count()}")
    print(f"  Service nodes: {len(graph.get_service_nodes())}")
    print(f"  Infrastructure nodes: {len(graph.get_infrastructure_nodes())}")
    print(f"  Total edges: {graph.get_edge_count()}")
    
    # Compute cascading impact scores
    print("\n" + "=" * 70)
    print("Cascading Impact Scores")
    print("=" * 70)
    print(f"{'Service':<30} {'Score':<10} {'Downstream':<15} {'Impact Level'}")
    print("-" * 70)
    
    services = [
        "api-gateway",
        "auth-service",
        "payment-service",
        "order-service",
        "inventory-service",
    ]
    
    for service in services:
        score = graph.compute_cascading_impact_score(service)
        downstream_count = len(graph.get_downstream_services(service))
        
        # Determine impact level
        if score == 0.0:
            impact_level = "None (Leaf)"
        elif score < 0.5:
            impact_level = "Low"
        elif score < 0.8:
            impact_level = "Medium"
        else:
            impact_level = "High"
        
        print(f"{service:<30} {score:<10.3f} {downstream_count:<15} {impact_level}")
    
    # Detailed analysis
    print("\n" + "=" * 70)
    print("Impact Analysis")
    print("=" * 70)
    
    # API Gateway analysis
    api_score = graph.compute_cascading_impact_score("api-gateway")
    api_downstream = graph.get_downstream_services("api-gateway")
    print(f"\napi-gateway (Score: {api_score:.3f}):")
    print(f"  - Directly depends on {len(api_downstream)} services")
    print(f"  - Affects all downstream services transitively")
    print(f"  - Critical service: failure impacts entire system")
    print(f"  - Recommendation: Set aggressive SLOs (99.9%+ availability)")
    
    # Order Service analysis
    order_score = graph.compute_cascading_impact_score("order-service")
    order_downstream = graph.get_downstream_services("order-service")
    print(f"\norder-service (Score: {order_score:.3f}):")
    print(f"  - Directly depends on {len(order_downstream)} services/infrastructure")
    print(f"  - Has deeper dependency chain than auth/payment")
    print(f"  - Moderate impact: affects inventory subsystem")
    print(f"  - Recommendation: Set balanced SLOs (99.5% availability)")
    
    # Inventory Service analysis
    inv_score = graph.compute_cascading_impact_score("inventory-service")
    inv_downstream = graph.get_downstream_services("inventory-service")
    print(f"\ninventory-service (Score: {inv_score:.3f}):")
    print(f"  - Directly depends on {len(inv_downstream)} infrastructure")
    print(f"  - Leaf service in the dependency chain")
    print(f"  - Lower impact: only affects inventory operations")
    print(f"  - Recommendation: Set conservative SLOs (99.0% availability)")
    
    print("\n" + "=" * 70)
    print("Key Insights")
    print("=" * 70)
    print("1. Services with higher cascading impact scores should have:")
    print("   - More aggressive SLO targets")
    print("   - Higher monitoring priority")
    print("   - More robust error handling")
    print("   - Better redundancy and failover")
    print("\n2. The cascading impact score helps prioritize:")
    print("   - Which services to optimize first")
    print("   - Where to invest in reliability improvements")
    print("   - How to allocate SRE resources")
    print("\n3. Formula: Σ (1 / depth) * (1 / fanout) for all downstream services")
    print("   - Closer services have higher weight (1/depth)")
    print("   - Services with fewer siblings have higher weight (1/fanout)")
    print("   - Score normalized to [0, 1] range")


if __name__ == "__main__":
    main()

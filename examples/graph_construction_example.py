"""Example demonstrating graph construction from dependency declarations."""

from datetime import datetime
from src.algorithms.service_graph import ServiceGraph
from src.models.dependency import (
    ServiceDependency,
    DependencyEdge,
    DependencyGraph
)


def example_build_from_declarations():
    """Example: Build graph from a list of ServiceDependency objects."""
    print("=" * 70)
    print("Example 1: Building graph from dependency declarations")
    print("=" * 70)
    print()
    
    # Create dependency declarations
    declarations = [
        ServiceDependency(
            service_id="api-gateway",
            dependencies=[
                DependencyEdge(
                    target_service_id="auth-service",
                    dependency_type="synchronous",
                    timeout_ms=500,
                    retry_policy="exponential_backoff",
                    criticality="high"
                ),
                DependencyEdge(
                    target_service_id="payment-service",
                    dependency_type="synchronous",
                    timeout_ms=1000,
                    criticality="high"
                )
            ]
        ),
        ServiceDependency(
            service_id="auth-service",
            dependencies=[
                DependencyEdge(
                    target_infrastructure_id="user-db",
                    infrastructure_type="postgresql",
                    dependency_type="synchronous",
                    criticality="high"
                ),
                DependencyEdge(
                    target_infrastructure_id="redis-cache",
                    infrastructure_type="redis",
                    dependency_type="synchronous",
                    criticality="medium"
                )
            ]
        ),
        ServiceDependency(
            service_id="payment-service",
            dependencies=[
                DependencyEdge(
                    target_infrastructure_id="payment-db",
                    infrastructure_type="postgresql",
                    dependency_type="synchronous",
                    criticality="high"
                ),
                DependencyEdge(
                    target_service_id="fraud-detection",
                    dependency_type="asynchronous",
                    criticality="medium"
                )
            ]
        ),
        ServiceDependency(
            service_id="fraud-detection",
            dependencies=[]
        )
    ]
    
    # Build the graph
    graph = ServiceGraph()
    warnings = graph.build_from_declarations(declarations)
    
    # Display results
    print(f"Graph built: {graph}")
    print()
    
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        print()
    else:
        print("No warnings - graph built successfully!")
        print()
    
    # Display graph structure
    print("Services:")
    for service in sorted(graph.get_service_nodes()):
        downstream = graph.get_downstream_services(service)
        upstream = graph.get_upstream_services(service)
        print(f"  {service}:")
        print(f"    Upstream: {upstream if upstream else 'None (root)'}")
        print(f"    Downstream: {downstream if downstream else 'None (leaf)'}")
    
    print()
    print("Infrastructure:")
    for infra in sorted(graph.get_infrastructure_nodes()):
        upstream = graph.get_upstream_services(infra)
        print(f"  {infra}:")
        print(f"    Used by: {upstream}")
    
    print()


def example_build_from_dependency_graph():
    """Example: Build graph from a DependencyGraph object."""
    print("=" * 70)
    print("Example 2: Building graph from DependencyGraph object")
    print("=" * 70)
    print()
    
    # Create a DependencyGraph object
    dependency_graph = DependencyGraph(
        version="1.0.0",
        updated_at=datetime.now(),
        services=[
            ServiceDependency(
                service_id="web-frontend",
                dependencies=[
                    DependencyEdge(
                        target_service_id="api-gateway",
                        dependency_type="synchronous",
                        timeout_ms=3000,
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(
                service_id="api-gateway",
                dependencies=[
                    DependencyEdge(
                        target_service_id="user-service",
                        dependency_type="synchronous",
                        criticality="high"
                    ),
                    DependencyEdge(
                        target_service_id="product-service",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(
                service_id="user-service",
                dependencies=[
                    DependencyEdge(
                        target_infrastructure_id="user-db",
                        infrastructure_type="postgresql",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            ),
            ServiceDependency(
                service_id="product-service",
                dependencies=[
                    DependencyEdge(
                        target_infrastructure_id="product-db",
                        infrastructure_type="mongodb",
                        dependency_type="synchronous",
                        criticality="high"
                    )
                ]
            )
        ]
    )
    
    # Build the graph
    graph = ServiceGraph()
    warnings = graph.build_from_dependency_graph(dependency_graph)
    
    # Display results
    print(f"Graph version: {dependency_graph.version}")
    print(f"Updated at: {dependency_graph.updated_at}")
    print(f"Graph built: {graph}")
    print()
    
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("No warnings - graph built successfully!")
    
    print()


def example_missing_dependencies():
    """Example: Handling missing dependencies with warnings."""
    print("=" * 70)
    print("Example 3: Handling missing dependencies")
    print("=" * 70)
    print()
    
    # Create declarations with missing dependencies
    declarations = [
        ServiceDependency(
            service_id="service-a",
            dependencies=[
                DependencyEdge(
                    target_service_id="service-b",
                    dependency_type="synchronous",
                    criticality="high"
                ),
                DependencyEdge(
                    target_service_id="service-c",
                    dependency_type="synchronous",
                    criticality="medium"
                )
            ]
        )
        # Note: service-b and service-c are not declared
    ]
    
    # Build the graph
    graph = ServiceGraph()
    warnings = graph.build_from_declarations(declarations)
    
    # Display results
    print(f"Graph built: {graph}")
    print()
    
    print("Warnings (missing dependencies):")
    for warning in warnings:
        print(f"  - {warning}")
    
    print()
    print("Graph still constructed with missing services:")
    print(f"  All nodes: {sorted(graph.get_all_nodes())}")
    print(f"  Edges: service-a -> {graph.get_downstream_services('service-a')}")
    
    print()


def example_complex_topology():
    """Example: Complex graph with multiple patterns."""
    print("=" * 70)
    print("Example 4: Complex topology with fan-out and fan-in")
    print("=" * 70)
    print()
    
    declarations = [
        # API Gateway fans out to multiple services
        ServiceDependency(
            service_id="api-gateway",
            dependencies=[
                DependencyEdge(
                    target_service_id="auth-service",
                    dependency_type="synchronous",
                    criticality="high"
                ),
                DependencyEdge(
                    target_service_id="user-service",
                    dependency_type="synchronous",
                    criticality="high"
                ),
                DependencyEdge(
                    target_service_id="order-service",
                    dependency_type="synchronous",
                    criticality="high"
                )
            ]
        ),
        # Multiple services fan in to shared database
        ServiceDependency(
            service_id="auth-service",
            dependencies=[
                DependencyEdge(
                    target_infrastructure_id="shared-db",
                    infrastructure_type="postgresql",
                    dependency_type="synchronous",
                    criticality="high"
                )
            ]
        ),
        ServiceDependency(
            service_id="user-service",
            dependencies=[
                DependencyEdge(
                    target_infrastructure_id="shared-db",
                    infrastructure_type="postgresql",
                    dependency_type="synchronous",
                    criticality="high"
                )
            ]
        ),
        ServiceDependency(
            service_id="order-service",
            dependencies=[
                DependencyEdge(
                    target_infrastructure_id="shared-db",
                    infrastructure_type="postgresql",
                    dependency_type="synchronous",
                    criticality="high"
                ),
                DependencyEdge(
                    target_service_id="payment-service",
                    dependency_type="synchronous",
                    criticality="high"
                )
            ]
        ),
        ServiceDependency(
            service_id="payment-service",
            dependencies=[]
        )
    ]
    
    # Build the graph
    graph = ServiceGraph()
    warnings = graph.build_from_declarations(declarations)
    
    # Display results
    print(f"Graph built: {graph}")
    print()
    
    # Analyze fan-out
    print("Fan-out analysis (api-gateway):")
    downstream = graph.get_downstream_services("api-gateway")
    print(f"  api-gateway -> {len(downstream)} services: {downstream}")
    
    print()
    
    # Analyze fan-in
    print("Fan-in analysis (shared-db):")
    upstream = graph.get_upstream_services("shared-db")
    print(f"  shared-db <- {len(upstream)} services: {upstream}")
    
    print()


def main():
    """Run all examples."""
    example_build_from_declarations()
    print()
    
    example_build_from_dependency_graph()
    print()
    
    example_missing_dependencies()
    print()
    
    example_complex_topology()


if __name__ == "__main__":
    main()

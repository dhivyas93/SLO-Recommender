"""
Example demonstrating missing dependency detection and warning management.

This example shows:
1. Building a graph with missing dependencies
2. Generating structured warnings
3. Saving warnings to a file
4. Loading warnings from a file
5. Analyzing warning patterns
"""

from datetime import datetime
from src.algorithms.service_graph import ServiceGraph
from src.algorithms.graph_warnings import save_warnings_to_file, load_warnings_from_file
from src.models.dependency import ServiceDependency, DependencyEdge, WarningType


def example_1_missing_dependencies():
    """Example 1: Detect missing dependencies."""
    print("=" * 80)
    print("Example 1: Missing Dependency Detection")
    print("=" * 80)
    
    graph = ServiceGraph()
    
    # Create declarations with missing dependencies
    declarations = [
        ServiceDependency(
            service_id="api-gateway",
            dependencies=[
                DependencyEdge(
                    target_service_id="auth-service",  # Not declared
                    dependency_type="synchronous",
                    criticality="high"
                ),
                DependencyEdge(
                    target_service_id="payment-service",  # Not declared
                    dependency_type="synchronous",
                    criticality="high"
                )
            ]
        ),
        ServiceDependency(
            service_id="user-service",
            dependencies=[
                DependencyEdge(
                    target_service_id="auth-service",  # Not declared
                    dependency_type="synchronous",
                    criticality="high"
                )
            ]
        )
    ]
    
    # Build graph and collect warnings
    warnings = graph.build_from_declarations(declarations)
    
    print(f"\nGraph built with {graph.get_node_count()} nodes and {graph.get_edge_count()} edges")
    print(f"Generated {len(warnings)} warnings:\n")
    
    for i, warning in enumerate(warnings, 1):
        print(f"{i}. Type: {warning.warning_type.value}")
        print(f"   Service: {warning.service_id}")
        if warning.target_id:
            print(f"   Target: {warning.target_id}")
        print(f"   Message: {warning.message}")
        print()


def example_2_isolated_nodes():
    """Example 2: Detect isolated nodes."""
    print("=" * 80)
    print("Example 2: Isolated Node Detection")
    print("=" * 80)
    
    graph = ServiceGraph()
    
    # Create declarations with isolated services
    declarations = [
        ServiceDependency(
            service_id="api-gateway",
            dependencies=[
                DependencyEdge(
                    target_service_id="auth-service",
                    dependency_type="synchronous",
                    criticality="high"
                )
            ]
        ),
        ServiceDependency(
            service_id="auth-service",
            dependencies=[]
        ),
        ServiceDependency(
            service_id="standalone-batch-job",  # Isolated
            dependencies=[]
        ),
        ServiceDependency(
            service_id="orphaned-service",  # Isolated
            dependencies=[]
        )
    ]
    
    warnings = graph.build_from_declarations(declarations)
    
    print(f"\nGraph built with {graph.get_node_count()} nodes")
    print(f"Generated {len(warnings)} warnings:\n")
    
    isolated_warnings = [w for w in warnings if w.warning_type == WarningType.ISOLATED_NODE]
    print(f"Found {len(isolated_warnings)} isolated nodes:")
    for warning in isolated_warnings:
        print(f"  - {warning.service_id}")
    print()


def example_3_no_target_dependencies():
    """Example 3: Detect dependencies with no target."""
    print("=" * 80)
    print("Example 3: No Target Detection")
    print("=" * 80)
    
    graph = ServiceGraph()
    
    # Create declarations with malformed dependencies
    declarations = [
        ServiceDependency(
            service_id="broken-service",
            dependencies=[
                DependencyEdge(
                    # Missing both target_service_id and target_infrastructure_id
                    dependency_type="synchronous",
                    criticality="high"
                )
            ]
        )
    ]
    
    warnings = graph.build_from_declarations(declarations)
    
    print(f"\nGenerated {len(warnings)} warnings:\n")
    
    for warning in warnings:
        print(f"Type: {warning.warning_type.value}")
        print(f"Service: {warning.service_id}")
        print(f"Message: {warning.message}")
        print()


def example_4_save_and_load_warnings():
    """Example 4: Save and load warnings."""
    print("=" * 80)
    print("Example 4: Save and Load Warnings")
    print("=" * 80)
    
    graph = ServiceGraph()
    
    # Build graph with various issues
    declarations = [
        ServiceDependency(
            service_id="api-gateway",
            dependencies=[
                DependencyEdge(
                    target_service_id="missing-service",
                    dependency_type="synchronous",
                    criticality="high"
                )
            ]
        ),
        ServiceDependency(
            service_id="isolated-service",
            dependencies=[]
        )
    ]
    
    warnings = graph.build_from_declarations(declarations)
    
    print(f"\nGenerated {len(warnings)} warnings")
    
    # Save warnings to file
    warnings_file = "dependencies/graph_warnings.json"
    save_warnings_to_file(warnings, warnings_file)
    print(f"Saved warnings to: {warnings_file}")
    
    # Load warnings back
    loaded_warnings = load_warnings_from_file(warnings_file)
    print(f"Loaded {len(loaded_warnings)} warnings from file")
    
    print("\nLoaded warnings:")
    for warning in loaded_warnings:
        print(f"  - {warning.warning_type.value}: {warning.service_id}")
    print()


def example_5_warning_analysis():
    """Example 5: Analyze warning patterns."""
    print("=" * 80)
    print("Example 5: Warning Pattern Analysis")
    print("=" * 80)
    
    graph = ServiceGraph()
    
    # Build a complex graph with multiple issues
    declarations = [
        ServiceDependency(
            service_id="api-gateway",
            dependencies=[
                DependencyEdge(
                    target_service_id="auth-service",
                    dependency_type="synchronous",
                    criticality="high"
                ),
                DependencyEdge(
                    target_service_id="missing-service-1",
                    dependency_type="synchronous",
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
                )
            ]
        ),
        ServiceDependency(
            service_id="payment-service",
            dependencies=[
                DependencyEdge(
                    target_service_id="missing-service-2",
                    dependency_type="synchronous",
                    criticality="high"
                )
            ]
        ),
        ServiceDependency(
            service_id="isolated-service-1",
            dependencies=[]
        ),
        ServiceDependency(
            service_id="isolated-service-2",
            dependencies=[]
        )
    ]
    
    warnings = graph.build_from_declarations(declarations)
    
    print(f"\nGraph Statistics:")
    print(f"  Total nodes: {graph.get_node_count()}")
    print(f"  Service nodes: {len(graph.get_service_nodes())}")
    print(f"  Infrastructure nodes: {len(graph.get_infrastructure_nodes())}")
    print(f"  Total edges: {graph.get_edge_count()}")
    print(f"  Total warnings: {len(warnings)}")
    
    # Analyze warnings by type
    print("\nWarning Breakdown:")
    warning_counts = {}
    for warning in warnings:
        warning_type = warning.warning_type.value
        warning_counts[warning_type] = warning_counts.get(warning_type, 0) + 1
    
    for warning_type, count in warning_counts.items():
        print(f"  {warning_type}: {count}")
    
    # List services with issues
    print("\nServices with Missing Dependencies:")
    missing_dep_warnings = [w for w in warnings if w.warning_type == WarningType.MISSING_DEPENDENCY]
    for warning in missing_dep_warnings:
        print(f"  {warning.service_id} -> {warning.target_id}")
    
    print("\nIsolated Services:")
    isolated_warnings = [w for w in warnings if w.warning_type == WarningType.ISOLATED_NODE]
    for warning in isolated_warnings:
        print(f"  {warning.service_id}")
    
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("MISSING DEPENDENCY DETECTION AND WARNING MANAGEMENT EXAMPLES")
    print("=" * 80 + "\n")
    
    example_1_missing_dependencies()
    example_2_isolated_nodes()
    example_3_no_target_dependencies()
    example_4_save_and_load_warnings()
    example_5_warning_analysis()
    
    print("=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()

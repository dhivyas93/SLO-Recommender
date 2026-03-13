# ServiceGraph Class Documentation

## Overview

The `ServiceGraph` class provides an efficient adjacency list representation for modeling service dependency graphs in the SLO Recommendation System. It supports both service-to-service and service-to-infrastructure dependencies.

## Features

- **Adjacency List Representation**: Efficient O(1) edge addition and O(k) neighbor queries where k is the number of neighbors
- **Bidirectional Queries**: Fast upstream and downstream dependency lookups
- **Mixed Node Types**: Supports both service nodes and infrastructure nodes (databases, caches, queues)
- **Edge Metadata**: Stores rich dependency information (type, timeout, criticality, retry policy)
- **Graph Statistics**: Quick access to node counts, edge counts, and graph structure

## Usage

### Basic Example

```python
from src.algorithms.service_graph import ServiceGraph
from src.models.dependency import DependencyEdge

# Create a new graph
graph = ServiceGraph()

# Add a service-to-service dependency
edge = DependencyEdge(
    target_service_id="auth-service",
    dependency_type="synchronous",
    timeout_ms=500,
    criticality="high"
)
graph.add_edge("api-gateway", "auth-service", edge)

# Query downstream dependencies
downstream = graph.get_downstream_services("api-gateway")
print(downstream)  # ['auth-service']

# Query upstream dependencies
upstream = graph.get_upstream_services("auth-service")
print(upstream)  # ['api-gateway']
```

### Adding Infrastructure Dependencies

```python
# Add a service-to-infrastructure dependency
db_edge = DependencyEdge(
    target_infrastructure_id="postgres-db",
    infrastructure_type="postgresql",
    dependency_type="synchronous",
    criticality="high"
)
graph.add_edge("auth-service", "postgres-db", db_edge)

# Check node types
print(graph.get_service_nodes())        # {'api-gateway', 'auth-service'}
print(graph.get_infrastructure_nodes()) # {'postgres-db'}
```

## API Reference

### Node Operations

#### `add_node(node_id: str, is_infrastructure: bool = False) -> None`
Add a node to the graph.

**Parameters:**
- `node_id`: Unique identifier for the node
- `is_infrastructure`: Whether this node represents infrastructure (default: False)

#### `has_node(node_id: str) -> bool`
Check if a node exists in the graph.

#### `get_all_nodes() -> Set[str]`
Get all nodes (services and infrastructure).

#### `get_service_nodes() -> Set[str]`
Get only service nodes.

#### `get_infrastructure_nodes() -> Set[str]`
Get only infrastructure nodes.

#### `get_node_count() -> int`
Get the total number of nodes.

### Edge Operations

#### `add_edge(source_id: str, target_id: str, edge_metadata: DependencyEdge) -> None`
Add a directed edge (dependency) from source to target.

**Parameters:**
- `source_id`: Source service ID
- `target_id`: Target service or infrastructure ID
- `edge_metadata`: Dependency metadata

#### `has_edge(source_id: str, target_id: str) -> bool`
Check if an edge exists between two nodes.

#### `get_edge_metadata(source_id: str, target_id: str) -> Optional[DependencyEdge]`
Get the metadata for a specific edge.

#### `get_edge_count() -> int`
Get the total number of edges.

### Query Operations

#### `get_downstream_services(service_id: str) -> List[str]`
Get all direct downstream dependencies of a service.

**Returns:** List of downstream service/infrastructure IDs

#### `get_upstream_services(service_id: str) -> List[str]`
Get all direct upstream services that depend on this service.

**Returns:** List of upstream service IDs

### Analysis Operations

#### `compute_cascading_impact_score(service_id: str) -> float`
Compute cascading impact score for a service using BFS traversal.

The impact score measures how many downstream services are affected by this service, weighted by dependency depth and fanout. Services closer in the dependency chain and with fewer siblings have higher impact.

**Formula:** Σ (1 / depth) * (1 / fanout) for all downstream services

**Parameters:**
- `service_id`: Service identifier

**Returns:** Cascading impact score in range [0, 1]
- Returns 0.0 for services with no downstream dependencies (leaf nodes)
- Returns 0.0 for non-existent services
- Score is normalized to maximum of 1.0

**Example:**
```python
# Build a graph: A -> B -> C, A -> D
graph = ServiceGraph()
graph.add_edge("A", "B", edge1)
graph.add_edge("B", "C", edge2)
graph.add_edge("A", "D", edge3)

# Compute impact scores
score_a = graph.compute_cascading_impact_score("A")  # Highest impact
score_b = graph.compute_cascading_impact_score("B")  # Medium impact
score_c = graph.compute_cascading_impact_score("C")  # 0.0 (leaf node)
```

**Use Cases:**
- Identify critical services that affect many downstream services
- Prioritize SLO recommendations based on cascading impact
- Understand blast radius of service failures

### Utility Operations

#### `get_adjacency_list() -> Dict[str, List[Tuple[str, DependencyEdge]]]`
Get the internal adjacency list representation.

**Returns:** Dictionary mapping source_id to list of (target_id, edge_metadata) tuples

#### `get_reverse_adjacency_list() -> Dict[str, List[str]]`
Get the reverse adjacency list for upstream queries.

**Returns:** Dictionary mapping target_id to list of source_ids

#### `clear() -> None`
Clear all nodes and edges from the graph.

## Performance Characteristics

- **Add Node**: O(1)
- **Add Edge**: O(1)
- **Get Downstream**: O(k) where k is the number of downstream dependencies
- **Get Upstream**: O(k) where k is the number of upstream dependencies
- **Has Node**: O(1)
- **Has Edge**: O(k) where k is the number of edges from source
- **Space Complexity**: O(V + E) where V is nodes and E is edges

## Design Decisions

### Adjacency List vs Adjacency Matrix

We chose adjacency list representation because:
1. **Sparse Graphs**: Microservice dependency graphs are typically sparse (each service depends on a few others)
2. **Memory Efficiency**: O(V + E) space vs O(V²) for adjacency matrix
3. **Fast Neighbor Queries**: O(k) to get all neighbors vs O(V) for matrix
4. **Scalability**: Handles up to 10,000+ services efficiently

### Bidirectional Storage

We maintain both forward and reverse adjacency lists to enable:
- Fast downstream queries (who does this service depend on?)
- Fast upstream queries (who depends on this service?)
- Efficient cascading impact analysis

### Separate Infrastructure Tracking

Infrastructure nodes (databases, caches, queues) are tracked separately to:
- Distinguish between service and infrastructure dependencies
- Enable infrastructure-specific analysis
- Support different SLO constraints for infrastructure

## Integration with Dependency Analyzer

The ServiceGraph class is used by the Dependency Analyzer component to:
1. **Construct the graph** from dependency declarations
2. **Detect circular dependencies** using Tarjan's algorithm
3. **Compute critical paths** using modified Dijkstra's algorithm
4. **Calculate cascading impact scores** using BFS traversal

See `src/engines/dependency_analyzer.py` for the full integration.

## Testing

Comprehensive unit tests are available in `tests/unit/test_service_graph.py`:
- Basic node and edge operations
- Query operations (upstream/downstream)
- Complex topologies (chains, fan-out, fan-in)
- Edge cases (self-loops, parallel edges, empty IDs)

Run tests with:
```bash
pytest tests/unit/test_service_graph.py -v
```

## Example

See `examples/service_graph_example.py` for a complete working example.

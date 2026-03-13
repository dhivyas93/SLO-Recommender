# Developer Guide

This guide explains how to extend and modify the SLO Recommendation System.

## Project Structure

```
slo-recommendation-system/
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── gateway.py              # FastAPI application and endpoints
│   │   └── middleware.py           # Authentication, rate limiting
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── metrics_ingestion.py    # Metrics processing
│   │   ├── dependency_analyzer.py  # Graph algorithms
│   │   ├── recommendation_engine.py # SLO generation
│   │   ├── ai_reasoning.py         # LLM integration
│   │   ├── rag_engine.py           # Knowledge retrieval
│   │   └── evaluation_engine.py    # Quality metrics
│   ├── models/
│   │   ├── __init__.py
│   │   └── data_models.py          # Pydantic models
│   ├── storage/
│   │   ├── __init__.py
│   │   └── file_storage.py         # File I/O with locking
│   └── utils/
│       ├── __init__.py
│       ├── validators.py           # Input validation
│       ├── pii_detector.py         # PII detection
│       └── logger.py               # Logging setup
├── tests/
│   ├── unit/                       # Unit tests
│   ├── integration/                # Integration tests
│   └── property/                   # Property-based tests
├── data/
│   ├── services/                   # Service metadata and metrics
│   ├── dependencies/               # Dependency graphs
│   ├── recommendations/            # Generated recommendations
│   ├── knowledge/                  # Knowledge base
│   ├── audit_logs/                 # Audit trail
│   └── api_keys.json              # API key configuration
├── docs/
│   ├── API_DOCUMENTATION.md        # API reference
│   ├── DEVELOPER_GUIDE.md          # This file
│   └── DEPLOYMENT_GUIDE.md         # Deployment instructions
├── scripts/
│   ├── generate_sample_data.py     # Sample data generation
│   └── generate_knowledge_base_embeddings.py
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker image
├── docker-compose.yml              # Docker Compose setup
└── README.md                       # Project overview
```

## Core Modules

### 1. API Gateway (`src/api/gateway.py`)

The FastAPI application that exposes all endpoints.

**Key Functions**:
- `app`: FastAPI application instance
- `@app.get("/health")`: Health check endpoint
- `@app.get("/api/v1/services/{service_id}/slo-recommendations")`: Get recommendations
- `@app.post("/api/v1/services/{service_id}/metrics")`: Submit metrics

**Adding a New Endpoint**:

```python
from fastapi import APIRouter, Depends, HTTPException
from src.models.data_models import RecommendationRequest

router = APIRouter(prefix="/api/v1", tags=["recommendations"])

@router.get("/services/{service_id}/custom-endpoint")
async def custom_endpoint(
    service_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Custom endpoint description."""
    try:
        # Your logic here
        return {"result": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add to main app
app.include_router(router)
```

### 2. Metrics Ingestion Engine (`src/engines/metrics_ingestion.py`)

Processes and validates operational metrics.

**Key Classes**:
- `MetricsIngestionEngine`: Main engine class
- `MetricsValidator`: Validates metric ranges and relationships

**Key Methods**:
- `ingest_metrics(service_id, metrics)`: Accept and process metrics
- `compute_aggregated_statistics(raw_metrics)`: Aggregate across time windows
- `detect_outliers(metrics)`: Identify anomalies

**Extending the Engine**:

```python
from src.engines.metrics_ingestion import MetricsIngestionEngine

class CustomMetricsEngine(MetricsIngestionEngine):
    def custom_processing(self, metrics):
        """Add custom metric processing."""
        # Your logic here
        return processed_metrics
    
    def ingest_metrics(self, service_id, metrics):
        # Call parent implementation
        result = super().ingest_metrics(service_id, metrics)
        # Add custom processing
        result = self.custom_processing(result)
        return result
```

### 3. Dependency Analyzer (`src/engines/dependency_analyzer.py`)

Constructs service graphs and computes critical paths.

**Key Classes**:
- `ServiceGraph`: Graph representation
- `DependencyAnalyzer`: Main analyzer

**Key Methods**:
- `build_graph(dependencies)`: Construct graph from declarations
- `detect_circular_dependencies()`: Find cycles using Tarjan's algorithm
- `compute_critical_path(service_id)`: Find longest latency path
- `compute_cascading_impact_score(service_id)`: Calculate impact score

**Adding a New Graph Algorithm**:

```python
from src.engines.dependency_analyzer import ServiceGraph

class CustomAnalyzer:
    def __init__(self, graph: ServiceGraph):
        self.graph = graph
    
    def custom_algorithm(self, service_id):
        """Implement custom graph algorithm."""
        # Access graph structure
        neighbors = self.graph.get_neighbors(service_id)
        # Your algorithm here
        return result
```

### 4. Recommendation Engine (`src/engines/recommendation_engine.py`)

Generates SLO recommendations using statistical analysis.

**Key Classes**:
- `RecommendationEngine`: Main engine
- `ConfidenceScoreCalculator`: Computes confidence scores

**Key Methods**:
- `generate_recommendations(service_id)`: Generate all tiers
- `compute_base_recommendations(metrics)`: Statistical baseline
- `apply_dependency_constraints(recommendations, dependencies)`: Adjust for dependencies
- `apply_infrastructure_constraints(recommendations, infrastructure)`: Adjust for infrastructure

**Customizing Recommendation Logic**:

```python
from src.engines.recommendation_engine import RecommendationEngine

class CustomRecommendationEngine(RecommendationEngine):
    def compute_base_recommendations(self, metrics):
        """Override base recommendation logic."""
        # Custom calculation
        return {
            "availability": custom_availability_calc(metrics),
            "latency_p95_ms": custom_latency_calc(metrics),
            "latency_p99_ms": custom_latency_calc(metrics),
            "error_rate_percent": custom_error_calc(metrics)
        }
```

### 5. AI Reasoning Layer (`src/engines/ai_reasoning.py`)

Integrates with LLM for explanation generation.

**Key Classes**:
- `OllamaClient`: Local LLM integration
- `AIReasoningEngine`: Main reasoning engine

**Key Methods**:
- `generate_explanation(context)`: Generate natural language explanation
- `refine_recommendations(baseline, context)`: LLM-based refinement

**Switching LLM Providers**:

```python
from src.engines.ai_reasoning import AIReasoningEngine

class OpenAIReasoningEngine(AIReasoningEngine):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
    
    def generate_explanation(self, context):
        """Use OpenAI instead of Ollama."""
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": self.build_prompt(context)}]
        )
        return response.choices[0].message.content
```

### 6. RAG Engine (`src/engines/rag_engine.py`)

Retrieves relevant knowledge for context.

**Key Classes**:
- `RAGEngine`: Main RAG engine
- `EmbeddingModel`: Sentence transformer wrapper

**Key Methods**:
- `retrieve_relevant_knowledge(query, top_k)`: Vector search
- `generate_embeddings(documents)`: Create embeddings

**Extending Knowledge Base**:

```python
from src.engines.rag_engine import RAGEngine

rag = RAGEngine()

# Add custom documents
custom_docs = [
    {
        "source": "custom_runbook",
        "content": "Your custom knowledge...",
        "metadata": {"type": "runbook"}
    }
]

# Generate embeddings
embeddings = rag.generate_embeddings(custom_docs)

# Retrieve similar documents
results = rag.retrieve_relevant_knowledge("query", top_k=5)
```

### 7. Data Models (`src/models/data_models.py`)

Pydantic models for data validation.

**Key Models**:
- `ServiceMetadata`: Service information
- `MetricsData`: Operational metrics
- `Recommendation`: SLO recommendation
- `DependencyGraph`: Service dependencies

**Adding a New Model**:

```python
from pydantic import BaseModel, Field, validator

class CustomModel(BaseModel):
    field1: str = Field(..., description="Field description")
    field2: int = Field(default=0, ge=0, le=100)
    
    @validator('field1')
    def validate_field1(cls, v):
        if not v:
            raise ValueError('field1 cannot be empty')
        return v
```

## Adding New Algorithms

### Example: Adding a New Recommendation Algorithm

1. **Create the algorithm class**:

```python
# src/engines/custom_algorithm.py
class CustomRecommendationAlgorithm:
    def __init__(self, metrics, dependencies):
        self.metrics = metrics
        self.dependencies = dependencies
    
    def compute_recommendations(self):
        """Compute recommendations using custom logic."""
        # Your algorithm implementation
        return recommendations
```

2. **Integrate with recommendation engine**:

```python
# In src/engines/recommendation_engine.py
from src.engines.custom_algorithm import CustomRecommendationAlgorithm

class RecommendationEngine:
    def generate_recommendations(self, service_id):
        # ... existing code ...
        
        # Use custom algorithm
        custom_algo = CustomRecommendationAlgorithm(metrics, dependencies)
        custom_recs = custom_algo.compute_recommendations()
        
        # Merge with existing recommendations
        return merged_recommendations
```

3. **Add tests**:

```python
# tests/unit/test_custom_algorithm.py
import pytest
from src.engines.custom_algorithm import CustomRecommendationAlgorithm

def test_custom_algorithm():
    metrics = {...}
    dependencies = {...}
    algo = CustomRecommendationAlgorithm(metrics, dependencies)
    recs = algo.compute_recommendations()
    assert recs is not None
```

## Extending the Knowledge Base

### Adding Runbooks

1. **Create markdown file**:

```bash
# data/knowledge/runbooks/my-service-type-slos.md
# My Service Type SLO Recommendations

## Overview
Description of your service type...

## Recommended Ranges
- **Availability**: X% - Y%
- **Latency p95**: X ms - Y ms
```

2. **Generate embeddings**:

```bash
python scripts/generate_knowledge_base_embeddings.py
```

### Adding Best Practices

1. **Update best practices JSON**:

```json
{
  "service_types": {
    "my_service_type": {
      "availability": {"min": 99.9, "typical": 99.95},
      "latency_p95_ms": {"min": 50, "typical": 100}
    }
  }
}
```

2. **Regenerate embeddings**:

```bash
python scripts/generate_knowledge_base_embeddings.py
```

## Adding API Endpoints

### Example: Adding a New Endpoint

1. **Define the request/response models**:

```python
# src/models/data_models.py
from pydantic import BaseModel

class CustomRequest(BaseModel):
    service_id: str
    custom_param: str

class CustomResponse(BaseModel):
    result: str
    status: str
```

2. **Implement the endpoint**:

```python
# src/api/gateway.py
from fastapi import APIRouter, Depends, HTTPException
from src.models.data_models import CustomRequest, CustomResponse

@app.post("/api/v1/custom-endpoint")
async def custom_endpoint(
    request: CustomRequest,
    api_key: str = Depends(verify_api_key)
) -> CustomResponse:
    """Custom endpoint description."""
    try:
        # Your logic here
        result = process_request(request)
        return CustomResponse(result=result, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

3. **Add tests**:

```python
# tests/integration/test_custom_endpoint.py
def test_custom_endpoint():
    response = client.post(
        "/api/v1/custom-endpoint",
        json={"service_id": "test", "custom_param": "value"},
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

## Testing Guidelines

### Unit Tests

Test individual functions and classes in isolation:

```python
# tests/unit/test_metrics_ingestion.py
import pytest
from src.engines.metrics_ingestion import MetricsIngestionEngine

def test_metrics_validation():
    engine = MetricsIngestionEngine()
    metrics = {
        "latency": {"p50_ms": 100, "p95_ms": 200, "p99_ms": 300},
        "availability": {"percent": 99.5},
        "error_rate": {"percent": 0.5}
    }
    result = engine.validate_metrics(metrics)
    assert result is True
```

### Integration Tests

Test complete workflows:

```python
# tests/integration/test_recommendation_workflow.py
def test_full_recommendation_workflow():
    # 1. Submit metrics
    metrics_response = submit_metrics("test-service", metrics_data)
    assert metrics_response.status_code == 200
    
    # 2. Get recommendations
    rec_response = get_recommendations("test-service")
    assert rec_response.status_code == 200
    
    # 3. Accept recommendation
    accept_response = accept_recommendation("test-service", "balanced")
    assert accept_response.status_code == 200
```

### Property-Based Tests

Test properties that should hold for all inputs:

```python
# tests/property/test_recommendations.py
from hypothesis import given, strategies as st

@given(
    availability=st.floats(min_value=90, max_value=100),
    latency=st.integers(min_value=1, max_value=10000)
)
def test_recommendations_are_achievable(availability, latency):
    """Recommendations should not exceed historical performance by >10%."""
    recs = generate_recommendations(availability, latency)
    assert recs.availability <= availability + 10
    assert recs.latency_p95_ms >= latency
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_metrics_ingestion.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run property-based tests
pytest tests/property/ -v
```

## Performance Optimization

### Profiling

```python
import cProfile
import pstats

# Profile a function
profiler = cProfile.Profile()
profiler.enable()

# Your code here
generate_recommendations("service-id")

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10 functions
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_service_metadata(service_id):
    """Cache service metadata to avoid repeated file reads."""
    return load_metadata(service_id)
```

### Async Operations

```python
import asyncio

async def process_multiple_services(service_ids):
    """Process multiple services concurrently."""
    tasks = [
        generate_recommendations_async(sid)
        for sid in service_ids
    ]
    return await asyncio.gather(*tasks)
```

## Debugging

### Enable Debug Logging

```python
# In .env
LOG_LEVEL=DEBUG

# Or in code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Debug Endpoints

```python
# Add debug endpoint to see internal state
@app.get("/debug/services/{service_id}")
async def debug_service(service_id: str):
    """Debug endpoint - remove in production."""
    return {
        "metadata": load_metadata(service_id),
        "metrics": load_metrics(service_id),
        "dependencies": load_dependencies(service_id)
    }
```

### Inspect File Storage

```bash
# View service metadata
cat data/services/payment-api/metadata.json | jq

# View dependency graph
cat data/dependencies/graph.json | jq

# View recommendations
cat data/recommendations/payment-api/latest.json | jq
```

## Contributing

1. **Create a feature branch**:
```bash
git checkout -b feature/my-feature
```

2. **Make your changes** and add tests

3. **Run tests**:
```bash
pytest
```

4. **Commit and push**:
```bash
git commit -m "Add my feature"
git push origin feature/my-feature
```

5. **Create a pull request**

## Common Tasks

### Regenerate Sample Data

```bash
python scripts/generate_sample_data.py
```

### Generate Knowledge Base Embeddings

```bash
python scripts/generate_knowledge_base_embeddings.py
```

### Export Audit Logs

```bash
curl -X GET "http://localhost:8000/api/v1/audit/export" \
  -H "X-API-Key: test-key-demo-tenant" > audit_logs.json
```

### Backup Data

```bash
# Backup all data
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Restore from backup
tar -xzf backup-20240115.tar.gz
```

## Troubleshooting Development

### Import Errors

```python
# Ensure src is in Python path
import sys
sys.path.insert(0, '/path/to/project')
```

### File Lock Issues

```bash
# Remove stale lock files
find data -name "*.lock" -delete
```

### Dependency Conflicts

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [NetworkX Documentation](https://networkx.org/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)

## Support

For development questions:
1. Check the [Design Document](.kiro/specs/slo-recommendation-system/design.md)
2. Review existing code and tests
3. Open an issue in the repository

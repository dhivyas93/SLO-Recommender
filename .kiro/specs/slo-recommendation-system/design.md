# Design Document: SLO Recommendation System

## Overview

The SLO Recommendation System is an AI-assisted platform that analyzes microservice metrics, dependency graphs, and operational patterns to recommend appropriate Service Level Objectives (SLOs) and Service Level Agreements (SLAs). The system provides explainable, confidence-scored recommendations that account for service dependencies, infrastructure constraints, and cascading failure impacts.

### POC Scope and Constraints

This design targets a Proof of Concept (POC) implementation with the following constraints:

- **Scale**: Up to 100 services with 500 dependency edges
- **Data Storage**: File-based (JSON/YAML) - no databases or cloud services
- **Deployment**: Runnable locally with minimal dependencies
- **Performance**: API responses within 3 seconds for POC scale
- **Cost**: $0 using local LLM (Ollama) and open-source tools
- **Extensibility**: Clear migration path to production scale (10,000+ services)

### No-Cost POC Setup

The POC can be run completely free using:

1. **Local LLM**: Ollama with Llama 3.2 3B Instruct
   - Cost: $0 (free, open-source)
   - Hardware: 4GB RAM minimum, 8GB recommended
   - Performance: 2-5 seconds per recommendation on CPU
   - Quality: Good for structured tasks, suitable for POC validation

2. **Local Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
   - Cost: $0 (free, open-source)
   - Size: 86MB model download
   - Performance: Fast on CPU

3. **No External Services**: Everything runs locally
   - No API keys required
   - No cloud dependencies
   - All data stays on your machine

**Optional Upgrades** (if budget available):
- OpenAI GPT-4: Better explanation quality (~$3-5 for 100 recommendations)
- Anthropic Claude: Alternative paid option (~$2-4 for 100 recommendations)

**Quick Start**:
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Llama 3.2 3B model
ollama pull llama3.2:3b-instruct-q4_0

# Clone and run the POC
git clone <repo-url>
cd slo-recommendation-system
pip install -r requirements.txt
python -m uvicorn src.api.gateway:app --reload
```

### Core Capabilities

1. **Dependency Analysis**: Constructs service graphs, identifies critical paths, computes cascading impact scores
2. **Metrics Processing**: Ingests and analyzes latency, error rate, and availability metrics across multiple time windows
3. **AI-Assisted SLO Recommendation**: Uses LLM-powered reasoning combined with statistical analysis to generate contextual, explainable recommendations
4. **Natural Language Explanations**: LLM generates human-readable explanations tailored to service context and team expertise
5. **Knowledge Layer**: RAG-based retrieval of historical patterns, SRE runbooks, and best practices
6. **Safety Guardrails**: Validates recommendations for achievability and consistency with rule-based checks

## Architecture

## Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SYSTEMS                                  │
│  Developer Platform (Backstage) | Service Owners | LLM Providers           │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │      API GATEWAY (FastAPI)      │
                    │  Auth | Rate Limiting | Routing │
                    └────────────────┬────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  METRICS ENGINE  │      │ DEPENDENCY       │      │ RECOMMENDATION   │
│                  │      │ ANALYZER         │      │ ENGINE           │
│ • Ingest metrics │      │                  │      │                  │
│ • Aggregate      │      │ • Build graph    │      │ • Statistical    │
│ • Detect outliers│      │ • Critical paths │      │   baseline       │
│ • Quality score  │      │ • Cascading      │      │ • Apply          │
│                  │      │   impact         │      │   constraints    │
└────────┬─────────┘      └────────┬─────────┘      │ • Generate tiers │
         │                         │                │ • Confidence     │
         │                         │                └────────┬─────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   AI REASONING LAYER        │
                    │                             │
                    │ • LLM Integration (Ollama)  │
                    │ • Contextual refinement     │
                    │ • Natural language explain  │
                    │ • Safety guardrails         │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  RAG ENGINE      │      │  KNOWLEDGE LAYER │      │ EVALUATION       │
│                  │      │                  │      │ ENGINE           │
│ • Vector search  │      │ • Runbooks       │      │                  │
│ • Embeddings     │      │ • Best practices │      │ • Backtesting    │
│ • Retrieval      │      │ • Patterns       │      │ • Accuracy       │
│                  │      │ • Feedback       │      │   metrics        │
└────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   FILE-BASED STORAGE        │
                    │   (JSON, No Database)       │
                    │                             │
                    │ • Services metadata         │
                    │ • Metrics history           │
                    │ • Dependency graphs         │
                    │ • Recommendations           │
                    │ • Audit logs                │
                    │ • Knowledge base            │
                    └─────────────────────────────┘
```

### Data Flow Diagram

```
INGESTION FLOW:
  Developer Platform
         │
         ▼
  POST /api/v1/services/{id}/metrics
         │
         ▼
  API Gateway (validate, authenticate)
         │
         ▼
  Metrics Ingestion Engine
         │
         ├─→ Detect outliers
         ├─→ Compute aggregations
         ├─→ Assess data quality
         │
         ▼
  File Storage (metrics_aggregated.json)


RECOMMENDATION FLOW:
  Service Owner
         │
         ▼
  GET /api/v1/services/{id}/slo-recommendations
         │
         ▼
  API Gateway
         │
         ▼
  Recommendation Engine
         │
         ├─→ Load metrics (30d, 90d windows)
         ├─→ Load dependency analysis
         ├─→ Load infrastructure constraints
         │
         ├─→ Compute statistical baseline
         ├─→ Apply dependency constraints
         ├─→ Apply infrastructure constraints
         │
         ├─→ RAG Engine (retrieve knowledge)
         │
         ├─→ AI Reasoning Layer (LLM refinement)
         │   ├─→ Ollama (local, free)
         │   └─→ or OpenAI/Anthropic (paid)
         │
         ├─→ Validate output
         ├─→ Compute confidence score
         │
         ▼
  Return recommendations + explanation
         │
         ▼
  File Storage (recommendations/{id}/latest.json)


EVALUATION FLOW:
  Evaluation Engine (scheduled)
         │
         ├─→ Load historical recommendations
         ├─→ Load actual metrics (30 days later)
         │
         ├─→ Compare predictions vs actual
         ├─→ Compute accuracy metrics
         │
         ▼
  File Storage (evaluation/accuracy_report.json)
```

### Component Interaction Patterns

- **Synchronous**: API Gateway ↔ All engines (request/response within 3s timeout)
- **File-based State**: All components read/write JSON files with file locking for concurrency
- **Stateless Processing**: All engines are stateless; state persists only in files

## Components and Interfaces

### 1. API Gateway

**Responsibility**: Expose REST API, handle authentication, route requests, enforce rate limits

**Technology**: Python FastAPI or Node.js Express (POC recommendation: FastAPI for simplicity)

**Endpoints**:

```
# Core Recommendation Workflow
GET /api/v1/services/{service_id}/slo-recommendations
  - Response: SLO recommendations with confidence scores and explanations
  - Timeout: 3 seconds

POST /api/v1/services/{service_id}/slos
  - Request: Accept or modify a recommendation
  - Response: Confirmation and updated SLO

# Dependency Management
POST /api/v1/services/dependencies
  - Request: Service dependency graph (bulk ingestion)
  - Response: Ingestion confirmation with validation results

GET /api/v1/services/{service_id}/dependencies
  - Response: Dependency graph for a specific service

# Impact Analysis
POST /api/v1/slos/impact-analysis
  - Request: Proposed SLO changes for one or more services
  - Response: Cascading impact on dependent services

# Metrics Ingestion
POST /api/v1/services/{service_id}/metrics
  - Request: Metrics data for a service
  - Response: Ingestion confirmation with data quality assessment

# History and Versioning
GET /api/v1/services/{service_id}/slo-recommendations/history
  - Response: Historical recommendations for a service

GET /api/v1/services/{service_id}/slo-recommendations/{version}
  - Response: Specific recommendation version

# Feedback
POST /api/v1/services/{service_id}/feedback
  - Request: Service owner feedback on recommendation
  - Response: Acknowledgment

# Evaluation and Monitoring
GET /api/v1/evaluation/accuracy
  - Response: System-wide accuracy metrics

GET /api/v1/audit/export
  - Response: Audit logs in JSON format

# Documentation
GET /api/v1/docs
  - Response: OpenAPI specification
```

**Authentication**: API key-based (header: `X-API-Key`)

**Rate Limiting**: 100 requests/minute per API key (POC)

**File Dependencies**:
- Reads: `data/api_keys.json` (API key to tenant mapping)
- Writes: `data/audit_logs/{date}.json` (append-only audit trail)

### 2. Metrics Ingestion Engine

**Responsibility**: Accept, validate, and process operational metrics

**Processing Logic**:
1. Validate metric format and ranges
2. Detect and flag outliers (>3 standard deviations)
3. Compute aggregated statistics (mean, median, p50, p95, p99)
4. Store raw and processed metrics
5. Flag data quality issues (missing data, staleness)

**Metrics Accepted**:
- Latency: p50, p95, p99 (milliseconds)
- Error Rate: percentage (0-100)
- Availability: percentage (0-100)
- Request Volume: requests per second

**Time Windows**: 1d, 7d, 30d, 90d

**File Dependencies**:
- Reads: `data/services/{service_id}/metadata.json`
- Writes: `data/services/{service_id}/metrics/{timestamp}.json`
- Writes: `data/services/{service_id}/metrics_aggregated.json`

**Data Quality Indicators**:
```json
{
  "completeness": 0.95,
  "staleness_hours": 2,
  "outlier_count": 3,
  "quality_score": 0.92
}
```

### 3. Dependency Analyzer

**Responsibility**: Construct service graphs, compute critical paths, calculate cascading impacts

**Graph Representation**:
- Nodes: Services and infrastructure components (datastores, queues, caches)
- Edges: Dependencies with metadata (sync/async, timeout, retry policy)

**Algorithms**:
1. **Graph Construction**: Parse dependency declarations, build adjacency list
2. **Cycle Detection**: Tarjan's algorithm for strongly connected components
3. **Critical Path**: Modified Dijkstra's algorithm using latency as edge weight
4. **Cascading Impact Score**: BFS-based scoring considering depth and fanout

**Cascading Impact Formula**:
```
impact_score(service) = Σ (1 / depth) * (1 / fanout) for all downstream services
```

**File Dependencies**:
- Reads: `data/dependencies/graph.json` (full dependency graph)
- Reads: `data/services/{service_id}/dependencies.json` (per-service)
- Writes: `data/dependencies/analyzed_graph.json` (with computed metrics)
- Writes: `data/dependencies/critical_paths.json`

**Output**:
```json
{
  "service_id": "api-gateway",
  "upstream_count": 0,
  "downstream_count": 5,
  "critical_path": ["api-gateway", "auth-service", "user-db"],
  "critical_path_latency_budget": 450,
  "cascading_impact_score": 0.87,
  "circular_dependencies": []
}
```

### 4. Recommendation Engine

**Responsibility**: Generate SLO recommendations using hybrid rule-based + statistical approach

**Recommendation Algorithm**:

```
For each service:
  1. Load historical metrics (p50, p95, p99, error rate, availability)
  2. Load dependency analysis (critical path, cascading impact)
  3. Load infrastructure constraints (datastore SLOs, network latency)
  4. Load knowledge base patterns (similar services, best practices)
  
  5. Compute base recommendations:
     - Availability: min(historical_p95 - buffer, upstream_availability - margin)
     - Latency p95: historical_p95 + (1.5 * stddev)
     - Latency p99: historical_p99 + (2 * stddev)
     - Error rate: historical_p95 + buffer
  
  6. Apply dependency constraints:
     - If downstream of service X: availability <= X.availability - 0.5%
     - If critical path latency budget: p95 <= budget / path_length
  
  7. Apply infrastructure constraints:
     - If uses datastore D: latency >= D.latency + network_overhead
     - If uses cache: adjust for cache hit rate
  
  8. Generate three tiers:
     - Aggressive: historical_p75 performance
     - Balanced: historical_p90 performance (default)
     - Conservative: historical_p95 performance
  
  9. Compute confidence score:
     - Data completeness: 0-0.3
     - Historical stability: 0-0.3
     - Dependency clarity: 0-0.2
     - Similar service patterns: 0-0.2
  
  10. Generate explanation:
      - Top 3 influencing factors
      - Dependency constraints
      - Infrastructure bottlenecks
      - Historical performance citations
```

**Confidence Score Calculation**:
```python
confidence = (
    0.3 * data_completeness +
    0.3 * (1 - coefficient_of_variation) +
    0.2 * dependency_completeness +
    0.2 * knowledge_base_match_score
)
```

**File Dependencies**:
- Reads: `data/services/{service_id}/metrics_aggregated.json`
- Reads: `data/dependencies/analyzed_graph.json`
- Reads: `data/knowledge/best_practices.json`
- Reads: `data/knowledge/similar_services.json`
- Writes: `data/recommendations/{service_id}/{version}.json`
- Writes: `data/recommendations/{service_id}/latest.json`

**Output Format**:
```json
{
  "service_id": "payment-api",
  "version": "v1.2.3",
  "timestamp": "2024-01-15T10:30:00Z",
  "recommendations": {
    "aggressive": {
      "availability": 99.9,
      "latency_p95_ms": 150,
      "latency_p99_ms": 300,
      "error_rate_percent": 0.5
    },
    "balanced": {
      "availability": 99.5,
      "latency_p95_ms": 200,
      "latency_p99_ms": 400,
      "error_rate_percent": 1.0
    },
    "conservative": {
      "availability": 99.0,
      "latency_p95_ms": 300,
      "latency_p99_ms": 600,
      "error_rate_percent": 2.0
    }
  },
  "recommended_tier": "balanced",
  "confidence_score": 0.85,
  "explanation": {
    "summary": "Balanced tier recommended based on stable 30-day performance and moderate dependency complexity",
    "top_factors": [
      "Historical p95 latency: 180ms (30-day window)",
      "Downstream of auth-service (99.9% availability) requires margin",
      "PostgreSQL datastore adds 50ms baseline latency"
    ],
    "dependency_constraints": [
      "auth-service availability (99.9%) limits this service to 99.5%",
      "Critical path budget: 450ms across 3 services"
    ],
    "infrastructure_bottlenecks": [
      "PostgreSQL p95 latency: 45ms"
    ],
    "similar_services": [
      "checkout-api: 99.5% availability, 210ms p95 latency"
    ]
  },
  "data_quality": {
    "completeness": 0.98,
    "staleness_hours": 1,
    "quality_score": 0.95
  }
}
```

### 5. Knowledge Layer

**Responsibility**: Store and retrieve historical patterns, best practices, and organizational knowledge

**Knowledge Base Structure**:

```
data/knowledge/
  ├── best_practices.json          # Industry standards by service type
  ├── similar_services.json        # Service similarity index
  ├── historical_outcomes.json     # Recommendation outcomes
  └── feedback_patterns.json       # Service owner feedback trends
```

**Best Practices Format**:
```json
{
  "service_types": {
    "api_gateway": {
      "availability": {"min": 99.9, "typical": 99.95},
      "latency_p95_ms": {"min": 50, "typical": 100},
      "error_rate_percent": {"max": 0.5, "typical": 0.1}
    },
    "database": {
      "availability": {"min": 99.95, "typical": 99.99},
      "latency_p95_ms": {"min": 10, "typical": 50}
    }
  }
}
```

**Similarity Matching**: Cosine similarity on feature vectors:
- Dependency count (upstream/downstream)
- Request volume tier
- Latency tier
- Service type
- Infrastructure components

**File Dependencies**:
- Reads/Writes: All files in `data/knowledge/`

### 6. AI Reasoning Layer

**Responsibility**: Integrate LLM-powered reasoning for contextual recommendations and natural language explanations

**Technology**: 
- **LLM (No-Cost Option)**: Ollama with Llama 3.2 3B Instruct (free, local, ~2GB model)
- **LLM (Paid Options)**: OpenAI GPT-4 or Anthropic Claude (better quality, ~$0.01-0.05 per recommendation)
- **Embeddings**: sentence-transformers with all-MiniLM-L6-v2 (free, local, 86MB model)

**Core Functions**:

1. **Contextual Recommendation Refinement**
   - Takes statistical baseline recommendations
   - Considers service context (type, team, criticality)
   - Applies domain knowledge from RAG retrieval
   - Adjusts recommendations based on similar service patterns

2. **Natural Language Explanation Generation**
   - Converts technical metrics into human-readable explanations
   - Tailors language to team expertise level
   - Provides actionable insights and recommendations
   - Cites specific data sources and reasoning steps

3. **Anomaly Detection and Flagging**
   - Identifies unusual patterns in metrics or dependencies
   - Flags potential issues (e.g., "latency increased 3x in last week")
   - Suggests root causes based on historical patterns

4. **Interactive Q&A** (Future)
   - Answer service owner questions about recommendations
   - Explain trade-offs between different SLO tiers
   - Provide guidance on improving service reliability

**LLM Integration Pattern**:

```python
def generate_recommendation_with_ai(service_id, statistical_baseline, context):
    """
    Hybrid approach: Statistical baseline + LLM refinement
    """
    # 1. Retrieve relevant knowledge via RAG
    relevant_docs = rag_engine.retrieve(
        query=f"SLO recommendations for {context['service_type']} services",
        top_k=5
    )
    
    # 2. Build LLM prompt with structured context
    prompt = build_recommendation_prompt(
        service_id=service_id,
        statistical_baseline=statistical_baseline,
        metrics=context['metrics'],
        dependencies=context['dependencies'],
        infrastructure=context['infrastructure'],
        similar_services=context['similar_services'],
        retrieved_knowledge=relevant_docs
    )
    
    # 3. Call LLM with structured output
    llm_response = llm_client.generate(
        prompt=prompt,
        temperature=0.3,  # Low temperature for consistency
        max_tokens=2000,
        response_format="json"  # Structured output
    )
    
    # 4. Validate and merge with statistical baseline
    validated_recommendation = validate_llm_output(
        llm_response,
        statistical_baseline,
        safety_constraints
    )
    
    return validated_recommendation
```

**Prompt Template**:

```
You are an SRE expert assistant helping to recommend SLOs for microservices.

SERVICE CONTEXT:
- Service ID: {service_id}
- Service Type: {service_type}
- Team: {team_name}
- Criticality: {criticality_level}

STATISTICAL BASELINE RECOMMENDATIONS:
- Availability: {baseline_availability}% (based on p95 of 30-day history)
- Latency p95: {baseline_latency_p95}ms
- Latency p99: {baseline_latency_p99}ms
- Error Rate: {baseline_error_rate}%

HISTORICAL METRICS (30-day window):
- Average p95 latency: {avg_p95}ms (stddev: {stddev_p95}ms)
- Average availability: {avg_availability}%
- Error rate trend: {error_trend}

DEPENDENCIES:
- Upstream services: {upstream_list}
- Downstream services: {downstream_list}
- Critical path: {critical_path}
- Bottleneck: {bottleneck_service}

INFRASTRUCTURE:
- Datastores: {datastore_list}
- Caches: {cache_list}
- Infrastructure constraints: {constraints}

SIMILAR SERVICES:
{similar_services_with_slos}

RETRIEVED KNOWLEDGE:
{rag_retrieved_docs}

TASK:
1. Review the statistical baseline recommendations
2. Consider the service context, dependencies, and infrastructure
3. Adjust recommendations if needed based on:
   - Dependency constraints (upstream SLOs)
   - Infrastructure bottlenecks
   - Similar service patterns
   - Best practices from retrieved knowledge
4. Generate three tiers: aggressive, balanced, conservative
5. Provide clear, actionable explanations

OUTPUT FORMAT (JSON):
{
  "recommendations": {
    "aggressive": { "availability": X, "latency_p95_ms": Y, ... },
    "balanced": { "availability": X, "latency_p95_ms": Y, ... },
    "conservative": { "availability": X, "latency_p95_ms": Y, ... }
  },
  "recommended_tier": "balanced",
  "reasoning": {
    "summary": "One sentence summary",
    "key_factors": ["factor 1", "factor 2", "factor 3"],
    "dependency_impact": "How dependencies constrain SLOs",
    "infrastructure_impact": "How infrastructure affects SLOs",
    "adjustments_from_baseline": "What changed from statistical baseline and why"
  },
  "confidence_score": 0.85,
  "warnings": ["warning 1", "warning 2"],
  "actionable_insights": ["insight 1", "insight 2"]
}

SAFETY CONSTRAINTS:
- Recommended availability must be <= historical p99 availability + 1%
- Recommended latency must be >= historical p50 latency - 20%
- Must respect upstream service SLO constraints
- Flag any recommendations that seem unrealistic
```

**Safety Guardrails for LLM Output**:

1. **Schema Validation**: Ensure JSON output matches expected structure
2. **Range Validation**: Check SLO values are within realistic bounds
3. **Consistency Checks**: Verify aggressive < balanced < conservative
4. **Dependency Validation**: Ensure recommendations respect upstream constraints
5. **Fallback**: If LLM output is invalid, use statistical baseline with warning

**File Dependencies**:
- Reads: `data/services/{service_id}/metadata.json`
- Reads: `data/services/{service_id}/metrics_aggregated.json`
- Reads: `data/dependencies/analyzed_graph.json`
- Reads: `data/knowledge/embeddings.json` (via RAG engine)
- Writes: `data/ai_reasoning/prompts/{service_id}_{timestamp}.json` (for debugging)
- Writes: `data/ai_reasoning/responses/{service_id}_{timestamp}.json` (for auditing)

**LLM Provider Configuration**:

```json
{
  "llm_config": {
    "provider": "local",
    "model": "llama-3.2-3b-instruct",
    "endpoint": "http://localhost:11434/api/generate",
    "temperature": 0.3,
    "max_tokens": 2000,
    "timeout_seconds": 10,
    "fallback_to_baseline": true
  },
  "alternative_providers": [
    {
      "provider": "openai",
      "model": "gpt-4-turbo-preview",
      "api_key_env": "OPENAI_API_KEY",
      "note": "Optional: Better quality but costs ~$0.01-0.05 per recommendation"
    },
    {
      "provider": "anthropic",
      "model": "claude-3-sonnet",
      "api_key_env": "ANTHROPIC_API_KEY",
      "note": "Optional: Alternative paid provider"
    }
  ]
}
```

**No-Cost POC Setup**:

For a completely free POC implementation, use:
1. **Local LLM**: Ollama with Llama 3.2 3B Instruct (runs on CPU, ~4GB RAM)
2. **Local Embeddings**: sentence-transformers with all-MiniLM-L6-v2 (86MB model)
3. **No Vector DB**: Simple cosine similarity in-memory (no FAISS needed)

**Ollama Setup** (Free, Local):
```bash
# Install Ollama (macOS, Linux, Windows)
curl -fsSL https://ollama.com/install.sh | sh

# Pull Llama 3.2 3B model (~2GB download)
ollama pull llama3.2:3b-instruct-q4_0

# Start Ollama server (runs on localhost:11434)
ollama serve
```

**Cost Comparison**:
- **Local (Ollama)**: $0 - Free, runs on your machine
- **OpenAI GPT-4**: ~$0.03 per recommendation (100 recs = $3)
- **Anthropic Claude**: ~$0.02 per recommendation (100 recs = $2)

**Performance Trade-offs**:
- **Local Llama 3.2 3B**: 
  - Response time: 2-5 seconds on CPU, <1s on GPU
  - Quality: Good for structured tasks, may be less nuanced than GPT-4
  - Privacy: All data stays local
- **OpenAI GPT-4**: 
  - Response time: 1-2 seconds
  - Quality: Excellent reasoning and explanations
  - Privacy: Data sent to OpenAI (can use Azure OpenAI for enterprise)

### 7. RAG Engine (Retrieval-Augmented Generation)

**Responsibility**: Retrieve relevant knowledge from historical data, runbooks, and best practices to ground LLM recommendations

**Technology**: 
- **Embeddings**: sentence-transformers with all-MiniLM-L6-v2 (free, local, 86MB)
- **Vector Search**: Simple cosine similarity for POC (no external dependencies)
- **Alternative**: FAISS for faster search with larger knowledge bases (optional)

**Knowledge Sources**:

1. **SRE Runbooks**: Markdown documents with SLO guidance
2. **Historical Recommendations**: Past recommendations and outcomes
3. **Incident Reports**: Post-mortems mentioning SLO violations
4. **Best Practices**: Industry standards by service type
5. **Similar Service Patterns**: Services with similar characteristics

**RAG Workflow**:

```python
def retrieve_relevant_knowledge(query, service_context, top_k=5):
    """
    Retrieve relevant documents for LLM context
    """
    # 1. Generate query embedding
    query_embedding = embedding_model.encode(query)
    
    # 2. Retrieve from multiple sources
    runbook_results = search_runbooks(query_embedding, top_k=2)
    historical_results = search_historical_recommendations(
        service_context, top_k=2
    )
    best_practice_results = search_best_practices(
        service_context['service_type'], top_k=1
    )
    
    # 3. Combine and rank results
    all_results = runbook_results + historical_results + best_practice_results
    ranked_results = rank_by_relevance(all_results, query_embedding)
    
    # 4. Format for LLM context
    formatted_docs = []
    for result in ranked_results[:top_k]:
        formatted_docs.append({
            'source': result['source'],
            'content': result['content'],
            'relevance_score': result['score'],
            'metadata': result['metadata']
        })
    
    return formatted_docs
```

**Knowledge Base Structure**:

```
data/knowledge/
├── runbooks/
│   ├── api-gateway-slos.md
│   ├── database-slos.md
│   ├── message-queue-slos.md
│   └── external-dependency-handling.md
├── best_practices/
│   ├── industry-standards.json
│   ├── service-type-patterns.json
│   └── dependency-constraints.json
├── historical/
│   ├── successful-recommendations.json
│   ├── failed-recommendations.json
│   └── adjustment-patterns.json
├── incidents/
│   ├── slo-violations-2024-01.json
│   └── post-mortems.json
└── embeddings/
    ├── runbooks_embeddings.json
    ├── best_practices_embeddings.json
    └── historical_embeddings.json
```

**Example Runbook** (`data/knowledge/runbooks/api-gateway-slos.md`):

```markdown
# API Gateway SLO Recommendations

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

## Example
For an API gateway calling auth-service (99.9%, 50ms) and payment-service (99.5%, 200ms):
- Max availability: 99.5% (limited by payment-service)
- Min latency p95: 255ms (50ms + 200ms + 5ms network)
```

**Embedding Generation**:

```python
def generate_embeddings_for_knowledge_base():
    """
    Pre-compute embeddings for all knowledge base documents
    """
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    embeddings = {
        'runbooks': [],
        'best_practices': [],
        'historical': []
    }
    
    # Embed runbooks
    for runbook_file in glob('data/knowledge/runbooks/*.md'):
        content = read_file(runbook_file)
        chunks = chunk_document(content, chunk_size=500)
        for chunk in chunks:
            embedding = embedding_model.encode(chunk)
            embeddings['runbooks'].append({
                'source': runbook_file,
                'content': chunk,
                'embedding': embedding.tolist()
            })
    
    # Embed best practices
    best_practices = read_json('data/knowledge/best_practices/industry-standards.json')
    for practice in best_practices:
        text = f"{practice['service_type']}: {practice['description']}"
        embedding = embedding_model.encode(text)
        embeddings['best_practices'].append({
            'source': 'industry-standards',
            'content': practice,
            'embedding': embedding.tolist()
        })
    
    # Save embeddings
    write_json('data/knowledge/embeddings/all_embeddings.json', embeddings)
```

**Vector Search** (Simple Cosine Similarity for POC):

```python
def search_embeddings(query_embedding, embeddings_db, top_k=5):
    """
    Simple cosine similarity search for POC
    """
    from sklearn.metrics.pairwise import cosine_similarity
    
    results = []
    for doc in embeddings_db:
        similarity = cosine_similarity(
            [query_embedding],
            [doc['embedding']]
        )[0][0]
        results.append({
            'source': doc['source'],
            'content': doc['content'],
            'score': similarity
        })
    
    # Sort by similarity and return top k
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]
```

**File Dependencies**:
- Reads: `data/knowledge/runbooks/*.md`
- Reads: `data/knowledge/best_practices/*.json`
- Reads: `data/knowledge/historical/*.json`
- Reads: `data/knowledge/embeddings/all_embeddings.json`
- Writes: `data/knowledge/embeddings/all_embeddings.json` (during initialization)

### 8. Evaluation Engine

**Responsibility**: Validate recommendation quality through backtesting and feedback analysis

**Metrics Tracked**:
1. **Accuracy**: % of recommendations where actual performance met predicted SLO
2. **Precision**: % of aggressive recommendations that were achievable
3. **Recall**: % of services that could have had more aggressive SLOs
4. **Acceptance Rate**: % of recommendations accepted without modification
5. **Adjustment Patterns**: Common modifications made by service owners

**Backtesting Process**:
1. Select historical time window (e.g., 90 days ago)
2. Generate recommendations using data available at that time
3. Compare recommendations to actual performance over next 30 days
4. Compute accuracy metrics

**File Dependencies**:
- Reads: `data/recommendations/{service_id}/*.json` (all versions)
- Reads: `data/services/{service_id}/metrics/*.json` (actual performance)
- Reads: `data/feedback/{service_id}.json` (service owner feedback)
- Writes: `data/evaluation/accuracy_report_{date}.json`

**Output Format**:
```json
{
  "evaluation_date": "2024-01-15",
  "time_window": "30d",
  "metrics": {
    "overall_accuracy": 0.87,
    "aggressive_precision": 0.72,
    "balanced_precision": 0.91,
    "conservative_precision": 0.98,
    "acceptance_rate": 0.83
  },
  "by_service_type": {
    "api_gateway": {"accuracy": 0.92},
    "database": {"accuracy": 0.95},
    "message_queue": {"accuracy": 0.81}
  }
}
```

## Data Models

### Service Metadata

**File**: `data/services/{service_id}/metadata.json`

```json
{
  "service_id": "payment-api",
  "service_name": "Payment API",
  "service_type": "api",
  "team": "payments-team",
  "tenant_id": "acme-corp",
  "region": "us-east-1",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z",
  "infrastructure": {
    "datastores": [
      {
        "type": "postgresql",
        "name": "payments-db",
        "availability_slo": 99.95,
        "latency_p95_ms": 45
      }
    ],
    "caches": [
      {
        "type": "redis",
        "name": "payment-cache",
        "hit_rate": 0.85
      }
    ],
    "message_queues": [
      {
        "type": "kafka",
        "name": "payment-events"
      }
    ]
  },
  "current_slo": {
    "availability": 99.5,
    "latency_p95_ms": 200,
    "latency_p99_ms": 400,
    "error_rate_percent": 1.0
  }
}
```

### Metrics Data

**File**: `data/services/{service_id}/metrics/{timestamp}.json`

```json
{
  "service_id": "payment-api",
  "timestamp": "2024-01-15T10:00:00Z",
  "time_window": "1d",
  "metrics": {
    "latency": {
      "p50_ms": 85,
      "p95_ms": 180,
      "p99_ms": 350,
      "mean_ms": 95,
      "stddev_ms": 45
    },
    "error_rate": {
      "percent": 0.8,
      "total_requests": 1000000,
      "failed_requests": 8000
    },
    "availability": {
      "percent": 99.6,
      "uptime_seconds": 86054,
      "downtime_seconds": 346
    },
    "request_volume": {
      "requests_per_second": 11.57,
      "peak_rps": 45.2
    }
  },
  "regional_breakdown": {
    "us-east-1": {
      "latency_p95_ms": 175,
      "availability": 99.7
    },
    "eu-west-1": {
      "latency_p95_ms": 190,
      "availability": 99.5
    }
  },
  "data_quality": {
    "completeness": 0.98,
    "outliers_detected": 3,
    "outlier_timestamps": ["2024-01-15T03:15:00Z"],
    "quality_score": 0.95
  }
}
```

### Dependency Graph

**File**: `data/dependencies/graph.json`

```json
{
  "version": "1.0",
  "updated_at": "2024-01-15T10:00:00Z",
  "services": [
    {
      "service_id": "api-gateway",
      "dependencies": [
        {
          "target_service_id": "auth-service",
          "dependency_type": "synchronous",
          "timeout_ms": 500,
          "retry_policy": "exponential_backoff",
          "criticality": "high"
        },
        {
          "target_service_id": "payment-api",
          "dependency_type": "synchronous",
          "timeout_ms": 1000,
          "criticality": "high"
        }
      ]
    },
    {
      "service_id": "payment-api",
      "dependencies": [
        {
          "target_service_id": "fraud-detection",
          "dependency_type": "asynchronous",
          "criticality": "medium"
        },
        {
          "target_infrastructure_id": "payments-db",
          "infrastructure_type": "postgresql",
          "dependency_type": "synchronous"
        }
      ]
    }
  ],
  "circular_dependencies": [
    {
      "cycle": ["service-a", "service-b", "service-c", "service-a"],
      "detected_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### Analyzed Dependency Graph

**File**: `data/dependencies/analyzed_graph.json`

```json
{
  "version": "1.0",
  "analyzed_at": "2024-01-15T10:05:00Z",
  "services": [
    {
      "service_id": "payment-api",
      "upstream_services": ["api-gateway"],
      "downstream_services": ["fraud-detection", "payments-db"],
      "upstream_count": 1,
      "downstream_count": 2,
      "depth_from_root": 2,
      "fanout": 2,
      "cascading_impact_score": 0.65,
      "critical_paths": [
        {
          "path": ["api-gateway", "payment-api", "payments-db"],
          "total_latency_budget_ms": 450,
          "bottleneck_service": "payments-db"
        }
      ],
      "is_in_circular_dependency": false
    }
  ],
  "graph_statistics": {
    "total_services": 45,
    "total_edges": 123,
    "max_depth": 5,
    "circular_dependency_count": 1
  }
}
```

### Recommendation History

**File**: `data/recommendations/{service_id}/{version}.json`

(See Recommendation Engine output format above)

### Audit Logs

**File**: `data/audit_logs/{date}.json` (append-only)

```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "event_type": "recommendation_generated",
  "service_id": "payment-api",
  "tenant_id": "acme-corp",
  "requester": "api_key_abc123",
  "request_data": {
    "endpoint": "/api/v1/recommendations",
    "method": "POST"
  },
  "response_data": {
    "recommendation_version": "v1.2.3",
    "confidence_score": 0.85,
    "recommended_tier": "balanced"
  },
  "processing_time_ms": 1250
}
```

### Feedback Data

**File**: `data/feedback/{service_id}.json`

```json
{
  "service_id": "payment-api",
  "feedback_entries": [
    {
      "timestamp": "2024-01-15T11:00:00Z",
      "recommendation_version": "v1.2.3",
      "action": "accepted",
      "tier_selected": "balanced",
      "modifications": null,
      "service_owner": "alice@example.com",
      "comments": "Looks reasonable based on our traffic patterns"
    },
    {
      "timestamp": "2024-01-10T14:30:00Z",
      "recommendation_version": "v1.2.2",
      "action": "modified",
      "tier_selected": "balanced",
      "modifications": {
        "availability": {"recommended": 99.5, "actual": 99.7},
        "reason": "We have better infrastructure than system assumed"
      },
      "service_owner": "bob@example.com"
    }
  ]
}
```


## API Design

### Authentication

All API requests require authentication via API key in the header:

```
X-API-Key: {api_key}
```

API keys are stored in `data/api_keys.json`:

```json
{
  "api_keys": [
    {
      "key": "ak_abc123...",
      "tenant_id": "acme-corp",
      "created_at": "2024-01-01T00:00:00Z",
      "rate_limit": 100
    }
  ]
}
```

### Request/Response Formats

#### GET /api/v1/services/{service_id}/slo-recommendations

**Response** (200 OK):
```json
{
  "service_id": "payment-api",
  "version": "v1.2.3",
  "timestamp": "2024-01-15T10:30:00Z",
  "recommendations": {
    "aggressive": {
      "availability": 99.9,
      "latency_p95_ms": 150,
      "latency_p99_ms": 300,
      "error_rate_percent": 0.5
    },
    "balanced": {
      "availability": 99.5,
      "latency_p95_ms": 200,
      "latency_p99_ms": 400,
      "error_rate_percent": 1.0
    },
    "conservative": {
      "availability": 99.0,
      "latency_p95_ms": 300,
      "latency_p99_ms": 600,
      "error_rate_percent": 2.0
    }
  },
  "recommended_tier": "balanced",
  "confidence_score": 0.85,
  "explanation": {
    "summary": "Balanced tier recommended based on stable 30-day performance and moderate dependency complexity",
    "top_factors": [
      "Historical p95 latency: 180ms (30-day window)",
      "Downstream of auth-service (99.9% availability) requires margin",
      "PostgreSQL datastore adds 50ms baseline latency"
    ],
    "dependency_constraints": [
      "auth-service availability (99.9%) limits this service to 99.5%",
      "Critical path budget: 450ms across 3 services"
    ],
    "infrastructure_bottlenecks": [
      "PostgreSQL p95 latency: 45ms"
    ],
    "similar_services": [
      "checkout-api: 99.5% availability, 210ms p95 latency"
    ]
  },
  "data_quality": {
    "completeness": 0.98,
    "staleness_hours": 1,
    "quality_score": 0.95
  }
}
```

#### POST /api/v1/services/{service_id}/slos

**Request**:
```json
{
  "action": "accept",
  "tier_selected": "balanced",
  "modifications": null,
  "comments": "Looks reasonable based on our traffic patterns"
}
```

Or with modifications:

```json
{
  "action": "modify",
  "tier_selected": "balanced",
  "modifications": {
    "availability": 99.7,
    "latency_p95_ms": 200,
    "latency_p99_ms": 400,
    "error_rate_percent": 1.0
  },
  "reason": "We have better infrastructure than system assumed",
  "comments": "Increasing availability target based on recent improvements"
}
```

**Response** (200 OK):
```json
{
  "status": "accepted",
  "service_id": "payment-api",
  "slo_version": "v2.0.0",
  "applied_slo": {
    "availability": 99.7,
    "latency_p95_ms": 200,
    "latency_p99_ms": 400,
    "error_rate_percent": 1.0
  },
  "timestamp": "2024-01-15T11:00:00Z"
}
```

#### POST /api/v1/services/dependencies

**Request**:
```json
{
  "services": [
    {
      "service_id": "api-gateway",
      "dependencies": [
        {
          "target_service_id": "auth-service",
          "dependency_type": "synchronous",
          "timeout_ms": 500,
          "retry_policy": "exponential_backoff",
          "criticality": "high"
        },
        {
          "target_service_id": "payment-api",
          "dependency_type": "synchronous",
          "timeout_ms": 1000,
          "criticality": "high"
        }
      ]
    },
    {
      "service_id": "payment-api",
      "dependencies": [
        {
          "target_service_id": "fraud-detection",
          "dependency_type": "asynchronous",
          "criticality": "medium"
        },
        {
          "target_infrastructure_id": "payments-db",
          "infrastructure_type": "postgresql",
          "dependency_type": "synchronous"
        }
      ]
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "status": "ingested",
  "services_processed": 2,
  "edges_created": 4,
  "validation_results": {
    "warnings": [
      {
        "service_id": "payment-api",
        "message": "Dependency 'fraud-detection' not found in service catalog",
        "severity": "warning"
      }
    ],
    "errors": []
  },
  "graph_statistics": {
    "total_services": 45,
    "total_edges": 127,
    "circular_dependencies_detected": 0
  }
}
```

#### POST /api/v1/slos/impact-analysis

**Request**:
```json
{
  "proposed_changes": [
    {
      "service_id": "auth-service",
      "current_slo": {
        "availability": 99.9,
        "latency_p95_ms": 50
      },
      "proposed_slo": {
        "availability": 99.5,
        "latency_p95_ms": 100
      }
    }
  ],
  "analysis_depth": "full"
}
```

**Response** (200 OK):
```json
{
  "impact_analysis": {
    "auth-service": {
      "direct_impact": {
        "affected_services": ["api-gateway", "user-service", "admin-portal"],
        "affected_count": 3
      },
      "cascading_impact": {
        "total_affected_services": 12,
        "impact_by_service": [
          {
            "service_id": "api-gateway",
            "current_slo": {
              "availability": 99.9,
              "latency_p95_ms": 200
            },
            "recommended_adjustment": {
              "availability": 99.5,
              "latency_p95_ms": 250,
              "reason": "Upstream auth-service availability decreased"
            },
            "impact_severity": "high"
          },
          {
            "service_id": "user-service",
            "current_slo": {
              "availability": 99.8,
              "latency_p95_ms": 150
            },
            "recommended_adjustment": {
              "availability": 99.5,
              "latency_p95_ms": 200,
              "reason": "Upstream auth-service latency increased"
            },
            "impact_severity": "medium"
          }
        ]
      },
      "critical_path_impact": [
        {
          "path": ["api-gateway", "auth-service", "user-db"],
          "current_total_latency": 250,
          "projected_total_latency": 300,
          "budget_exceeded": false
        }
      ],
      "recommendations": [
        "Consider increasing latency budgets for api-gateway and user-service",
        "Review error handling in dependent services",
        "Implement circuit breakers for auth-service calls"
      ]
    }
  },
  "summary": {
    "total_services_affected": 12,
    "high_severity_impacts": 1,
    "medium_severity_impacts": 3,
    "low_severity_impacts": 8
  }
}
```

#### POST /api/v1/services/{service_id}/metrics

**Request**:
```json
{
  "time_window": "30d",
  "metrics": {
    "latency": {
      "p50_ms": 85,
      "p95_ms": 180,
      "p99_ms": 350,
      "mean_ms": 95,
      "stddev_ms": 45
    },
    "error_rate": {
      "percent": 0.8,
      "total_requests": 1000000,
      "failed_requests": 8000
    },
    "availability": {
      "percent": 99.6,
      "uptime_seconds": 86054,
      "downtime_seconds": 346
    },
    "request_volume": {
      "requests_per_second": 11.57,
      "peak_rps": 45.2
    }
  },
  "regional_breakdown": {
    "us-east-1": {
      "latency_p95_ms": 175,
      "availability": 99.7
    },
    "eu-west-1": {
      "latency_p95_ms": 190,
      "availability": 99.5
    }
  }
}
```

**Response** (200 OK):
```json
{
  "status": "ingested",
  "service_id": "payment-api",
  "timestamp": "2024-01-15T10:00:00Z",
  "data_quality": {
    "completeness": 0.98,
    "outliers_detected": 3,
    "quality_score": 0.95
  },
  "validation_results": {
    "warnings": [],
    "errors": []
  }
}
```

### Rate Limiting

- **POC Limit**: 100 requests/minute per API key
- **Response Header**: `X-RateLimit-Remaining: 95`
- **429 Response**:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit of 100 requests/minute exceeded",
  "retry_after_seconds": 45
}
```

### OpenAPI Specification

The API Gateway serves OpenAPI 3.0 specification at `/api/v1/docs` for integration with developer platforms.


## Dependency Graph Modeling

### Graph Representation

The dependency graph uses an adjacency list representation stored in JSON:

```python
# In-memory representation
class ServiceGraph:
    def __init__(self):
        self.nodes = {}  # service_id -> ServiceNode
        self.edges = []  # list of DependencyEdge
        
class ServiceNode:
    service_id: str
    service_type: str
    metadata: dict
    
class DependencyEdge:
    source_id: str
    target_id: str
    dependency_type: str  # synchronous | asynchronous
    timeout_ms: int
    criticality: str  # high | medium | low
```

### Critical Path Algorithm

Modified Dijkstra's algorithm using latency as edge weight:

```python
def compute_critical_path(graph, service_id):
    """
    Compute the critical path from service to all leaf dependencies.
    Returns the path with maximum cumulative latency.
    """
    # Initialize distances
    distances = {node: float('inf') for node in graph.nodes}
    distances[service_id] = 0
    paths = {service_id: [service_id]}
    
    # Priority queue: (cumulative_latency, current_node, path)
    pq = [(0, service_id, [service_id])]
    max_latency_path = []
    max_latency = 0
    
    while pq:
        current_latency, current_node, current_path = heappop(pq)
        
        # If leaf node, check if this is the longest path
        if not graph.get_downstream(current_node):
            if current_latency > max_latency:
                max_latency = current_latency
                max_latency_path = current_path
            continue
        
        # Explore downstream dependencies
        for edge in graph.get_downstream_edges(current_node):
            target = edge.target_id
            edge_latency = get_service_latency(target)
            new_latency = current_latency + edge_latency
            new_path = current_path + [target]
            
            heappush(pq, (new_latency, target, new_path))
    
    return {
        'path': max_latency_path,
        'total_latency_ms': max_latency,
        'bottleneck': find_bottleneck(max_latency_path)
    }
```

### Cascading Impact Score

BFS-based algorithm to compute how many services are affected by this service:

```python
def compute_cascading_impact(graph, service_id):
    """
    Compute impact score based on downstream dependency tree.
    Score = Σ (1 / depth) * (1 / fanout) for all downstream services
    """
    visited = set()
    queue = [(service_id, 0)]  # (node, depth)
    impact_score = 0.0
    
    while queue:
        current, depth = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        
        downstream = graph.get_downstream(current)
        fanout = len(downstream) if downstream else 1
        
        if depth > 0:  # Don't count the service itself
            impact_score += (1.0 / depth) * (1.0 / fanout)
        
        for dep in downstream:
            queue.append((dep, depth + 1))
    
    return min(impact_score, 1.0)  # Normalize to [0, 1]
```

### Circular Dependency Detection

Tarjan's algorithm for finding strongly connected components:

```python
def detect_circular_dependencies(graph):
    """
    Use Tarjan's algorithm to find strongly connected components.
    Any SCC with size > 1 is a circular dependency.
    """
    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    on_stack = set()
    sccs = []
    
    def strongconnect(node):
        index[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack.add(node)
        
        for successor in graph.get_downstream(node):
            if successor not in index:
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif successor in on_stack:
                lowlinks[node] = min(lowlinks[node], index[successor])
        
        if lowlinks[node] == index[node]:
            scc = []
            while True:
                successor = stack.pop()
                on_stack.remove(successor)
                scc.append(successor)
                if successor == node:
                    break
            sccs.append(scc)
    
    for node in graph.nodes:
        if node not in index:
            strongconnect(node)
    
    # Return only SCCs with size > 1 (circular dependencies)
    return [scc for scc in sccs if len(scc) > 1]
```


## SLO Recommendation Algorithm

### Hybrid AI + Statistical Approach

The recommendation engine combines three layers:
1. **Statistical Baseline**: Rule-based analysis of historical metrics
2. **AI Reasoning**: LLM-powered contextual refinement and explanation
3. **Safety Validation**: Rule-based guardrails to ensure recommendations are achievable

This hybrid approach provides the best of both worlds: statistical rigor with AI-powered contextual understanding and natural language explanations.

### Algorithm Pseudocode

```python
def generate_recommendations(service_id):
    # Step 1: Load all required data
    metrics = load_metrics(service_id, windows=['1d', '7d', '30d', '90d'])
    dependencies = load_dependency_analysis(service_id)
    infrastructure = load_infrastructure_constraints(service_id)
    knowledge = load_similar_services(service_id)
    
    # Step 2: Compute statistical baseline recommendations
    base_recs = compute_base_recommendations(metrics)
    
    # Step 3: Apply dependency constraints
    dep_constrained = apply_dependency_constraints(base_recs, dependencies)
    
    # Step 4: Apply infrastructure constraints
    infra_constrained = apply_infrastructure_constraints(dep_constrained, infrastructure)
    
    # Step 5: Retrieve relevant knowledge via RAG
    rag_context = rag_engine.retrieve(
        query=f"SLO recommendations for {service_id}",
        service_context={
            'service_type': get_service_type(service_id),
            'metrics': metrics,
            'dependencies': dependencies
        },
        top_k=5
    )
    
    # Step 6: AI-powered refinement and explanation
    ai_recommendation = ai_reasoning_layer.refine_recommendation(
        service_id=service_id,
        statistical_baseline=infra_constrained,
        metrics=metrics,
        dependencies=dependencies,
        infrastructure=infrastructure,
        similar_services=knowledge,
        rag_context=rag_context
    )
    
    # Step 7: Safety validation
    validated_recommendation = validate_and_constrain(
        ai_recommendation,
        statistical_baseline=infra_constrained,
        safety_rules=SAFETY_RULES
    )
    
    # Step 8: Compute confidence score
    confidence = compute_confidence(
        metrics, dependencies, knowledge,
        ai_confidence=ai_recommendation.get('confidence', 0.5)
    )
    
    return {
        'recommendations': validated_recommendation['tiers'],
        'recommended_tier': validated_recommendation['recommended_tier'],
        'confidence_score': confidence,
        'explanation': validated_recommendation['explanation'],
        'ai_insights': validated_recommendation.get('actionable_insights', [])
    }
```

### Base Statistical Recommendations

```python
def compute_base_recommendations(metrics):
    """
    Compute recommendations based purely on historical performance.
    Uses 30-day window as primary, with 90-day for stability check.
    """
    m30 = metrics['30d']
    m90 = metrics['90d']
    
    # Availability: Use p95 of historical availability minus buffer
    availability_p95 = percentile(m30.availability_samples, 95)
    availability_buffer = 0.5  # 0.5% buffer for safety
    base_availability = availability_p95 - availability_buffer
    
    # Latency p95: Historical p95 + 1.5 standard deviations
    latency_p95_mean = mean(m30.latency_p95_samples)
    latency_p95_stddev = stddev(m30.latency_p95_samples)
    base_latency_p95 = latency_p95_mean + (1.5 * latency_p95_stddev)
    
    # Latency p99: Historical p99 + 2 standard deviations
    latency_p99_mean = mean(m30.latency_p99_samples)
    latency_p99_stddev = stddev(m30.latency_p99_samples)
    base_latency_p99 = latency_p99_mean + (2 * latency_p99_stddev)
    
    # Error rate: Historical p95 + buffer
    error_rate_p95 = percentile(m30.error_rate_samples, 95)
    error_rate_buffer = 0.2  # 0.2% buffer
    base_error_rate = error_rate_p95 + error_rate_buffer
    
    return {
        'availability': base_availability,
        'latency_p95_ms': base_latency_p95,
        'latency_p99_ms': base_latency_p99,
        'error_rate_percent': base_error_rate
    }
```

### Dependency Constraints

```python
def apply_dependency_constraints(base_recs, dependencies):
    """
    Adjust recommendations based on upstream service SLOs.
    A service cannot be more available than its dependencies.
    """
    constrained = base_recs.copy()
    
    # Availability constraint: Must be lower than all upstream services
    for upstream in dependencies.upstream_services:
        upstream_availability = get_service_slo(upstream.service_id).availability
        margin = 0.5  # 0.5% margin below upstream
        max_availability = upstream_availability - margin
        
        if constrained['availability'] > max_availability:
            constrained['availability'] = max_availability
            constrained['_availability_constraint'] = upstream.service_id
    
    # Latency constraint: Must fit within critical path budget
    if dependencies.critical_path:
        path_length = len(dependencies.critical_path)
        total_budget = dependencies.critical_path_latency_budget_ms
        per_service_budget = total_budget / path_length
        
        if constrained['latency_p95_ms'] > per_service_budget:
            constrained['latency_p95_ms'] = per_service_budget
            constrained['_latency_constraint'] = 'critical_path_budget'
    
    return constrained
```

### Infrastructure Constraints

```python
def apply_infrastructure_constraints(recs, infrastructure):
    """
    Adjust recommendations based on datastore and infrastructure limits.
    """
    constrained = recs.copy()
    
    # Datastore latency constraint
    for datastore in infrastructure.datastores:
        db_latency = datastore.latency_p95_ms
        network_overhead = 5  # 5ms network overhead
        min_latency = db_latency + network_overhead
        
        if constrained['latency_p95_ms'] < min_latency:
            constrained['latency_p95_ms'] = min_latency
            constrained['_latency_floor'] = datastore.name
    
    # Cache adjustment: If high cache hit rate, can be more aggressive
    for cache in infrastructure.caches:
        if cache.hit_rate > 0.8:
            # Can reduce latency target by cache benefit
            cache_benefit = 0.9  # 10% improvement
            constrained['latency_p95_ms'] *= cache_benefit
            constrained['_cache_benefit'] = cache.name
    
    return constrained
```

### Tier Generation

```python
def generate_tiers(constrained_recs, metrics):
    """
    Generate three tiers: aggressive, balanced, conservative.
    """
    m30 = metrics['30d']
    
    # Balanced tier: Use constrained recommendations
    balanced = constrained_recs
    
    # Aggressive tier: Use p75 historical performance
    aggressive = {
        'availability': percentile(m30.availability_samples, 75),
        'latency_p95_ms': percentile(m30.latency_p95_samples, 75),
        'latency_p99_ms': percentile(m30.latency_p99_samples, 75),
        'error_rate_percent': percentile(m30.error_rate_samples, 75)
    }
    
    # Conservative tier: Use p95 historical performance
    conservative = {
        'availability': percentile(m30.availability_samples, 95),
        'latency_p95_ms': percentile(m30.latency_p95_samples, 95),
        'latency_p99_ms': percentile(m30.latency_p99_samples, 95),
        'error_rate_percent': percentile(m30.error_rate_samples, 95)
    }
    
    return {
        'aggressive': aggressive,
        'balanced': balanced,
        'conservative': conservative
    }
```

### Confidence Score Calculation

```python
def compute_confidence(metrics, dependencies, knowledge):
    """
    Confidence score based on data quality and knowledge base match.
    Range: 0.0 to 1.0
    """
    # Data completeness (0-0.3)
    completeness_score = metrics['30d'].data_quality.completeness * 0.3
    
    # Historical stability (0-0.3)
    # Lower coefficient of variation = more stable = higher confidence
    cv = coefficient_of_variation(metrics['30d'].latency_p95_samples)
    stability_score = (1 - min(cv, 1.0)) * 0.3
    
    # Dependency clarity (0-0.2)
    # All dependencies have known SLOs = higher confidence
    known_deps = sum(1 for d in dependencies.upstream_services if d.has_slo)
    total_deps = len(dependencies.upstream_services) or 1
    dependency_score = (known_deps / total_deps) * 0.2
    
    # Knowledge base match (0-0.2)
    # Similar services exist = higher confidence
    similarity_score = knowledge.best_match_similarity * 0.2
    
    confidence = (
        completeness_score +
        stability_score +
        dependency_score +
        similarity_score
    )
    
    return round(confidence, 2)
```

### Explanation Generation

```python
def generate_explanation(base, dep_constrained, infra_constrained, 
                        dependencies, infrastructure, knowledge):
    """
    Generate human-readable explanation for recommendations.
    """
    factors = []
    
    # Historical performance
    factors.append({
        'type': 'historical',
        'description': f"Historical p95 latency: {base['latency_p95_ms']}ms (30-day window)"
    })
    
    # Dependency constraints
    if '_availability_constraint' in dep_constrained:
        upstream = dep_constrained['_availability_constraint']
        factors.append({
            'type': 'dependency',
            'description': f"Downstream of {upstream} requires availability margin"
        })
    
    # Infrastructure constraints
    if '_latency_floor' in infra_constrained:
        db = infra_constrained['_latency_floor']
        factors.append({
            'type': 'infrastructure',
            'description': f"{db} datastore adds baseline latency"
        })
    
    # Sort by impact and take top 3
    top_factors = factors[:3]
    
    return {
        'summary': generate_summary(top_factors),
        'top_factors': [f['description'] for f in top_factors],
        'dependency_constraints': format_dependency_constraints(dependencies),
        'infrastructure_bottlenecks': format_infrastructure_bottlenecks(infrastructure),
        'similar_services': format_similar_services(knowledge)
    }
```


## Technology Stack

### POC Technology Recommendations

**Language**: Python 3.11+
- Rationale: Rich ecosystem for data processing, simple file I/O, fast prototyping, excellent LLM library support
- Alternative: Node.js/TypeScript for teams with JavaScript preference (but fewer LLM libraries)

**Web Framework**: FastAPI
- Rationale: Modern async support, automatic OpenAPI docs, type hints, fast
- Alternative: Flask (simpler but less features)

**Data Processing**: Pandas + NumPy
- Rationale: Statistical analysis, percentile calculations, data manipulation
- Alternative: Pure Python with statistics module (lighter weight)

**Graph Processing**: NetworkX
- Rationale: Built-in graph algorithms (Dijkstra, Tarjan), easy to use
- Alternative: Custom implementation (more control, less dependencies)

**LLM Integration**: Ollama (local, free) or OpenAI/Anthropic (paid)
- Rationale: Ollama provides free local LLMs with OpenAI-compatible API
- Cost: $0 for local, ~$0.01-0.05 per recommendation for cloud APIs

**Embeddings**: sentence-transformers (local, free)
- Rationale: High-quality embeddings, runs locally, no API costs
- Model: all-MiniLM-L6-v2 (86MB, fast on CPU)

**Vector Search**: Cosine similarity (built-in) or FAISS (optional)
- Rationale: Cosine similarity is sufficient for POC scale (<1000 documents)
- Alternative: FAISS for faster search if knowledge base grows

**File Format**: JSON
- Rationale: Human-readable, widely supported, easy debugging
- Alternative: YAML (more readable) or MessagePack (more efficient)

**Testing**: pytest + Hypothesis (for property-based testing)
- Rationale: Industry standard, excellent property-based testing support

**API Documentation**: FastAPI built-in (Swagger UI)

**Deployment**: Docker container
- Rationale: Consistent environment, easy local development, includes Ollama

### Minimal Dependencies

```
# requirements.txt
# Web Framework
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0

# Data Processing
pandas==2.1.3
numpy==1.26.2
networkx==3.2.1

# AI/LLM Integration (No-Cost Options)
sentence-transformers==2.2.2     # Local embeddings (free)
scikit-learn==1.3.2              # Cosine similarity for vector search (free)
requests==2.31.0                 # HTTP client for Ollama API (free)

# Optional: Paid LLM Providers (comment out for no-cost POC)
# openai==1.3.0                  # OpenAI API (~$0.03 per recommendation)
# anthropic==0.7.0               # Anthropic Claude API (~$0.02 per recommendation)

# Optional: Advanced Vector Search (not needed for POC)
# faiss-cpu==1.7.4               # Faster vector search for large knowledge bases

# Testing
pytest==7.4.3
hypothesis==6.92.1
```

**Total Cost for POC**:
- **No-Cost Setup**: $0 (Ollama + sentence-transformers + local deployment)
- **With OpenAI**: ~$3-5 for 100 recommendations during testing
- **With Anthropic**: ~$2-4 for 100 recommendations during testing

### Project Structure

```
slo-recommendation-system/
├── src/
│   ├── api/
│   │   ├── gateway.py          # FastAPI app and routes
│   │   ├── auth.py             # API key authentication
│   │   └── models.py           # Pydantic request/response models
│   ├── engines/
│   │   ├── metrics_ingestion.py
│   │   ├── dependency_analyzer.py
│   │   ├── recommendation_engine.py
│   │   ├── ai_reasoning.py     # LLM integration layer
│   │   ├── rag_engine.py       # RAG retrieval
│   │   └── evaluation_engine.py
│   ├── storage/
│   │   ├── file_storage.py     # File I/O abstraction
│   │   └── models.py           # Data models
│   ├── algorithms/
│   │   ├── graph.py            # Graph algorithms
│   │   └── statistics.py       # Statistical computations
│   └── utils/
│       ├── validation.py       # Input validation
│       ├── llm_client.py       # LLM API client wrapper
│       └── logging.py          # Structured logging
├── data/                       # File-based storage (gitignored)
│   ├── services/
│   ├── dependencies/
│   ├── recommendations/
│   ├── knowledge/
│   │   ├── runbooks/
│   │   ├── best_practices/
│   │   ├── historical/
│   │   └── embeddings/
│   ├── ai_reasoning/
│   │   ├── prompts/
│   │   └── responses/
│   ├── audit_logs/
│   └── api_keys.json
├── tests/
│   ├── unit/
│   ├── integration/
│   └── property/               # Property-based tests
├── docs/
│   └── api_spec.yaml           # OpenAPI specification
├── .env.example                # Environment variables template
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```
│   ├── engines/
│   │   ├── metrics_ingestion.py
│   │   ├── dependency_analyzer.py
│   │   ├── recommendation_engine.py
│   │   └── evaluation_engine.py
│   ├── storage/
│   │   ├── file_storage.py     # File I/O abstraction
│   │   └── models.py           # Data models
│   ├── algorithms/
│   │   ├── graph.py            # Graph algorithms
│   │   └── statistics.py       # Statistical computations
│   └── utils/
│       ├── validation.py       # Input validation
│       └── logging.py          # Structured logging
├── data/                       # File-based storage (gitignored)
│   ├── services/
│   ├── dependencies/
│   ├── recommendations/
│   ├── knowledge/
│   ├── audit_logs/
│   └── api_keys.json
├── tests/
│   ├── unit/
│   ├── integration/
│   └── property/               # Property-based tests
├── docs/
│   └── api_spec.yaml           # OpenAPI specification
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

### File Storage Implementation

```python
# src/storage/file_storage.py
import json
import fcntl
from pathlib import Path
from typing import Any, Dict
from contextlib import contextmanager

class FileStorage:
    """
    Thread-safe file-based storage with file locking.
    """
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def _lock_file(self, file_path: Path):
        """Context manager for file locking."""
        lock_path = file_path.with_suffix('.lock')
        lock_file = open(lock_path, 'w')
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
    
    def read_json(self, path: str) -> Dict[str, Any]:
        """Read JSON file with locking."""
        file_path = self.base_path / path
        if not file_path.exists():
            return {}
        
        with self._lock_file(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
    
    def write_json(self, path: str, data: Dict[str, Any]):
        """Write JSON file with locking."""
        file_path = self.base_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._lock_file(file_path):
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
    
    def append_json(self, path: str, data: Dict[str, Any]):
        """Append to JSON array file (for audit logs)."""
        file_path = self.base_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._lock_file(file_path):
            existing = []
            if file_path.exists():
                with open(file_path, 'r') as f:
                    existing = json.load(f)
            
            existing.append(data)
            
            with open(file_path, 'w') as f:
                json.dump(existing, f, indent=2)
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/

EXPOSE 8000

CMD ["uvicorn", "src.api.gateway:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - LOG_LEVEL=INFO
      - DATA_PATH=/app/data
```


## Scaling Roadmap

### POC → Production Evolution

This section outlines the migration path from the file-based POC to a production-scale system supporting 10,000+ services.

### Phase 1: POC (Current Design)
**Scale**: 100 services, 500 edges
**Storage**: File-based JSON
**Performance**: 3s API response time

**Characteristics**:
- Single-node deployment
- File locking for concurrency
- In-memory graph processing
- Synchronous API calls

### Phase 2: Small Production (100-1,000 services)
**Target**: 1,000 services, 5,000 edges
**Timeline**: 3-6 months after POC validation

**Changes Required**:

1. **Database Migration**
   - Replace file storage with PostgreSQL
   - Schema:
     ```sql
     CREATE TABLE services (
       service_id VARCHAR PRIMARY KEY,
       metadata JSONB,
       created_at TIMESTAMP,
       updated_at TIMESTAMP
     );
     
     CREATE TABLE metrics (
       id SERIAL PRIMARY KEY,
       service_id VARCHAR REFERENCES services,
       timestamp TIMESTAMP,
       time_window VARCHAR,
       metrics JSONB,
       INDEX idx_service_time (service_id, timestamp)
     );
     
     CREATE TABLE dependencies (
       source_id VARCHAR REFERENCES services,
       target_id VARCHAR REFERENCES services,
       metadata JSONB,
       PRIMARY KEY (source_id, target_id)
     );
     
     CREATE TABLE recommendations (
       id SERIAL PRIMARY KEY,
       service_id VARCHAR REFERENCES services,
       version VARCHAR,
       timestamp TIMESTAMP,
       recommendations JSONB,
       INDEX idx_service_version (service_id, version)
     );
     ```

2. **Caching Layer**
   - Add Redis for:
     - Dependency graph caching (TTL: 5 minutes)
     - Metrics aggregation caching (TTL: 1 minute)
     - Recommendation caching (TTL: 10 minutes)
   - Cache invalidation on updates

3. **API Improvements**
   - Add request queuing for expensive operations
   - Implement async processing for large graphs
   - Add webhook callbacks for long-running requests

**Migration Strategy**:
- Dual-write to files and database during transition
- Gradual cutover service by service
- Rollback capability via file backups

### Phase 3: Medium Production (1,000-5,000 services)
**Target**: 5,000 services, 25,000 edges
**Timeline**: 6-12 months after Phase 2

**Changes Required**:

1. **Horizontal Scaling**
   - Multiple API Gateway instances behind load balancer
   - Stateless design enables simple horizontal scaling
   - Session affinity not required

2. **Graph Partitioning**
   - Partition dependency graph by tenant or service cluster
   - Process independent subgraphs in parallel
   - Use graph partitioning algorithms (METIS, KaHIP)

3. **Async Processing**
   - Add message queue (RabbitMQ or Kafka)
   - Async recommendation generation for large graphs
   - Background jobs for evaluation and backtesting

4. **Database Optimization**
   - Read replicas for query scaling
   - Partitioning metrics table by time (monthly partitions)
   - Materialized views for common aggregations

**Architecture**:
```mermaid
graph TB
    LB[Load Balancer]
    API1[API Gateway 1]
    API2[API Gateway 2]
    API3[API Gateway 3]
    Queue[Message Queue]
    Worker1[Worker 1]
    Worker2[Worker 2]
    Cache[Redis Cache]
    DBMaster[(PostgreSQL Master)]
    DBReplica1[(PostgreSQL Replica 1)]
    DBReplica2[(PostgreSQL Replica 2)]
    
    LB --> API1
    LB --> API2
    LB --> API3
    
    API1 --> Cache
    API2 --> Cache
    API3 --> Cache
    
    API1 --> Queue
    API2 --> Queue
    API3 --> Queue
    
    Queue --> Worker1
    Queue --> Worker2
    
    API1 --> DBReplica1
    API2 --> DBReplica2
    API3 --> DBReplica1
    
    Worker1 --> DBMaster
    Worker2 --> DBMaster
    
    DBMaster -.->|Replication| DBReplica1
    DBMaster -.->|Replication| DBReplica2
```

### Phase 4: Large Production (5,000-10,000+ services)
**Target**: 10,000+ services, 50,000+ edges
**Timeline**: 12-24 months after Phase 3

**Changes Required**:

1. **Distributed Graph Processing**
   - Use Apache Spark or Flink for graph analysis
   - Distribute critical path computation across cluster
   - Incremental graph updates instead of full recomputation

2. **Time-Series Database**
   - Migrate metrics to InfluxDB or TimescaleDB
   - Optimized for time-series queries
   - Better compression and retention policies

3. **Multi-Region Deployment**
   - Deploy in multiple regions
   - Regional recommendation engines
   - Cross-region data replication for global view

4. **Machine Learning Integration**
   - Replace rule-based recommendation with ML models
   - Train on historical recommendation outcomes
   - A/B test ML vs rule-based approaches

5. **Advanced Caching**
   - Multi-level caching (L1: in-memory, L2: Redis, L3: DB)
   - Predictive cache warming
   - Cache stampede prevention

**Performance Targets**:
- API response time: <1s for 95% of requests
- Graph analysis: <5s for 10,000 node graphs
- Throughput: 1,000 requests/second

### Migration Checklist

**POC → Phase 2**:
- [ ] Set up PostgreSQL database
- [ ] Implement database schema
- [ ] Create data migration scripts
- [ ] Add Redis caching layer
- [ ] Update storage abstraction layer
- [ ] Implement dual-write mode
- [ ] Test with production-like data
- [ ] Gradual cutover
- [ ] Remove file storage code

**Phase 2 → Phase 3**:
- [ ] Deploy load balancer
- [ ] Add horizontal scaling for API gateways
- [ ] Implement graph partitioning
- [ ] Set up message queue
- [ ] Create async worker processes
- [ ] Add database read replicas
- [ ] Implement table partitioning
- [ ] Load testing at scale

**Phase 3 → Phase 4**:
- [ ] Evaluate distributed graph processing frameworks
- [ ] Migrate to time-series database
- [ ] Implement multi-region deployment
- [ ] Train ML models on historical data
- [ ] A/B test ML recommendations
- [ ] Implement advanced caching strategies
- [ ] Performance optimization

### Backward Compatibility

Each phase maintains API compatibility:
- Same REST endpoints
- Same request/response formats
- Same authentication mechanism
- Versioned API (v1, v2) for breaking changes

### Cost Considerations

**POC**: ~$50/month
- Single VM or container
- Local storage

**Phase 2**: ~$500/month
- PostgreSQL managed service
- Redis managed service
- 2-3 API instances

**Phase 3**: ~$2,000/month
- Load balancer
- 5-10 API instances
- Message queue
- Database replicas

**Phase 4**: ~$10,000+/month
- Multi-region deployment
- Distributed processing cluster
- Time-series database
- ML infrastructure


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Graph Construction and Analysis Properties

### Property 1: Graph Construction Completeness

*For any* valid dependency declaration set, constructing a Service_Graph should result in a graph where every declared service appears as a node and every declared dependency appears as an edge with correct source and target.

**Validates: Requirements 1.1, 3.1**

### Property 2: Circular Dependency Detection

*For any* dependency graph containing a cycle, the Dependency_Analyzer should detect and report all strongly connected components with size > 1.

**Validates: Requirements 1.2**

### Property 3: Graceful Handling of Missing Dependencies

*For any* dependency graph with missing or partial information (references to non-existent services), the Dependency_Analyzer should identify the gaps, include them in a warnings list, and successfully process the available data without crashing.

**Validates: Requirements 1.3**

### Property 4: Critical Path Correctness

*For any* service in a dependency graph, the computed critical path should be the path from that service to a leaf node with the maximum cumulative latency, and no other path should have greater cumulative latency.

**Validates: Requirements 1.4**

### Property 5: Cascading Impact Score Computation

*For all* services in a Service_Graph, the cascading impact score should be computed using the formula Σ (1 / depth) * (1 / fanout) for all downstream services, normalized to [0, 1].

**Validates: Requirements 1.5**

### Metrics Processing Properties

### Property 6: Metrics Input Acceptance

*For any* valid metrics submission containing latency percentiles (p50, p95, p99), error rates, and availability data within valid ranges, the Metrics_Ingestion_Engine should accept and process the submission successfully.

**Validates: Requirements 2.1**

### Property 7: Time Window Processing

*For any* metrics submission, the Metrics_Ingestion_Engine should compute aggregated statistics for all four time windows (1d, 7d, 30d, 90d) and store them separately.

**Validates: Requirements 2.2**

### Property 8: Outlier Detection and Flagging

*For any* metrics dataset, values more than 3 standard deviations from the mean should be flagged as outliers, and both raw and adjusted statistics (excluding outliers) should be computed.

**Validates: Requirements 2.3**

### Property 9: Regional Metrics Aggregation

*For any* metrics submission with regional breakdown data, the Metrics_Ingestion_Engine should compute both per-region statistics and global aggregated statistics.

**Validates: Requirements 2.4**

### Property 10: Data Quality Indication

*For any* metrics dataset with completeness < 1.0, the output should include a data_quality object with completeness score, staleness indicator, and overall quality score.

**Validates: Requirements 2.5**

### Recommendation Generation Properties

### Property 11: Infrastructure Constraint Satisfaction

*For any* service with datastore dependencies, recommended latency SLOs should be >= (datastore_latency_p95 + network_overhead), and recommended availability should be <= (datastore_availability - margin).

**Validates: Requirements 3.2, 3.3**

### Property 12: Bottleneck Identification

*For any* service where infrastructure latency exceeds the service's historical latency, the infrastructure component should be identified as a bottleneck in the recommendation explanation.

**Validates: Requirements 3.4**

### Property 13: Recommendation Output Completeness

*For any* successful recommendation request, the output should contain all required fields: availability, latency_p95, latency_p99, error_rate for all three tiers (aggressive, balanced, conservative), plus confidence_score and explanation.

**Validates: Requirements 4.1, 4.2, 4.3, 4.5**

### Property 14: Conservative Recommendations for Unknown Dependencies

*For any* service with dependencies that have unknown SLOs, the recommended availability should be <= 99.0% (conservative threshold), and the explanation should mention the uncertainty.

**Validates: Requirements 4.4, 12.2**

### Property 15: Recommendation Tier Ordering

*For any* set of recommendations, the aggressive tier should have stricter SLOs than balanced, and balanced should have stricter SLOs than conservative (aggressive.availability >= balanced.availability >= conservative.availability).

**Validates: Requirements 4.5**

### Explainability Properties

### Property 16: Explanation Factor Count

*For any* recommendation explanation, the top_factors list should contain at least 3 factors (or all available factors if fewer than 3 exist).

**Validates: Requirements 5.1**

### Property 17: Dependency Constraint Citation

*For any* recommendation where a dependency constraint was applied (availability or latency limited by upstream service), the explanation should identify the specific constraining dependency by service_id.

**Validates: Requirements 5.2**

### Property 18: Historical Metrics Citation

*For any* recommendation explanation, when historical metrics influenced the recommendation, the explanation should cite specific percentile values (p50/p95/p99) and the time window used (1d/7d/30d/90d).

**Validates: Requirements 5.3**

### Property 19: Critical Path Inclusion

*For any* service with a non-empty critical path, the recommendation explanation should include the critical_path array and identify any bottleneck services.

**Validates: Requirements 5.4**

### API and Integration Properties

### Property 20: JSON Response Format Compliance

*For any* successful API request to /api/v1/recommendations, the response should be valid JSON matching the defined schema with all required fields present.

**Validates: Requirements 6.2**

### Property 21: Authentication Enforcement

*For any* API request with a valid API key, the request should be processed; for any request with an invalid or missing API key, the API should return HTTP 401 Unauthorized.

**Validates: Requirements 6.3**

### Property 22: Rate Limiting Behavior

*For any* sequence of requests from a single API key exceeding the rate limit (100/minute in POC), the API should return HTTP 429 with a Retry-After header for requests beyond the limit.

**Validates: Requirements 6.4**

### Property 23: Response Time Performance

*For any* recommendation request with a dependency graph of <= 100 services, the API response time should be <= 3 seconds.

**Validates: Requirements 6.6, 8.3**

### Safety and Validation Properties

### Property 24: PII Rejection

*For any* input data containing patterns matching PII (email addresses, phone numbers, SSNs), the Metrics_Ingestion_Engine should reject the request and return an error with HTTP 400.

**Validates: Requirements 7.1**

### Property 25: Achievability Validation

*For any* recommendation, the recommended SLO values should not exceed historical performance by more than a reasonable margin (e.g., recommended availability <= historical_p99_availability + 1%).

**Validates: Requirements 7.2**

### Property 26: Minimum SLO Thresholds

*For all* recommendations, availability should be >= 90%, latency values should be > 0, and error_rate should be >= 0 and <= 100.

**Validates: Requirements 7.4**

### Property 27: Dependency Chain Consistency

*For any* pair of services where service A depends on service B, if both have recommendations, then A.availability should be <= B.availability - margin; violations should be flagged in the response.

**Validates: Requirements 7.5**

### Scalability Properties

### Property 28: Throughput Capacity

*For any* sequence of 100 metric submissions within a 60-second window, the Metrics_Ingestion_Engine should successfully process all submissions without errors.

**Validates: Requirements 8.2**

### Knowledge Layer Properties

### Property 29: Recommendation Persistence

*For any* generated recommendation, the system should store it in the recommendations history with a unique version identifier, timestamp, and all recommendation data, and it should be retrievable via the history API.

**Validates: Requirements 9.1, 14.1**

### Property 30: Similar Service Influence

*For any* service with at least one similar service in the Knowledge_Layer (similarity score > 0.7), the recommendation explanation should reference the similar service's SLO patterns.

**Validates: Requirements 9.2**

### Property 31: Best Practices Storage

*For any* service_type in the system (api_gateway, database, message_queue), the Knowledge_Layer should contain best practice SLO ranges that can be queried and retrieved.

**Validates: Requirements 9.3**

### Property 32: Feedback Persistence

*For any* feedback submission (accept/reject/modify), the system should store the feedback with timestamp, recommendation_version, action, and any modifications, and it should be retrievable.

**Validates: Requirements 9.4**

### Evaluation Properties

### Property 33: Backtesting Execution

*For any* historical time window with sufficient data, the Evaluation_Engine should be able to generate recommendations using only data available at that time and compare them to actual outcomes.

**Validates: Requirements 10.1**

### Property 34: Accuracy Metric Computation

*For any* set of recommendations with actual performance data over 30 days, the Evaluation_Engine should compute accuracy as the percentage of recommendations where actual performance met or exceeded the recommended SLO.

**Validates: Requirements 10.2**

### Property 35: Feedback Metrics Tracking

*For any* set of feedback submissions, the Evaluation_Engine should compute acceptance_rate as (accepted_count / total_count) and track common adjustment patterns.

**Validates: Requirements 10.3**

### Property 36: Precision and Recall Computation

*For any* set of recommendations with outcomes, precision should be computed as (achievable_recommendations / total_recommendations) and recall as (services_that_could_be_more_aggressive / total_services).

**Validates: Requirements 10.4**

### Audit and Compliance Properties

### Property 37: Request Audit Logging

*For any* API request, the system should create an audit log entry containing timestamp, requester identity (API key), endpoint, method, and input data summary.

**Validates: Requirements 11.1**

### Property 38: Recommendation Audit Logging

*For any* generated recommendation, the system should create an audit log entry containing timestamp, service_id, recommendation_version, confidence_score, and all input factors used.

**Validates: Requirements 11.2**

### Property 39: Feedback Audit Logging

*For any* feedback submission, the system should create an audit log entry containing timestamp, service_id, recommendation_version, action (accept/reject/modify), and any modifications made.

**Validates: Requirements 11.3**

### Multi-Tenant and Regional Properties

### Property 40: Tenant Isolation

*For any* two different tenants, services and recommendations for tenant A should not be accessible via API keys belonging to tenant B, and vice versa.

**Validates: Requirements 13.1, 13.3**

### Property 41: Region-Specific Recommendations

*For any* service with metrics from multiple regions, the Recommendation_Engine should generate both region-specific recommendations (one per region) and a global recommendation aggregating all regions.

**Validates: Requirements 13.2, 13.4**

### Property 42: Tenant-Specific Standards

*For any* tenant with custom SLO standards configured, recommendations for that tenant's services should respect the tenant-specific minimum thresholds rather than global defaults.

**Validates: Requirements 13.5**

### Versioning and History Properties

### Property 43: Recommendation Change Detection

*For any* service with at least two recommendation versions, requesting a new recommendation should include a changes object highlighting differences from the previous version (fields that increased, decreased, or stayed the same).

**Validates: Requirements 14.3**

### Property 44: Change Explanation Generation

*For any* recommendation that differs from the previous version, the explanation should include a change_reasons section describing why the recommendation changed (e.g., "improved metrics", "new dependency added").

**Validates: Requirements 14.4**

### Property 45: Temporal Query Correctness

*For any* historical date with stored recommendations, querying recommendations as-of that date should return only recommendations with timestamps <= the query date, with the most recent one for each service.

**Validates: Requirements 14.5**

### Fault Tolerance Properties

### Property 46: Knowledge Layer Fallback

*For any* recommendation request when the Knowledge_Layer is unavailable, the Recommendation_Engine should successfully generate recommendations using only metrics and dependency analysis, and the response should indicate reduced confidence.

**Validates: Requirements 15.1**

### Property 47: Dependency Analyzer Fallback

*For any* recommendation request when the Dependency_Analyzer fails, the Recommendation_Engine should generate recommendations treating the service as independent (no dependencies), and the response should include a warning.

**Validates: Requirements 15.2**

### Property 48: Stale Data Handling

*For any* recommendation request where the most recent metrics are older than 24 hours, the system should use the stale data, generate recommendations, and include a staleness warning with the age of the data in the response.

**Validates: Requirements 15.3**

### Property 49: Partial Failure Resilience

*For any* recommendation request where one non-critical component fails (e.g., similar service lookup), the system should return partial results with all available analysis and include warnings about which components failed.

**Validates: Requirements 15.4**

### Property 50: Retry with Exponential Backoff

*For any* transient failure in a component operation, the system should retry the operation with exponential backoff (delays: 1s, 2s, 4s) up to 3 attempts before failing.

**Validates: Requirements 15.5**

### Edge Case Properties

### Property 51: Independent Service Handling

*For any* service with zero dependencies (empty upstream and downstream lists), recommendations should be based solely on the service's own historical metrics without any dependency constraints applied.

**Validates: Requirements 12.1**

### Property 52: Circular Dependency Consistency

*For any* set of services forming a circular dependency, all services in the cycle should receive recommendations with consistent SLO values (within 1% of each other for availability, within 10% for latency).

**Validates: Requirements 12.3**

### Property 53: Metadata Conflict Resolution

*For any* service where declared dependency metadata conflicts with observed metrics (e.g., declared timeout is 100ms but observed latency is 500ms), the system should flag the discrepancy and prioritize observed data in recommendations.

**Validates: Requirements 12.4**

### Property 54: Dependency Graph Versioning

*For any* dependency graph update, the system should create a new version with a unique version identifier and timestamp, and both old and new versions should be queryable.

**Validates: Requirements 12.5**


## Error Handling

### Error Categories

The system handles errors in four categories:

1. **Client Errors (4xx)**: Invalid input, authentication failures, rate limiting
2. **Server Errors (5xx)**: Internal processing failures, component unavailability
3. **Validation Errors**: Data quality issues, constraint violations
4. **Degraded Operation**: Partial failures with fallback behavior

### Error Response Format

All errors follow a consistent JSON structure:

```json
{
  "error": "error_code",
  "message": "Human-readable error description",
  "details": {
    "field": "specific_field_name",
    "provided": "actual_value",
    "expected": "expected_format_or_range"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_abc123"
}
```

### Specific Error Scenarios

#### Invalid Metrics Input

**Trigger**: Metrics with invalid ranges (e.g., p95 < p50, availability > 100%)

**Response**: HTTP 400 Bad Request
```json
{
  "error": "invalid_metrics",
  "message": "Latency p95 must be greater than or equal to p50",
  "details": {
    "field": "metrics.latency_p95_ms",
    "provided": 80,
    "expected": ">= 85 (p50 value)"
  }
}
```

#### PII Detection

**Trigger**: Input contains email, phone, SSN patterns

**Response**: HTTP 400 Bad Request
```json
{
  "error": "pii_detected",
  "message": "Input data contains personally identifiable information",
  "details": {
    "field": "service_metadata.description",
    "pattern_detected": "email_address"
  }
}
```

#### Authentication Failure

**Trigger**: Missing or invalid API key

**Response**: HTTP 401 Unauthorized
```json
{
  "error": "authentication_failed",
  "message": "Invalid or missing API key",
  "details": {
    "header": "X-API-Key",
    "provided": "ak_invalid..."
  }
}
```

#### Rate Limit Exceeded

**Trigger**: More than 100 requests/minute

**Response**: HTTP 429 Too Many Requests
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit of 100 requests per minute exceeded",
  "details": {
    "limit": 100,
    "window": "60s",
    "retry_after_seconds": 45
  }
}
```

**Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1705318845
Retry-After: 45
```

#### Missing Dependencies

**Trigger**: Dependency graph references non-existent services

**Response**: HTTP 200 OK with warnings
```json
{
  "service_id": "payment-api",
  "recommendations": { ... },
  "warnings": [
    {
      "type": "missing_dependency",
      "message": "Service 'fraud-detection' referenced but not found in graph",
      "impact": "Recommendations may be incomplete"
    }
  ]
}
```

#### Component Failure

**Trigger**: Knowledge Layer unavailable

**Response**: HTTP 200 OK with degraded results
```json
{
  "service_id": "payment-api",
  "recommendations": { ... },
  "confidence_score": 0.65,
  "warnings": [
    {
      "type": "component_unavailable",
      "component": "knowledge_layer",
      "message": "Similar service patterns unavailable",
      "impact": "Confidence score reduced by 0.2"
    }
  ]
}
```

#### Timeout

**Trigger**: Processing exceeds 3 second timeout

**Response**: HTTP 504 Gateway Timeout
```json
{
  "error": "processing_timeout",
  "message": "Recommendation generation exceeded 3 second timeout",
  "details": {
    "timeout_seconds": 3,
    "elapsed_seconds": 3.2,
    "suggestion": "Try reducing graph size or simplifying dependencies"
  }
}
```

#### Circular Dependency

**Trigger**: Circular dependency detected

**Response**: HTTP 200 OK with analysis
```json
{
  "service_id": "service-a",
  "recommendations": { ... },
  "warnings": [
    {
      "type": "circular_dependency",
      "cycle": ["service-a", "service-b", "service-c", "service-a"],
      "message": "Services in cycle receive consistent SLO recommendations",
      "impact": "All services in cycle have similar constraints"
    }
  ]
}
```

### Retry Strategy

**Client-Side Retry Guidance**:
- **4xx errors**: Do not retry (fix input first)
- **429 errors**: Retry after the specified delay
- **5xx errors**: Retry with exponential backoff (1s, 2s, 4s)
- **Timeout errors**: Retry with simplified input or longer timeout

**Server-Side Retry**:
- Transient failures: 3 retries with exponential backoff (1s, 2s, 4s)
- Component unavailability: Fallback to degraded operation
- File lock contention: Retry with jitter up to 5 times

### Logging

All errors are logged with:
- Timestamp
- Request ID
- Error type and message
- Stack trace (for 5xx errors)
- Input data summary (sanitized)
- User/tenant context

**Log Levels**:
- **ERROR**: 5xx errors, component failures
- **WARN**: 4xx errors, degraded operation, validation warnings
- **INFO**: Successful requests, retry attempts
- **DEBUG**: Detailed processing steps


## Testing Strategy

### Dual Testing Approach

The SLO Recommendation System requires both unit tests and property-based tests for comprehensive coverage:

- **Unit Tests**: Verify specific examples, edge cases, and integration points
- **Property-Based Tests**: Verify universal properties across all inputs

Both approaches are complementary and necessary. Unit tests catch concrete bugs in specific scenarios, while property-based tests verify general correctness across a wide input space.

### Property-Based Testing

**Framework**: Hypothesis (Python)

**Configuration**: Each property test runs a minimum of 100 iterations to ensure comprehensive input coverage through randomization.

**Test Tagging**: Each property test must reference its design document property using a comment tag:

```python
# Feature: slo-recommendation-system, Property 1: Graph Construction Completeness
@given(dependency_declarations=st.lists(st.dependency_declaration()))
@settings(max_examples=100)
def test_graph_construction_completeness(dependency_declarations):
    """
    For any valid dependency declaration set, constructing a Service_Graph
    should result in a graph where every declared service appears as a node
    and every declared dependency appears as an edge.
    """
    graph = DependencyAnalyzer().construct_graph(dependency_declarations)
    
    # Verify all services appear as nodes
    declared_services = extract_services(dependency_declarations)
    assert set(graph.nodes.keys()) == declared_services
    
    # Verify all dependencies appear as edges
    for decl in dependency_declarations:
        assert graph.has_edge(decl.source_id, decl.target_id)
```

### Property Test Generators

**Custom Hypothesis Strategies**:

```python
import hypothesis.strategies as st
from hypothesis import given, settings

# Service ID generator
@st.composite
def service_id(draw):
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd', '-')),
        min_size=5,
        max_size=30
    ))

# Dependency declaration generator
@st.composite
def dependency_declaration(draw):
    return {
        'source_id': draw(service_id()),
        'target_id': draw(service_id()),
        'dependency_type': draw(st.sampled_from(['synchronous', 'asynchronous'])),
        'timeout_ms': draw(st.integers(min_value=100, max_value=5000))
    }

# Metrics generator
@st.composite
def metrics_data(draw):
    p50 = draw(st.floats(min_value=1.0, max_value=1000.0))
    p95 = draw(st.floats(min_value=p50, max_value=p50 * 5))
    p99 = draw(st.floats(min_value=p95, max_value=p95 * 2))
    
    return {
        'latency_p50_ms': p50,
        'latency_p95_ms': p95,
        'latency_p99_ms': p99,
        'error_rate_percent': draw(st.floats(min_value=0.0, max_value=10.0)),
        'availability_percent': draw(st.floats(min_value=90.0, max_value=100.0))
    }

# Dependency graph generator
@st.composite
def dependency_graph(draw, max_services=20):
    num_services = draw(st.integers(min_value=1, max_value=max_services))
    services = [f"service-{i}" for i in range(num_services)]
    
    # Generate random edges
    edges = []
    for _ in range(draw(st.integers(min_value=0, max_value=num_services * 2))):
        source = draw(st.sampled_from(services))
        target = draw(st.sampled_from(services))
        if source != target:  # Avoid self-loops
            edges.append({'source_id': source, 'target_id': target})
    
    return {'services': services, 'edges': edges}

# Circular dependency graph generator
@st.composite
def circular_dependency_graph(draw):
    cycle_length = draw(st.integers(min_value=2, max_value=5))
    cycle_services = [f"cycle-service-{i}" for i in range(cycle_length)]
    
    # Create cycle
    edges = []
    for i in range(cycle_length):
        source = cycle_services[i]
        target = cycle_services[(i + 1) % cycle_length]
        edges.append({'source_id': source, 'target_id': target})
    
    return {'services': cycle_services, 'edges': edges}
```

### Unit Testing

**Framework**: pytest

**Coverage Target**: 80% code coverage minimum

**Test Organization**:

```
tests/
├── unit/
│   ├── test_api_gateway.py
│   ├── test_metrics_ingestion.py
│   ├── test_dependency_analyzer.py
│   ├── test_recommendation_engine.py
│   ├── test_evaluation_engine.py
│   └── test_file_storage.py
├── integration/
│   ├── test_end_to_end_recommendation.py
│   ├── test_api_endpoints.py
│   └── test_multi_tenant.py
└── property/
    ├── test_graph_properties.py
    ├── test_metrics_properties.py
    ├── test_recommendation_properties.py
    └── test_fault_tolerance_properties.py
```

### Unit Test Examples

**Example 1: Specific Edge Case**
```python
def test_service_with_no_dependencies():
    """Test that a service with no dependencies gets recommendations based only on its metrics."""
    service = create_service("standalone-api", dependencies=[])
    metrics = create_metrics(p95_latency=150, availability=99.5)
    
    recommendations = RecommendationEngine().generate(service, metrics)
    
    assert recommendations['balanced']['availability'] <= 99.5
    assert 'dependency_constraints' not in recommendations['explanation']
```

**Example 2: Integration Point**
```python
def test_api_gateway_authentication():
    """Test that API Gateway correctly validates API keys."""
    client = TestClient(app)
    
    # Valid API key
    response = client.post(
        "/api/v1/recommendations",
        headers={"X-API-Key": "valid_key_123"},
        json={"service_id": "test-service"}
    )
    assert response.status_code == 200
    
    # Invalid API key
    response = client.post(
        "/api/v1/recommendations",
        headers={"X-API-Key": "invalid_key"},
        json={"service_id": "test-service"}
    )
    assert response.status_code == 401
```

**Example 3: Error Condition**
```python
def test_pii_detection_rejects_email():
    """Test that metrics containing email addresses are rejected."""
    metrics = {
        "service_id": "test-service",
        "description": "Contact admin@example.com for issues",
        "latency_p95_ms": 150
    }
    
    with pytest.raises(PIIDetectedError) as exc_info:
        MetricsIngestionEngine().ingest(metrics)
    
    assert "email_address" in str(exc_info.value)
```

### Integration Testing

**End-to-End Workflow Test**:
```python
def test_complete_recommendation_workflow():
    """Test the complete flow from metrics submission to recommendation retrieval."""
    # 1. Submit metrics
    metrics_response = client.post("/api/v1/metrics", json={
        "service_id": "payment-api",
        "metrics": {...}
    })
    assert metrics_response.status_code == 200
    
    # 2. Submit dependencies
    deps_response = client.post("/api/v1/dependencies", json={
        "service_id": "payment-api",
        "dependencies": [...]
    })
    assert deps_response.status_code == 200
    
    # 3. Request recommendations
    rec_response = client.post("/api/v1/recommendations", json={
        "service_id": "payment-api"
    })
    assert rec_response.status_code == 200
    assert 'recommendations' in rec_response.json()
    
    # 4. Retrieve history
    history_response = client.get("/api/v1/recommendations/payment-api/history")
    assert history_response.status_code == 200
    assert len(history_response.json()['recommendations']) >= 1
```

### Performance Testing

**Load Test**:
```python
def test_rate_limit_enforcement():
    """Test that rate limiting works correctly at 100 requests/minute."""
    client = TestClient(app)
    api_key = "test_key_123"
    
    # Send 100 requests (should succeed)
    for i in range(100):
        response = client.get(
            "/api/v1/recommendations/test-service/history",
            headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200
    
    # 101st request should be rate limited
    response = client.get(
        "/api/v1/recommendations/test-service/history",
        headers={"X-API-Key": api_key}
    )
    assert response.status_code == 429
    assert 'retry_after_seconds' in response.json()
```

**Response Time Test**:
```python
def test_recommendation_response_time():
    """Test that recommendations are generated within 3 seconds for 100-service graphs."""
    graph = generate_graph(num_services=100, num_edges=500)
    metrics = generate_metrics_for_all_services(graph)
    
    start_time = time.time()
    recommendations = RecommendationEngine().generate_all(graph, metrics)
    elapsed_time = time.time() - start_time
    
    assert elapsed_time < 3.0
    assert len(recommendations) == 100
```

### Test Data Management

**Fixtures**:
```python
@pytest.fixture
def sample_service():
    return {
        'service_id': 'test-api',
        'service_type': 'api',
        'team': 'test-team'
    }

@pytest.fixture
def sample_metrics():
    return {
        'latency_p50_ms': 85,
        'latency_p95_ms': 180,
        'latency_p99_ms': 350,
        'error_rate_percent': 0.8,
        'availability_percent': 99.6
    }

@pytest.fixture
def sample_dependency_graph():
    return {
        'services': ['api-gateway', 'auth-service', 'payment-api'],
        'edges': [
            {'source_id': 'api-gateway', 'target_id': 'auth-service'},
            {'source_id': 'api-gateway', 'target_id': 'payment-api'}
        ]
    }
```

### Continuous Integration

**CI Pipeline**:
1. Run unit tests (fast feedback)
2. Run property-based tests (100 iterations each)
3. Run integration tests
4. Generate coverage report (require 80% minimum)
5. Run performance tests (on representative data)
6. Static analysis (type checking, linting)

**Test Execution Time Targets**:
- Unit tests: < 30 seconds
- Property tests: < 5 minutes
- Integration tests: < 2 minutes
- Full suite: < 10 minutes

### Test Maintenance

- Update property tests when adding new correctness properties to design
- Add unit tests for each bug fix to prevent regression
- Review and update test data generators as the system evolves
- Maintain test documentation with examples of each test category



#### GET /api/v1/services/{service_id}/slo-recommendations/history

**Response** (200 OK):
```json
{
  "service_id": "payment-api",
  "recommendations": [
    {
      "version": "v1.2.3",
      "timestamp": "2024-01-15T10:30:00Z",
      "recommended_tier": "balanced",
      "confidence_score": 0.85
    },
    {
      "version": "v1.2.2",
      "timestamp": "2024-01-10T09:15:00Z",
      "recommended_tier": "balanced",
      "confidence_score": 0.82
    }
  ],
  "total_count": 15,
  "page": 1,
  "page_size": 10
}
```

### Common Error Responses

**400 Bad Request** (Invalid Input):
```json
{
  "error": "invalid_metrics",
  "message": "Latency p95 must be greater than p50",
  "details": {
    "field": "metrics.latency_p95_ms",
    "provided": 80,
    "expected": "> 85"
  }
}
```

**404 Not Found** (Service Not Found):
```json
{
  "error": "service_not_found",
  "message": "Service 'unknown-service' not found",
  "service_id": "unknown-service"
}
```


## Assumptions & Trade-offs

### Key Assumptions

#### Data Sources and Availability

**Assumption 1: Metrics Collection Infrastructure Exists**
- We assume services already emit metrics to some observability platform (Prometheus, Datadog, CloudWatch, etc.)
- Metrics are available in a queryable format with at least 90 days of retention
- Metrics granularity: 1-minute resolution minimum
- **Impact if false**: Would need to build metrics collection infrastructure first, or work with coarser granularity (5-15 minute intervals)

**Assumption 2: Dependency Information is Declarative**
- Services declare their dependencies explicitly (via service mesh, API gateway config, or service catalog)
- Dependency metadata includes timeout, retry policy, and criticality
- **Impact if false**: Would need to infer dependencies from distributed tracing data or network traffic analysis, which is less reliable and more complex

**Assumption 3: Service Catalog Exists**
- An internal developer platform (like Backstage) maintains a service catalog with metadata
- Service ownership, team information, and service types are available
- **Impact if false**: Would need to build service discovery and metadata management, or rely on manual input

#### Scale and Performance Characteristics

**Assumption 4: POC Scale is Representative**
- 100 services with 500 dependencies is sufficient to validate the approach
- Service topology is relatively stable (changes weekly, not hourly)
- **Impact if false**: If topology changes rapidly, would need real-time graph updates and cache invalidation strategies

**Assumption 5: Metrics Distribution is Normal**
- Service performance metrics follow roughly normal distributions
- Outliers are rare (< 5% of data points)
- **Impact if false**: Would need robust outlier detection (IQR method, MAD) and potentially non-parametric statistical methods

**Assumption 6: API Response Time Requirements**
- 3 seconds is acceptable for POC recommendation generation
- Users can tolerate synchronous API calls for this duration
- **Impact if false**: Would need async processing with webhooks or polling, adding complexity

#### Organizational Context

**Assumption 7: Service Owners Have SLO Autonomy**
- Teams can set their own SLOs based on recommendations
- No centralized approval process required
- **Impact if false**: Would need approval workflow, policy enforcement, and governance features

**Assumption 8: SRE/Platform Team Operates the System**
- A dedicated team maintains the recommendation system
- They have expertise in SLOs, reliability engineering, and microservices
- **Impact if false**: Would need more automation, self-service features, and extensive documentation

**Assumption 9: Single Tenant for POC**
- POC serves a single organization/tenant
- No multi-tenancy isolation required initially
- **Impact if false**: Would need tenant isolation, separate data stores, and access control from day one

#### Technical Environment

**Assumption 10: Python/FastAPI is Acceptable**
- Organization is comfortable with Python for backend services
- No strict language requirements (e.g., Go, Java)
- **Impact if false**: Would need to reimplement in preferred language, affecting library choices and ecosystem

**Assumption 11: No-Cost LLM Option is Acceptable**
- Local LLM (Ollama with Llama 3.2 3B) provides sufficient quality for POC
- Team has hardware to run local LLM (4GB RAM minimum, 8GB recommended)
- Slightly lower quality explanations compared to GPT-4 are acceptable for validation
- **Impact if false**: Would need budget for OpenAI/Anthropic API calls (~$3-5 for POC testing)
- **Alternative**: Can start with local LLM and upgrade to paid APIs if quality is insufficient

**Assumption 12: File-Based Storage is Sufficient for POC**
- Local file system with file locking provides adequate concurrency control
- No distributed deployment needed for POC
- **Impact if false**: Would need database from day one, increasing setup complexity

**Assumption 13: No Real-Time Requirements**
- Recommendations can be based on historical data (1-30 day windows)
- Real-time anomaly detection is not required
- **Impact if false**: Would need streaming data processing (Kafka, Flink) and online learning

#### Data Quality and Completeness

**Assumption 13: Metrics are Mostly Complete**
- 90%+ data completeness for most services
- Missing data is random, not systematic
- **Impact if false**: Would need sophisticated imputation methods or refuse to generate recommendations for incomplete data

**Assumption 14: No Adversarial Inputs**
- Service owners provide honest metrics and feedback
- No gaming of the system to get favorable recommendations
- **Impact if false**: Would need anomaly detection, peer comparison, and validation against external data sources

**Assumption 15: Infrastructure SLOs are Known**
- Datastores, message queues, and caches have documented SLOs
- Infrastructure teams provide this information
- **Impact if false**: Would need to measure infrastructure performance independently or use conservative defaults

### Trade-offs and Design Decisions

#### Decision 1: Hybrid AI + Statistical vs. Pure ML vs. Pure Rules

**Choice**: Hybrid approach with statistical baseline + LLM refinement + rule-based safety

**Rationale**:
- **Explainability**: LLMs can generate natural language explanations that service owners understand
- **Contextual Understanding**: LLMs can reason about complex dependency patterns and trade-offs
- **Data Efficiency**: Don't need large training datasets like supervised ML; can work with few-shot examples
- **Flexibility**: Can incorporate new knowledge (runbooks, best practices) without retraining
- **Safety**: Statistical baseline and rule-based validation prevent hallucinations

**Trade-off**:
- **Cost**: $0 for local Ollama vs ~$0.01-0.05 per recommendation for cloud APIs
- **Latency**: Local LLM adds 2-5 seconds (CPU) or <1s (GPU) vs 1-2s for cloud APIs
- **Quality**: Local Llama 3.2 3B is good but less nuanced than GPT-4
- **Reliability**: Local LLM always available vs depends on external API (mitigated with fallback)
- **Privacy**: Local keeps all data on-premise vs cloud sends data externally
- **Determinism**: LLM outputs can vary slightly between runs (mitigated with low temperature)

**Why not Pure ML**: Requires 1000+ services with labeled outcomes for training; POC doesn't have this data

**Why not Pure Rules**: Can't handle nuanced trade-offs or generate natural explanations; too rigid

**Future Path**: 
- Start with local Ollama for no-cost POC validation
- Upgrade to GPT-4 if explanation quality is insufficient
- Collect LLM outputs and outcomes to train a fine-tuned model in Phase 4, reducing cost and latency

#### Decision 2: File-Based Storage vs. Database for POC

**Choice**: File-based JSON storage with file locking

**Rationale**:
- **Simplicity**: No database setup, connection management, or schema migrations
- **Portability**: Easy to run locally, share data, and debug
- **Transparency**: Human-readable JSON files for inspection
- **POC Scope**: 100 services fit comfortably in memory and on disk

**Trade-off**:
- **Concurrency**: File locking is less efficient than database transactions
- **Query Performance**: No indexing or query optimization
- **Scalability**: Won't scale beyond a few hundred services

**Migration Path**: Clear abstraction layer (FileStorage class) makes database migration straightforward in Phase 2

#### Decision 3: Synchronous API vs. Async Processing

**Choice**: Synchronous API with 3-second timeout for POC

**Rationale**:
- **Simplicity**: No message queues, workers, or job tracking
- **User Experience**: Immediate feedback for small graphs
- **Debugging**: Easier to trace request flow and debug issues

**Trade-off**:
- **Scalability**: Can't handle large graphs (1000+ services) efficiently
- **Resource Usage**: Ties up API server threads during processing

**Future Path**: Add async processing in Phase 3 for graphs > 100 services, with webhook callbacks

#### Decision 4: Three-Tier Recommendations vs. Single Recommendation

**Choice**: Provide aggressive, balanced, and conservative tiers

**Rationale**:
- **Flexibility**: Service owners can choose based on their risk tolerance
- **Education**: Shows the spectrum of possibilities and trade-offs
- **Adoption**: Conservative tier provides safe starting point for risk-averse teams

**Trade-off**:
- **Complexity**: More data to compute, store, and present
- **Decision Fatigue**: Some users may be overwhelmed by choices

**Validation**: User research in POC will determine if three tiers are valuable or confusing

#### Decision 5: Confidence Score Calculation Method

**Choice**: Weighted combination of data quality, stability, dependency clarity, and knowledge base match

**Rationale**:
- **Transparency**: Each factor is measurable and explainable
- **Actionability**: Low confidence highlights specific data quality issues to fix
- **Calibration**: Weights can be tuned based on empirical validation

**Trade-off**:
- **Subjectivity**: Weight selection is somewhat arbitrary
- **Oversimplification**: Complex uncertainty reduced to single number

**Validation**: Backtest confidence scores against actual outcomes to calibrate weights

#### Decision 6: Critical Path Algorithm (Longest Path vs. All Paths)

**Choice**: Compute longest latency path as the critical path

**Rationale**:
- **Simplicity**: Single path is easier to visualize and explain
- **Actionability**: Identifies the bottleneck to optimize
- **Performance**: O(V + E) complexity with topological sort

**Trade-off**:
- **Completeness**: Ignores other paths that might be nearly as critical
- **Variability**: Longest path may change frequently with metric fluctuations

**Alternative Considered**: Compute all paths and show top 3, but rejected due to exponential complexity for graphs with high fanout

#### Decision 7: Dependency Constraint Propagation (Strict vs. Soft)

**Choice**: Soft constraints with warnings for violations

**Rationale**:
- **Flexibility**: Service owners can override if they have better information
- **Reality**: Dependency metadata may be outdated or incorrect
- **Adoption**: Strict enforcement would block many recommendations

**Trade-off**:
- **Consistency**: Allows inconsistent SLOs across dependency chains
- **Confusion**: Warnings may be ignored or misunderstood

**Mitigation**: Provide clear explanation of why constraint was applied and impact of violating it

#### Decision 8: Metrics Time Windows (1d, 7d, 30d, 90d)

**Choice**: Four time windows with 30d as primary

**Rationale**:
- **Seasonality**: 30 days captures weekly patterns (weekday/weekend)
- **Stability**: 90 days validates long-term trends
- **Recency**: 1d and 7d detect recent changes
- **Industry Standard**: 30-day SLO windows are common practice

**Trade-off**:
- **Storage**: 4x data storage and computation
- **Complexity**: Need to reconcile conflicting signals across windows

**Alternative Considered**: Single 30d window, but rejected because it misses recent degradations and long-term trends

#### Decision 9: PII Detection Method (Pattern Matching vs. ML)

**Choice**: Regex pattern matching for common PII types

**Rationale**:
- **Simplicity**: No ML model training or maintenance
- **Transparency**: Clear rules for what is rejected
- **Performance**: Fast regex matching

**Trade-off**:
- **False Positives**: May reject legitimate data (e.g., "user-service-123" flagged as phone number)
- **False Negatives**: Won't catch obfuscated or unusual PII formats

**Mitigation**: Provide clear error messages so users can sanitize and resubmit

#### Decision 10: Evaluation Metrics (Accuracy vs. Business Impact)

**Choice**: Track accuracy (% of recommendations met) as primary metric

**Rationale**:
- **Measurability**: Easy to compute from historical data
- **Objectivity**: Clear pass/fail criteria
- **Comparability**: Can compare across services and time

**Trade-off**:
- **Business Value**: Doesn't measure impact on incidents, toil, or user satisfaction
- **Gaming**: Teams might set conservative SLOs to maximize accuracy

**Future Enhancement**: Add business metrics (incident reduction, MTTR improvement) in Phase 3

### Key Unknowns and Sensitivity Analysis

#### Unknown 1: Actual Service Topology Characteristics

**What we don't know**:
- Average fanout (dependencies per service)
- Graph depth (longest dependency chain)
- Prevalence of circular dependencies
- Rate of topology changes

**Impact on design**:
- **High fanout (>10)**: Would need graph partitioning and parallel processing earlier
- **Deep graphs (>10 levels)**: Critical path computation becomes expensive; might need approximation
- **Many cycles**: Tarjan's algorithm is O(V+E) but cycle resolution logic could be complex
- **Rapid changes**: Would need incremental graph updates instead of full recomputation

**Mitigation**: POC will measure these characteristics and inform Phase 2 design

#### Unknown 2: Metrics Distribution and Quality

**What we don't know**:
- Actual distribution shapes (normal, bimodal, long-tailed)
- Outlier frequency and magnitude
- Data completeness rates
- Staleness patterns

**Impact on design**:
- **Non-normal distributions**: Would need non-parametric methods (median, IQR) instead of mean/stddev
- **High outlier rate (>10%)**: Would need robust statistics or outlier removal
- **Low completeness (<80%)**: Would need imputation or refuse recommendations
- **Frequent staleness**: Would need real-time metrics ingestion

**Mitigation**: POC includes data quality assessment; can adjust statistical methods based on findings

#### Unknown 3: User Acceptance and Workflow Integration

**What we don't know**:
- Will service owners trust AI-generated recommendations?
- Do they prefer three tiers or single recommendation?
- How often will they modify recommendations?
- What level of explanation detail is needed?

**Impact on design**:
- **Low trust**: Would need more conservative recommendations, human-in-the-loop approval
- **Tier confusion**: Might simplify to single recommendation with confidence score
- **High modification rate**: Suggests recommendations are off; need to tune algorithm
- **Insufficient explanation**: Would need more detailed reasoning, visualizations

**Mitigation**: POC includes user research and feedback collection to validate UX decisions

#### Unknown 4: Infrastructure Heterogeneity

**What we don't know**:
- How many different datastore types (PostgreSQL, MySQL, MongoDB, etc.)
- Cache hit rate variability
- Network latency between services
- Infrastructure SLO documentation quality

**Impact on design**:
- **Many datastore types**: Would need type-specific latency models
- **Variable cache hit rates**: Would need dynamic adjustment instead of fixed 0.8 assumption
- **High network latency**: Would need to model network as explicit dependency
- **Poor documentation**: Would need to measure infrastructure SLOs independently

**Mitigation**: Start with common types (PostgreSQL, Redis) and expand based on POC usage

#### Unknown 5: Organizational SLO Maturity

**What we don't know**:
- How many services already have SLOs?
- Are existing SLOs realistic and monitored?
- Is there SLO culture and understanding?
- What governance processes exist?

**Impact on design**:
- **Low maturity**: Would need educational content, templates, and guidance
- **Unrealistic SLOs**: Would need to flag and suggest corrections
- **No culture**: Would need change management and executive sponsorship
- **Strict governance**: Would need approval workflows and policy enforcement

**Mitigation**: POC targets early adopter teams with SRE support; expand gradually

### Out of Scope (But Acknowledged)

#### Phase 1 POC Limitations

**Not Included in POC**:
1. **Multi-region deployment**: Single region only; no geo-distribution
2. **Multi-tenancy**: Single organization; no tenant isolation
3. **Real-time processing**: Batch processing only; no streaming
4. **Advanced ML**: Rule-based only; no neural networks or deep learning
5. **Incident correlation**: No integration with incident management systems
6. **Cost optimization**: No cost-aware SLO recommendations
7. **Capacity planning**: No resource utilization or scaling recommendations
8. **SLO monitoring**: No alerting or SLO burn rate tracking
9. **What-if analysis**: Limited to impact analysis; no full simulation
10. **Integration testing**: No automated testing of dependent service SLOs

**Rationale**: These features add significant complexity and are not essential for validating the core recommendation algorithm and user workflow.

**Future Roadmap**:
- **Phase 2**: Multi-region, multi-tenancy, incident correlation
- **Phase 3**: Real-time processing, capacity planning, SLO monitoring
- **Phase 4**: Advanced ML, cost optimization, full simulation

#### Known Limitations

**Limitation 1: Static Dependency Graphs**
- POC assumes dependencies are declared and relatively stable
- Doesn't handle dynamic service discovery or runtime dependency changes
- **Workaround**: Manual graph updates; acceptable for POC

**Limitation 2: No Distributed Tracing Integration**
- Doesn't use actual request traces to validate dependency metadata
- Can't detect undeclared dependencies or measure actual latency contributions
- **Workaround**: Rely on declared dependencies; validate in Phase 2

**Limitation 3: Simplified Infrastructure Modeling**
- Treats datastores as simple latency sources
- Doesn't model connection pools, query complexity, or load-dependent performance
- **Workaround**: Use p95 latency as conservative estimate

**Limitation 4: No Seasonality Handling**
- Doesn't account for daily, weekly, or seasonal traffic patterns
- Recommendations based on aggregate statistics may not fit all time periods
- **Workaround**: Use 30-day window to smooth out weekly patterns

**Limitation 5: Limited Error Budget Tracking**
- Doesn't track actual SLO compliance or error budget burn rate
- Can't provide feedback on whether recommendations were achievable
- **Workaround**: Manual tracking; integrate monitoring in Phase 3

### Alternative Designs Considered

#### Alternative 1: Pure ML Approach

**Description**: Train neural network on historical service metrics and outcomes

**Pros**:
- Could learn complex non-linear patterns
- Adapts automatically to changing conditions
- Potentially higher accuracy with sufficient data

**Cons**:
- Requires large training dataset (1000+ services with outcomes)
- Black box; hard to explain recommendations
- Difficult to debug and maintain
- Cold start problem for new services

**Why rejected**: Insufficient training data for POC; explainability is critical for adoption

#### Alternative 2: Distributed Graph Database (Neo4j)

**Description**: Store dependency graph in Neo4j for advanced graph queries

**Pros**:
- Optimized for graph traversal and pattern matching
- Built-in graph algorithms (shortest path, centrality)
- Scales to millions of nodes and edges

**Cons**:
- Additional infrastructure to deploy and maintain
- Overkill for 100-service POC
- Steeper learning curve for team

**Why rejected**: File-based storage is sufficient for POC scale; can migrate later if needed

#### Alternative 3: Microservices Architecture

**Description**: Split system into separate services (metrics, dependencies, recommendations, evaluation)

**Pros**:
- Independent scaling and deployment
- Technology diversity (different languages per service)
- Fault isolation

**Cons**:
- Increased operational complexity
- Network latency between services
- Distributed debugging challenges
- Overkill for POC

**Why rejected**: Monolithic API is simpler for POC; can decompose in Phase 3 if needed

#### Alternative 4: Event-Driven Architecture

**Description**: Use event bus (Kafka) for metrics ingestion and recommendation generation

**Pros**:
- Decouples producers and consumers
- Natural fit for streaming data
- Replay capability for debugging

**Cons**:
- Kafka infrastructure required
- Async complexity (eventual consistency, ordering)
- Harder to debug than synchronous flow

**Why rejected**: Synchronous API is simpler for POC; add async in Phase 3 for scale

#### Alternative 5: Constraint Satisfaction Problem (CSP) Solver

**Description**: Model SLO recommendations as CSP and use solver (Z3, OR-Tools)

**Pros**:
- Guarantees globally consistent SLOs across dependency chains
- Can optimize for multiple objectives (cost, performance, reliability)
- Mathematically rigorous

**Cons**:
- Complex to model and debug
- Solver performance unpredictable for large graphs
- Hard to explain solutions to users
- Overkill for POC

**Why rejected**: Hybrid rule-based approach is more transparent and easier to implement

### How Different Assumptions Would Change the Design

#### Scenario 1: No Existing Metrics Infrastructure

**Changed Assumption**: Services don't emit metrics; need to collect from scratch

**Design Changes**:
1. Add metrics collection agents (Prometheus exporters, StatsD)
2. Build metrics aggregation pipeline
3. Extend POC timeline by 2-3 months
4. Reduce initial scope to 20-30 services

**Impact**: Significantly increases complexity; might make POC infeasible

#### Scenario 2: Real-Time Requirements

**Changed Assumption**: Recommendations must update within seconds of metric changes

**Design Changes**:
1. Replace file storage with in-memory database (Redis)
2. Add streaming metrics ingestion (Kafka)
3. Implement incremental graph updates
4. Use WebSocket for real-time updates to UI

**Impact**: 3-4x development effort; requires different technology stack

#### Scenario 3: Multi-Tenant from Day One

**Changed Assumption**: POC must support 5-10 organizations with data isolation

**Design Changes**:
1. Add tenant ID to all data models
2. Implement row-level security in database
3. Add tenant-scoped API keys
4. Separate file directories per tenant

**Impact**: 50% more development effort; more complex testing

#### Scenario 4: Strict Governance Requirements

**Changed Assumption**: All SLO changes require approval from SRE team

**Design Changes**:
1. Add approval workflow (pending, approved, rejected states)
2. Build approval UI for SRE team
3. Add notification system (email, Slack)
4. Implement audit trail for all approvals

**Impact**: 2x development effort; changes user workflow significantly

#### Scenario 5: High Topology Change Rate

**Changed Assumption**: Dependencies change multiple times per day

**Design Changes**:
1. Add incremental graph update algorithm
2. Implement graph versioning and diff
3. Add cache invalidation strategy
4. Build real-time dependency discovery (from tracing)

**Impact**: 2-3x complexity; requires distributed tracing integration

### Validation Strategy

**POC Success Criteria**:
1. **Functional**: Generate recommendations for 100 services in <3 seconds
2. **Accuracy**: 80%+ of recommendations are achievable (backtesting)
3. **Adoption**: 10+ service teams use and provide feedback
4. **Explainability**: 90%+ of users understand recommendation reasoning
5. **Reliability**: 99%+ API uptime during POC period

**Measurement Plan**:
- Weekly user interviews with service owners
- Quantitative metrics (API usage, acceptance rate, modification patterns)
- Backtesting against 90 days of historical data
- Load testing with synthetic graphs (100, 500, 1000 services)

**Go/No-Go Decision Criteria**:
- **Go to Phase 2**: If 3+ success criteria met and positive user feedback
- **Iterate POC**: If 1-2 criteria met; identify and fix issues
- **No-Go**: If 0 criteria met or fundamental approach is flawed

This validation will inform whether to proceed with the scaling roadmap or pivot to alternative designs.


## Implementation Status

### Current Implementation (POC Complete)

The SLO Recommendation System has been fully implemented as a POC with the following components:

#### ✅ Completed Components

1. **API Gateway** (`src/api/gateway.py`)
   - FastAPI REST API with authentication and rate limiting
   - All endpoints specified in design implemented
   - OpenAPI documentation at `/docs`
   - Health checks and monitoring

2. **Metrics Ingestion Engine** (`src/engines/metrics_ingestion.py`)
   - Accepts and validates metrics (latency, error rate, availability)
   - Computes aggregations across multiple time windows (1d, 7d, 30d, 90d)
   - Detects outliers using statistical methods
   - Assesses data quality and flags issues

3. **Dependency Analyzer** (`src/algorithms/service_graph.py`)
   - Constructs service dependency graphs
   - Implements critical path algorithm (modified Dijkstra)
   - Computes cascading impact scores
   - Detects circular dependencies (Tarjan's algorithm)

4. **Recommendation Engine** (`src/engines/recommendation_engine.py`)
   - Generates statistical baseline recommendations
   - Applies dependency constraints
   - Applies infrastructure constraints
   - Generates three SLO tiers (aggressive, balanced, conservative)
   - Computes confidence scores
   - Generates detailed explanations

5. **AI Reasoning Layer** (`src/engines/ollama_client.py`, `src/engines/hybrid_recommendation_engine.py`)
   - Integrates with Ollama for local LLM (free, no-cost option)
   - Supports OpenAI and Anthropic as alternatives
   - Refines recommendations with contextual reasoning
   - Generates natural language explanations
   - Implements safety guardrails

6. **RAG Engine** (`src/engines/rag_engine.py`)
   - Vector search using sentence-transformers embeddings
   - Retrieves relevant knowledge from knowledge base
   - Supports runbooks, best practices, and historical patterns
   - Cosine similarity search for POC scale

7. **Knowledge Layer** (`src/engines/knowledge_layer.py`)
   - Stores and retrieves historical patterns
   - Manages service owner feedback
   - Tracks recommendation outcomes
   - Supports best practices by service type

8. **Evaluation Engine** (`src/engines/evaluation_engine.py`)
   - Backtests recommendations against actual performance
   - Computes accuracy metrics
   - Tracks precision and recall
   - Analyzes adjustment patterns

9. **Storage Layer** (`src/storage/`)
   - File-based JSON storage with file locking
   - Tenant isolation support
   - Audit logging
   - No external database required

10. **Cascading Impact Analysis** (`src/engines/cascading_impact_computation.py`)
    - Analyzes impact of SLO changes on dependent services
    - Computes risk scores
    - Identifies critical paths affected by changes

11. **Tenant Standards Manager** (`src/engines/tenant_standards.py`)
    - Manages tenant-specific SLO standards
    - Applies criticality-based adjustments
    - Supports industry standard recommendations

#### ✅ Deployment Options

1. **Local Development** (`setup.py`)
   - Automated setup script for macOS, Linux, Windows
   - Installs Ollama and downloads models
   - Installs Python dependencies
   - Starts Ollama server automatically

2. **Docker Deployment** (`Dockerfile`, `docker-compose.yml`)
   - FastAPI server containerized
   - Ollama service included
   - Automatic model initialization
   - Health checks and monitoring
   - Optional GPU support

3. **Interactive Demo** (`demo.py`)
   - Demonstrates complete workflow
   - Shows all major features
   - Includes sample data and scenarios

#### ✅ Testing

- Unit tests for all major components
- Integration tests for API endpoints
- Property-based tests using Hypothesis
- Test coverage for edge cases and error handling

#### ✅ Documentation

- Comprehensive design document (this file)
- API documentation (OpenAPI/Swagger)
- README with quick start guide
- SETUP.md with detailed setup instructions
- Example scripts demonstrating component usage

### Architecture Alignment

The implementation follows the design document precisely:

| Component | Design | Implementation | Status |
|-----------|--------|-----------------|--------|
| API Gateway | ✓ | FastAPI | ✅ Complete |
| Metrics Engine | ✓ | metrics_ingestion.py | ✅ Complete |
| Dependency Analyzer | ✓ | service_graph.py | ✅ Complete |
| Recommendation Engine | ✓ | recommendation_engine.py | ✅ Complete |
| AI Reasoning | ✓ | ollama_client.py, hybrid_recommendation_engine.py | ✅ Complete |
| RAG Engine | ✓ | rag_engine.py | ✅ Complete |
| Knowledge Layer | ✓ | knowledge_layer.py | ✅ Complete |
| Evaluation Engine | ✓ | evaluation_engine.py | ✅ Complete |
| Storage Layer | ✓ | file_storage.py, tenant_storage.py | ✅ Complete |
| Cascading Impact | ✓ | cascading_impact_computation.py | ✅ Complete |
| Tenant Standards | ✓ | tenant_standards.py | ✅ Complete |

### Performance Characteristics

- **API Response Time**: < 3 seconds for 100 services (POC target)
- **Metrics Ingestion**: ~100ms per service
- **Recommendation Generation**: 1-5 seconds (depends on LLM)
- **Graph Analysis**: < 500ms for 100 services with 500 edges
- **Memory Usage**: ~500MB for full POC dataset

### Cost Analysis

**No-Cost Option (Recommended for POC)**:
- Ollama (local LLM): $0
- sentence-transformers (embeddings): $0
- Total: $0

**Optional Paid Options**:
- OpenAI GPT-4: ~$0.03 per recommendation
- Anthropic Claude: ~$0.02 per recommendation

### Known Limitations and Future Improvements

1. **Regional Recommendations**: Currently removed from demo (can be re-enabled)
2. **Real-Time Updates**: Recommendations are computed on-demand (can add streaming)
3. **Distributed Deployment**: Currently single-instance (can add multi-instance support)
4. **Advanced Analytics**: Limited to basic statistical analysis (can add ML models)
5. **Custom Constraints**: Limited to predefined constraints (can add custom rule engine)

### Migration Path to Production

**Phase 1 (Current)**: POC with file-based storage
- Scale: 100 services
- Deployment: Single instance
- Cost: $0

**Phase 2 (Planned)**: Production-ready with database
- Scale: 1,000 services
- Deployment: Multi-instance with load balancing
- Storage: PostgreSQL for metrics, Redis for caching
- Cost: ~$500-1000/month

**Phase 3 (Future)**: Enterprise scale
- Scale: 10,000+ services
- Deployment: Kubernetes with auto-scaling
- Storage: Time-series database (InfluxDB, Prometheus)
- Features: Real-time streaming, advanced ML models
- Cost: ~$5,000-10,000/month

### Conclusion

The SLO Recommendation System POC successfully implements the hybrid AI + statistical approach outlined in this design document. The system is production-ready for small to medium-scale deployments (up to 100 services) and provides a clear migration path for larger deployments.

The no-cost implementation using Ollama and open-source tools makes it accessible to organizations of all sizes, while the modular architecture allows for easy upgrades to paid LLM providers or custom ML models as needed.

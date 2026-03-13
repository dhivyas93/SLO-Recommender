# SLO Recommendation System - Architecture

> A production-ready system for generating AI-assisted SLO recommendations for microservices at scale.

---

## System Overview

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor':'#667eea', 'primaryTextColor':'#fff', 'primaryBorderColor':'#5568d3', 'lineColor':'#f39c12', 'secondBkgColor':'#f093fb', 'tertiaryColor':'#fff'}}}%%
graph TB
    subgraph Input["📥 INPUT LAYER"]
        direction LR
        Metrics["<b>Service Metrics</b><br/>━━━━━━━━━━━━<br/>• Latency p95/p99<br/>• Error Rate<br/>• Availability"]
        Dependencies["<b>Dependencies</b><br/>━━━━━━━━━━━━<br/>• Service Graph<br/>• Upstream/Downstream<br/>• Criticality"]
    end

    subgraph Processing["⚙️ PROCESSING LAYER"]
        direction LR
        MetricsEngine["<b>Metrics Engine</b><br/>━━━━━━━━━━━━<br/>✓ Aggregate data<br/>✓ Detect outliers<br/>✓ Quality scoring"]
        DepEngine["<b>Dependency Engine</b><br/>━━━━━━━━━━━━<br/>✓ Build graph<br/>✓ Critical paths<br/>✓ Impact analysis"]
        RecEngine["<b>Recommendation<br/>Engine</b><br/>━━━━━━━━━━━━<br/>✓ Statistical baseline<br/>✓ Apply constraints<br/>✓ Generate tiers"]
    end

    subgraph Enhancement["🧠 AI ENHANCEMENT LAYER"]
        direction LR
        RAG["<b>Knowledge Retrieval</b><br/>━━━━━━━━━━━━<br/>📚 Similar services<br/>📚 Best practices<br/>📚 Historical patterns"]
        LLM["<b>LLM Reasoning</b><br/>━━━━━━━━━━━━<br/>🤖 Contextual analysis<br/>🤖 Natural language<br/>🤖 Explanations"]
    end

    subgraph Output["📤 OUTPUT LAYER"]
        direction LR
        Recommendations["<b>SLO Recommendations</b><br/>━━━━━━━━━━━━<br/>🎯 Aggressive Tier<br/>⚖️ Balanced Tier<br/>🛡️ Conservative Tier<br/>━━━━━━━━━━━━<br/>📊 Confidence Score<br/>💬 Explanation"]
    end

    subgraph Storage["💾 STORAGE LAYER"]
        direction LR
        FileStorage["<b>File-Based Storage</b><br/>━━━━━━━━━━━━<br/>📄 JSON Files<br/>🔒 File Locking<br/>📋 Audit Logs<br/>━━━━━━━━━━━━<br/>✓ No Database<br/>✓ Fully Portable"]
    end

    %% Input to Processing
    Metrics -->|Ingest| MetricsEngine
    Dependencies -->|Ingest| DepEngine
    
    %% Processing to Enhancement
    MetricsEngine -->|Baseline| RecEngine
    DepEngine -->|Constraints| RecEngine
    RecEngine -->|Context| RAG
    RecEngine -->|Baseline| LLM
    RAG -->|Knowledge| LLM
    
    %% Enhancement to Output
    LLM -->|Refined| Recommendations
    
    %% Storage connections
    MetricsEngine -->|Store| FileStorage
    DepEngine -->|Store| FileStorage
    RecEngine -->|Store| FileStorage
    LLM -->|Store| FileStorage
    FileStorage -->|Load| MetricsEngine
    FileStorage -->|Load| DepEngine
    FileStorage -->|Load| RecEngine
    FileStorage -->|Load| RAG
    
    %% Styling
    classDef input fill:#e3f2fd,stroke:#1976d2,stroke-width:3px,color:#000
    classDef process fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px,color:#000
    classDef enhance fill:#e8f5e9,stroke:#388e3c,stroke-width:3px,color:#000
    classDef output fill:#fff3e0,stroke:#f57c00,stroke-width:3px,color:#000
    classDef storage fill:#fce4ec,stroke:#c2185b,stroke-width:3px,color:#000
    
    class Metrics,Dependencies input
    class MetricsEngine,DepEngine,RecEngine process
    class RAG,LLM enhance
    class Recommendations output
    class FileStorage storage
```

---

## Component Responsibilities

| Component | Responsibility | Key Functions |
|-----------|-----------------|----------------|
| **Metrics Engine** | Aggregate and analyze service metrics | • Collect latency, error rate, availability<br/>• Detect statistical outliers<br/>• Generate quality scores |
| **Dependency Engine** | Build and analyze service dependencies | • Construct service graph<br/>• Identify critical paths<br/>• Calculate cascading impact |
| **Recommendation Engine** | Generate baseline SLO recommendations | • Statistical baseline calculation<br/>• Apply infrastructure constraints<br/>• Generate 3 SLO tiers |
| **Knowledge Retrieval** | Provide contextual information | • Find similar services<br/>• Retrieve best practices<br/>• Access historical patterns |
| **LLM Reasoning** | Enhance recommendations with AI | • Contextual analysis<br/>• Natural language explanations<br/>• Confidence scoring |

---

## Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as API Gateway
    participant ME as Metrics Engine
    participant DE as Dependency Engine
    participant RE as Recommendation Engine
    participant KB as Knowledge Base
    participant LLM as LLM Engine
    participant Storage as File Storage

    Client->>API: POST /api/generate<br/>(service_id)
    
    API->>Storage: Load service metrics
    API->>Storage: Load dependencies
    
    API->>ME: Analyze metrics
    ME->>Storage: Store analysis
    
    API->>DE: Analyze dependencies
    DE->>Storage: Store graph
    
    API->>RE: Generate baseline
    RE->>Storage: Store baseline
    
    API->>KB: Retrieve context
    KB->>Storage: Load knowledge
    
    API->>LLM: Refine with AI
    LLM->>Storage: Store reasoning
    
    API->>Client: Return recommendations<br/>(3 tiers + confidence)
```

---

## Key Features

```mermaid
graph TB
    System["🎯 SLO Recommendation System"]
    
    System -->|Analyzes| F1["📊 Service Metrics<br/>Latency • Error Rate • Availability"]
    System -->|Understands| F2["🔗 Dependencies<br/>Critical Paths • Cascading Impact"]
    System -->|Generates| F3["🎯 Smart Recommendations<br/>3 Tiers • Confidence Scores"]
    System -->|Explains| F4["💬 Natural Language<br/>Reasoning • Context"]
    System -->|Learns| F5["📚 Knowledge Base<br/>Best Practices • Patterns"]
    System -->|Validates| F6["✅ Safety Guardrails<br/>Achievability • Constraints"]
    
    F1 -->|Powers| Output["✨ Actionable<br/>Recommendations"]
    F2 -->|Powers| Output
    F3 -->|Powers| Output
    F4 -->|Powers| Output
    F5 -->|Powers| Output
    F6 -->|Powers| Output
    
    style System fill:#fff9c4,stroke:#f57f17,stroke-width:3px
    style F1 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style F2 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style F3 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style F4 fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style F5 fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style F6 fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    style Output fill:#fff3e0,stroke:#f57c00,stroke-width:3px
```

---

## Deployment Architecture

```mermaid
graph TB
    subgraph "Development"
        Dev["💻 Local Setup<br/>setup.py<br/>• Ollama<br/>• Models<br/>• Demo"]
    end
    
    subgraph "Staging"
        Docker["🐳 Docker Compose<br/>• API Server<br/>• Ollama Service<br/>• Persistent Storage"]
    end
    
    subgraph "Production"
        K8s["☸️ Kubernetes<br/>• Horizontal Scaling<br/>• High Availability<br/>• Multi-region"]
    end
    
    Dev -->|Validate| Docker
    Docker -->|Deploy| K8s
    
    style Dev fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style Docker fill:#bbdefb,stroke:#1565c0,stroke-width:2px
    style K8s fill:#f8bbd0,stroke:#ad1457,stroke-width:2px
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Python 3.11+ | Core runtime |
| | FastAPI | REST API framework |
| **Data Processing** | Pandas | Metrics aggregation |
| | NumPy | Statistical analysis |
| | NetworkX | Dependency graph |
| **AI/ML** | Ollama | Local LLM inference |
| | Embeddings | Vector search & similarity |
| **Storage** | JSON Files | Persistent storage (no DB) |
| | File Locking | Concurrent access safety |
| **Deployment** | Docker | Containerization |
| | Kubernetes | Orchestration & scaling |

---

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Response Time** | < 3 seconds | Per recommendation |
| **Throughput** | 100+ req/min | Single instance |
| **Scalability** | 100 → 10,000+ services | Linear with K8s |
| **Storage** | ~1 MB per service | JSON-based |
| **Memory** | ~500 MB base | + 100 MB per concurrent request |
| **CPU** | 1-2 cores | Scales horizontally |

---

## Quick Start

### Local Development
```bash
python setup.py
python demo.py
```

### Docker
```bash
docker-compose up
curl http://localhost:8000/api/generate?service_id=api-gateway
```

### Production
```bash
kubectl apply -f k8s/
```

---

## API Reference

### Generate Recommendations
```
POST /api/generate
Query Parameters:
  - service_id: string (required)
  - tenant_id: string (optional)

Response:
{
  "service_id": "api-gateway",
  "recommendations": {
    "aggressive": { "availability": 99.9, "latency_p99": 100 },
    "balanced": { "availability": 99.5, "latency_p99": 150 },
    "conservative": { "availability": 99.0, "latency_p99": 200 }
  },
  "confidence_score": 0.85,
  "explanation": "Based on 30-day metrics and dependency analysis..."
}
```

---

## Data Model

### Service Metrics
```json
{
  "service_id": "api-gateway",
  "timestamp": "2026-03-12T00:00:00Z",
  "metrics": {
    "latency_p95": 45,
    "latency_p99": 120,
    "error_rate": 0.001,
    "availability": 0.9995
  }
}
```

### SLO Recommendation
```json
{
  "service_id": "api-gateway",
  "tier": "balanced",
  "slos": {
    "availability": 99.5,
    "latency_p99": 150,
    "error_rate": 0.01
  },
  "confidence": 0.85,
  "reasoning": "..."
}
```

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **File-based Storage** | Simplicity, portability, no DB ops |
| **Local LLM (Ollama)** | Privacy, cost, offline capability |
| **FastAPI** | Performance, async support, auto-docs |
| **NetworkX** | Graph algorithms, dependency analysis |
| **Pandas** | Data manipulation, statistical analysis |

---

## Known Limitations

- Single-instance LLM (Ollama) may timeout on large services
- File-based storage not suitable for 100k+ concurrent requests
- Confidence scores based on heuristics, not ML models
- Regional recommendations removed (POC scope)

---

## Future Enhancements

- [ ] Distributed LLM inference (vLLM, Ray)
- [ ] PostgreSQL backend for production scale
- [ ] ML-based confidence scoring
- [ ] Multi-tenant isolation & RBAC
- [ ] Webhook notifications for SLO changes
- [ ] Historical trend analysis
- [ ] A/B testing framework


# SLO Recommendation System - POC

An AI-assisted platform that analyzes microservice metrics, dependency graphs, and operational patterns to recommend appropriate Service Level Objectives (SLOs). The system provides explainable, confidence-scored recommendations that account for service dependencies, infrastructure constraints, and cascading failure impacts.

## ⚡ Quick Start

### Option 1: Local Development (Recommended for Testing)

Get up and running in 2 minutes:

```bash
# Run the automated setup (installs Ollama, downloads models, installs dependencies)
python setup.py

# In another terminal, start the demo
python demo.py
```

The setup script handles everything:
- ✅ Installs Ollama (if needed)
- ✅ Downloads AI models (orca-mini, mistral)
- ✅ Installs Python dependencies
- ✅ Starts Ollama server

### Option 2: Docker Deployment (Recommended for Production)

Run everything in Docker with a single command:

```bash
# Start all services (API, Ollama, model initialization)
docker-compose up

# Access the API at http://localhost:8000
# API docs available at http://localhost:8000/docs
```

Docker setup includes:
- ✅ FastAPI server on port 8000
- ✅ Ollama LLM service on port 11434
- ✅ Automatic model download on first run
- ✅ Persistent data volumes
- ✅ Health checks
- ✅ Optional GPU support (uncomment in docker-compose.yml)

### Choosing Your Setup

| Aspect | Local | Docker |
|--------|-------|--------|
| **Use Case** | Development, Testing, Demo | Production, Deployment, API |
| **Setup Time** | 2-5 minutes | 5-10 minutes (first run) |
| **Dependencies** | Python 3.8+, Ollama | Docker, Docker Compose |
| **Data Persistence** | Local filesystem | Docker volumes |
| **Scaling** | Single machine | Container orchestration ready |
| **Access** | CLI demo | REST API |

For detailed setup instructions, see [SETUP.md](SETUP.md)

## 🚀 Running the API Server

If you're using Docker or want to run the API server locally:

```bash
# Option 1: Using Docker (recommended)
docker-compose up

# Option 2: Local API server (requires setup.py first)
python setup.py
uvicorn src.api.gateway:app --host 0.0.0.0 --port 8000
```

Then access:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Example API Calls

```bash
# Get SLO recommendations for a service
curl http://localhost:8000/api/v1/services/api-gateway/slo-recommendations

# Get service metrics
curl http://localhost:8000/api/v1/services/api-gateway/metrics

# Get dependency graph
curl http://localhost:8000/api/v1/dependencies/graph
```

## 📁 Project Structure

```
slo-recommender/
├── src/                          # Core production code
│   ├── engines/                  # Recommendation and analysis engines
│   │   ├── recommendation_engine.py
│   │   ├── hybrid_recommendation_engine.py
│   │   ├── metrics_ingestion.py
│   │   ├── ollama_client.py
│   │   ├── rag_engine.py
│   │   └── ...
│   ├── algorithms/               # Graph algorithms and analysis
│   │   ├── service_graph.py
│   │   └── critical_path.py
│   ├── models/                   # Data models and schemas
│   ├── storage/                  # File storage layer
│   ├── api/                      # FastAPI gateway
│   └── utils/                    # Utility functions
│
├── examples/                     # Educational examples (reference only)
│   ├── hybrid_recommendation_example.py
│   ├── cascading_impact_example.py
│   └── ...
│
├── tests/                        # Unit and integration tests
│   ├── unit/
│   ├── integration/
│   └── property/
│
├── data/                         # File-based storage (JSON)
│   ├── services/
│   ├── dependencies/
│   ├── metrics/
│   ├── recommendations/
│   └── audit_logs/
│
├── docs/                         # Documentation
├── demo.py                       # Interactive demo script
├── setup.py                      # Automated setup script
├── Dockerfile                    # Docker image definition
├── docker-compose.yml            # Docker deployment
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

### Key Directories

- **src/** - All production code (engines, algorithms, API, storage)
- **examples/** - Reference examples for learning (not required for running)
- **tests/** - Test suite (unit, integration, property-based tests)
- **data/** - File-based storage for all system data
- **docs/** - Detailed documentation and implementation notes

## 🎯 POC Scope

This Proof of Concept implementation targets:
- **Scale**: Up to 100 services with 500 dependency edges
- **Storage**: File-based (JSON) - no databases required
- **Cost**: $0 using local LLM and open-source tools
- **Performance**: API responses within 3 seconds
- **Deployment**: Runnable locally with minimal dependencies

## 🏗️ System Architecture

The SLO Recommendation System consists of several interconnected components:

```
┌─────────────────────────────────────────────────────────────┐
│                    External Systems                          │
│  Developer Platform (Backstage) | Service Owners | LLM API  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    API Gateway (FastAPI)                     │
│  Authentication | Rate Limiting | Request Routing           │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬──────────────┐
        │            │            │              │
┌───────▼──┐  ┌──────▼──┐  ┌─────▼──┐  ┌──────▼──┐
│ Metrics  │  │Dependency│  │Recommend│  │Evaluation│
│ Ingestion│  │ Analyzer │  │ Engine  │  │ Engine   │
└──────────┘  └──────────┘  └─────────┘  └──────────┘
        │            │            │              │
        └────────────┼────────────┼──────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──┐  ┌──────▼──┐  ┌─────▼──┐
│   AI     │  │   RAG   │  │Knowledge│
│ Reasoning│  │ Engine  │  │  Layer  │
└──────────┘  └─────────┘  └─────────┘
        │            │            │
        └────────────┼────────────┘
                     │
        ┌────────────▼────────────┐
        │   File-Based Storage    │
        │  (JSON, no database)    │
        └─────────────────────────┘
```

### Key Components

1. **API Gateway**: REST API with authentication and rate limiting
2. **Metrics Ingestion Engine**: Processes operational metrics
3. **Dependency Analyzer**: Constructs graphs and computes critical paths
4. **Recommendation Engine**: Generates SLO recommendations
5. **AI Reasoning Layer**: LLM-powered explanation generation
6. **RAG Engine**: Retrieves relevant knowledge for context
7. **Evaluation Engine**: Validates recommendation quality

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.11 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: ~3GB for Ollama and models
- **OS**: macOS, Linux, or Windows

### 1. Install Ollama (Local LLM)

Ollama provides free, local LLM inference with no API costs.

**macOS / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download and install from [ollama.com/download](https://ollama.com/download)

**Verify installation:**
```bash
ollama --version
```

### 2. Pull the Llama 3.2 3B Model

This downloads the ~2GB quantized model optimized for CPU inference:

```bash
ollama pull llama3.2:3b-instruct-q4_0
```

**Start Ollama server** (runs on `localhost:11434`):
```bash
ollama serve
```

Keep this terminal open, or run Ollama as a background service.

### 3. Clone and Setup the Project

```bash
# Clone the repository
git clone <repository-url>
cd slo-recommendation-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Initialize Data Directory

```bash
# Create data directory structure
mkdir -p data/{services,dependencies,recommendations,knowledge,audit_logs}
mkdir -p data/knowledge/{runbooks,best_practices,historical,embeddings}
mkdir -p data/ai_reasoning/{prompts,responses}

# Create sample API key (for testing)
echo '{
  "api_keys": [
    {
      "key": "test-key-12345",
      "tenant_id": "demo-tenant",
      "created_at": "2024-01-01T00:00:00Z",
      "rate_limit": 100
    }
  ]
}' > data/api_keys.json
```

### 5. Run the API Server

```bash
uvicorn src.api.gateway:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Spec**: http://localhost:8000/api/v1/docs

### 6. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Get SLO recommendations (example)
curl -X GET "http://localhost:8000/api/v1/services/payment-api/slo-recommendations" \
  -H "X-API-Key: test-key-12345"
```

## 📦 What's Included

### Core Components

1. **API Gateway** (`src/api/gateway.py`)
   - REST API with FastAPI
   - API key authentication
   - Rate limiting (100 req/min)
   - OpenAPI documentation

2. **Metrics Ingestion Engine** (`src/engines/metrics_ingestion.py`)
   - Accepts latency, error rate, availability metrics
   - Validates and processes data
   - Computes aggregated statistics

3. **Dependency Analyzer** (`src/engines/dependency_analyzer.py`)
   - Constructs service dependency graphs
   - Detects circular dependencies
   - Computes critical paths
   - Calculates cascading impact scores

4. **Recommendation Engine** (`src/engines/recommendation_engine.py`)
   - Hybrid statistical + AI approach
   - Generates three tiers: aggressive, balanced, conservative
   - Provides confidence scores and explanations

5. **AI Reasoning Layer** (`src/engines/ai_reasoning.py`)
   - Integrates with Ollama for local LLM inference
   - Generates natural language explanations
   - Contextual recommendation refinement

6. **RAG Engine** (`src/engines/rag_engine.py`)
   - Retrieval-Augmented Generation
   - Uses sentence-transformers for embeddings
   - Searches runbooks and best practices

7. **Evaluation Engine** (`src/engines/evaluation_engine.py`)
   - Backtesting and accuracy metrics
   - Tracks recommendation outcomes
   - Analyzes feedback patterns

## 🛠️ Technology Stack

### Core Framework
- **FastAPI**: Modern async web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation

### Data Processing
- **NetworkX**: Graph algorithms (critical path, cycle detection)
- **NumPy/Pandas**: Statistical analysis (optional, can use built-in statistics)

### AI/ML (No-Cost Options)
- **Ollama**: Local LLM inference (Llama 3.2 3B)
- **sentence-transformers**: Local embeddings (all-MiniLM-L6-v2, 86MB)
- **scikit-learn**: Cosine similarity for vector search

### Testing
- **pytest**: Unit and integration tests
- **Hypothesis**: Property-based testing

## 💰 Cost Comparison

### No-Cost Setup (Recommended for POC)
- **LLM**: Ollama with Llama 3.2 3B - **$0**
- **Embeddings**: sentence-transformers - **$0**
- **Infrastructure**: Local deployment - **$0**
- **Total**: **$0/month**

### Optional Paid Upgrades
- **OpenAI GPT-4**: ~$0.03 per recommendation (~$3 for 100 recommendations)
- **Anthropic Claude**: ~$0.02 per recommendation (~$2 for 100 recommendations)

**Performance Trade-offs:**
- **Local Llama 3.2 3B**: 2-5s on CPU, <1s on GPU, all data stays local
- **OpenAI GPT-4**: 1-2s response time, better reasoning quality
- **Anthropic Claude**: 1-2s response time, alternative paid option

## 📊 Hardware Requirements

### Minimum (CPU-only)
- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 5GB
- **Performance**: 3-5 seconds per recommendation

### Recommended
- **CPU**: 4+ cores
- **RAM**: 8GB
- **Disk**: 10GB
- **Performance**: 2-3 seconds per recommendation

### Optimal (with GPU)
- **GPU**: NVIDIA GPU with 4GB+ VRAM
- **RAM**: 8GB
- **Performance**: <1 second per recommendation

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# LLM Configuration
LLM_PROVIDER=local              # Options: local, openai, anthropic
LLM_MODEL=llama3.2:3b-instruct-q4_0
OLLAMA_ENDPOINT=http://localhost:11434/api/generate

# Optional: Paid LLM Providers (comment out for no-cost POC)
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Data Storage
DATA_PATH=./data

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
```

### Switching to Paid LLM Providers

To use OpenAI or Anthropic instead of Ollama:

1. **Install the provider SDK:**
```bash
pip install openai  # For OpenAI
# OR
pip install anthropic  # For Anthropic
```

2. **Update `.env`:**
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=sk-your-key-here
```

3. **Restart the server:**
```bash
uvicorn src.api.gateway:app --reload
```

## 📖 API Usage Examples

### 1. Submit Service Metrics

```bash
curl -X POST "http://localhost:8000/api/v1/services/payment-api/metrics" \
  -H "X-API-Key: test-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
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
      }
    }
  }'
```

### 2. Submit Dependency Graph

```bash
curl -X POST "http://localhost:8000/api/v1/services/dependencies" \
  -H "X-API-Key: test-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "services": [
      {
        "service_id": "api-gateway",
        "dependencies": [
          {
            "target_service_id": "auth-service",
            "dependency_type": "synchronous",
            "timeout_ms": 500,
            "criticality": "high"
          },
          {
            "target_service_id": "payment-api",
            "dependency_type": "synchronous",
            "timeout_ms": 1000,
            "criticality": "high"
          }
        ]
      }
    ]
  }'
```

### 3. Get SLO Recommendations

```bash
curl -X GET "http://localhost:8000/api/v1/services/payment-api/slo-recommendations" \
  -H "X-API-Key: test-key-12345"
```

**Response:**
```json
{
  "service_id": "payment-api",
  "version": "v1.0.0",
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
    "summary": "Balanced tier recommended based on stable 30-day performance",
    "top_factors": [
      "Historical p95 latency: 180ms (30-day window)",
      "Downstream of auth-service (99.9% availability) requires margin",
      "PostgreSQL datastore adds 50ms baseline latency"
    ]
  }
}
```

### 4. Accept or Modify Recommendation

```bash
curl -X POST "http://localhost:8000/api/v1/services/payment-api/slos" \
  -H "X-API-Key: test-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept",
    "tier_selected": "balanced",
    "comments": "Looks reasonable based on our traffic patterns"
  }'
```

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run property-based tests
pytest tests/property/

# Run with coverage
pytest --cov=src --cov-report=html
```

## 🐳 Docker Deployment

The easiest way to run the SLO Recommendation System is with Docker Compose, which automatically sets up both the API server and Ollama LLM.

### Prerequisites

- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **RAM**: 6GB minimum (4GB for Ollama + 2GB for API)
- **Disk**: 5GB for images and models

### Quick Start with Docker Compose

```bash
# Clone the repository
git clone <repository-url>
cd slo-recommendation-system

# Start all services (API + Ollama)
docker-compose up -d

# Wait for Ollama to download the model (first run only, ~2GB)
# This takes 2-5 minutes depending on your internet connection
docker-compose logs -f ollama-init

# Once the model is ready, the API will be available at:
# http://localhost:8000
```

**What happens on first run:**
1. Docker builds the API image
2. Ollama container starts
3. Llama 3.2 3B model is automatically downloaded (~2GB)
4. API server starts and connects to Ollama
5. System is ready to accept requests

### Verify the Deployment

```bash
# Check service status
docker-compose ps

# Test the API
curl http://localhost:8000/health

# View API logs
docker-compose logs -f slo-api

# View Ollama logs
docker-compose logs -f ollama
```

### Docker Compose Services

The `docker-compose.yml` includes:

1. **slo-api**: FastAPI application server
   - Port: 8000
   - Depends on: Ollama
   - Volumes: `./data` (persisted), `./src` (development)

2. **ollama**: Local LLM server
   - Port: 11434
   - Model: Llama 3.2 3B Instruct
   - Volume: `ollama-data` (persisted models)

3. **ollama-init**: One-time model download
   - Pulls the Llama 3.2 3B model on first run
   - Exits after completion

### Managing the Services

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f slo-api

# Rebuild after code changes
docker-compose up -d --build

# Remove all data (including models)
docker-compose down -v
```

### Development Mode

The docker-compose.yml mounts the `./src` directory for live code reloading:

```bash
# Edit code in ./src
# Changes are automatically reflected in the container
# No rebuild needed!

# To disable live reloading (production mode):
# Comment out the volume mount in docker-compose.yml:
# volumes:
#   - ./data:/app/data
#   # - ./src:/app/src  # <-- Comment this line
```

### Using GPU Acceleration (Optional)

If you have an NVIDIA GPU, uncomment the GPU section in `docker-compose.yml`:

```yaml
ollama:
  # ... other config ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

### Switching to Paid LLM Providers

To use OpenAI or Anthropic instead of local Ollama:

1. **Update `docker-compose.yml`:**
```yaml
slo-api:
  environment:
    - LLM_PROVIDER=openai
    - LLM_MODEL=gpt-4-turbo-preview
    - OPENAI_API_KEY=${OPENAI_API_KEY}
  # Remove depends_on: ollama
```

2. **Create `.env` file:**
```bash
OPENAI_API_KEY=sk-your-key-here
```

3. **Restart:**
```bash
docker-compose up -d
```

### Manual Docker Build (without Compose)

If you prefer to run Docker manually:

```bash
# Build the image
docker build -t slo-recommendation-system .

# Run with external Ollama
docker run -d \
  --name slo-api \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e LLM_PROVIDER=local \
  -e OLLAMA_ENDPOINT=http://host.docker.internal:11434 \
  slo-recommendation-system

# Run with OpenAI
docker run -d \
  --name slo-api \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e LLM_PROVIDER=openai \
  -e OPENAI_API_KEY=sk-your-key \
  slo-recommendation-system
```

### Troubleshooting

**Issue: Ollama model download is slow**
- The first run downloads ~2GB. This is normal.
- Check progress: `docker-compose logs -f ollama-init`

**Issue: API can't connect to Ollama**
- Verify Ollama is healthy: `docker-compose ps`
- Check Ollama logs: `docker-compose logs ollama`
- Restart services: `docker-compose restart`

**Issue: Out of memory**
- Increase Docker memory limit to 6GB+
- Docker Desktop → Settings → Resources → Memory

**Issue: Port 8000 already in use**
- Change the port in `docker-compose.yml`:
  ```yaml
  ports:
    - "8080:8000"  # Use port 8080 instead
  ```

## 📈 Scaling Roadmap

This POC is designed with a clear path to production scale:

### Current: POC (100 services)
- File-based storage
- Single-node deployment
- 3s response time

### Phase 2: Small Production (1,000 services)
- PostgreSQL database
- Redis caching
- Async processing

### Phase 3: Medium Production (5,000 services)
- Horizontal scaling
- Graph partitioning
- Message queue (RabbitMQ/Kafka)

### Phase 4: Large Production (10,000+ services)
- Distributed graph processing (Spark/Flink)
- Time-series database (InfluxDB/TimescaleDB)
- Multi-region deployment
- ML-based recommendations

See the [Design Document](.kiro/specs/slo-recommendation-system/design.md) for detailed scaling strategies.

## 📚 Documentation

- **[Requirements](.kiro/specs/slo-recommendation-system/requirements.md)**: Detailed functional requirements
- **[Design](.kiro/specs/slo-recommendation-system/design.md)**: Architecture and component design
- **[Tasks](.kiro/specs/slo-recommendation-system/tasks.md)**: Implementation task list
- **[API Docs](http://localhost:8000/docs)**: Interactive API documentation (when server is running)

## 🤝 Contributing

This is a POC implementation. Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

[Add your license here]

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Issue: Ollama Model Download is Slow

**Symptoms**: First run takes 5-10 minutes, lots of network activity

**Solution**: This is normal. The Llama 3.2 3B model is ~2GB and needs to be downloaded once.
```bash
# Monitor progress
ollama pull llama3.2:3b-instruct-q4_0

# Check if model is already downloaded
ollama list
```

#### Issue: API Can't Connect to Ollama

**Symptoms**: 
```
Error: Failed to connect to Ollama at http://localhost:11434
```

**Solution**:
1. Verify Ollama is running: `ollama serve`
2. Check Ollama is accessible: `curl http://localhost:11434/api/tags`
3. Verify the endpoint in `.env` matches your Ollama setup
4. If using Docker, use `http://ollama:11434` instead of `localhost`

#### Issue: Out of Memory

**Symptoms**:
```
MemoryError: Unable to allocate X GB
```

**Solution**:
1. Increase Docker memory limit to 6GB+
   - Docker Desktop → Settings → Resources → Memory
2. Or reduce model size (use `llama3.2:1b` instead of `3b`)
3. Or use a paid LLM provider (OpenAI/Anthropic)

#### Issue: Port 8000 Already in Use

**Symptoms**:
```
Address already in use: ('0.0.0.0', 8000)
```

**Solution**:
```bash
# Option 1: Use a different port
uvicorn src.api.gateway:app --port 8080

# Option 2: Kill the process using port 8000
lsof -i :8000
kill -9 <PID>

# Option 3: In docker-compose.yml, change:
# ports:
#   - "8080:8000"  # Use 8080 instead
```

#### Issue: API Responses are Slow (>3 seconds)

**Symptoms**: Recommendations take 5+ seconds to generate

**Solution**:
1. Check if Ollama is running on CPU (slow) vs GPU (fast)
   - GPU: <1 second per recommendation
   - CPU: 2-5 seconds per recommendation
2. Use a paid LLM provider for faster responses
3. Reduce the number of services in the dependency graph
4. Check system resources: `top` or `Activity Monitor`

#### Issue: Metrics Validation Fails

**Symptoms**:
```
ValidationError: Metrics validation failed
```

**Solution**:
1. Verify metric ranges:
   - Latency: positive numbers in milliseconds
   - Availability: 0-100 percent
   - Error rate: 0-100 percent
   - p95 >= p50, p99 >= p95
2. Check for PII in metrics (email addresses, phone numbers, SSNs)
3. Review the error message for specific field issues

#### Issue: File Lock Contention

**Symptoms**:
```
FileLockedError: Could not acquire lock on data/services/...
```

**Solution**:
1. This is normal under high concurrency
2. The system automatically retries with exponential backoff
3. If persistent, check for stuck processes: `lsof data/`
4. Remove stale lock files: `find data -name "*.lock" -delete`

#### Issue: Docker Build Fails

**Symptoms**:
```
ERROR: failed to solve with frontend dockerfile.v0
```

**Solution**:
```bash
# Clean up Docker
docker system prune -a

# Rebuild
docker-compose build --no-cache

# Or rebuild specific service
docker-compose build --no-cache slo-api
```

#### Issue: Recommendations Don't Match Expectations

**Symptoms**: Generated SLOs seem too aggressive or too conservative

**Solution**:
1. Check the confidence score (lower = less certain)
2. Review the explanation for influencing factors
3. Verify historical metrics are accurate
4. Check dependency constraints are correct
5. Review the selected tier (aggressive/balanced/conservative)

### Getting Help

1. **Check the logs**:
   ```bash
   # API logs
   docker-compose logs -f slo-api
   
   # Ollama logs
   docker-compose logs -f ollama
   ```

2. **Enable debug logging**:
   ```bash
   # In .env
   LOG_LEVEL=DEBUG
   ```

3. **Test individual components**:
   ```bash
   # Test metrics ingestion
   curl -X POST http://localhost:8000/api/v1/services/test/metrics \
     -H "X-API-Key: test-key-demo-tenant" \
     -H "Content-Type: application/json" \
     -d @test_metrics.json
   
   # Test dependency ingestion
   curl -X POST http://localhost:8000/api/v1/services/dependencies \
     -H "X-API-Key: test-key-demo-tenant" \
     -H "Content-Type: application/json" \
     -d @test_dependencies.json
   ```

4. **Review documentation**:
   - [Design Document](.kiro/specs/slo-recommendation-system/design.md)
   - [Requirements](.kiro/specs/slo-recommendation-system/requirements.md)
   - [API Documentation](http://localhost:8000/docs)

## 🙋 Support

For questions or issues:
- Open an issue in the repository
- Check the [Design Document](.kiro/specs/slo-recommendation-system/design.md) for detailed information
- Review the [API Documentation](http://localhost:8000/docs)
- See the Troubleshooting section above for common issues

## 🎓 Learn More

### About SLOs
- [Google SRE Book - Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Implementing SLOs](https://sre.google/workbook/implementing-slos/)

### About the Technology
- [Ollama Documentation](https://ollama.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [NetworkX Documentation](https://networkx.org/documentation/stable/)
- [Sentence Transformers](https://www.sbert.net/)

---

**Built with ❤️ for SRE teams**

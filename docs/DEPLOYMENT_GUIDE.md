# Deployment Guide

This guide covers deploying the SLO Recommendation System using Docker and Docker Compose.

## Prerequisites

- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **RAM**: 6GB minimum (4GB for Ollama + 2GB for API)
- **Disk**: 5GB for images and models
- **OS**: macOS, Linux, or Windows

## Quick Start with Docker Compose

The easiest way to deploy is with Docker Compose, which automatically sets up both the API server and Ollama LLM.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd slo-recommendation-system
```

### 2. Start Services

```bash
# Start all services (API + Ollama)
docker-compose up -d

# Wait for Ollama to download the model (first run only, ~2GB)
# This takes 2-5 minutes depending on your internet connection
docker-compose logs -f ollama-init

# Once the model is ready, the API will be available at:
# http://localhost:8000
```

### 3. Verify Deployment

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

## Docker Compose Configuration

The `docker-compose.yml` includes three services:

### 1. slo-api Service

**Purpose**: FastAPI application server

**Configuration**:
```yaml
slo-api:
  build: .
  ports:
    - "8000:8000"
  depends_on:
    - ollama
  environment:
    - LLM_PROVIDER=local
    - OLLAMA_ENDPOINT=http://ollama:11434/api/generate
    - LOG_LEVEL=INFO
  volumes:
    - ./data:/app/data              # Persistent data
    - ./src:/app/src                # Live code reloading (dev)
```

**Environment Variables**:
- `LLM_PROVIDER`: local, openai, or anthropic
- `OLLAMA_ENDPOINT`: Ollama server URL
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR
- `API_HOST`: 0.0.0.0 (listen on all interfaces)
- `API_PORT`: 8000
- `RATE_LIMIT_PER_MINUTE`: 100

### 2. ollama Service

**Purpose**: Local LLM inference server

**Configuration**:
```yaml
ollama:
  image: ollama/ollama:latest
  ports:
    - "11434:11434"
  volumes:
    - ollama-data:/root/.ollama
  environment:
    - OLLAMA_HOST=0.0.0.0:11434
```

**Model**: Llama 3.2 3B Instruct (automatically pulled on first run)

### 3. ollama-init Service

**Purpose**: One-time model download

**Configuration**:
```yaml
ollama-init:
  image: ollama/ollama:latest
  depends_on:
    - ollama
  entrypoint: /bin/sh
  command: -c "ollama pull llama3.2:3b-instruct-q4_0"
  environment:
    - OLLAMA_HOST=http://ollama:11434
```

## Environment Configuration

### Create .env File

```bash
# .env
LLM_PROVIDER=local
LLM_MODEL=llama3.2:3b-instruct-q4_0
OLLAMA_ENDPOINT=http://ollama:11434/api/generate

API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

DATA_PATH=/app/data
RATE_LIMIT_PER_MINUTE=100
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | local | LLM provider (local, openai, anthropic) |
| `LLM_MODEL` | llama3.2:3b-instruct-q4_0 | Model identifier |
| `OLLAMA_ENDPOINT` | http://ollama:11434/api/generate | Ollama server URL |
| `OPENAI_API_KEY` | - | OpenAI API key (if using OpenAI) |
| `ANTHROPIC_API_KEY` | - | Anthropic API key (if using Anthropic) |
| `API_HOST` | 0.0.0.0 | API server host |
| `API_PORT` | 8000 | API server port |
| `LOG_LEVEL` | INFO | Logging level |
| `DATA_PATH` | ./data | Data directory path |
| `RATE_LIMIT_PER_MINUTE` | 100 | Rate limit per API key |

## Managing Services

### Start Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d slo-api

# Start with logs
docker-compose up
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop specific service
docker-compose stop slo-api

# Stop and remove volumes
docker-compose down -v
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart slo-api
```

### View Logs

```bash
# View all logs
docker-compose logs

# Follow logs (real-time)
docker-compose logs -f

# View specific service logs
docker-compose logs -f slo-api

# View last 100 lines
docker-compose logs --tail=100
```

### Check Service Status

```bash
# List all services
docker-compose ps

# Inspect service
docker-compose exec slo-api ps aux

# Check resource usage
docker stats
```

## Volume Mounting

### Data Persistence

The `./data` directory is mounted as a volume for persistent storage:

```yaml
volumes:
  - ./data:/app/data
```

**What's stored**:
- Service metadata
- Metrics history
- Dependency graphs
- Recommendations
- Audit logs
- Knowledge base

### Live Code Reloading (Development)

The `./src` directory is mounted for development:

```yaml
volumes:
  - ./src:/app/src
```

**To disable** (production mode):
```yaml
# Comment out this line in docker-compose.yml
# - ./src:/app/src
```

### Ollama Model Cache

Ollama models are stored in a named volume:

```yaml
volumes:
  ollama-data:
```

**To persist models** across container restarts, this volume is automatically managed by Docker.

## Scaling Considerations

### Horizontal Scaling

For multiple API instances:

```yaml
slo-api:
  deploy:
    replicas: 3
  ports:
    - "8000-8002:8000"
```

**Considerations**:
- All instances share the same `./data` volume
- File locking prevents concurrent writes
- For high concurrency, migrate to a database

### Load Balancing

Add a reverse proxy (nginx):

```yaml
nginx:
  image: nginx:latest
  ports:
    - "80:80"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
  depends_on:
    - slo-api
```

### Resource Limits

Set resource limits for containers:

```yaml
slo-api:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G

ollama:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 4G
```

## GPU Acceleration

### Enable GPU Support

Uncomment the GPU section in `docker-compose.yml`:

```yaml
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### Prerequisites

1. **Install NVIDIA Docker runtime**:
```bash
# Ubuntu/Debian
sudo apt-get install nvidia-docker2

# macOS
# Use Docker Desktop with GPU support enabled
```

2. **Verify GPU access**:
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-runtime-ubuntu22.04 nvidia-smi
```

### Performance Impact

- **CPU only**: 2-5 seconds per recommendation
- **GPU**: <1 second per recommendation
- **Memory**: GPU requires 4GB+ VRAM

## Switching LLM Providers

### Using OpenAI

1. **Update docker-compose.yml**:
```yaml
slo-api:
  environment:
    - LLM_PROVIDER=openai
    - LLM_MODEL=gpt-4-turbo-preview
    - OPENAI_API_KEY=${OPENAI_API_KEY}
  # Remove depends_on: ollama
```

2. **Create .env file**:
```bash
OPENAI_API_KEY=sk-your-key-here
```

3. **Restart services**:
```bash
docker-compose up -d
```

### Using Anthropic Claude

1. **Update docker-compose.yml**:
```yaml
slo-api:
  environment:
    - LLM_PROVIDER=anthropic
    - LLM_MODEL=claude-3-sonnet
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
  # Remove depends_on: ollama
```

2. **Create .env file**:
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

3. **Restart services**:
```bash
docker-compose up -d
```

## Manual Docker Build

If you prefer to build and run Docker manually:

### Build Image

```bash
# Build the image
docker build -t slo-recommendation-system .

# Build with specific tag
docker build -t slo-recommendation-system:v1.0.0 .
```

### Run Container

```bash
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

# Run with GPU
docker run -d \
  --name slo-api \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --gpus all \
  slo-recommendation-system
```

### Stop Container

```bash
docker stop slo-api
docker rm slo-api
```

## Troubleshooting

### Issue: Ollama Model Download is Slow

**Symptoms**: First run takes 5-10 minutes

**Solution**: This is normal. Monitor progress:
```bash
docker-compose logs -f ollama-init
```

### Issue: API Can't Connect to Ollama

**Symptoms**: 
```
Error: Failed to connect to Ollama at http://ollama:11434
```

**Solution**:
1. Verify Ollama is running: `docker-compose ps`
2. Check Ollama logs: `docker-compose logs ollama`
3. Restart services: `docker-compose restart`

### Issue: Out of Memory

**Symptoms**:
```
MemoryError: Unable to allocate X GB
```

**Solution**:
1. Increase Docker memory limit to 6GB+
2. Or reduce model size: `ollama pull llama3.2:1b`
3. Or use a paid LLM provider

### Issue: Port 8000 Already in Use

**Symptoms**:
```
Error: bind: address already in use
```

**Solution**:
```bash
# Change port in docker-compose.yml
ports:
  - "8080:8000"  # Use 8080 instead

# Or kill the process using port 8000
lsof -i :8000
kill -9 <PID>
```

### Issue: Docker Build Fails

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
```

### Issue: File Permissions

**Symptoms**:
```
Permission denied: data/services/...
```

**Solution**:
```bash
# Fix permissions
chmod -R 755 data/

# Or run with correct user
docker-compose exec -u root slo-api chown -R 1000:1000 /app/data
```

## Production Deployment

### Security Considerations

1. **Use environment variables** for sensitive data:
```bash
# Don't hardcode API keys
OPENAI_API_KEY=${OPENAI_API_KEY}
```

2. **Enable HTTPS**:
```yaml
# Use a reverse proxy (nginx) with SSL
nginx:
  ports:
    - "443:443"
  volumes:
    - ./ssl:/etc/nginx/ssl
```

3. **Restrict API access**:
```bash
# Use firewall rules
ufw allow 8000/tcp from 10.0.0.0/8
```

4. **Rotate API keys** regularly:
```bash
# Update data/api_keys.json
# Restart services
docker-compose restart
```

### Monitoring

1. **Health checks**:
```yaml
slo-api:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

2. **Logging**:
```bash
# Centralize logs
docker-compose logs -f > logs/app.log
```

3. **Metrics**:
```bash
# Monitor resource usage
docker stats
```

### Backup and Recovery

1. **Backup data**:
```bash
# Backup all data
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Backup specific service
tar -czf backup-payment-api.tar.gz data/services/payment-api/
```

2. **Restore from backup**:
```bash
# Restore all data
tar -xzf backup-20240115.tar.gz

# Restart services
docker-compose restart
```

## Performance Tuning

### Optimize Ollama

```yaml
ollama:
  environment:
    - OLLAMA_NUM_PARALLEL=4
    - OLLAMA_NUM_THREAD=8
```

### Optimize API

```yaml
slo-api:
  environment:
    - WORKERS=4
    - WORKER_CLASS=uvicorn.workers.UvicornWorker
```

### Caching

```yaml
redis:
  image: redis:latest
  ports:
    - "6379:6379"

slo-api:
  depends_on:
    - redis
  environment:
    - REDIS_URL=redis://redis:6379
```

## Cleanup

### Remove All Services

```bash
# Stop and remove all services
docker-compose down

# Remove volumes (data will be deleted)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

### Clean Up Docker

```bash
# Remove unused containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Remove everything
docker system prune -a
```

## Support

For deployment issues:
1. Check the [Troubleshooting Guide](../README.md#-troubleshooting)
2. Review Docker logs: `docker-compose logs`
3. Check Docker documentation: https://docs.docker.com/
4. Open an issue in the repository

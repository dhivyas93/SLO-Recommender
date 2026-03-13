# SLO Recommendation System - Local Setup Guide

This guide will help you set up the SLO Recommendation System locally with Ollama for AI-powered recommendations.

## Quick Start

### macOS / Linux
```bash
chmod +x setup.sh
./setup.sh
```

### Windows
```cmd
setup.bat
```

## Manual Setup

If you prefer to set up manually or the automated script doesn't work, follow these steps:

### 1. Install Ollama

**macOS:**
```bash
# Using Homebrew
brew install ollama

# Or download from https://ollama.ai
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
- Download installer from https://ollama.ai
- Run the installer and follow the prompts

### 2. Start Ollama Server

```bash
ollama serve
```

This starts the Ollama server on `http://localhost:11434`

### 3. Download Models

In a new terminal (while Ollama is running):

```bash
# Recommended: Fast, lightweight model
ollama pull orca-mini

# Alternative: Balanced model
ollama pull mistral

# Alternative: Larger model
ollama pull neural-chat
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Demo

```bash
python demo.py
```

## Troubleshooting

### Ollama Installation Issues

**macOS:**
- If Homebrew installation fails, download the installer from https://ollama.ai
- Make sure you have at least 4GB of free disk space

**Linux:**
- Ensure you have `curl` installed: `sudo apt-get install curl`
- You may need to add Ollama to your PATH after installation

**Windows:**
- Make sure Python is added to PATH during installation
- Run Command Prompt as Administrator if you encounter permission issues

### Model Download Issues

**Slow Download:**
- Model downloads can take 5-15 minutes depending on your internet speed
- orca-mini is the fastest (~1.3GB)
- mistral is balanced (~4.4GB)

**Disk Space:**
- Ensure you have at least 10GB of free disk space for models
- Models are stored in `~/.ollama/models`

**Network Issues:**
- If download fails, try again - Ollama will resume from where it left off
- Check your internet connection

### Demo Execution Issues

**Timeout Errors:**
- First run may be slow as models are loaded into memory
- Subsequent runs will be faster
- If timeouts persist, increase timeout in `src/engines/ollama_client.py`

**JSON Parsing Errors:**
- This usually means the model response wasn't valid JSON
- Try running the demo again - it may be a one-time issue
- The system will fall back to rule-based recommendations if AI fails

**Port Already in Use:**
- If port 11434 is already in use, stop other Ollama instances:
  ```bash
  killall ollama  # macOS/Linux
  taskkill /IM ollama.exe /F  # Windows
  ```

## System Requirements

- **CPU:** 2+ cores recommended
- **RAM:** 4GB minimum, 8GB+ recommended
- **Disk Space:** 10GB+ for models
- **Python:** 3.8+
- **Internet:** Required for initial model download

## Model Comparison

| Model | Size | Speed | Quality | Recommended For |
|-------|------|-------|---------|-----------------|
| orca-mini | 1.3GB | Fast | Good | Quick demos, limited resources |
| mistral | 4.4GB | Medium | Excellent | Balanced performance |
| neural-chat | 4.1GB | Medium | Good | General purpose |
| llama2 | 3.8GB | Medium | Good | Alternative option |

## Changing Models

To use a different model, edit `src/engines/ollama_client.py`:

```python
@dataclass
class OllamaConfig:
    model: str = "orca-mini"  # Change this to your preferred model
```

Then restart the demo.

## Stopping Ollama

**macOS/Linux:**
```bash
killall ollama
```

**Windows:**
```cmd
taskkill /IM ollama.exe /F
```

## Next Steps

1. Read the [README.md](README.md) for system overview
2. Run `python demo.py` to see the system in action
3. Check the [docs/](docs/) folder for detailed documentation

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the logs in `/tmp/ollama.log` (macOS/Linux)
3. Check Ollama documentation at https://ollama.ai

## Performance Tips

1. **First Run:** First model load takes longer (1-2 minutes)
2. **Keep Ollama Running:** Don't stop/start between demos
3. **Close Other Apps:** Free up RAM for better performance
4. **Use orca-mini:** For faster responses on limited hardware
5. **Increase Timeout:** If you have slow hardware, increase timeout in config

## Advanced Configuration

### Custom Ollama Endpoint

If Ollama is running on a different machine:

```python
from src.engines.ollama_client import OllamaClient, OllamaConfig

config = OllamaConfig(
    endpoint="http://192.168.1.100:11434",
    model="orca-mini"
)
client = OllamaClient(config)
```

### Disable AI (Use Rule-Based Only)

```python
from src.engines.hybrid_recommendation_engine import HybridRecommendationEngine

engine = HybridRecommendationEngine(use_ai=False)
```

This will use statistical recommendations without AI refinement.

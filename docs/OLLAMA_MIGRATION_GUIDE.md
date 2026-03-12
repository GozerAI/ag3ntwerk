# Ollama Migration Guide

This guide covers migrating from GPT4All to Ollama for ag3ntwerk local LLM inference.

## Why Ollama?

Ollama is the recommended LLM provider for ag3ntwerk because:

- **Simple Setup**: Single binary, no dependencies
- **Efficient Model Management**: Pull models with one command
- **GPU Acceleration**: Automatic CUDA/Metal support
- **OpenAI-Compatible API**: Drop-in replacement
- **Container-Friendly**: Easy Docker/Kubernetes deployment
- **Active Development**: Frequent updates and new model support

## Quick Start

### 1. Install Ollama

**Windows:**
```powershell
# Run setup script
.\scripts\setup_ollama.ps1

# Or download from https://ollama.ai/download
```

**macOS/Linux:**
```bash
# Run setup script
./scripts/setup_ollama.sh

# Or install directly
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Start the Server

```bash
ollama serve
```

The server runs on `http://localhost:11434` by default.

### 3. Pull Recommended Models

```bash
# Primary reasoning model (2GB)
ollama pull llama3.2:3b

# Fast inference model (2GB)
ollama pull phi3:mini

# Code generation (optional, 4GB)
ollama pull deepseek-coder:6.7b

# Embeddings (optional, 500MB)
ollama pull nomic-embed-text
```

### 4. Verify Setup

```bash
# Check status
ag3ntwerk status

# List available models
ag3ntwerk models
```

## Configuration

ag3ntwerk automatically uses Ollama when available. Configuration in `config/settings.yaml`:

```yaml
llm:
  provider: ollama  # or "gpt4all" for legacy support

  ollama:
    base_url: "http://localhost:11434"
    default_model: null  # Auto-selects if null
    timeout: 300.0  # Longer timeout for local inference

  gpt4all:
    base_url: "http://localhost:4891/v1"
    default_model: null
    timeout: 120.0
```

## Model Recommendations

| Use Case | Model | Size | Notes |
|----------|-------|------|-------|
| General Chat | llama3.2:3b | 2GB | Good balance of speed/quality |
| Fast Inference | phi3:mini | 2GB | Quick responses, lower quality |
| Code Generation | deepseek-coder:6.7b | 4GB | Best for code tasks |
| Analysis | llama3.1:8b | 5GB | Better reasoning |
| Embeddings | nomic-embed-text | 500MB | Vector search |

## API Usage

### Python

```python
from ag3ntwerk.llm import get_provider

async def main():
    # Auto-connect (prefers Ollama)
    provider = get_provider()
    await provider.connect()

    # Generate text
    response = await provider.generate("Hello, world!")
    print(response.content)

    # Chat completion
    from ag3ntwerk.llm.base import Message
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="What is Python?")
    ]
    response = await provider.chat(messages)
    print(response.content)

    # Embeddings
    embedding = await provider.embed("Some text to embed")
    print(f"Embedding dim: {len(embedding)}")

    await provider.disconnect()
```

### Auto-Detection

```python
from ag3ntwerk.llm import auto_connect

async def main():
    # Tries Ollama first, falls back to GPT4All
    provider = await auto_connect()

    if provider:
        print(f"Connected to {provider.name}")
        response = await provider.generate("Hello!")
        await provider.disconnect()
    else:
        print("No LLM provider available")
```

### Task-Specific Model Selection

```python
async def main():
    async with get_provider() as provider:
        # Get best model for code tasks
        code_model = provider.get_model_for_task("code")

        # Get fast model for quick responses
        fast_model = provider.get_model_for_task("fast")

        # Generate with specific model
        response = await provider.generate(
            "Write a Python function",
            model=code_model
        )
```

## Model Tiers

ag3ntwerk automatically categorizes models:

| Tier | Description | Examples |
|------|-------------|----------|
| FAST | Quick, lower quality | phi3:mini, tinyllama, gemma:2b |
| BALANCED | Good balance | llama3.2, mistral, gemma2 |
| POWERFUL | Best quality, slower | llama3.1:70b, mixtral |
| SPECIALIZED | Domain-specific | codellama, sqlcoder, nomic-embed-text |

## Troubleshooting

### Ollama Server Not Running

```bash
# Check if running
curl http://localhost:11434/api/tags

# Start server
ollama serve
```

### No Models Available

```bash
# List models
ollama list

# Pull a model
ollama pull llama3.2
```

### Connection Timeout

Increase timeout in config:

```yaml
llm:
  ollama:
    timeout: 600.0  # 10 minutes for large models
```

### Model Not Found

```python
from ag3ntwerk.core.exceptions import LLMModelNotFoundError

try:
    response = await provider.generate("Hello", model="invalid-model")
except LLMModelNotFoundError as e:
    print(f"Available models: {e.available_models}")
```

### GPU Not Detected

```bash
# Check GPU support
ollama ps

# Pull with specific GPU layers
ollama pull llama3.2 --gpu-layers 32
```

## Migration from GPT4All

1. Install Ollama (see Quick Start)
2. Update `config/settings.yaml`:
   ```yaml
   llm:
     provider: ollama
   ```
3. Pull equivalent models:
   - GPT4All Mistral → `ollama pull mistral`
   - GPT4All Llama → `ollama pull llama3.2`
4. Test with `ag3ntwerk status`

## Docker Deployment

```dockerfile
FROM ollama/ollama

# Pull models during build
RUN ollama pull llama3.2:3b
RUN ollama pull phi3:mini

EXPOSE 11434
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  ag3ntwerk:
    build: .
    environment:
      - OLLAMA_HOST=ollama:11434
    depends_on:
      - ollama

volumes:
  ollama_data:
```

## Performance Tuning

### Memory

```bash
# Limit memory usage
OLLAMA_NUM_PARALLEL=1 ollama serve

# Set context size
ollama run llama3.2 --set parameter num_ctx 2048
```

### GPU

```bash
# Use specific GPU
CUDA_VISIBLE_DEVICES=0 ollama serve

# Set GPU layers
ollama run llama3.2 --gpu-layers 32
```

### Batch Processing

```python
# Process multiple prompts efficiently
async def batch_generate(prompts: list[str]):
    async with get_provider() as provider:
        results = []
        for prompt in prompts:
            response = await provider.generate(prompt)
            results.append(response.content)
        return results
```

## API Reference

### OllamaProvider

| Method | Description |
|--------|-------------|
| `connect()` | Connect to Ollama server |
| `disconnect()` | Disconnect from server |
| `generate(prompt, ...)` | Text generation |
| `chat(messages, ...)` | Chat completion |
| `embed(text, ...)` | Generate embeddings |
| `list_models()` | List available models |
| `pull_model(name)` | Pull model from library |
| `show_model(name)` | Get model info |
| `health_check()` | Check server status |
| `get_model_for_task(task)` | Get best model for task |

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `base_url` | localhost:11434 | Ollama server URL |
| `default_model` | auto | Default model to use |
| `timeout` | 300.0 | Request timeout (seconds) |

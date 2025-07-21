# AI Module Documentation

The AI module provides intelligent assistance for project creation through integration with Ollama, a local AI model server. This module offers contextual help, error recovery suggestions, and project creation guidance while maintaining privacy and performance.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [Performance Considerations](#performance-considerations)
- [Best Practices](#best-practices)

## Overview

The AI module consists of several key components:

- **Ollama Client**: HTTP client for communicating with Ollama server
- **Model Manager**: Discovers and manages available AI models
- **Response Generator**: Generates contextual AI responses
- **Cache Manager**: LRU cache for response persistence
- **Context Collector**: Gathers error context for AI assistance
- **AI Service**: Unified facade for all AI operations

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AI Service                           │
│                    (Facade Pattern)                         │
├─────────────────────────────────────────────────────────────┤
│   Ollama      │   Model      │  Response   │    Cache      │
│   Client      │   Manager    │  Generator  │   Manager     │
├───────────────┼──────────────┼─────────────┼───────────────┤
│   Ollama      │   Context    │   Prompt    │  Platform     │
│   Detector    │  Collector   │  Manager    │   Dirs        │
└───────────────┴──────────────┴─────────────┴───────────────┘
```

## Installation

### Prerequisites

1. **Python 3.9.6+** - Required for the project
2. **Ollama** - Local AI model server

### Installing Ollama

#### macOS
```bash
# Using Homebrew
brew install ollama

# Start Ollama service
ollama serve
```

#### Linux
```bash
# Download and install
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve
```

#### Windows
```bash
# Download installer from https://ollama.ai/download/windows
# Run the installer and start Ollama from the system tray
```

### Pulling Models

```bash
# Pull recommended models
ollama pull llama3.2:3b        # Fast, general purpose
ollama pull codellama:7b       # Code-focused assistance
ollama pull mistral:7b         # Alternative general model
```

## Configuration

### Settings File Configuration

The AI module is configured through `config/settings.json`:

```json
{
  "ai": {
    "enabled": true,
    "ollama": {
      "host": "localhost",
      "port": 11434,
      "timeout": 30.0,
      "max_retries": 3,
      "retry_delay": 1.0
    },
    "models": {
      "preferred": ["llama3.2:3b", "codellama:7b"],
      "fallback": "llama3.2:3b",
      "max_tokens": 2048,
      "temperature": 0.7
    },
    "cache": {
      "enabled": true,
      "max_size": 100,
      "ttl_hours": 24,
      "location": null
    },
    "prompt_templates": {
      "custom_dir": null,
      "cache_templates": true
    }
  }
}
```

### Environment Variables

All AI settings can be overridden with environment variables:

```bash
# Enable/disable AI
export APP_AI_ENABLED=true

# Ollama connection
export APP_AI_OLLAMA_HOST=localhost
export APP_AI_OLLAMA_PORT=11434
export APP_AI_OLLAMA_TIMEOUT=30.0

# Model preferences
export APP_AI_MODELS_PREFERRED=llama3.2:3b,codellama:7b
export APP_AI_MODELS_FALLBACK=llama3.2:3b
export APP_AI_MODELS_TEMPERATURE=0.7

# Cache settings
export APP_AI_CACHE_ENABLED=true
export APP_AI_CACHE_MAX_SIZE=100
export APP_AI_CACHE_TTL_HOURS=24
```

## API Reference

### AIService

The main entry point for AI functionality:

```python
from create_project.ai import AIService
from create_project.config import ConfigManager

# Initialize with configuration
config_manager = ConfigManager()
ai_service = AIService(config_manager)

# Check if AI is available
if ai_service.is_available():
    # Generate help for an error
    response = await ai_service.get_help(
        error_type="FileNotFoundError",
        error_message="Template file not found",
        context={"template": "python-cli", "path": "/templates/python-cli.yaml"}
    )
    print(response.content)
```

### Key Methods

#### `AIService.get_help()`
Generate contextual help for errors:
```python
response = await ai_service.get_help(
    error_type="ValidationError",
    error_message="Invalid project name",
    context={"name": "my-project!", "reason": "special characters"}
)
```

#### `AIService.get_suggestions()`
Get project creation suggestions:
```python
suggestions = await ai_service.get_suggestions(
    project_type="web-app",
    description="React app with TypeScript",
    requirements=["authentication", "database", "API"]
)
```

#### `AIService.stream_response()`
Stream responses for better UX:
```python
async for chunk in ai_service.stream_response(
    prompt="How do I structure a Flask application?",
    max_tokens=500
):
    print(chunk, end="", flush=True)
```

### Model Manager

Discover and manage available models:

```python
from create_project.ai.model_manager import ModelManager

manager = ModelManager(ollama_client)

# List available models
models = await manager.list_models()
for model in models:
    print(f"{model.name} - {model.size_gb:.1f}GB - {model.capabilities}")

# Get models by capability
code_models = await manager.get_models_by_capability(ModelCapability.CODE)
```

### Context Collector

Gather context for AI assistance:

```python
from create_project.ai.context_collector import ErrorContextCollector

collector = ErrorContextCollector()
context = collector.collect_context(
    error=exception,
    project_config=config,
    additional_context={"step": "template_validation"}
)
```

## Usage Examples

### Basic Error Help

```python
# In your error handling code
try:
    generate_project(config)
except ProjectGenerationError as e:
    if ai_service.is_available():
        help_response = await ai_service.get_help(
            error_type=type(e).__name__,
            error_message=str(e),
            context={"config": config.dict()}
        )
        print(f"\n💡 AI Suggestion:\n{help_response.content}")
```

### Project Creation Assistant

```python
# Get AI suggestions for project setup
async def create_project_with_ai():
    # Collect project requirements
    project_info = {
        "type": "python-package",
        "name": "my-awesome-lib",
        "description": "A utility library for data processing",
        "features": ["CLI", "async support", "type hints"]
    }
    
    # Get AI suggestions
    suggestions = await ai_service.get_suggestions(
        project_type=project_info["type"],
        description=project_info["description"],
        requirements=project_info["features"]
    )
    
    print("AI Recommendations:")
    print(suggestions.content)
```

### Streaming Responses

```python
# Stream AI responses for long-form help
async def explain_concept(concept: str):
    prompt = f"Explain {concept} in the context of Python project creation"
    
    print(f"🤖 AI: ", end="", flush=True)
    async for chunk in ai_service.stream_response(prompt):
        print(chunk, end="", flush=True)
    print()  # New line after streaming
```

## Troubleshooting

### Common Issues

#### Ollama Not Found
```
Error: OllamaNotFoundError: Ollama is not installed or not in PATH
```

**Solution**:
1. Verify Ollama is installed: `ollama --version`
2. Ensure Ollama service is running: `ollama serve`
3. Check firewall settings for port 11434

#### Model Not Available
```
Error: ModelNotAvailableError: Model 'llama3.2:3b' not found
```

**Solution**:
```bash
# Pull the required model
ollama pull llama3.2:3b

# List available models
ollama list
```

#### Connection Timeout
```
Error: ResponseTimeoutError: Request to Ollama timed out
```

**Solution**:
1. Increase timeout in configuration
2. Check Ollama service status
3. Verify network connectivity

#### Cache Corruption
```
Error: CacheError: Failed to load cache file
```

**Solution**:
```python
# Clear cache programmatically
ai_service.cache_manager.clear()

# Or delete cache file manually
rm ~/.cache/create-project/ai_responses.json
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Set debug environment variable
export APP_DEBUG=true

# Run with verbose logging
python -m create_project
```

### Health Check

Check AI service health:

```python
# Programmatic health check
status = ai_service.get_status()
print(f"AI Available: {status.available}")
print(f"Ollama Version: {status.ollama_version}")
print(f"Models: {', '.join(status.available_models)}")
print(f"Cache Hits: {status.cache_stats['hits']}")
```

## Performance Considerations

### Response Caching

The AI module implements an LRU cache with TTL expiration:

- **Cache Hit Performance**: <5ms for cached responses
- **Cache Size**: Default 100 entries (configurable)
- **TTL**: 24 hours default (configurable)
- **Persistence**: JSON file with atomic writes

### Model Selection

Choose models based on your needs:

| Model | Size | Speed | Use Case |
|-------|------|-------|----------|
| llama3.2:3b | 2.0GB | Fast | General help, quick responses |
| codellama:7b | 3.8GB | Medium | Code-specific assistance |
| mistral:7b | 4.1GB | Medium | Detailed explanations |
| llama3.2:70b | 40GB | Slow | Complex analysis (not recommended) |

### Connection Pooling

The Ollama client uses connection pooling:
- Max connections: 10
- Connection timeout: 5s
- Keep-alive: enabled

### Thread Safety

All AI components are thread-safe:
- Cache operations use RLock
- Model discovery uses thread-local caching
- HTTP client uses asyncio-safe pooling

## Best Practices

### 1. Model Selection

```python
# Configure preferred models by use case
config = {
    "ai": {
        "models": {
            "preferred": [
                "codellama:7b",     # First choice for code
                "llama3.2:3b",      # Fallback for general
                "mistral:7b"        # Alternative
            ]
        }
    }
}
```

### 2. Error Context

Always provide rich context for better AI assistance:

```python
# Good - provides specific context
context = {
    "template": "fastapi-app",
    "error_step": "dependency_installation",
    "python_version": "3.9.6",
    "dependencies": ["fastapi", "uvicorn", "sqlalchemy"]
}

# Bad - minimal context
context = {"error": "installation failed"}
```

### 3. Graceful Degradation

Always handle AI unavailability:

```python
def get_error_help(error: Exception) -> str:
    """Get help for an error, with or without AI."""
    base_help = get_static_error_help(error)
    
    if ai_service.is_available():
        try:
            ai_help = await ai_service.get_help(
                error_type=type(error).__name__,
                error_message=str(error)
            )
            return f"{base_help}\n\n{ai_help.content}"
        except Exception:
            logger.warning("AI help unavailable", exc_info=True)
    
    return base_help
```

### 4. Response Validation

Validate AI responses before using:

```python
response = await ai_service.get_help(...)

# Check response quality
if response.content and len(response.content) > 50:
    # Use AI response
    display_help(response.content)
else:
    # Fall back to static help
    display_help(get_default_help())
```

### 5. Privacy Considerations

The context collector automatically sanitizes sensitive information:

- User paths are replaced with placeholders
- Credentials are removed
- Personal information is redacted

To disable AI for sensitive projects:

```bash
export APP_AI_ENABLED=false
```

## Development

### Running Tests

```bash
# Run AI module tests
uv run pytest tests/ai/ -v

# Run with coverage
uv run pytest tests/ai/ --cov=create_project.ai

# Run integration tests (requires Ollama)
uv run pytest tests/integration/test_ai_*.py -v
```

### Adding Custom Templates

Create custom prompt templates:

1. Create template file:
```jinja2
{# templates/custom/debugging_help.j2 #}
Help debug this {{ error_type }} error:

Error: {{ error_message }}
{% if context %}
Context:
{% for key, value in context.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Provide specific debugging steps.
```

2. Configure custom directory:
```json
{
  "ai": {
    "prompt_templates": {
      "custom_dir": "~/.config/create-project/ai-templates"
    }
  }
}
```

3. Use custom template:
```python
response = await ai_service.get_response(
    prompt_type="debugging_help",
    variables={"error_type": "ImportError", ...}
)
```

## Contributing

When contributing to the AI module:

1. Follow TDD approach - write tests first
2. Maintain thread safety for GUI compatibility
3. Use type hints and docstrings
4. Handle Ollama unavailability gracefully
5. Preserve user privacy in context collection

---

For more information, see the main project documentation or file an issue on GitHub.
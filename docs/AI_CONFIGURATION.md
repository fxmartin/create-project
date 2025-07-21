# ABOUTME: Documentation for AI service configuration options and settings
# ABOUTME: Provides detailed reference for all AI-related configuration parameters

# AI Service Configuration Guide

This document describes all configuration options available for the AI service in the Project Creator application.

## Configuration Location

AI settings are stored in the main configuration file at:
- **Default location**: `~/.project-creator/config/settings.json`
- **Settings section**: `ai`

## Configuration Options

### Core AI Settings

#### `ai.enabled`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Master switch to enable/disable AI features globally
- **Example**: `"enabled": true`

#### `ai.ollama_url`
- **Type**: `string`
- **Default**: `"http://localhost:11434"`
- **Description**: URL of the Ollama API server
- **Example**: `"ollama_url": "http://localhost:11434"`

#### `ai.ollama_timeout`
- **Type**: `integer`
- **Default**: `30`
- **Description**: Timeout in seconds for Ollama API requests
- **Example**: `"ollama_timeout": 30`

### Caching Configuration

#### `ai.cache_enabled`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable caching of AI responses for improved performance
- **Example**: `"cache_enabled": true`

#### `ai.cache_ttl_hours`
- **Type**: `integer`
- **Default**: `24`
- **Description**: Time-to-live for cached responses in hours
- **Example**: `"cache_ttl_hours": 24`

#### `ai.max_cache_entries`
- **Type**: `integer`
- **Default**: `100`
- **Description**: Maximum number of responses to cache (LRU eviction)
- **Example**: `"max_cache_entries": 100`

### Model Configuration

#### `ai.preferred_models`
- **Type**: `array[string]`
- **Default**: `["codellama:13b", "llama2:13b", "mistral:7b", "codellama:7b", "llama2:7b"]`
- **Description**: Ordered list of preferred models for AI responses
- **Example**: 
  ```json
  "preferred_models": [
      "codellama:13b",
      "llama2:13b",
      "mistral:7b"
  ]
  ```

### Context Collection

#### `ai.context_collection_enabled`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable collection of error context for better AI assistance
- **Example**: `"context_collection_enabled": true`

#### `ai.max_context_size_kb`
- **Type**: `integer`
- **Default**: `4`
- **Description**: Maximum size of error context in kilobytes
- **Example**: `"max_context_size_kb": 4`

### Response Generation

#### `ai.enable_ai_assistance`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable AI assistance for project generation errors
- **Example**: `"enable_ai_assistance": true`

#### `ai.response_quality_check`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable quality validation for AI responses
- **Example**: `"response_quality_check": true`

#### `ai.max_response_tokens`
- **Type**: `integer`
- **Default**: `1000`
- **Description**: Maximum tokens for AI response generation
- **Example**: `"max_response_tokens": 1000`

#### `ai.temperature`
- **Type**: `float`
- **Default**: `0.7`
- **Description**: Temperature for response generation (0.0-1.0, higher = more creative)
- **Example**: `"temperature": 0.7`

#### `ai.top_p`
- **Type**: `float`
- **Default**: `0.9`
- **Description**: Top-p sampling parameter for response generation
- **Example**: `"top_p": 0.9`

#### `ai.stream_responses`
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Enable streaming of AI responses for better UX
- **Example**: `"stream_responses": false`

### Template Configuration

#### `ai.prompt_templates.custom_path`
- **Type**: `string`
- **Default**: `"~/.project-creator/ai-templates"`
- **Description**: Directory for custom AI prompt templates
- **Example**: `"custom_path": "~/.project-creator/ai-templates"`

## Example Configuration

Here's a complete example of AI configuration:

```json
{
    "ai": {
        "enabled": true,
        "ollama_url": "http://localhost:11434",
        "ollama_timeout": 30,
        "cache_enabled": true,
        "cache_ttl_hours": 24,
        "max_cache_entries": 100,
        "preferred_models": [
            "codellama:13b",
            "llama2:13b", 
            "mistral:7b",
            "codellama:7b",
            "llama2:7b"
        ],
        "context_collection_enabled": true,
        "max_context_size_kb": 4,
        "enable_ai_assistance": true,
        "response_quality_check": true,
        "max_response_tokens": 1000,
        "temperature": 0.7,
        "top_p": 0.9,
        "stream_responses": false,
        "prompt_templates": {
            "custom_path": "~/.project-creator/ai-templates"
        }
    }
}
```

## Environment Variables

All AI configuration options can be overridden using environment variables:

```bash
# Enable/disable AI
export APP_AI_ENABLED=true

# Ollama configuration
export APP_AI_OLLAMA_URL=http://localhost:11434
export APP_AI_OLLAMA_TIMEOUT=30

# Cache configuration
export APP_AI_CACHE_ENABLED=true
export APP_AI_CACHE_TTL_HOURS=24

# Model preferences (comma-separated)
export APP_AI_PREFERRED_MODELS=codellama:13b,llama2:13b

# Response generation
export APP_AI_TEMPERATURE=0.7
export APP_AI_MAX_RESPONSE_TOKENS=1000
```

## Disabling AI Features

To completely disable AI features:

1. **Via configuration file**:
   ```json
   {
       "ai": {
           "enabled": false
       }
   }
   ```

2. **Via environment variable**:
   ```bash
   export APP_AI_ENABLED=false
   ```

3. **Via project options** (per-project basis):
   ```python
   options = ProjectOptions(enable_ai_assistance=False)
   ```

## Performance Tuning

### For faster responses:
- Reduce `max_response_tokens`
- Use smaller models (e.g., 7b models)
- Enable caching with longer TTL
- Disable `response_quality_check`

### For better quality:
- Use larger models (e.g., 13b models)
- Increase `max_response_tokens`
- Enable `response_quality_check`
- Adjust `temperature` (lower for consistency, higher for creativity)

## Troubleshooting

### AI features not working:
1. Check Ollama is running: `curl http://localhost:11434/api/version`
2. Verify `ai.enabled` is `true`
3. Check logs for connection errors
4. Ensure models are installed: `ollama list`

### Slow responses:
1. Check network connection to Ollama
2. Consider using smaller models
3. Enable caching
4. Reduce `max_response_tokens`

### Poor quality responses:
1. Use larger models from `preferred_models`
2. Enable `response_quality_check`
3. Increase `max_context_size_kb` for better context
4. Adjust `temperature` settings

## Security Considerations

- **PII Protection**: Error context collection automatically sanitizes personal information
- **API Security**: Ollama runs locally by default, no external API calls
- **Cache Security**: Cached responses are stored locally with appropriate permissions
- **Custom Templates**: Validate custom prompt templates before use
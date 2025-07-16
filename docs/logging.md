# Logging Infrastructure Documentation

## Overview

The logging infrastructure provides comprehensive, structured logging capabilities for the Python Project Creator application. It supports environment-specific configurations, log rotation, colored console output, and component-specific loggers.

## Quick Start

### Basic Usage

```python
from create_project.utils import init_logging, get_default_logger

# Initialize logging (call once at application startup)
init_logging()

# Get the default logger
logger = get_default_logger()

# Log messages
logger.info("Application started")
logger.debug("Debug information", user_id=123)
logger.error("An error occurred", error_code=500)
```

### Component-Specific Loggers

```python
from create_project.utils import get_logger

# Create component-specific loggers
ui_logger = get_logger("ui.wizard")
core_logger = get_logger("core.generator")
template_logger = get_logger("templates.engine")

# Use hierarchical naming
button_logger = get_logger("ui.wizard.button")
```

## Configuration

### Environment Detection

The logging system automatically detects the environment from the `ENVIRONMENT` environment variable:

```bash
# Development environment (default)
export ENVIRONMENT=development
# or
export ENVIRONMENT=dev

# Production environment
export ENVIRONMENT=production
# or
export ENVIRONMENT=prod

# Testing environment
export ENVIRONMENT=testing
# or
export ENVIRONMENT=test
```

### Default Configurations

| Environment | Level | JSON Format | Console Colors | File Output |
|-------------|-------|-------------|----------------|-------------|
| Development | DEBUG | No | Yes | Yes |
| Production | INFO | Yes | No | Yes |
| Testing | WARNING | No | No | Memory only |

### Custom Configuration

```python
from create_project.utils import LoggerConfig, init_logging

# Create custom configuration
config = LoggerConfig(
    level="INFO",
    format_json=True,
    include_context=True,
    log_dir="/custom/log/path",
    max_bytes=5 * 1024 * 1024,  # 5MB
    backup_count=10,
    console_colors=False,
)

# Initialize with custom configuration
init_logging(config)
```

### YAML Configuration

Create a `config/logging.yaml` file for advanced configuration:

```yaml
development:
  level: DEBUG
  format_json: false
  include_context: true
  console_colors: true
  max_bytes: 10485760  # 10MB
  backup_count: 30

production:
  level: INFO
  format_json: true
  include_context: true
  console_colors: false
  max_bytes: 10485760  # 10MB
  backup_count: 30
```

Load from YAML:

```python
from create_project.utils import load_config_from_yaml

config = load_config_from_yaml("config/logging.yaml", "development")
```

## Log Files

### File Structure

```
logs/
├── app.log          # All log messages
├── error.log        # ERROR and CRITICAL messages only
├── debug.log        # All messages (DEBUG level only)
├── app.log.1        # Rotated files
├── app.log.2
└── ...
```

### Log Rotation

- **Size-based rotation**: Files rotate when they exceed `max_bytes` (default: 10MB)
- **Backup retention**: Keeps `backup_count` old files (default: 30)
- **Automatic cleanup**: Old files are automatically deleted

### Log Formats

#### Development Format (Human-readable)
```
2025-07-16 16:20:46 [    INFO] ui.wizard [wizard:start:42]: User started project creation
```

#### Production Format (JSON)
```json
{"timestamp": "2025-07-16 16:20:46", "level": "INFO", "logger": "ui.wizard", "message": "User started project creation", "module": "wizard", "function": "start", "line": 42}
```

## Advanced Features

### Contextual Logging

Add context to log messages:

```python
logger.info("User action performed", 
           user_id=123, 
           action="create_project", 
           project_type="web")
```

### Exception Logging

Log exceptions with full traceback:

```python
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed", operation="risky_operation")
```

### Structured Logging

For advanced structured logging, use the structlog integration:

```python
from create_project.utils import get_logger

logger = get_logger("component")
struct_logger = logger.get_structlog_logger()

struct_logger.info("Event occurred", 
                   event_type="user_action",
                   user_id=123,
                   session_id="abc123")
```

## Performance Considerations

### Best Practices

1. **Use appropriate log levels**: Don't log DEBUG messages in production
2. **Avoid string formatting in log calls**: Use parameterized logging
3. **Use contextual information**: Add relevant context to log messages
4. **Component-specific loggers**: Use hierarchical logger names

### Good Examples

```python
# Good: Parameterized logging
logger.info("User %s created project %s", user_id, project_name)

# Good: Contextual logging
logger.info("Project created", user_id=user_id, project_name=project_name)

# Good: Appropriate level
logger.debug("Database query executed", query=sql, duration=0.05)
```

### Avoid

```python
# Bad: String formatting before logging
logger.info(f"User {user_id} created project {project_name}")

# Bad: Wrong log level
logger.info("Detailed debug information that should be DEBUG level")

# Bad: No context
logger.error("Something went wrong")
```

## Testing

### Test Configuration

```python
from create_project.utils import LoggerConfig, get_logger

# Create test configuration
test_config = LoggerConfig(
    level="WARNING",
    format_json=False,
    include_context=False,
    log_dir="/tmp/test_logs",
    console_colors=False,
)

# Use in tests
logger = get_logger("test_component", test_config)
```

### Testing Log Output

```python
import tempfile
from pathlib import Path

def test_logging():
    with tempfile.TemporaryDirectory() as temp_dir:
        config = LoggerConfig(log_dir=temp_dir)
        logger = get_logger("test", config)
        
        logger.info("Test message")
        
        # Check log file
        log_file = Path(temp_dir) / "app.log"
        assert log_file.exists()
        
        with open(log_file) as f:
            content = f.read()
            assert "Test message" in content
```

## Environment-Specific Setup

### Development Environment

```bash
# Set environment
export ENVIRONMENT=development

# Optional: Enable verbose logging
export LOG_LEVEL=DEBUG
```

Features:
- Colored console output
- DEBUG level logging
- Human-readable format
- All log files created

### Production Environment

```bash
# Set environment
export ENVIRONMENT=production

# Optional: Custom log directory
export LOG_DIR=/var/log/create-project
```

Features:
- JSON structured logging
- INFO level logging
- No console colors
- Optimized for log analysis

### Testing Environment

```bash
# Set environment
export ENVIRONMENT=testing
```

Features:
- WARNING level logging
- No file output (memory only)
- Minimal overhead
- No colors

## Troubleshooting

### Common Issues

#### Log Files Not Created

**Problem**: Log files are not being created
**Solution**: Check that the log directory exists and is writable

```python
from create_project.utils import LoggerConfig
import os

config = LoggerConfig()
print(f"Log directory: {config.log_dir}")
print(f"Directory exists: {config.log_dir.exists()}")
print(f"Directory writable: {os.access(config.log_dir, os.W_OK)}")
```

#### Logging Not Working

**Problem**: No log output appears
**Solution**: Ensure logging is initialized

```python
from create_project.utils import init_logging, get_default_logger

# Initialize logging first
init_logging()

# Then get logger
logger = get_default_logger()
logger.info("Test message")
```

#### Performance Issues

**Problem**: Logging is slow
**Solution**: Check log level and file I/O

```python
# Check current log level
logger = get_default_logger()
print(f"Current level: {logger.config.level}")

# Reduce log level in production
config = LoggerConfig(level="WARNING")
```

### Debug Mode

Enable debug mode for troubleshooting:

```python
import logging

# Enable debug mode for all loggers
logging.getLogger().setLevel(logging.DEBUG)

# Check logger configuration
from create_project.utils import get_default_logger
logger = get_default_logger()
print(f"Logger level: {logger.config.level}")
print(f"Log directory: {logger.config.log_dir}")
```

## API Reference

### Classes

#### LoggerConfig

Configuration class for logging setup.

**Parameters:**
- `level` (str): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `format_json` (bool): Whether to use JSON formatting
- `include_context` (bool): Whether to include contextual information
- `log_dir` (str): Directory for log files
- `max_bytes` (int): Maximum size per log file in bytes
- `backup_count` (int): Number of backup log files to keep
- `console_colors` (bool): Whether to use colored console output

#### StructuredLogger

Main logger class with structured logging support.

**Methods:**
- `debug(message, **kwargs)`: Log debug message
- `info(message, **kwargs)`: Log info message
- `warning(message, **kwargs)`: Log warning message
- `error(message, **kwargs)`: Log error message
- `critical(message, **kwargs)`: Log critical message
- `exception(message, **kwargs)`: Log exception with traceback
- `get_structlog_logger()`: Get structlog logger instance

### Functions

#### init_logging(config=None)

Initialize logging system with specified configuration.

**Parameters:**
- `config` (LoggerConfig, optional): Configuration object

#### get_logger(name, config=None)

Get or create a logger instance.

**Parameters:**
- `name` (str): Logger name
- `config` (LoggerConfig, optional): Configuration object

**Returns:** StructuredLogger instance

#### get_default_logger()

Get the default application logger.

**Returns:** StructuredLogger instance

#### get_default_config(environment=None)

Get default configuration for specified environment.

**Parameters:**
- `environment` (str, optional): Environment name

**Returns:** LoggerConfig instance

#### load_config_from_yaml(config_file=None, environment=None)

Load configuration from YAML file.

**Parameters:**
- `config_file` (str, optional): Path to YAML file
- `environment` (str, optional): Environment name

**Returns:** LoggerConfig instance

#### get_environment()

Detect current environment from environment variables.

**Returns:** str (development, production, or testing)

## Examples

### Basic Application Setup

```python
#!/usr/bin/env python3
"""Example application with logging."""

import sys
from create_project.utils import init_logging, get_default_logger

def main():
    # Initialize logging
    init_logging()
    logger = get_default_logger()
    
    logger.info("Application starting")
    
    try:
        # Your application logic here
        logger.info("Application logic executed successfully")
    except Exception as e:
        logger.exception("Application failed")
        return 1
    
    logger.info("Application completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Component-Based Logging

```python
"""Example component with dedicated logger."""

from create_project.utils import get_logger

class ProjectGenerator:
    def __init__(self):
        self.logger = get_logger("core.generator")
    
    def create_project(self, name, project_type):
        self.logger.info("Creating project", 
                        name=name, 
                        project_type=project_type)
        
        try:
            # Project creation logic
            self.logger.debug("Project structure created")
            self.logger.info("Project created successfully", 
                           name=name)
        except Exception as e:
            self.logger.exception("Project creation failed", 
                                name=name, 
                                error=str(e))
            raise
```

### Configuration-Based Setup

```python
"""Example with custom configuration."""

from create_project.utils import LoggerConfig, init_logging, get_logger

# Custom configuration
config = LoggerConfig(
    level="INFO",
    format_json=True,
    log_dir="/app/logs",
    max_bytes=50 * 1024 * 1024,  # 50MB
    backup_count=5,
)

# Initialize with custom config
init_logging(config)

# Use throughout application
logger = get_logger("myapp")
logger.info("Application configured with custom logging")
```

## Best Practices Summary

1. **Initialize once**: Call `init_logging()` once at application startup
2. **Use component loggers**: Create loggers for each component/module
3. **Include context**: Add relevant metadata to log messages
4. **Choose appropriate levels**: DEBUG for development, INFO for production
5. **Handle exceptions**: Use `logger.exception()` for error handling
6. **Configure for environment**: Use environment-specific configurations
7. **Monitor performance**: Watch log file sizes and rotation
8. **Test logging**: Include logging in your test suite

## Security Considerations

- **Never log sensitive data**: Passwords, API keys, personal information
- **Sanitize user input**: Clean user data before logging
- **Use structured logging**: Makes log analysis safer and easier
- **Rotate logs regularly**: Prevent log files from growing too large
- **Secure log directories**: Ensure proper file permissions

This documentation provides comprehensive coverage of the logging infrastructure. For additional support or questions, refer to the source code in `create_project/utils/logger.py` or the test suite in `tests/test_logger.py`.
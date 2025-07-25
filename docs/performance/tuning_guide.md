# Performance Tuning Guide

This guide provides comprehensive strategies for optimizing the performance of the create-project application. It covers common bottlenecks, optimization techniques, and configuration options to achieve optimal performance.

## Table of Contents

1. [Overview](#overview)
2. [Performance Bottlenecks](#performance-bottlenecks)
3. [Optimization Strategies](#optimization-strategies)
4. [Configuration Options](#configuration-options)
5. [Best Practices](#best-practices)
6. [Monitoring Performance](#monitoring-performance)
7. [Troubleshooting](#troubleshooting)

## Overview

The create-project application is designed with performance in mind, using efficient algorithms and caching strategies. However, performance can vary based on:

- Project size and complexity
- Template complexity
- System resources
- Configuration settings
- External dependencies (Git, virtual environment tools)

### Performance Goals

- **Project Generation**: < 5 seconds for typical projects
- **GUI Responsiveness**: < 100ms for user interactions
- **Memory Usage**: < 100MB for typical operations
- **Startup Time**: < 2 seconds

## Performance Bottlenecks

### 1. Template Rendering

Template rendering can be slow for complex templates with many variables and conditional logic.

**Common Issues:**
- Large number of template files
- Complex Jinja2 expressions
- Nested template includes
- Large variable substitutions

**Symptoms:**
- Slow project generation
- High CPU usage during rendering
- Memory spikes

### 2. File I/O Operations

File system operations are often the slowest part of project generation.

**Common Issues:**
- Creating many small files
- Deep directory structures
- Network file systems
- Antivirus software interference

**Symptoms:**
- Slow directory creation
- File write delays
- Permission errors

### 3. External Tool Integration

Integration with external tools can introduce significant delays.

**Common Issues:**
- Git repository initialization
- Virtual environment creation
- Package installation
- Network operations

**Symptoms:**
- Long pauses during generation
- Timeout errors
- Network-related failures

### 4. GUI Responsiveness

The GUI can become unresponsive during long operations.

**Common Issues:**
- Blocking operations on main thread
- Large data processing in UI
- Inefficient widget updates
- Memory leaks in dialogs

**Symptoms:**
- Frozen UI
- Delayed button responses
- Slow dialog opening

### 5. Memory Usage

Memory usage can spike during certain operations.

**Common Issues:**
- Loading large templates
- Caching too much data
- Memory leaks in long-running operations
- Large variable contexts

**Symptoms:**
- Out of memory errors
- System slowdown
- Application crashes

## Optimization Strategies

### 1. Template Optimization

#### Use Template Caching

Enable template caching to avoid re-parsing templates:

```python
# In settings.json
{
  "template": {
    "enable_cache": true,
    "cache_size": 100,
    "cache_ttl": 3600
  }
}
```

#### Optimize Jinja2 Templates

```jinja2
{# Bad: Complex logic in template #}
{% for item in items %}
  {% if item.type == 'module' and item.visibility == 'public' %}
    {% if item.has_tests and item.coverage > 80 %}
      {{ render_module(item) }}
    {% endif %}
  {% endif %}
{% endfor %}

{# Good: Pre-filter in Python #}
{% for item in public_tested_modules %}
  {{ render_module(item) }}
{% endfor %}
```

#### Minimize Template Files

Combine small template files to reduce I/O operations:

```yaml
# Bad: Many small files
files:
  - path: __init__.py
    content: ""
  - path: utils/__init__.py
    content: ""
  - path: tests/__init__.py
    content: ""

# Good: Use directory creation
structure:
  directories:
    - utils
    - tests
  files:
    # Only files with actual content
```

### 2. File I/O Optimization

#### Batch Operations

```python
# Bad: Individual file operations
for file in files:
    create_file(file)

# Good: Batch operations
with batch_file_operations():
    for file in files:
        queue_file_creation(file)
```

#### Use Efficient Directory Creation

```python
# Enable parallel directory creation
config_manager.set("core.parallel_operations", True)
config_manager.set("core.max_workers", 4)
```

#### Optimize for SSD vs HDD

```json
{
  "performance": {
    "storage_type": "ssd",  // or "hdd"
    "buffer_size": 65536,   // Larger for SSD
    "sync_writes": false    // Disable for better performance
  }
}
```

### 3. External Tool Optimization

#### Git Optimization

```json
{
  "git": {
    "shallow_clone": true,
    "single_branch": true,
    "no_checkout": false,
    "compression_level": 1  // Faster but larger
  }
}
```

#### Virtual Environment Optimization

```json
{
  "venv": {
    "tool_preference": ["uv", "venv"],  // uv is 10x faster
    "system_packages": false,
    "pip_cache": true,
    "parallel_downloads": 4
  }
}
```

#### Skip Optional Operations

```python
# In project creation
create_project(
    template_name="python_library",
    project_name="myproject",
    skip_git=True,  # Skip if not needed
    skip_venv=True,  # Skip if not needed
    skip_install=True  # Skip dependency installation
)
```

### 4. GUI Optimization

#### Enable Lazy Loading

```json
{
  "ui": {
    "lazy_load_templates": true,
    "preload_common_templates": ["python_library", "cli_app"],
    "template_preview_delay": 300  // ms
  }
}
```

#### Optimize Dialog Loading

```python
# Bad: Create dialog every time
def show_settings():
    dialog = SettingsDialog()
    dialog.exec()

# Good: Reuse dialog instance
class Application:
    def __init__(self):
        self._settings_dialog = None
    
    def show_settings(self):
        if not self._settings_dialog:
            self._settings_dialog = SettingsDialog()
        self._settings_dialog.exec()
```

#### Use Progress Indicators

```python
# Always show progress for operations > 1 second
with ProgressDialog("Creating project...") as progress:
    progress.set_total_steps(5)
    for i, step in enumerate(steps):
        progress.update(i, f"Executing {step.name}")
        step.execute()
```

### 5. Memory Optimization

#### Configure Cache Limits

```json
{
  "cache": {
    "template_cache_size": 50,  // Max templates in memory
    "file_cache_size": "100MB",  // Max file cache
    "ai_response_cache": true,
    "ai_cache_size": 100,
    "ai_cache_ttl": 86400
  }
}
```

#### Enable Garbage Collection

```python
# For long-running operations
import gc

def create_many_projects(projects):
    for i, project in enumerate(projects):
        create_project(**project)
        if i % 10 == 0:
            gc.collect()  # Force garbage collection
```

#### Monitor Memory Usage

```python
# Enable memory profiling
if config_manager.get("debug.memory_profiling"):
    from memory_profiler import profile
    
    @profile
    def memory_intensive_operation():
        # Your code here
        pass
```

## Configuration Options

### Performance Profile Presets

Create different profiles for different use cases:

```json
// settings.json
{
  "profiles": {
    "fast": {
      "template.enable_cache": true,
      "core.parallel_operations": true,
      "core.max_workers": 8,
      "git.compression_level": 1,
      "ui.lazy_load_templates": true
    },
    "balanced": {
      "template.enable_cache": true,
      "core.parallel_operations": true,
      "core.max_workers": 4,
      "git.compression_level": 5,
      "ui.lazy_load_templates": false
    },
    "low_memory": {
      "template.enable_cache": false,
      "cache.template_cache_size": 10,
      "cache.file_cache_size": "10MB",
      "core.parallel_operations": false
    }
  },
  "active_profile": "balanced"
}
```

### Environment Variables

Override settings via environment variables:

```bash
# Optimize for CI/CD environments
export CREATE_PROJECT_PROFILE=fast
export CREATE_PROJECT_PARALLEL=true
export CREATE_PROJECT_MAX_WORKERS=16
export CREATE_PROJECT_SKIP_ANIMATIONS=true

# Low memory environments
export CREATE_PROJECT_PROFILE=low_memory
export CREATE_PROJECT_CACHE_DISABLED=true
```

### Command Line Options

```bash
# Fast generation with minimal features
create-project --profile=fast --skip-git --skip-venv myproject

# Debug performance issues
create-project --debug --profile=balanced --benchmark myproject

# Memory-constrained environment
create-project --profile=low_memory --no-cache myproject
```

## Best Practices

### 1. Template Design

- **Keep templates simple**: Avoid complex logic in templates
- **Pre-process data**: Do heavy processing in Python, not Jinja2
- **Minimize file count**: Combine related small files
- **Use template inheritance**: Reduce duplication

### 2. Project Structure

- **Flatten when possible**: Avoid deeply nested directories
- **Group related files**: Reduce directory traversal
- **Use .gitkeep sparingly**: Only for essential empty directories

### 3. Resource Management

- **Close resources**: Always use context managers
- **Limit concurrent operations**: Respect system limits
- **Monitor resource usage**: Use built-in performance monitoring

### 4. Caching Strategy

- **Cache hot paths**: Template metadata, parsed templates
- **Invalidate intelligently**: TTL-based and event-based
- **Monitor cache hit rates**: Adjust sizes based on usage

### 5. Error Handling

- **Fail fast**: Don't retry expensive operations unnecessarily
- **Provide progress**: Keep users informed during long operations
- **Log performance metrics**: Track degradation over time

## Monitoring Performance

### Built-in Performance Monitor

Enable the performance monitor in debug mode:

```bash
create-project --debug myproject
```

This opens the performance dashboard showing:
- Real-time memory usage
- Operation timings
- System resource utilization
- Cache statistics

### Performance Logging

Enable detailed performance logging:

```json
{
  "logging": {
    "performance_logging": true,
    "log_slow_operations": true,
    "slow_operation_threshold": 1000  // ms
  }
}
```

### Benchmarking

Run performance benchmarks:

```bash
# Run all benchmarks
pytest tests/performance/ --benchmark-only

# Run specific benchmark
pytest tests/performance/test_generation_speed.py -k template_rendering

# Compare results
pytest tests/performance/ --benchmark-compare=old_results.json

# Generate HTML report
pytest tests/performance/ --benchmark-only --benchmark-html=report.html
```

### Profiling

Profile specific operations:

```python
# CPU profiling
python -m cProfile -o profile.stats create_project ...
python -m pstats profile.stats

# Memory profiling
mprof run create_project ...
mprof plot

# Line profiling
kernprof -l -v create_project.py
```

## Troubleshooting

### Slow Project Generation

1. **Check template complexity**
   ```bash
   # Analyze template
   python scripts/analyze_template.py path/to/template.yaml
   ```

2. **Profile the operation**
   ```bash
   create-project --profile --benchmark myproject
   ```

3. **Disable optional features**
   ```bash
   create-project --skip-git --skip-venv --no-cache myproject
   ```

### High Memory Usage

1. **Check cache sizes**
   ```python
   from create_project.utils.performance import PerformanceMonitor
   monitor = PerformanceMonitor()
   print(monitor.get_cache_stats())
   ```

2. **Reduce cache limits**
   ```json
   {
     "cache.template_cache_size": 20,
     "cache.file_cache_size": "50MB"
   }
   ```

3. **Enable garbage collection**
   ```python
   import gc
   gc.set_threshold(700, 10, 10)  # More aggressive GC
   ```

### GUI Freezing

1. **Check for blocking operations**
   - Ensure long operations use background threads
   - Add progress indicators

2. **Reduce update frequency**
   ```python
   # Batch UI updates
   with self.batch_updates():
       for item in items:
           self.update_ui(item)
   ```

3. **Profile Qt operations**
   ```bash
   QT_LOGGING_RULES="qt.*.debug=true" create-project-gui
   ```

### Network Timeouts

1. **Increase timeouts**
   ```json
   {
     "network": {
       "timeout": 30,
       "retry_count": 3,
       "retry_delay": 1
     }
   }
   ```

2. **Use offline mode**
   ```bash
   create-project --offline myproject
   ```

3. **Configure proxy**
   ```bash
   export HTTP_PROXY=http://proxy:8080
   export HTTPS_PROXY=http://proxy:8080
   ```

## Conclusion

Performance optimization is an iterative process. Start by:

1. Identifying bottlenecks using profiling tools
2. Applying targeted optimizations
3. Measuring improvements
4. Iterating based on results

Remember that premature optimization is the root of all evil. Focus on:
- User-perceived performance
- Common use cases
- Measurable improvements

For additional help, refer to the [benchmarks documentation](benchmarks.md) for baseline performance metrics and regression detection strategies.
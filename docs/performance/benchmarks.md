# Performance Benchmarks

This document provides baseline performance metrics for the create-project application, including benchmark results, performance targets, and regression detection strategies.

## Table of Contents

1. [Benchmark Overview](#benchmark-overview)
2. [Baseline Metrics](#baseline-metrics)
3. [Performance Test Suite](#performance-test-suite)
4. [Running Benchmarks](#running-benchmarks)
5. [Interpreting Results](#interpreting-results)
6. [Regression Detection](#regression-detection)
7. [Continuous Performance Testing](#continuous-performance-testing)
8. [Historical Trends](#historical-trends)

## Benchmark Overview

The create-project performance test suite measures:

- **Project Generation Speed**: Time to create complete projects
- **Template Rendering Performance**: Speed of template processing
- **File I/O Operations**: Directory and file creation efficiency
- **Memory Usage**: RAM consumption during operations
- **GUI Responsiveness**: UI interaction latency
- **Startup Performance**: Application initialization time

### Test Categories

1. **Unit Performance Tests**: Isolated component benchmarks
2. **Integration Performance Tests**: End-to-end workflow measurements
3. **Stress Tests**: Performance under heavy load
4. **Memory Profiling**: Memory usage and leak detection
5. **Regression Tests**: Comparison against baseline metrics

## Baseline Metrics

### Project Generation Performance

Performance targets for different project templates:

| Template | Target Time | Acceptable Range | Files Created | Directories |
|----------|------------|------------------|---------------|-------------|
| Python Library | < 2.0s | 1.5s - 3.0s | 15-20 | 5-8 |
| CLI Application | < 2.5s | 2.0s - 4.0s | 20-25 | 8-10 |
| Django Web App | < 4.0s | 3.0s - 6.0s | 30-40 | 15-20 |
| Flask Web App | < 3.0s | 2.5s - 5.0s | 25-30 | 10-15 |
| One-off Script | < 1.0s | 0.5s - 2.0s | 3-5 | 1-2 |

### Component Performance

Individual component benchmarks:

| Operation | Target | P50 | P95 | P99 |
|-----------|--------|-----|-----|-----|
| Directory Creation | < 1ms | 0.24ms | 0.8ms | 1.2ms |
| File Write (1KB) | < 2ms | 0.5ms | 1.5ms | 2.5ms |
| Template Parse | < 50ms | 20ms | 45ms | 80ms |
| Template Render | < 100ms | 40ms | 90ms | 150ms |
| Config Load | < 10ms | 3ms | 8ms | 15ms |
| Git Init | < 500ms | 200ms | 450ms | 800ms |
| Venv Create (uv) | < 2s | 0.8s | 1.8s | 3.0s |

### Memory Usage

Expected memory consumption:

| Operation | Baseline | Peak | Acceptable Max |
|-----------|----------|------|----------------|
| Idle State | 30-40 MB | - | 50 MB |
| Template Loading | 40-50 MB | 60 MB | 80 MB |
| Project Generation | 50-60 MB | 80 MB | 100 MB |
| Large Project (100+ files) | 60-80 MB | 120 MB | 150 MB |
| GUI Operations | 80-100 MB | 150 MB | 200 MB |

### GUI Responsiveness

User interface performance targets:

| Interaction | Target | Maximum |
|-------------|--------|---------|
| Button Click Response | < 50ms | 100ms |
| Dialog Open | < 100ms | 200ms |
| Page Navigation | < 150ms | 300ms |
| Form Validation | < 30ms | 50ms |
| Template Preview Update | < 200ms | 500ms |
| Progress Update | < 16ms | 33ms |

## Performance Test Suite

### Test Structure

```
tests/performance/
├── conftest.py              # Performance fixtures
├── benchmarks.py            # Benchmark utilities
├── test_generation_speed.py # Project generation benchmarks
├── test_template_performance.py # Template processing
├── test_file_operations.py  # I/O performance
├── test_memory_usage.py     # Memory profiling
├── test_ui_responsiveness.py # GUI performance
└── test_config_performance.py # Configuration benchmarks
```

### Key Benchmark Tests

#### 1. Project Generation Speed

```python
@pytest.mark.benchmark
def test_python_library_generation_speed(benchmark):
    """Benchmark complete project generation."""
    result = benchmark(
        create_project,
        template_name="python_library",
        project_name="benchmark_project",
        variables={...}
    )
    assert result.success
    assert benchmark.stats['mean'] < 2.0  # seconds
```

#### 2. Template Rendering Performance

```python
@pytest.mark.benchmark
def test_template_rendering_performance(benchmark):
    """Benchmark template rendering speed."""
    template = load_template("python_library")
    result = benchmark(
        render_template,
        template,
        variables={...}
    )
    assert benchmark.stats['mean'] < 0.1  # seconds
```

#### 3. Memory Usage Profiling

```python
@pytest.mark.memory
def test_generation_memory_usage():
    """Profile memory usage during generation."""
    monitor = MemoryMonitor()
    monitor.start()
    
    create_project(...)
    
    peak_memory = monitor.get_peak_memory()
    assert peak_memory < 100 * 1024 * 1024  # 100MB
```

## Running Benchmarks

### Basic Benchmark Execution

```bash
# Run all performance tests
pytest tests/performance/ -v --benchmark-only

# Run specific test category
pytest tests/performance/test_generation_speed.py --benchmark-only

# Run with custom iterations
pytest tests/performance/ --benchmark-only --benchmark-min-rounds=10
```

### Detailed Performance Analysis

```bash
# Generate detailed statistics
pytest tests/performance/ --benchmark-only --benchmark-verbose

# Save results to JSON
pytest tests/performance/ --benchmark-only --benchmark-json=results.json

# Generate HTML report
pytest tests/performance/ --benchmark-only --benchmark-html=report.html

# Compare with previous results
pytest tests/performance/ --benchmark-compare=baseline.json
```

### Memory Profiling

```bash
# Run memory profiling tests
pytest tests/performance/test_memory_usage.py -v

# Generate memory profile
mprof run pytest tests/performance/test_memory_usage.py
mprof plot

# Line-by-line memory profiling
python -m memory_profiler tests/performance/memory_profile_script.py
```

### Stress Testing

```bash
# Run stress tests
pytest tests/performance/ -m stress --benchmark-only

# Custom stress parameters
CREATE_PROJECT_STRESS_LEVEL=high pytest tests/performance/
```

## Interpreting Results

### Benchmark Output

Example benchmark results:

```
------------------------------ benchmark: 15 tests ------------------------------
Name (time in ms)                    Min       Max      Mean    StdDev    Median
---------------------------------------------------------------------------------
test_directory_creation            0.2145    0.8234   0.2418    0.0523   0.2398
test_python_library_generation   1523.234  2134.567  1756.89   234.567  1698.234
test_template_rendering           34.5678   89.1234   45.6789   12.3456   42.1234
---------------------------------------------------------------------------------
```

### Key Metrics

- **Min**: Best-case performance
- **Max**: Worst-case performance
- **Mean**: Average performance
- **StdDev**: Consistency indicator
- **Median**: Typical performance

### Performance Grades

| Grade | Criteria |
|-------|----------|
| A+ | < 50% of target |
| A | < 75% of target |
| B | < 100% of target |
| C | < 150% of target |
| D | < 200% of target |
| F | > 200% of target |

### Warning Signs

- **High StdDev**: Inconsistent performance
- **Increasing trend**: Performance degradation
- **Memory growth**: Potential memory leak
- **CPU spikes**: Inefficient algorithms

## Regression Detection

### Automated Regression Testing

```python
# regression_test.py
def test_performance_regression():
    """Detect performance regressions."""
    current = run_benchmarks()
    baseline = load_baseline_results()
    
    for test, result in current.items():
        baseline_result = baseline[test]
        regression = (result.mean - baseline_result.mean) / baseline_result.mean
        
        assert regression < 0.1, f"{test} regressed by {regression:.1%}"
```

### Regression Thresholds

| Severity | Threshold | Action |
|----------|-----------|--------|
| Critical | > 50% slower | Block merge |
| Major | > 25% slower | Require review |
| Minor | > 10% slower | Warning |
| Acceptable | < 10% slower | Pass |

### Baseline Management

```bash
# Update baseline after improvements
pytest tests/performance/ --benchmark-only --benchmark-json=baseline.json

# Store baseline in version control
git add tests/performance/baseline.json
git commit -m "Update performance baseline"
```

## Continuous Performance Testing

### CI/CD Integration

```yaml
# .github/workflows/performance.yml
name: Performance Tests
on:
  pull_request:
  schedule:
    - cron: '0 0 * * *'  # Daily

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run benchmarks
        run: |
          pytest tests/performance/ --benchmark-only \
            --benchmark-json=results.json \
            --benchmark-compare=baseline.json
      
      - name: Check regressions
        run: python scripts/check_performance_regression.py
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: results.json
```

### Performance Dashboard

```python
# Generate performance dashboard
from create_project.utils.performance import PerformanceDashboard

dashboard = PerformanceDashboard()
dashboard.add_results('results.json')
dashboard.add_baseline('baseline.json')
dashboard.generate_report('performance_report.html')
```

### Alerts and Monitoring

```python
# performance_monitor.py
class PerformanceAlert:
    def check_metrics(self, results):
        alerts = []
        
        # Check for regressions
        if results['mean'] > self.baseline['mean'] * 1.1:
            alerts.append(f"Performance regression: {results['test']}")
        
        # Check for memory leaks
        if results['memory_growth'] > 10 * 1024 * 1024:  # 10MB
            alerts.append(f"Possible memory leak: {results['test']}")
        
        return alerts
```

## Historical Trends

### Tracking Performance Over Time

```python
# Store historical data
results = {
    'timestamp': datetime.now().isoformat(),
    'commit': git.get_current_commit(),
    'benchmarks': benchmark_results
}

with open('performance_history.jsonl', 'a') as f:
    f.write(json.dumps(results) + '\n')
```

### Visualization

```python
import matplotlib.pyplot as plt
import pandas as pd

# Load historical data
df = pd.read_json('performance_history.jsonl', lines=True)

# Plot trends
plt.figure(figsize=(12, 6))
for test in ['test_python_library_generation', 'test_template_rendering']:
    data = df[df['test'] == test]
    plt.plot(data['timestamp'], data['mean'], label=test)

plt.xlabel('Date')
plt.ylabel('Time (seconds)')
plt.title('Performance Trends')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('performance_trends.png')
```

### Performance Reports

Generate weekly performance reports:

```bash
# Weekly performance report
python scripts/generate_performance_report.py \
  --start-date 2024-01-01 \
  --end-date 2024-01-07 \
  --output weekly_report.html
```

Report includes:
- Performance trends
- Regression analysis
- Memory usage patterns
- Bottleneck identification
- Optimization recommendations

## Best Practices

### 1. Regular Benchmarking

- Run benchmarks on every PR
- Daily full benchmark suite
- Weekly trend analysis
- Monthly performance review

### 2. Baseline Maintenance

- Update baseline after optimizations
- Document baseline changes
- Keep historical baselines
- Version control benchmarks

### 3. Realistic Testing

- Use production-like data
- Test on target hardware
- Include edge cases
- Simulate real workflows

### 4. Actionable Metrics

- Focus on user-perceived performance
- Set realistic targets
- Track trends, not just snapshots
- Prioritize based on impact

### 5. Performance Culture

- Make performance visible
- Celebrate improvements
- Learn from regressions
- Share optimization techniques

## Conclusion

Performance benchmarking is essential for maintaining a fast, responsive application. By establishing baselines, running regular benchmarks, and detecting regressions early, we can ensure the create-project application remains performant as it evolves.

Key takeaways:
- Establish clear performance targets
- Automate benchmark execution
- Monitor trends over time
- Act on regressions quickly
- Optimize based on data

For optimization strategies, see the [Performance Tuning Guide](tuning_guide.md).
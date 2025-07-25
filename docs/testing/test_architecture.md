# Test Architecture

## Overview

This document describes the comprehensive testing architecture for the create-project application. Our testing strategy ensures reliability, maintainability, and confidence in the codebase through multiple layers of testing.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Categories](#test-categories)
3. [Test Infrastructure](#test-infrastructure)
4. [Coverage Strategy](#coverage-strategy)
5. [Continuous Integration](#continuous-integration)
6. [Test Organization](#test-organization)
7. [Best Practices](#best-practices)

## Testing Philosophy

### Test Pyramid Approach

We follow the test pyramid principle with a balanced distribution:

```
         /\
        /  \  E2E Tests (5%)
       /----\  Integration Tests (25%)
      /------\  Unit Tests (70%)
     /--------\
```

- **Unit Tests**: Fast, isolated, testing individual components
- **Integration Tests**: Testing component interactions
- **E2E Tests**: Full system validation

### Core Principles

1. **Test-Driven Development (TDD)**: Write tests before implementation
2. **Comprehensive Coverage**: Aim for >80% code coverage
3. **Fast Feedback**: Most tests should run in milliseconds
4. **Isolation**: Tests should not depend on external services by default
5. **Clarity**: Test names should describe the scenario and expected outcome

## Test Categories

### 1. Unit Tests (39% coverage - targeting 70%)

**Location**: `tests/unit/`

**Purpose**: Test individual functions, classes, and modules in isolation

**Characteristics**:
- No external dependencies (file system, network, database)
- Fast execution (<100ms per test)
- High code coverage
- Easy to debug

**Example Structure**:
```
tests/unit/
├── ai/                  # AI module unit tests
├── config/              # Configuration system tests
├── core/               # Core business logic tests
├── gui/                # GUI component tests
├── templates/          # Template system tests
└── utils/              # Utility function tests
```

**Key Test Files**:
- `test_api.py`: 100% coverage of public API
- `test_exceptions.py`: 100% coverage of exception hierarchy
- `test_config_manager.py`: Thread-safe configuration testing
- `test_logger.py`: Logging system validation

### 2. Integration Tests

**Location**: `tests/integration/`

**Purpose**: Validate interactions between components

**Characteristics**:
- Test component boundaries
- May use temporary file system
- Mock external services
- Focus on data flow

**Coverage Areas**:
- Template loading and rendering
- Project generation workflow
- Configuration persistence
- AI service integration
- Error recovery mechanisms

### 3. GUI Tests

**Location**: `tests/gui/`

**Purpose**: Test PyQt6 user interface components

**Characteristics**:
- Use pytest-qt fixtures
- Test widget behavior
- Validate user interactions
- May skip in headless CI

**Test Types**:
- Widget unit tests
- Dialog interaction tests
- Wizard workflow tests
- Event handling validation

### 4. Performance Tests

**Location**: `tests/performance/`

**Purpose**: Ensure system meets performance requirements

**Characteristics**:
- Use pytest-benchmark
- Establish baseline metrics
- Detect performance regressions
- Profile memory usage

**Metrics Tracked**:
- Project generation time
- Template rendering speed
- Memory consumption
- UI responsiveness

### 5. Security Tests

**Location**: `tests/security/`

**Purpose**: Validate security measures

**Characteristics**:
- Test input validation
- Verify path traversal prevention
- Check command injection protection
- Validate template injection prevention

**Attack Vectors Tested**:
- 115+ malicious payloads
- SQL injection attempts
- XSS patterns
- Directory traversal
- Command injection

## Test Infrastructure

### pytest Configuration

**File**: `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "strict"
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "gui: marks tests requiring GUI",
    "requires_ai: marks tests requiring Ollama",
    "benchmark: marks performance tests",
    "security: marks security tests"
]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=create_project",
    "--cov-branch",
    "--cov-report=term-missing:skip-covered"
]
```

### Test Fixtures

**Global Fixtures** (`tests/conftest.py`):
```python
@pytest.fixture
def mock_config_manager():
    """Provides configured mock ConfigManager."""

@pytest.fixture
def sample_project_data():
    """Common project data for tests."""

@pytest.fixture
def temp_template_dir(tmp_path):
    """Temporary directory with test templates."""
```

**Scoped Fixtures**:
- `function`: Default, fresh for each test
- `class`: Shared within test class
- `module`: Shared within test module
- `session`: Shared across entire session

### Custom Markers

```python
# Skip in CI without display
@pytest.mark.skipif(
    not os.environ.get("DISPLAY"),
    reason="Requires display"
)

# Run only with Ollama available
@pytest.mark.requires_ai

# Performance tests
@pytest.mark.benchmark(
    group="template_rendering",
    min_rounds=10
)

# Security tests
@pytest.mark.security
@pytest.mark.parametrize("payload", MALICIOUS_PAYLOADS)
```

### Test Utilities

**Location**: `tests/utils/`

Common test helpers:
```python
# tests/utils/helpers.py
def create_test_template(path, name, variables):
    """Create a test template structure."""

def assert_project_structure(project_path, expected_files):
    """Verify project structure matches expectations."""

def mock_ai_responses(responses):
    """Configure mock AI service responses."""
```

## Coverage Strategy

### Current Status
- **Overall**: 39% (targeting 80%)
- **Core Modules**: 51-100%
- **GUI**: Limited due to headless CI
- **Integration**: Growing with each milestone

### Coverage Goals

| Module | Current | Target | Priority |
|--------|---------|---------|-----------|
| `core.api` | 100% | 100% | Critical |
| `templates` | 51% | 80% | High |
| `gui` | 30% | 60% | Medium |
| `ai` | 90% | 95% | High |
| `config` | 85% | 90% | High |
| `utils` | 70% | 80% | Medium |

### Measuring Effectiveness

1. **Line Coverage**: Basic metric, all lines executed
2. **Branch Coverage**: All decision paths tested
3. **Integration Coverage**: Component interactions validated
4. **Scenario Coverage**: User workflows tested

### Coverage Reports

Generate detailed reports:
```bash
# HTML report
pytest --cov=create_project --cov-report=html

# XML for CI
pytest --cov=create_project --cov-report=xml

# Console with missing lines
pytest --cov=create_project --cov-report=term-missing
```

## Continuous Integration

### GitHub Actions Workflows

**File**: `.github/workflows/tests.yml`

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install uv
        uv pip install -e ".[test]"
    
    - name: Run tests
      run: |
        pytest -v --cov=create_project --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v4
```

### Test Execution Strategy

1. **Fast Tests First**: Unit tests run immediately
2. **Parallel Execution**: Use `pytest-xdist` for speed
3. **Fail Fast**: Stop on first failure in CI
4. **Matrix Testing**: Multiple OS and Python versions

### CI-Specific Considerations

```python
# Skip GUI tests in headless environment
@pytest.mark.skipif(
    os.environ.get("CI") and not os.environ.get("DISPLAY"),
    reason="GUI tests require display"
)

# Increase timeout for CI
@pytest.mark.timeout(30 if os.environ.get("CI") else 10)

# Use CI-appropriate paths
@pytest.fixture
def project_dir(tmp_path):
    if os.environ.get("CI"):
        return tmp_path / "ci_test"
    return tmp_path / "local_test"
```

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py              # Root fixtures and configuration
├── unit/                   # Unit tests by module
│   ├── conftest.py         # Unit test fixtures
│   ├── ai/
│   ├── config/
│   ├── core/
│   ├── gui/
│   ├── templates/
│   └── utils/
├── integration/            # Integration tests
│   ├── conftest.py         # Integration fixtures
│   └── ...
├── gui/                    # GUI-specific tests
│   ├── conftest.py         # GUI fixtures (qtbot, etc.)
│   └── ...
├── performance/            # Performance benchmarks
│   ├── conftest.py         # Performance fixtures
│   └── ...
├── security/               # Security tests
│   ├── conftest.py         # Security fixtures
│   └── ...
└── utils/                  # Test utilities
    └── helpers.py
```

### Naming Conventions

1. **Test Files**: `test_<module_name>.py`
2. **Test Classes**: `Test<FeatureName>`
3. **Test Functions**: `test_<scenario>_<expected_result>`
4. **Fixtures**: `<scope>_<purpose>` (e.g., `mock_ai_service`)

### Test Discovery

pytest automatically discovers tests following these patterns:
- Files matching `test_*.py` or `*_test.py`
- Classes prefixed with `Test`
- Functions prefixed with `test_`

## Best Practices

### 1. Test Independence

Each test should:
- Set up its own data
- Not depend on test execution order
- Clean up after itself
- Use `tmp_path` for file operations

### 2. Clear Test Names

```python
# Good
def test_create_project_with_invalid_name_raises_validation_error():
    pass

# Bad
def test_error():
    pass
```

### 3. Arrange-Act-Assert Pattern

```python
def test_template_rendering():
    # Arrange
    template = create_test_template()
    variables = {"name": "test"}
    
    # Act
    result = template.render(variables)
    
    # Assert
    assert result.success
    assert "test" in result.content
```

### 4. Parametrized Testing

```python
@pytest.mark.parametrize("project_name,expected_valid", [
    ("valid_name", True),
    ("invalid-name!", False),
    ("123start", False),
    ("_underscore", True),
])
def test_project_name_validation(project_name, expected_valid):
    assert is_valid_project_name(project_name) == expected_valid
```

### 5. Mock External Dependencies

```python
@patch('subprocess.run')
def test_git_init(mock_run):
    mock_run.return_value = Mock(returncode=0)
    
    git_manager = GitManager()
    result = git_manager.init_repository("/path/to/repo")
    
    assert result.success
    mock_run.assert_called_with(
        ["git", "init"],
        cwd="/path/to/repo",
        capture_output=True
    )
```

### 6. Test Error Cases

Always test:
- Invalid inputs
- Missing dependencies
- Permission errors
- Network failures
- Timeout scenarios

### 7. Use Appropriate Assertions

```python
# Specific assertions
assert result.error_count == 2
assert "permission denied" in result.errors[0].lower()

# Not just
assert not result.success
```

### 8. Document Complex Tests

```python
def test_complex_workflow():
    """
    Test the complete project creation workflow including:
    1. Template selection and validation
    2. Variable substitution
    3. File generation
    4. Git initialization
    5. Virtual environment creation
    
    This ensures all components work together correctly.
    """
```

## Debugging Failed Tests

### 1. Use pytest flags

```bash
# Verbose output
pytest -vv

# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Show local variables
pytest -l

# Run specific test
pytest tests/unit/test_api.py::TestAPI::test_create_project
```

### 2. Add Debug Logging

```python
def test_failing_integration(caplog):
    with caplog.at_level(logging.DEBUG):
        result = perform_operation()
    
    if not result.success:
        print(f"Debug logs:\n{caplog.text}")
    
    assert result.success
```

### 3. Use Fixtures for Debugging

```python
@pytest.fixture
def debug_on_failure(request):
    yield
    if request.node.rep_call.failed:
        import pdb; pdb.set_trace()
```

## Performance Considerations

### 1. Test Execution Time

Target execution times:
- Unit tests: <100ms
- Integration tests: <1s
- E2E tests: <5s
- Full suite: <2 minutes

### 2. Optimize Slow Tests

```python
# Use class-scoped fixtures
@pytest.fixture(scope="class")
def expensive_setup():
    return create_large_test_dataset()

# Mark slow tests
@pytest.mark.slow
def test_large_project_generation():
    pass
```

### 3. Parallel Execution

```bash
# Run tests in parallel
pytest -n auto

# Run specific markers in parallel
pytest -n 4 -m "not slow"
```

## Summary

Our test architecture provides comprehensive validation of the create-project application through multiple testing layers. By following these patterns and practices, we maintain high quality and reliability while enabling rapid development.

Key takeaways:
- Balanced test pyramid with emphasis on unit tests
- Comprehensive fixture system for test isolation
- Multiple test categories for different aspects
- Strong CI/CD integration
- Clear organization and naming conventions
- Focus on maintainability and debuggability

The testing architecture continues to evolve as the project grows, always maintaining the balance between coverage, speed, and maintainability.
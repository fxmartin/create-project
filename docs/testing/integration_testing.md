# Integration Testing Guide

## Overview

This guide provides comprehensive documentation for writing and maintaining integration tests in the create-project application. Integration tests validate the interaction between multiple components, ensuring they work together correctly to deliver complete functionality.

## Table of Contents

1. [Introduction](#introduction)
2. [Test Organization](#test-organization)
3. [Integration Test Patterns](#integration-test-patterns)
4. [Fixtures and Test Data](#fixtures-and-test-data)
5. [Mock Strategies](#mock-strategies)
6. [Writing Integration Tests](#writing-integration-tests)
7. [Debugging Integration Tests](#debugging-integration-tests)
8. [Best Practices](#best-practices)

## Introduction

Integration tests in create-project serve to:
- Validate end-to-end workflows from UI through to project generation
- Ensure components interact correctly (templates, generators, configuration)
- Test error handling and recovery scenarios
- Verify external integrations (Git, AI service, file system)

### Scope and Boundaries

Integration tests focus on:
- **Component Integration**: How modules work together
- **Workflow Validation**: Complete user scenarios
- **External Dependencies**: Interactions with Git, Ollama AI, file system
- **Error Scenarios**: Recovery and fallback mechanisms

They do NOT test:
- Individual function logic (unit tests)
- UI widget behavior in isolation (GUI unit tests)
- Performance characteristics (performance tests)
- Security vulnerabilities (security tests)

## Test Organization

### Directory Structure

```
tests/integration/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── templates/                     # Template-specific integration tests
│   ├── test_engine_integration.py
│   └── test_schema_integration.py
├── test_ai_error_handling.py      # AI service error scenarios
├── test_ai_integration.py         # AI service integration
├── test_end_to_end.py            # Complete workflow tests
├── test_error_recovery_integration.py
├── test_generator_integration.py  # Project generator tests
├── test_gui_integration.py        # GUI-backend integration
├── test_workflows.py              # Common user workflows
└── test_project_generation_e2e.py # End-to-end generation tests
```

### Test Categorization

Tests are organized by functional area and marked with appropriate pytest markers:

```python
@pytest.mark.integration  # All integration tests
@pytest.mark.slow        # Tests taking >1 second
@pytest.mark.requires_ai # Tests needing Ollama
@pytest.mark.gui         # Tests with GUI components
```

### Naming Conventions

- Test files: `test_<component>_integration.py` or `test_<workflow>.py`
- Test classes: `Test<Feature>Integration` or `Test<Workflow>Scenarios`
- Test methods: `test_<scenario>_<expected_outcome>`

Example:
```python
class TestProjectGenerationIntegration:
    def test_python_library_creation_with_git_succeeds(self):
        """Test creating a Python library project with Git initialization."""
```

## Integration Test Patterns

### 1. End-to-End Workflow Testing

Tests complete user journeys from start to finish:

```python
def test_complete_wizard_flow_python_library(self, qtbot, tmp_path, mock_config_manager):
    """Test complete wizard workflow for Python library creation."""
    # 1. Setup wizard with dependencies
    wizard = ProjectWizard(config_manager=mock_config_manager)
    qtbot.addWidget(wizard)
    
    # 2. Navigate through wizard steps
    # Select template
    wizard.project_type_step.template_list.setCurrentRow(0)
    wizard.next()
    
    # Fill basic info
    qtbot.keyClicks(wizard.basic_info_step.project_name_edit, "test_lib")
    wizard.next()
    
    # 3. Trigger project generation
    wizard.accept()
    
    # 4. Verify results
    project_path = tmp_path / "test_lib"
    assert project_path.exists()
    assert (project_path / "pyproject.toml").exists()
```

### 2. Component Integration Testing

Tests interactions between specific components:

```python
def test_template_engine_with_project_generator(self, tmp_path):
    """Test template engine integration with project generator."""
    # Setup components
    template_loader = TemplateLoader()
    template_engine = TemplateEngine()
    generator = ProjectGenerator(template_loader=template_loader)
    
    # Execute integration
    template = template_loader.load_template("python_library")
    result = generator.create_project(
        template_name="python_library",
        project_name="test_project",
        target_directory=str(tmp_path),
        variables={"author": "Test Author"}
    )
    
    # Verify integration
    assert result.success
    assert len(result.files_created) > 0
```

### 3. Error Recovery Testing

Tests system behavior under failure conditions:

```python
def test_disk_space_error_recovery(self, tmp_path, monkeypatch):
    """Test recovery when disk space is exhausted."""
    # Simulate disk full error
    def mock_write(*args, **kwargs):
        raise OSError(28, "No space left on device")
    
    monkeypatch.setattr(Path, "write_text", mock_write)
    
    # Attempt operation
    result = create_project(
        template_name="python_library",
        project_name="test_project",
        target_directory=str(tmp_path),
        variables={}
    )
    
    # Verify graceful failure and cleanup
    assert not result.success
    assert "No space left" in result.errors[0]
    assert not (tmp_path / "test_project").exists()  # Cleanup occurred
```

### 4. Async Integration Testing

Tests asynchronous operations and callbacks:

```python
async def test_async_project_creation_with_progress(self):
    """Test async project creation with progress callbacks."""
    progress_updates = []
    
    async def progress_callback(progress):
        progress_updates.append(progress)
    
    result = await create_project_async(
        template_name="cli_single_package",
        project_name="async_test",
        target_directory=str(tmp_path),
        variables={},
        progress_callback=progress_callback
    )
    
    assert result.success
    assert len(progress_updates) > 0
    assert progress_updates[-1].percentage == 100
```

## Fixtures and Test Data

### Common Fixtures

Located in `conftest.py`:

```python
@pytest.fixture
def mock_config_manager():
    """Provides a mock ConfigManager with default settings."""
    manager = Mock(spec=ConfigManager)
    manager.get_setting.side_effect = lambda key, default=None: {
        "defaults.author": "Test Author",
        "defaults.location": "/tmp/projects",
        "ai.enabled": True,
        "ai.ollama_url": "http://localhost:11434",
        "templates.builtin_path": "create_project/templates/builtin"
    }.get(key, default)
    return manager

@pytest.fixture
def sample_template_variables():
    """Common template variables for testing."""
    return {
        "project_name": "test_project",
        "author": "Test Author",
        "version": "0.1.0",
        "description": "Test project description",
        "python_version": "3.9",
        "created_date": "2025-07-25",
        "project_type": "library",
        "license": "MIT",
        "email": "test@example.com"
    }
```

### Test Data Management

1. **Temporary Directories**: Use `tmp_path` fixture for isolated file operations
2. **Mock Data**: Keep test data minimal but realistic
3. **Fixtures Scoping**: Use appropriate scope (function, class, module, session)

```python
@pytest.fixture(scope="class")
def template_test_data():
    """Reusable template test data for a test class."""
    return {
        "templates": ["python_library", "cli_single_package", "flask_web_app"],
        "variables": {
            "minimal": {"project_name": "test", "author": "Test"},
            "complete": {
                "project_name": "full_test",
                "author": "Test Author",
                "version": "1.0.0",
                "description": "Complete test project",
                # ... all variables
            }
        }
    }
```

## Mock Strategies

### 1. AI Service Mocking

```python
@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing without Ollama."""
    service = Mock(spec=AIService)
    service.is_available.return_value = True
    service.get_project_suggestions.return_value = [
        "Consider adding type hints",
        "Include comprehensive tests"
    ]
    service.get_error_help.return_value = "Try checking file permissions"
    return service
```

### 2. File System Mocking

```python
def test_file_operations_with_mock_fs(tmp_path, monkeypatch):
    """Test with controlled file system behavior."""
    # Mock specific file operations
    written_files = []
    
    def mock_write_text(self, content, encoding='utf-8'):
        written_files.append((str(self), content))
        return len(content)
    
    monkeypatch.setattr(Path, "write_text", mock_write_text)
    
    # Run test
    result = create_project(...)
    
    # Verify mock interactions
    assert len(written_files) == expected_file_count
```

### 3. Git Operations Mocking

```python
@pytest.fixture
def mock_git_operations(monkeypatch):
    """Mock Git commands for testing."""
    git_commands = []
    
    def mock_run(cmd, *args, **kwargs):
        git_commands.append(cmd)
        if "git --version" in cmd:
            return Mock(returncode=0, stdout=b"git version 2.39.0")
        elif "git init" in cmd:
            return Mock(returncode=0)
        return Mock(returncode=1, stderr=b"error")
    
    monkeypatch.setattr("subprocess.run", mock_run)
    return git_commands
```

### 4. Network Request Mocking

```python
@pytest.fixture
def mock_http_client(monkeypatch):
    """Mock HTTP client for AI service tests."""
    responses = {
        "/api/tags": {"models": [{"name": "llama2"}, {"name": "codellama"}]},
        "/api/generate": {"response": "AI suggestion here"}
    }
    
    async def mock_get(url, **kwargs):
        path = url.split("localhost:11434")[-1]
        return Mock(
            status_code=200,
            json=lambda: responses.get(path, {})
        )
    
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
```

## Writing Integration Tests

### Step-by-Step Guide

1. **Identify the Integration Points**
   ```python
   # What components interact?
   # - TemplateLoader loads templates
   # - TemplateEngine renders them
   # - ProjectGenerator creates the project
   # - GitManager initializes repository
   ```

2. **Set Up Test Environment**
   ```python
   def test_full_project_generation_flow(self, tmp_path, mock_config_manager):
       # Arrange - Set up all components
       template_loader = TemplateLoader(config_manager=mock_config_manager)
       generator = ProjectGenerator(
           template_loader=template_loader,
           config_manager=mock_config_manager
       )
   ```

3. **Execute the Integration**
   ```python
       # Act - Run the integration
       result = generator.create_project(
           template_name="python_library",
           project_name="test_lib",
           target_directory=str(tmp_path),
           variables={"author": "Test Author"}
       )
   ```

4. **Verify Results**
   ```python
       # Assert - Check all integration points
       assert result.success
       assert (tmp_path / "test_lib").exists()
       assert (tmp_path / "test_lib" / ".git").exists()
       assert len(result.files_created) >= 10
   ```

5. **Clean Up**
   ```python
       # Cleanup happens automatically with tmp_path fixture
       # For other resources:
       finally:
           if hasattr(generator, 'cleanup'):
               generator.cleanup()
   ```

### Common Pitfalls

1. **Over-mocking**: Don't mock what you're testing
   ```python
   # BAD - Mocks the integration point
   mock_generator.create_project.return_value = Success()
   
   # GOOD - Mocks external dependencies only
   monkeypatch.setattr("subprocess.run", mock_git_command)
   ```

2. **Test Isolation**: Ensure tests don't affect each other
   ```python
   # Use tmp_path for file operations
   # Reset global state in teardown
   # Use fresh instances for each test
   ```

3. **Timing Issues**: Handle async operations properly
   ```python
   # Use pytest-asyncio for async tests
   # Add appropriate timeouts
   # Use qtbot.wait_until for GUI events
   ```

## Debugging Integration Tests

### 1. Enable Debug Logging

```python
# In conftest.py or test file
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use pytest's built-in
pytest -vv --log-cli-level=DEBUG
```

### 2. Capture More Context

```python
def test_complex_integration(self, caplog, capsys):
    """Test with output capture for debugging."""
    with caplog.at_level(logging.DEBUG):
        result = perform_integration()
    
    if not result.success:
        print(f"Captured logs:\n{caplog.text}")
        print(f"Result errors:\n{result.errors}")
        
    assert result.success
```

### 3. Use Breakpoints Strategically

```python
def test_failing_integration(self):
    # Add conditional breakpoint
    if not result.success:
        import pdb; pdb.set_trace()
        # Or use pytest --pdb flag
```

### 4. Isolate Failing Components

```python
# Break down complex integrations
def test_component_a_to_b(self):
    # Test just A->B interaction

def test_component_b_to_c(self):
    # Test just B->C interaction
```

## Best Practices

### 1. Test Realistic Scenarios
- Use real template structures
- Include edge cases users might encounter
- Test with various configuration states

### 2. Maintain Test Performance
- Mark slow tests with `@pytest.mark.slow`
- Use class-scoped fixtures when possible
- Run expensive setup once per class

### 3. Handle External Dependencies
- Always provide offline fallbacks
- Mock network calls by default
- Use markers for tests requiring external services

### 4. Keep Tests Maintainable
- Use descriptive test names
- Add docstrings explaining the scenario
- Extract common operations to fixtures
- Avoid magic numbers and strings

### 5. Test Data Management
```python
# Good - Centralized test data
VALID_PROJECT_NAMES = ["my_project", "test-lib", "app123"]
INVALID_PROJECT_NAMES = ["", "123start", "my project", "../etc"]

# Use in multiple tests
@pytest.mark.parametrize("project_name", VALID_PROJECT_NAMES)
def test_valid_project_names(self, project_name):
    ...
```

### 6. Error Message Verification
```python
# Verify specific error conditions
assert not result.success
assert any("permission denied" in err.lower() for err in result.errors)
```

### 7. Coverage Considerations
- Integration tests complement unit tests
- Focus on paths not covered by unit tests
- Test component boundaries thoroughly

## CI/CD Integration

Integration tests run in GitHub Actions:

```yaml
# .github/workflows/tests.yml
- name: Run Integration Tests
  run: |
    pytest tests/integration/ \
      -v \
      --timeout=300 \
      --cov=create_project \
      --cov-report=xml
```

Special considerations for CI:
- Skip GUI tests in headless environment
- Increase timeouts for slower CI runners
- Use matrix testing for multiple Python versions
- Cache dependencies for faster runs

## Summary

Integration tests are crucial for ensuring create-project works correctly as a complete system. By following these patterns and practices, you can write effective integration tests that catch real issues while remaining maintainable and performant.

Remember: Integration tests verify that components work together, not how they work individually. Focus on the interactions and data flow between components to ensure the system delivers value to users.
# ABOUTME: Unit tests for template engine - covers template loading, rendering, and error handling
# ABOUTME: Tests Jinja2 integration, variable substitution, and template validation

"""
Unit tests for create_project.templates.engine module.

Tests cover template loading, rendering, variable substitution,
error handling, and Jinja2 integration.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from create_project.config.config_manager import ConfigManager
from create_project.templates.engine import (
    RenderingError,
    TemplateEngine,
    TemplateEngineError,
    TemplateLoadError,
    VariableResolutionError,
)
from create_project.templates.schema.template import Template


class TestTemplateEngine:
    """Test the TemplateEngine class."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock ConfigManager."""
        config = Mock()
        config.get_setting.return_value = []
        return config

    @pytest.fixture
    def template_engine(self, mock_config_manager):
        """Create a TemplateEngine instance for testing."""
        return TemplateEngine(config_manager=mock_config_manager)

    @pytest.fixture
    def sample_template_data(self):
        """Create sample template data for testing."""
        return {
            "metadata": {
                "name": "Test Template",
                "description": "A test template",
                "version": "1.0.0",
                "author": "Test Author",
                "category": "script"
            },
            "variables": [
                {
                    "name": "project_name",
                    "type": "string",
                    "description": "Project name",
                    "required": True
                },
                {
                    "name": "author",
                    "type": "string",
                    "description": "Author name",
                    "required": False,
                    "default": "Anonymous"
                }
            ],
            "structure": {
                "root_directory": {
                    "name": "{{project_name}}",
                    "files": [
                        {
                            "name": "README.md",
                            "content": "# {{project_name}}\n\nBy {{author}}"
                        }
                    ]
                }
            }
        }

    @pytest.fixture
    def sample_template_file(self, sample_template_data):
        """Create a temporary template file."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        try:
            yaml.dump(sample_template_data, temp_file)
            temp_file.flush()
            yield Path(temp_file.name)
        finally:
            temp_file.close()
            Path(temp_file.name).unlink(missing_ok=True)

    def test_init_with_config_manager(self, mock_config_manager):
        """Test TemplateEngine initialization with ConfigManager."""
        engine = TemplateEngine(config_manager=mock_config_manager)
        assert engine.config_manager is mock_config_manager

    def test_init_without_config_manager(self):
        """Test TemplateEngine initialization without ConfigManager."""
        engine = TemplateEngine()
        assert engine.config_manager is not None
        assert hasattr(engine, "jinja_env")
        assert hasattr(engine, "logger")

    def test_load_template_success(self, template_engine, sample_template_file):
        """Test successful template loading."""
        with patch.object(template_engine, "_evaluate_variable_condition", return_value=True):
            template = template_engine.load_template(sample_template_file)

            assert isinstance(template, Template)
            assert template.metadata.name == "Test Template"
            assert template.metadata.description == "A test template"
            assert len(template.variables) == 2

    def test_load_template_nonexistent_file(self, template_engine):
        """Test loading nonexistent template file."""
        with pytest.raises(TemplateLoadError) as exc_info:
            template_engine.load_template("/nonexistent/template.yaml")

        assert "Template file not found" in str(exc_info.value)

    def test_load_template_invalid_yaml(self, template_engine):
        """Test loading template with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_file = Path(f.name)

        try:
            with pytest.raises(TemplateLoadError) as exc_info:
                template_engine.load_template(invalid_file)

            assert "YAML parsing error" in str(exc_info.value)
        finally:
            invalid_file.unlink(missing_ok=True)

    def test_load_template_validation_error(self, template_engine):
        """Test loading template that fails validation."""
        invalid_data = {
            "metadata": {
                "name": "Invalid Template"
                # Missing required fields
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_data, f)
            invalid_file = Path(f.name)

        try:
            with pytest.raises(TemplateLoadError) as exc_info:
                template_engine.load_template(invalid_file)

            assert "Template validation error" in str(exc_info.value)
        finally:
            invalid_file.unlink(missing_ok=True)

    def test_resolve_variables_success(self, template_engine, sample_template_file):
        """Test successful variable resolution."""
        with patch.object(template_engine, "_evaluate_variable_condition", return_value=True):
            template = template_engine.load_template(sample_template_file)
            variables = {
                "project_name": "my-project",
                "author": "John Doe"
            }

            resolved = template_engine.resolve_variables(template, variables)

            assert resolved["project_name"] == "my-project"
            assert resolved["author"] == "John Doe"

    def test_resolve_variables_with_defaults(self, template_engine, sample_template_file):
        """Test variable resolution using default values."""
        with patch.object(template_engine, "_evaluate_variable_condition", return_value=True):
            template = template_engine.load_template(sample_template_file)
            variables = {
                "project_name": "my-project"
                # author not provided, should use default
            }

            resolved = template_engine.resolve_variables(template, variables)

            assert resolved["project_name"] == "my-project"
            assert resolved["author"] == "Anonymous"

    def test_resolve_variables_missing_required(self, template_engine, sample_template_file):
        """Test variable resolution with missing required variable."""
        with patch.object(template_engine, "_evaluate_variable_condition", return_value=True):
            template = template_engine.load_template(sample_template_file)
            variables = {
                "author": "John Doe"
                # project_name is required but missing
            }

            with pytest.raises(VariableResolutionError) as exc_info:
                template_engine.resolve_variables(template, variables)

            assert "Required variable 'project_name' not provided" in str(exc_info.value)

    def test_resolve_variables_validation_error(self, template_engine, sample_template_file):
        """Test variable resolution with validation error."""
        with patch.object(template_engine, "_evaluate_variable_condition", return_value=True):
            template = template_engine.load_template(sample_template_file)

            # Create a variable with a validation rule that will fail
            from create_project.templates.schema.variables import (
                TemplateVariable,
                ValidationRule,
                VariableType,
            )

            invalid_var = TemplateVariable(
                name="project_name",
                type=VariableType.STRING,
                description="Project name",
                required=True,
                validation_rules=[
                    ValidationRule(rule_type="pattern", value="^[A-Z].*", message="Must start with uppercase")
                ]
            )

            # Replace the first variable with our invalid one
            template.variables[0] = invalid_var

            variables = {
                "project_name": "invalid-name",  # Starts with lowercase, will fail validation
                "author": "John Doe"
            }

            with pytest.raises(VariableResolutionError) as exc_info:
                template_engine.resolve_variables(template, variables)

            assert "Variable resolution failed" in str(exc_info.value)

    def test_render_template_success(self, template_engine):
        """Test successful template rendering."""
        template_content = "Hello {{name}}!"
        variables = {"name": "World"}

        result = template_engine.render_template_string(template_content, variables)

        assert result == "Hello World!"

    def test_render_template_undefined_variable(self, template_engine):
        """Test template rendering with undefined variable."""
        template_content = "Hello {{undefined_var}}!"
        variables = {}

        with pytest.raises(RenderingError) as exc_info:
            template_engine.render_template_string(template_content, variables)

        assert "Template rendering failed" in str(exc_info.value)

    def test_render_template_syntax_error(self, template_engine):
        """Test template rendering with syntax error."""
        template_content = "Hello {{name"  # Missing closing }}
        variables = {"name": "World"}

        with pytest.raises(RenderingError) as exc_info:
            template_engine.render_template_string(template_content, variables)

        assert "Template rendering failed" in str(exc_info.value)

    def test_render_file_success(self, template_engine):
        """Test successful file rendering from string."""
        template_content = "Project: {{project_name}}\nAuthor: {{author}}"
        variables = {"project_name": "test-project", "author": "Test Author"}

        result = template_engine.render_template_string(template_content, variables)

        assert "Project: test-project" in result
        assert "Author: Test Author" in result

    def test_render_file_not_found(self, template_engine):
        """Test loading nonexistent template file."""
        with pytest.raises(TemplateLoadError) as exc_info:
            template_engine.load_template("/nonexistent/file.yaml")

        assert "Template file not found" in str(exc_info.value)

    def test_get_undefined_variables(self, template_engine):
        """Test getting undefined variables from template."""
        template_content = "{{var1}} and {{var2}} but not {{var3}}"

        # Get all variables from template
        variables = template_engine.get_template_variables(template_content)

        assert "var1" in variables
        assert "var2" in variables
        assert "var3" in variables

    def test_get_undefined_variables_none(self, template_engine):
        """Test getting template variables when none are undefined."""
        template_content = "{{var1}} and {{var2}}"

        variables = template_engine.get_template_variables(template_content)

        assert "var1" in variables
        assert "var2" in variables
        assert len(variables) == 2

    def test_validate_template_syntax_valid(self, template_engine):
        """Test rendering valid template syntax."""
        template_content = "Hello {{name}}! Welcome to {{project}}."
        variables = {"name": "User", "project": "Test"}

        # Should not raise any exception
        result = template_engine.render_template_string(template_content, variables)
        assert "Hello User!" in result
        assert "Welcome to Test" in result

    def test_validate_template_syntax_invalid(self, template_engine):
        """Test rendering invalid template syntax."""
        template_content = "Hello {{name! Welcome to {{project}}"  # Syntax errors

        with pytest.raises(RenderingError) as exc_info:
            template_engine.render_template_string(template_content, {})

        assert "Template rendering failed" in str(exc_info.value)

    def test_extract_template_variables(self, template_engine):
        """Test extracting variables from template content."""
        template_content = "{{var1}} and {{var2}} and {{var1}} again"

        variables = template_engine.get_template_variables(template_content)

        assert variables == {"var1", "var2"}

    def test_extract_template_variables_complex(self, template_engine):
        """Test extracting variables from complex template."""
        template_content = """
        {% if condition %}
            {{project_name}}
        {% endif %}
        {% for item in items %}
            {{item.name}}
        {% endfor %}
        """

        variables = template_engine.get_template_variables(template_content)

        # Should find variables in conditions and loops
        assert "condition" in variables
        assert "project_name" in variables
        assert "items" in variables
        # Note: 'item' is a loop variable and is not included in undeclared variables

    def test_thread_safety(self, template_engine):
        """Test that template engine is thread-safe."""
        import threading

        results = []
        errors = []

        def render_template(name: str):
            try:
                content = template_engine.render_template_string("Hello {{name}}!", {"name": name})
                results.append(content)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=render_template, args=[f"Thread{i}"])
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Thread safety test failed with errors: {errors}"
        assert len(results) == 10
        assert all("Hello Thread" in result for result in results)

    def test_error_handling_chain(self, template_engine):
        """Test error handling propagation through the engine."""
        # Test that errors are properly wrapped and propagated

        # Template load error
        with pytest.raises(TemplateLoadError):
            template_engine.load_template("/nonexistent/file.yaml")

        # Rendering error
        with pytest.raises(RenderingError):
            template_engine.render_template_string("{{undefined}}", {})

        # Syntax error during rendering
        with pytest.raises(RenderingError):
            template_engine.render_template_string("{{invalid syntax", {})

    def test_custom_jinja_filters(self, template_engine):
        """Test custom Jinja2 filters if any are registered."""
        # Test custom filters implemented in the engine

        # Test slugify filter
        result = template_engine.render_template_string("{{name|slugify}}", {"name": "Test Project Name"})
        assert result == "test-project-name"

        # Test snake_case filter
        result = template_engine.render_template_string("{{name|snake_case}}", {"name": "TestProjectName"})
        assert result == "test_project_name"

        # Test pascal_case filter
        result = template_engine.render_template_string("{{name|pascal_case}}", {"name": "test_project_name"})
        assert result == "TestProjectName"

        # Test camel_case filter
        result = template_engine.render_template_string("{{name|camel_case}}", {"name": "test_project_name"})
        assert result == "testProjectName"

    def test_template_caching_behavior(self, template_engine, sample_template_file):
        """Test template caching if implemented."""
        # Load template first time
        template1 = template_engine.load_template(sample_template_file)

        # Load same template again - should use cache
        template2 = template_engine.load_template(sample_template_file)

        # Should be the same object from cache
        assert template1 is template2

        # Check cache stats
        stats = template_engine.get_cache_stats()
        assert stats["cached_templates"] == 1

        # Clear cache and verify
        template_engine.clear_cache()
        stats = template_engine.get_cache_stats()
        assert stats["cached_templates"] == 0

    def test_memory_cleanup(self, template_engine):
        """Test that engine properly cleans up resources."""
        # Render many templates to test memory management
        for i in range(100):
            template_engine.render_template_string(f"Template {i}: {{{{var{i}}}}}", {f"var{i}": f"value{i}"})

        # Engine should still be functional
        result = template_engine.render_template_string("Final: {{name}}", {"name": "test"})
        assert result == "Final: test"


class TestTemplateEngineExceptions:
    """Test template engine exception classes."""

    def test_template_engine_error(self):
        """Test TemplateEngineError base exception."""
        error = TemplateEngineError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_template_load_error(self):
        """Test TemplateLoadError exception."""
        error = TemplateLoadError("Load error")
        assert str(error) == "Load error"
        assert isinstance(error, TemplateEngineError)

    def test_variable_resolution_error(self):
        """Test VariableResolutionError exception."""
        error = VariableResolutionError("Variable error")
        assert str(error) == "Variable error"
        assert isinstance(error, TemplateEngineError)

    def test_rendering_error(self):
        """Test RenderingError exception."""
        error = RenderingError("Render error")
        assert str(error) == "Render error"
        assert isinstance(error, TemplateEngineError)


class TestTemplateEngineIntegration:
    """Integration tests for template engine with real components."""

    @pytest.fixture
    def real_config_manager(self):
        """Create a real ConfigManager for integration tests."""
        return ConfigManager()

    @pytest.fixture
    def sample_template_data(self):
        """Create sample template data for testing."""
        return {
            "metadata": {
                "name": "Test Template",
                "description": "A test template",
                "version": "1.0.0",
                "author": "Test Author",
                "category": "script"
            },
            "variables": [
                {
                    "name": "project_name",
                    "type": "string",
                    "description": "Project name",
                    "required": True
                },
                {
                    "name": "author",
                    "type": "string",
                    "description": "Author name",
                    "required": False,
                    "default": "Anonymous"
                }
            ],
            "structure": {
                "root_directory": {
                    "name": "{{project_name}}",
                    "files": [
                        {
                            "name": "README.md",
                            "content": "# {{project_name}}\n\nBy {{author}}"
                        }
                    ]
                }
            }
        }

    @pytest.fixture
    def sample_template_file(self, sample_template_data):
        """Create a temporary template file."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        try:
            yaml.dump(sample_template_data, temp_file)
            temp_file.flush()
            yield Path(temp_file.name)
        finally:
            temp_file.close()
            Path(temp_file.name).unlink(missing_ok=True)

    def test_integration_with_real_config(self, real_config_manager):
        """Test template engine with real ConfigManager."""
        engine = TemplateEngine(config_manager=real_config_manager)

        # Should be able to render simple templates
        result = engine.render_template_string("Hello {{name}}!", {"name": "Integration"})
        assert result == "Hello Integration!"

    def test_full_template_workflow(self, real_config_manager, sample_template_file):
        """Test complete template workflow from load to render."""
        engine = TemplateEngine(config_manager=real_config_manager)

        # Load template with mocked condition evaluation
        with patch.object(engine, "_evaluate_variable_condition", return_value=True):
            template = engine.load_template(sample_template_file)
            assert template.metadata.name == "Test Template"

            # Resolve variables
            variables = {"project_name": "integration-test", "author": "Test Suite"}
            resolved = engine.resolve_variables(template, variables)

        # Render content
        content = "# {{project_name}}\n\nBy {{author}}"
        result = engine.render_template_string(content, resolved)

        assert "# integration-test" in result
        assert "By Test Suite" in result

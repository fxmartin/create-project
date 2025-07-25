# ABOUTME: Unit tests for template engine - covers template loading, rendering, and error handling
# ABOUTME: Tests Jinja2 integration, variable substitution, and template validation

"""
Unit tests for create_project.templates.engine module.

Tests cover template loading, rendering, variable substitution,
error handling, and Jinja2 integration.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

import pytest
import yaml
from jinja2 import TemplateError, UndefinedError

from create_project.templates.engine import (
    TemplateEngine,
    TemplateEngineError,
    TemplateLoadError,
    VariableResolutionError,
    RenderingError
)
from create_project.config.config_manager import ConfigManager
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
                "author": "Test Author"
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
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
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
        with patch('create_project.templates.engine.ConfigManager') as mock_cm_class:
            mock_cm_instance = Mock()
            mock_cm_class.return_value = mock_cm_instance
            
            engine = TemplateEngine()
            assert engine.config_manager is mock_cm_instance
            mock_cm_class.assert_called_once()

    def test_load_template_success(self, template_engine, sample_template_file):
        """Test successful template loading."""
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
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_file = Path(f.name)
        
        with pytest.raises(TemplateLoadError) as exc_info:
            template_engine.load_template(invalid_file)
        
        assert "Failed to parse YAML" in str(exc_info.value)

    def test_load_template_validation_error(self, template_engine):
        """Test loading template that fails validation."""
        invalid_data = {
            "metadata": {
                "name": "Invalid Template"
                # Missing required fields
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_data, f)
            invalid_file = Path(f.name)
        
        with pytest.raises(TemplateLoadError) as exc_info:
            template_engine.load_template(invalid_file)
        
        assert "Template validation failed" in str(exc_info.value)

    def test_resolve_variables_success(self, template_engine, sample_template_file):
        """Test successful variable resolution."""
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
        template = template_engine.load_template(sample_template_file)
        
        # Mock template variable validation to fail
        with patch.object(template.variables[0], 'validate_value', return_value=['Validation error']):
            variables = {
                "project_name": "invalid-name",
                "author": "John Doe"
            }
            
            with pytest.raises(VariableResolutionError) as exc_info:
                template_engine.resolve_variables(template, variables)
            
            assert "Variable validation failed" in str(exc_info.value)

    def test_render_template_success(self, template_engine):
        """Test successful template rendering."""
        template_content = "Hello {{name}}!"
        variables = {"name": "World"}
        
        result = template_engine.render_template(template_content, variables)
        
        assert result == "Hello World!"

    def test_render_template_undefined_variable(self, template_engine):
        """Test template rendering with undefined variable."""
        template_content = "Hello {{undefined_var}}!"
        variables = {}
        
        with pytest.raises(RenderingError) as exc_info:
            template_engine.render_template(template_content, variables)
        
        assert "Template rendering failed" in str(exc_info.value)
        assert "undefined_var" in str(exc_info.value)

    def test_render_template_syntax_error(self, template_engine):
        """Test template rendering with syntax error."""
        template_content = "Hello {{name"  # Missing closing }}
        variables = {"name": "World"}
        
        with pytest.raises(RenderingError) as exc_info:
            template_engine.render_template(template_content, variables)
        
        assert "Template rendering failed" in str(exc_info.value)

    def test_render_file_success(self, template_engine):
        """Test successful file rendering."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.j2', delete=False) as f:
            f.write("Project: {{project_name}}\nAuthor: {{author}}")
            template_file = Path(f.name)
        
        variables = {"project_name": "test-project", "author": "Test Author"}
        result = template_engine.render_file(template_file, variables)
        
        assert "Project: test-project" in result
        assert "Author: Test Author" in result

    def test_render_file_not_found(self, template_engine):
        """Test rendering nonexistent file."""
        variables = {"name": "test"}
        
        with pytest.raises(RenderingError) as exc_info:
            template_engine.render_file("/nonexistent/file.j2", variables)
        
        assert "Template file not found" in str(exc_info.value)

    def test_get_undefined_variables(self, template_engine):
        """Test getting undefined variables from template."""
        template_content = "{{var1}} and {{var2}} but not {{var3}}"
        provided_vars = {"var1": "value1", "var3": "value3"}
        
        undefined = template_engine.get_undefined_variables(template_content, provided_vars)
        
        assert undefined == {"var2"}

    def test_get_undefined_variables_none(self, template_engine):
        """Test getting undefined variables when all are defined."""
        template_content = "{{var1}} and {{var2}}"
        provided_vars = {"var1": "value1", "var2": "value2"}
        
        undefined = template_engine.get_undefined_variables(template_content, provided_vars)
        
        assert undefined == set()

    def test_validate_template_syntax_valid(self, template_engine):
        """Test validating valid template syntax."""
        template_content = "Hello {{name}}! Welcome to {{project}}."
        
        # Should not raise any exception
        template_engine.validate_template_syntax(template_content)

    def test_validate_template_syntax_invalid(self, template_engine):
        """Test validating invalid template syntax."""
        template_content = "Hello {{name! Welcome to {{project}}"  # Syntax errors
        
        with pytest.raises(RenderingError) as exc_info:
            template_engine.validate_template_syntax(template_content)
        
        assert "Template syntax validation failed" in str(exc_info.value)

    def test_extract_template_variables(self, template_engine):
        """Test extracting variables from template content."""
        template_content = "{{var1}} and {{var2}} and {{var1}} again"
        
        variables = template_engine.extract_template_variables(template_content)
        
        assert variables == {"var1", "var2"}

    def test_extract_template_variables_complex(self, template_engine):
        """Test extracting variables from complex template."""
        template_content = """
        {% if condition %}
            {{project_name}}
        {% endif %}
        {% for item in {{items}} %}
            {{item.name}}
        {% endfor %}
        """
        
        variables = template_engine.extract_template_variables(template_content)
        
        # Should find variables in conditions and loops
        assert "condition" in variables
        assert "project_name" in variables
        assert "items" in variables

    def test_thread_safety(self, template_engine):
        """Test that template engine is thread-safe."""
        import threading
        import time
        
        results = []
        errors = []
        
        def render_template(name: str):
            try:
                content = template_engine.render_template("Hello {{name}}!", {"name": name})
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
            template_engine.render_template("{{undefined}}", {})
        
        # Validation error should be caught and re-raised appropriately
        with pytest.raises(RenderingError):
            template_engine.validate_template_syntax("{{invalid syntax")

    def test_custom_jinja_filters(self, template_engine):
        """Test custom Jinja2 filters if any are registered."""
        # This test checks if custom filters work correctly
        # Adjust based on actual custom filters in the engine
        
        # Test basic template rendering works (baseline)
        result = template_engine.render_template("{{name|upper}}", {"name": "test"})
        assert result == "TEST"

    def test_template_caching_behavior(self, template_engine):
        """Test template caching if implemented."""
        template_content = "Hello {{name}}!"
        variables = {"name": "World"}
        
        # Render same template multiple times
        result1 = template_engine.render_template(template_content, variables)
        result2 = template_engine.render_template(template_content, variables)
        
        assert result1 == result2 == "Hello World!"
        # If caching is implemented, this would be a good place to test it

    def test_memory_cleanup(self, template_engine):
        """Test that engine properly cleans up resources."""
        # Render many templates to test memory management
        for i in range(100):
            template_engine.render_template(f"Template {i}: {{{{var{i}}}}}", {f"var{i}": f"value{i}"})
        
        # Engine should still be functional
        result = template_engine.render_template("Final: {{name}}", {"name": "test"})
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

    def test_integration_with_real_config(self, real_config_manager):
        """Test template engine with real ConfigManager."""
        engine = TemplateEngine(config_manager=real_config_manager)
        
        # Should be able to render simple templates
        result = engine.render_template("Hello {{name}}!", {"name": "Integration"})
        assert result == "Hello Integration!"

    def test_full_template_workflow(self, real_config_manager, sample_template_file):
        """Test complete template workflow from load to render."""
        engine = TemplateEngine(config_manager=real_config_manager)
        
        # Load template
        template = engine.load_template(sample_template_file)
        assert template.metadata.name == "Test Template"
        
        # Resolve variables
        variables = {"project_name": "integration-test", "author": "Test Suite"}
        resolved = engine.resolve_variables(template, variables)
        
        # Render content
        content = "# {{project_name}}\n\nBy {{author}}"
        result = engine.render_template(content, resolved)
        
        assert "# integration-test" in result
        assert "By Test Suite" in result
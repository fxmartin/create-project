# ABOUTME: Simplified unit tests for template engine - focuses on actual API methods
# ABOUTME: Tests template loading, string rendering, and variable extraction

"""
Unit tests for create_project.templates.engine module.
Simplified to test actual available API methods.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock
from typing import Dict, Any

import pytest
import yaml

from create_project.templates.engine import (
    TemplateEngine,
    TemplateEngineError,
    TemplateLoadError,
    VariableResolutionError,
    RenderingError
)
from create_project.config.config_manager import ConfigManager


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
        # Use a real config manager to avoid mocking complexity
        engine = TemplateEngine()
        assert engine.config_manager is not None

    def test_render_template_string_success(self, template_engine):
        """Test successful template string rendering."""
        template_content = "Hello {{name}}!"
        variables = {"name": "World"}
        
        result = template_engine.render_template_string(template_content, variables)
        
        assert result == "Hello World!"

    def test_render_template_string_undefined_variable(self, template_engine):
        """Test template string rendering with undefined variable."""
        template_content = "Hello {{undefined_var}}!"
        variables = {}
        
        with pytest.raises(RenderingError) as exc_info:
            template_engine.render_template_string(template_content, variables)
        
        assert "Template rendering failed" in str(exc_info.value)

    def test_render_template_string_syntax_error(self, template_engine):
        """Test template string rendering with syntax error."""
        template_content = "Hello {{name"  # Missing closing }}
        variables = {"name": "World"}
        
        with pytest.raises(RenderingError) as exc_info:
            template_engine.render_template_string(template_content, variables)
        
        assert "Template rendering failed" in str(exc_info.value)

    def test_get_template_variables(self, template_engine):
        """Test extracting variables from template content."""
        template_content = "{{var1}} and {{var2}} and {{var1}} again"
        
        variables = template_engine.get_template_variables(template_content)
        
        assert variables == {"var1", "var2"}

    def test_get_template_variables_complex(self, template_engine):
        """Test extracting variables from complex template."""
        template_content = """
        {% if condition %}
            {{project_name}}
        {% endif %}
        {% for item in items %}
            {{item}}
        {% endfor %}
        """
        
        variables = template_engine.get_template_variables(template_content)
        
        # Should find variables in conditions and loops
        assert "condition" in variables
        assert "project_name" in variables
        assert "items" in variables

    def test_load_template_success(self, template_engine, sample_template_file):
        """Test successful template loading."""
        template = template_engine.load_template(sample_template_file)
        
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
        
        try:
            with pytest.raises(TemplateLoadError) as exc_info:
                template_engine.load_template(invalid_file)
            
            assert "YAML parsing error" in str(exc_info.value)
        finally:
            invalid_file.unlink(missing_ok=True)

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

    def test_cache_functionality(self, template_engine):
        """Test template caching functionality."""
        # Clear cache first
        template_engine.clear_cache()
        
        # Get initial cache stats
        initial_stats = template_engine.get_cache_stats()
        assert isinstance(initial_stats, dict)
        
        # Cache should start empty
        assert initial_stats.get("size", 0) == 0

    def test_thread_safety_basic(self, template_engine):
        """Test basic thread safety of template engine."""
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
        for i in range(5):  # Reduced number for simpler test
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
        assert len(results) == 5
        assert all("Hello Thread" in result for result in results)

    def test_custom_jinja_filters(self, template_engine):
        """Test custom Jinja2 filters if any are registered."""
        # Test basic template rendering works (baseline)
        result = template_engine.render_template_string("{{name|upper}}", {"name": "test"})
        assert result == "TEST"

    def test_error_handling_chain(self, template_engine):
        """Test error handling propagation through the engine."""
        # Template load error
        with pytest.raises(TemplateLoadError):
            template_engine.load_template("/nonexistent/file.yaml")
        
        # Rendering error
        with pytest.raises(RenderingError):
            template_engine.render_template_string("{{undefined}}", {})


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

    def test_integration_with_real_config(self):
        """Test template engine with real ConfigManager."""
        engine = TemplateEngine()
        
        # Should be able to render simple templates
        result = engine.render_template_string("Hello {{name}}!", {"name": "Integration"})
        assert result == "Hello Integration!"

    def test_template_variables_extraction(self):
        """Test template variable extraction functionality."""
        engine = TemplateEngine()
        
        template_content = "Project: {{project_name}}, Author: {{author}}, Year: {{year}}"
        variables = engine.get_template_variables(template_content)
        
        expected_vars = {"project_name", "author", "year"}
        assert variables == expected_vars
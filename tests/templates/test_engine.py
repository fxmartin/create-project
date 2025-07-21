# ABOUTME: Unit tests for the template engine core functionality
# ABOUTME: Tests template loading, variable resolution, and Jinja2 integration

"""Tests for template engine."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from create_project.config.config_manager import ConfigManager
from create_project.templates.engine import (
    RenderingError,
    TemplateEngine,
    TemplateLoadError,
    VariableResolutionError,
)
from create_project.templates.schema.template import Template
from create_project.templates.schema.variables import VariableType


class TestTemplateEngine:
    """Tests for TemplateEngine class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_manager = Mock(spec=ConfigManager)
        self.config_manager.get_setting.side_effect = lambda key, default: {
            "templates.directories": ["tests/fixtures/templates"],
            "templates.builtin_directory": "tests/fixtures/builtin",
            "templates.user_directory": "tests/fixtures/user"
        }.get(key, default)
        self.engine = TemplateEngine(self.config_manager)

    def test_engine_initialization(self):
        """Test template engine initialization."""
        assert self.engine.config_manager == self.config_manager
        assert self.engine.jinja_env is not None
        assert hasattr(self.engine, "_template_cache")
        assert hasattr(self.engine, "_cache_lock")

    def test_jinja_environment_setup(self):
        """Test Jinja2 environment configuration."""
        # Check that custom filters are registered
        assert "slugify" in self.engine.jinja_env.filters
        assert "snake_case" in self.engine.jinja_env.filters
        assert "pascal_case" in self.engine.jinja_env.filters
        assert "camel_case" in self.engine.jinja_env.filters

    def test_custom_filters(self):
        """Test custom Jinja2 filters."""
        # Test slugify filter
        result = self.engine.render_template_string("{{ 'Hello World!' | slugify }}", {})
        assert result == "hello-world"

        # Test snake_case filter
        result = self.engine.render_template_string("{{ 'HelloWorld' | snake_case }}", {})
        assert result == "hello_world"

        # Test pascal_case filter
        result = self.engine.render_template_string("{{ 'hello_world' | pascal_case }}", {})
        assert result == "HelloWorld"

        # Test camel_case filter
        result = self.engine.render_template_string("{{ 'hello_world' | camel_case }}", {})
        assert result == "helloWorld"

    def test_load_template_success(self):
        """Test successful template loading."""
        # Create a temporary template file
        template_data = {
            "metadata": {
                "name": "test-template",
                "description": "Test template",
                "version": "1.0.0",
                "category": "custom",
                "author": "Test Author"
            },
            "variables": [],
            "structure": {
                "root_directory": {
                    "name": "test-project",
                    "files": [],
                    "directories": []
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(template_data, f)
            temp_path = Path(f.name)

        try:
            template = self.engine.load_template(temp_path)
            assert isinstance(template, Template)
            assert template.metadata.name == "test-template"
            assert template.metadata.description == "Test template"
        finally:
            temp_path.unlink()

    def test_load_template_file_not_found(self):
        """Test template loading with non-existent file."""
        with pytest.raises(TemplateLoadError, match="Template file not found"):
            self.engine.load_template("nonexistent.yaml")

    def test_load_template_invalid_yaml(self):
        """Test template loading with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)

        try:
            with pytest.raises(TemplateLoadError, match="YAML parsing error"):
                self.engine.load_template(temp_path)
        finally:
            temp_path.unlink()

    def test_load_template_validation_error(self):
        """Test template loading with validation errors."""
        template_data = {
            "metadata": {
                "name": "",  # Invalid empty name
                "description": "Test template",
                "version": "1.0.0",
                "category": "custom"
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(template_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(TemplateLoadError, match="Template validation error"):
                self.engine.load_template(temp_path)
        finally:
            temp_path.unlink()

    def test_template_caching(self):
        """Test template caching functionality."""
        template_data = {
            "metadata": {
                "name": "cached-template",
                "description": "Test template",
                "version": "1.0.0",
                "category": "custom",
                "author": "Test Author"
            },
            "variables": [],
            "structure": {
                "root_directory": {
                    "name": "test-project",
                    "files": [],
                    "directories": []
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(template_data, f)
            temp_path = Path(f.name)

        try:
            # Load template first time
            template1 = self.engine.load_template(temp_path)

            # Load template second time (should come from cache)
            template2 = self.engine.load_template(temp_path)

            # Should be the same object from cache
            assert template1 is template2

            # Check cache stats
            stats = self.engine.get_cache_stats()
            assert stats["cached_templates"] == 1
            assert str(temp_path.absolute()) in stats["template_paths"]
        finally:
            temp_path.unlink()

    def test_resolve_variables_success(self):
        """Test successful variable resolution."""
        # Create mock template with variables
        template = Mock(spec=Template)
        var1 = Mock()
        var1.name = "project_name"
        var1.type = VariableType.STRING
        var1.required = True
        var1.default = None
        var1.show_if = None
        var1.hide_if = None
        var1.validate_value = Mock(return_value=[])

        var2 = Mock()
        var2.name = "description"
        var2.type = VariableType.STRING
        var2.required = False
        var2.default = "Default description"
        var2.show_if = None
        var2.hide_if = None
        var2.validate_value = Mock(return_value=[])

        template.variables = [var1, var2]
        template.metadata = Mock()
        template.metadata.name = "test-template"

        user_values = {"project_name": "my-project"}

        resolved = self.engine.resolve_variables(template, user_values)

        assert resolved["project_name"] == "my-project"
        assert resolved["description"] == "Default description"

    def test_resolve_variables_missing_required(self):
        """Test variable resolution with missing required variable."""
        template = Mock(spec=Template)
        var = Mock()
        var.name = "required_var"
        var.type = VariableType.STRING
        var.required = True
        var.default = None
        var.show_if = None
        var.hide_if = None

        template.variables = [var]
        template.metadata = Mock()
        template.metadata.name = "test-template"

        with pytest.raises(VariableResolutionError, match="Required variable 'required_var' not provided"):
            self.engine.resolve_variables(template, {})

    def test_resolve_variables_validation_error(self):
        """Test variable resolution with validation errors."""
        template = Mock(spec=Template)
        var = Mock()
        var.name = "invalid_var"
        var.type = VariableType.STRING
        var.required = True
        var.default = None
        var.show_if = None
        var.hide_if = None
        var.validate_value = Mock(return_value=["Value is invalid"])

        template.variables = [var]
        template.metadata = Mock()
        template.metadata.name = "test-template"

        user_values = {"invalid_var": "bad_value"}

        with pytest.raises(VariableResolutionError, match="Variable 'invalid_var': Value is invalid"):
            self.engine.resolve_variables(template, user_values)

    def test_evaluate_variable_condition_show_if(self):
        """Test variable condition evaluation with show_if."""
        variable = Mock()
        variable.name = "conditional_var"
        variable.show_if = {"variable": "enable_feature", "operator": "equals", "value": True}
        variable.hide_if = None

        # Test condition true
        resolved_values = {"enable_feature": True}
        result = self.engine._evaluate_variable_condition(variable, resolved_values)
        assert result is True

        # Test condition false
        resolved_values = {"enable_feature": False}
        result = self.engine._evaluate_variable_condition(variable, resolved_values)
        assert result is False

    def test_evaluate_variable_condition_hide_if(self):
        """Test variable condition evaluation with hide_if."""
        variable = Mock()
        variable.name = "conditional_var"
        variable.show_if = None
        variable.hide_if = {"variable": "disable_feature", "operator": "equals", "value": True}

        # Test condition true (should hide)
        resolved_values = {"disable_feature": True}
        result = self.engine._evaluate_variable_condition(variable, resolved_values)
        assert result is False

        # Test condition false (should show)
        resolved_values = {"disable_feature": False}
        result = self.engine._evaluate_variable_condition(variable, resolved_values)
        assert result is True

    def test_evaluate_condition_operators(self):
        """Test different condition operators."""
        # Test equals
        condition = {"variable": "test_var", "operator": "equals", "value": "test"}
        values = {"test_var": "test"}
        assert self.engine._evaluate_condition(condition, values) is True

        # Test not_equals
        condition = {"variable": "test_var", "operator": "not_equals", "value": "other"}
        values = {"test_var": "test"}
        assert self.engine._evaluate_condition(condition, values) is True

        # Test in
        condition = {"variable": "test_var", "operator": "in", "value": ["a", "b", "c"]}
        values = {"test_var": "b"}
        assert self.engine._evaluate_condition(condition, values) is True

        # Test contains
        condition = {"variable": "test_var", "operator": "contains", "value": "sub"}
        values = {"test_var": "substring"}
        assert self.engine._evaluate_condition(condition, values) is True

    def test_render_template_string_success(self):
        """Test successful template string rendering."""
        template_string = "Hello {{ name }}!"
        variables = {"name": "World"}

        result = self.engine.render_template_string(template_string, variables)
        assert result == "Hello World!"

    def test_render_template_string_undefined_variable(self):
        """Test template string rendering with undefined variable."""
        template_string = "Hello {{ undefined_var }}!"
        variables = {}

        with pytest.raises(RenderingError, match="Template rendering failed"):
            self.engine.render_template_string(template_string, variables)

    def test_get_template_variables(self):
        """Test extracting variables from template string."""
        template_string = "Hello {{ name }}! Your email is {{ email }}."

        variables = self.engine.get_template_variables(template_string)
        assert variables == {"name", "email"}

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Add something to cache first
        template_data = {
            "metadata": {
                "name": "test-template",
                "description": "Test template",
                "version": "1.0.0",
                "category": "custom",
                "author": "Test Author"
            },
            "variables": [],
            "structure": {
                "root_directory": {
                    "name": "test-project",
                    "files": [],
                    "directories": []
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(template_data, f)
            temp_path = Path(f.name)

        try:
            # Load template to cache it
            self.engine.load_template(temp_path)

            # Verify cache has content
            stats = self.engine.get_cache_stats()
            assert stats["cached_templates"] == 1

            # Clear cache
            self.engine.clear_cache()

            # Verify cache is empty
            stats = self.engine.get_cache_stats()
            assert stats["cached_templates"] == 0
        finally:
            temp_path.unlink()

    def test_get_cache_stats(self):
        """Test cache statistics functionality."""
        stats = self.engine.get_cache_stats()
        assert "cached_templates" in stats
        assert "template_paths" in stats
        assert isinstance(stats["cached_templates"], int)
        assert isinstance(stats["template_paths"], list)

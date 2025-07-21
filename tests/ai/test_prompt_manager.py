# ABOUTME: Comprehensive test suite for PromptManager
# ABOUTME: Tests template loading, validation, rendering, caching, and custom template support

"""
Test suite for PromptManager.

Tests the prompt template management system including:
- Template loading and discovery
- Template validation and syntax checking
- Dynamic template rendering with context
- Variable validation and injection
- Template caching functionality
- Custom template support
- Error type to template mapping
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import shutil

import pytest
from jinja2 import TemplateError as Jinja2TemplateError

from create_project.ai.prompt_manager import PromptManager
from create_project.ai.types import PromptType
from create_project.ai.exceptions import AIError
from create_project.core.exceptions import TemplateError, PathError


class TestPromptType:
    """Test PromptType enum."""
    
    def test_prompt_types(self):
        """Test all prompt types are defined."""
        assert PromptType.ERROR_HELP.value == "error_help"
        assert PromptType.SUGGESTIONS.value == "suggestions"
        assert PromptType.EXPLANATION.value == "explanation"
        assert PromptType.GENERIC_HELP.value == "generic_help"
    
    def test_prompt_type_iteration(self):
        """Test iterating over prompt types."""
        types = list(PromptType)
        assert len(types) == 4
        assert PromptType.ERROR_HELP in types


class TestPromptManager:
    """Test PromptManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories for templates
        self.temp_dir = tempfile.mkdtemp()
        self.template_dir = Path(self.temp_dir) / "templates"
        self.custom_dir = Path(self.temp_dir) / "custom"
        self.template_dir.mkdir(parents=True)
        
        # Create test templates
        self._create_test_templates()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_templates(self):
        """Create test template files."""
        templates = {
            "error_help.j2": "Error: {{ error_type }} - {{ error_message }}",
            "suggestions.j2": "Suggestions for {{ project_type }}",
            "explanation.j2": "Explaining {{ topic }}",
            "generic_help.j2": "Help with: {{ request }}"
        }
        
        for name, content in templates.items():
            (self.template_dir / name).write_text(content)
    
    def test_initialization(self):
        """Test manager initialization with valid templates."""
        manager = PromptManager(template_dir=self.template_dir)
        
        assert manager.template_dir == self.template_dir
        assert manager.custom_template_dir is None
        assert manager.cache_enabled is True
    
    def test_initialization_custom_dir(self):
        """Test initialization with custom template directory."""
        self.custom_dir.mkdir()
        manager = PromptManager(
            template_dir=self.template_dir,
            custom_template_dir=self.custom_dir
        )
        
        assert manager.custom_template_dir == self.custom_dir
    
    def test_initialization_missing_dir(self):
        """Test initialization with missing template directory."""
        with pytest.raises(AIError, match="Template directory not found"):
            PromptManager(template_dir=Path("/nonexistent"))
    
    def test_validate_builtin_templates(self):
        """Test built-in template validation on init."""
        # Create template with syntax error
        (self.template_dir / "error_help.j2").write_text("{{ unclosed")
        
        with pytest.raises(AIError, match="Template syntax error"):
            PromptManager(template_dir=self.template_dir)
    
    def test_get_template(self):
        """Test retrieving a template."""
        manager = PromptManager(template_dir=self.template_dir)
        
        template = manager.get_template(PromptType.ERROR_HELP)
        assert template is not None
        
        # Test caching
        template2 = manager.get_template(PromptType.ERROR_HELP)
        assert template is template2  # Same object from cache
    
    def test_get_template_no_cache(self):
        """Test template retrieval without caching."""
        manager = PromptManager(template_dir=self.template_dir, cache_enabled=False)
        
        template1 = manager.get_template(PromptType.ERROR_HELP)
        template2 = manager.get_template(PromptType.ERROR_HELP)
        # Different objects when cache disabled
        assert template1.name == template2.name
    
    def test_render_prompt(self):
        """Test rendering a prompt with context."""
        manager = PromptManager(template_dir=self.template_dir)
        
        context = {
            "error_type": "FileNotFoundError",
            "error_message": "Cannot find template.yaml"
        }
        
        rendered = manager.render_prompt(PromptType.ERROR_HELP, context)
        assert rendered == "Error: FileNotFoundError - Cannot find template.yaml"
    
    def test_render_prompt_missing_required(self):
        """Test rendering with missing required variables."""
        manager = PromptManager(template_dir=self.template_dir)
        
        context = {"error_type": "TestError"}  # Missing error_message
        
        with pytest.raises(AIError, match="Missing required variables"):
            manager.render_prompt(PromptType.ERROR_HELP, context)
    
    def test_render_prompt_no_validation(self):
        """Test rendering without required variable validation."""
        manager = PromptManager(template_dir=self.template_dir)
        
        context = {"error_type": "TestError"}  # Missing error_message
        
        # Should work but with missing variable in output
        rendered = manager.render_prompt(
            PromptType.ERROR_HELP,
            context,
            validate_required=False
        )
        assert "TestError" in rendered
    
    def test_render_prompt_extra_variables(self):
        """Test rendering with extra context variables."""
        manager = PromptManager(template_dir=self.template_dir)
        
        context = {
            "error_type": "TestError",
            "error_message": "Test message",
            "extra_var": "ignored"  # Extra variable
        }
        
        rendered = manager.render_prompt(PromptType.ERROR_HELP, context)
        assert rendered == "Error: TestError - Test message"
    
    def test_get_template_variables(self):
        """Test extracting variables from template."""
        # Create template with multiple variables
        (self.template_dir / "test.j2").write_text(
            "{{ var1 }} and {{ var2 }} with {% if condition %}{{ var3 }}{% endif %}"
        )
        
        manager = PromptManager(template_dir=self.template_dir)
        
        # Need to get template first
        vars = manager.get_template_variables(PromptType.ERROR_HELP)
        assert "error_type" in vars
        assert "error_message" in vars
    
    def test_add_custom_template(self):
        """Test adding a custom template."""
        self.custom_dir.mkdir()
        manager = PromptManager(
            template_dir=self.template_dir,
            custom_template_dir=self.custom_dir
        )
        
        # Add custom template
        manager.add_custom_template(
            "custom_error",
            "Custom help for {{ error_type }}: {{ solution }}",
            required_vars={"error_type", "solution"}
        )
        
        # Verify file created
        custom_file = self.custom_dir / "custom_error.j2"
        assert custom_file.exists()
        assert "Custom help for" in custom_file.read_text()
    
    def test_add_custom_template_no_dir(self):
        """Test adding custom template without custom directory."""
        manager = PromptManager(template_dir=self.template_dir)
        
        with pytest.raises(AIError, match="No custom template directory"):
            manager.add_custom_template("test", "content")
    
    def test_add_custom_template_invalid_syntax(self):
        """Test adding custom template with syntax error."""
        self.custom_dir.mkdir()
        manager = PromptManager(
            template_dir=self.template_dir,
            custom_template_dir=self.custom_dir
        )
        
        with pytest.raises(AIError, match="Invalid template syntax"):
            manager.add_custom_template("bad", "{{ unclosed")
    
    def test_list_available_templates(self):
        """Test listing all available templates."""
        manager = PromptManager(template_dir=self.template_dir)
        
        templates = manager.list_available_templates()
        
        # Should have all built-in templates
        assert "error_help" in templates
        assert "suggestions" in templates
        assert "explanation" in templates
        assert "generic_help" in templates
        
        # Check template metadata
        error_help = templates["error_help"]
        assert error_help["type"] == "builtin"
        assert "error_type" in error_help["variables"]
        assert "error_message" in error_help["variables"]
        assert "error_type" in error_help["required"]
        assert "error_message" in error_help["required"]
    
    def test_list_templates_with_custom(self):
        """Test listing templates including custom ones."""
        self.custom_dir.mkdir()
        
        # Add custom template directly
        (self.custom_dir / "custom_help.j2").write_text(
            "Custom: {{ custom_var }}"
        )
        
        manager = PromptManager(
            template_dir=self.template_dir,
            custom_template_dir=self.custom_dir
        )
        
        templates = manager.list_available_templates()
        
        # Should have custom template
        assert "custom_help" in templates
        custom = templates["custom_help"]
        assert custom["type"] == "custom"
        assert "custom_var" in custom["variables"]
        assert custom["required"] == []  # No enforced requirements
    
    def test_select_template_for_error(self):
        """Test selecting appropriate template for error type."""
        manager = PromptManager(template_dir=self.template_dir)
        
        # Test known error types
        template_error = TemplateError("test")
        assert manager.select_template_for_error(template_error) == PromptType.ERROR_HELP
        
        path_error = PathError("test")
        assert manager.select_template_for_error(path_error) == PromptType.ERROR_HELP
        
        # Test unknown error type
        generic_error = ValueError("test")
        assert manager.select_template_for_error(generic_error) == PromptType.ERROR_HELP
    
    def test_clear_cache(self):
        """Test clearing template cache."""
        manager = PromptManager(template_dir=self.template_dir)
        
        # Load template to populate cache
        template1 = manager.get_template(PromptType.ERROR_HELP)
        assert PromptType.ERROR_HELP.value in manager._template_cache
        
        # Clear cache
        manager.clear_cache()
        assert len(manager._template_cache) == 0
    
    def test_custom_template_precedence(self):
        """Test that custom templates take precedence over built-in."""
        self.custom_dir.mkdir()
        
        # Create custom version of built-in template
        (self.custom_dir / "error_help.j2").write_text(
            "CUSTOM: {{ error_type }}"
        )
        
        manager = PromptManager(
            template_dir=self.template_dir,
            custom_template_dir=self.custom_dir
        )
        
        # Should use custom version
        rendered = manager.render_prompt(
            PromptType.ERROR_HELP,
            {"error_type": "Test", "error_message": "msg"}
        )
        assert rendered == "CUSTOM: Test"
    
    def test_template_with_complex_logic(self):
        """Test template with complex Jinja2 logic."""
        # Create complex template
        complex_template = """
{% if error_context %}
Error Context:
{% for key, value in error_context.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Error: {{ error_type }}
{% if suggestions %}
Suggestions:
{% for suggestion in suggestions %}
{{ loop.index }}. {{ suggestion }}
{% endfor %}
{% endif %}
"""
        (self.template_dir / "error_help.j2").write_text(complex_template)
        
        manager = PromptManager(template_dir=self.template_dir)
        
        context = {
            "error_type": "TestError",
            "error_message": "Test",
            "error_context": {"file": "test.py", "line": 42},
            "suggestions": ["Check syntax", "Verify imports"]
        }
        
        rendered = manager.render_prompt(PromptType.ERROR_HELP, context)
        assert "Error Context:" in rendered
        assert "file: test.py" in rendered
        assert "line: 42" in rendered
        assert "1. Check syntax" in rendered
        assert "2. Verify imports" in rendered
    
    def test_template_with_filters(self):
        """Test template using Jinja2 filters."""
        # Create template with filters
        (self.template_dir / "error_help.j2").write_text(
            "Error: {{ error_type | upper }} - {{ error_message | truncate(20) }}"
        )
        
        manager = PromptManager(template_dir=self.template_dir)
        
        context = {
            "error_type": "FileNotFound",
            "error_message": "This is a very long error message that should be truncated"
        }
        
        rendered = manager.render_prompt(PromptType.ERROR_HELP, context)
        assert "FILENOTFOUND" in rendered
        assert "..." in rendered  # Truncation marker
# ABOUTME: Comprehensive unit tests for PromptManager with template loading, validation, and rendering
# ABOUTME: Tests Jinja2 template management, custom templates, caching, and error handling

"""Unit tests for prompt manager module."""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from jinja2 import TemplateNotFound, TemplateSyntaxError, TemplateError as Jinja2TemplateError

from create_project.ai.exceptions import AIError
from create_project.ai.prompt_manager import PromptManager
from create_project.ai.types import PromptType


class TestPromptManager:
    """Test PromptManager class."""

    @pytest.fixture
    def temp_template_dir(self, tmp_path):
        """Create temporary template directory with test templates."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        
        # Create test templates for each prompt type
        templates = {
            "error_help.j2": """Error: {{ error_message }}
Type: {{ error_type }}
Help: Try fixing this error.""",
            "suggestions.j2": """Project type: {{ project_type }}
Suggestions:
1. Use proper structure
2. Follow best practices""",
            "explanation.j2": """Topic: {{ topic }}
Explanation: This explains the topic in detail.""",
            "generic_help.j2": """Request: {{ request }}
Response: Here's help with your request."""
        }
        
        for filename, content in templates.items():
            (template_dir / filename).write_text(content)
        
        return template_dir

    @pytest.fixture
    def temp_custom_dir(self, tmp_path):
        """Create temporary custom template directory."""
        custom_dir = tmp_path / "custom_templates"
        custom_dir.mkdir()
        return custom_dir

    @pytest.fixture
    def prompt_manager(self, temp_template_dir):
        """Create prompt manager with test templates."""
        return PromptManager(
            template_dir=temp_template_dir,
            cache_enabled=True
        )

    def test_initialization_default_template_dir(self, tmp_path):
        """Test initialization with default template directory."""
        # Mock the default template dir to exist
        with patch.object(PromptManager, 'DEFAULT_TEMPLATE_DIR', tmp_path / "mock_templates"):
            # Create mock template files
            mock_dir = tmp_path / "mock_templates"
            mock_dir.mkdir()
            for prompt_type in PromptType:
                template_file = mock_dir / f"{prompt_type.value}.j2"
                template_file.write_text(f"Mock template for {prompt_type.value}: {{{{ request }}}}")
            
            manager = PromptManager()
            assert manager.template_dir == mock_dir
            assert manager.custom_template_dir is None
            assert manager.cache_enabled is True

    def test_initialization_custom_dirs(self, temp_template_dir, temp_custom_dir):
        """Test initialization with custom directories."""
        manager = PromptManager(
            template_dir=temp_template_dir,
            custom_template_dir=temp_custom_dir,
            cache_enabled=False
        )
        
        assert manager.template_dir == temp_template_dir
        assert manager.custom_template_dir == temp_custom_dir
        assert manager.cache_enabled is False

    def test_initialization_template_dir_not_found(self, tmp_path):
        """Test initialization with non-existent template directory."""
        nonexistent_dir = tmp_path / "nonexistent"
        
        with pytest.raises(AIError) as exc_info:
            PromptManager(template_dir=nonexistent_dir)
        
        assert "Template directory not found" in str(exc_info.value)

    def test_initialization_validates_builtin_templates(self, temp_template_dir):
        """Test that initialization validates all builtin templates."""
        # Remove one template to cause validation failure
        (temp_template_dir / "error_help.j2").unlink()
        
        with pytest.raises(AIError) as exc_info:
            PromptManager(template_dir=temp_template_dir)
        
        assert "Required template not found: error_help.j2" in str(exc_info.value)

    def test_initialization_with_invalid_template_syntax(self, temp_template_dir):
        """Test initialization with invalid template syntax."""
        # Create template with invalid syntax
        (temp_template_dir / "error_help.j2").write_text("Invalid syntax: {{ unclosed")
        
        with pytest.raises(AIError) as exc_info:
            PromptManager(template_dir=temp_template_dir)
        
        assert "Template syntax error in error_help.j2" in str(exc_info.value)

    def test_get_template_success(self, prompt_manager):
        """Test successful template retrieval."""
        template = prompt_manager.get_template(PromptType.ERROR_HELP)
        assert template is not None
        # Check template contains expected variables by rendering
        rendered = template.render(error_message="test", error_type="test")
        assert "test" in rendered

    def test_get_template_caching(self, prompt_manager):
        """Test template caching functionality."""
        # First call loads and caches
        template1 = prompt_manager.get_template(PromptType.ERROR_HELP)
        
        # Second call should return cached version
        template2 = prompt_manager.get_template(PromptType.ERROR_HELP)
        
        assert template1 is template2
        assert PromptType.ERROR_HELP.value in prompt_manager._template_cache

    def test_get_template_cache_disabled(self, temp_template_dir):
        """Test template retrieval with caching disabled."""
        manager = PromptManager(template_dir=temp_template_dir, cache_enabled=False)
        
        template1 = manager.get_template(PromptType.ERROR_HELP)
        template2 = manager.get_template(PromptType.ERROR_HELP)
        
        # Should be different instances when caching disabled
        assert template1 is not template2
        assert len(manager._template_cache) == 0

    def test_get_template_not_found(self, prompt_manager):
        """Test template retrieval when file doesn't exist."""
        # Clear cache first to ensure we hit the exception path
        prompt_manager._template_cache.clear()
        
        # Mock environment to raise TemplateNotFound
        with patch.object(prompt_manager._env, 'get_template', side_effect=TemplateNotFound("error_help.j2")) as mock_get:
            with pytest.raises(AIError) as exc_info:
                prompt_manager.get_template(PromptType.ERROR_HELP)
            
            # Check the error message contains expected text
            error_msg = str(exc_info.value)
            assert "Template loading failed for error_help.j2" in error_msg
            mock_get.assert_called_once_with("error_help.j2")

    def test_render_prompt_success(self, prompt_manager):
        """Test successful prompt rendering."""
        context = {
            "error_message": "File not found",
            "error_type": "FileNotFoundError"
        }
        
        rendered = prompt_manager.render_prompt(PromptType.ERROR_HELP, context)
        
        assert "File not found" in rendered
        assert "FileNotFoundError" in rendered

    def test_render_prompt_with_validation(self, prompt_manager):
        """Test prompt rendering with variable validation."""
        # Missing required variables
        incomplete_context = {"error_message": "Test error"}
        
        with pytest.raises(AIError) as exc_info:
            prompt_manager.render_prompt(PromptType.ERROR_HELP, incomplete_context, validate_required=True)
        
        assert "Missing required variables" in str(exc_info.value)
        assert "error_type" in str(exc_info.value)

    def test_render_prompt_without_validation(self, prompt_manager):
        """Test prompt rendering without variable validation."""
        incomplete_context = {"error_message": "Test error"}
        
        # Should work without validation
        rendered = prompt_manager.render_prompt(PromptType.ERROR_HELP, incomplete_context, validate_required=False)
        
        assert "Test error" in rendered

    def test_render_prompt_template_error(self, prompt_manager):
        """Test prompt rendering with template error."""
        # Mock template to raise error during rendering
        with patch.object(prompt_manager, 'get_template') as mock_get:
            mock_template = Mock()
            # Use generic Jinja2TemplateError which is what the code catches
            mock_template.render.side_effect = Jinja2TemplateError("Template rendering failed")
            mock_get.return_value = mock_template
            
            # Provide required context but disable validation to test template error path
            context = {"error_message": "test", "error_type": "test"}
            with pytest.raises(AIError) as exc_info:
                prompt_manager.render_prompt(PromptType.ERROR_HELP, context, validate_required=False)
            
            assert "Failed to render error_help template" in str(exc_info.value)

    def test_get_template_variables(self, prompt_manager):
        """Test getting template variables."""
        variables = prompt_manager.get_template_variables(PromptType.ERROR_HELP)
        
        assert "error_message" in variables
        assert "error_type" in variables
        assert isinstance(variables, set)

    def test_add_custom_template_success(self, prompt_manager, temp_custom_dir):
        """Test adding custom template successfully."""
        prompt_manager.custom_template_dir = temp_custom_dir
        
        template_content = "Custom template: {{ custom_var }}"
        required_vars = {"custom_var"}
        
        prompt_manager.add_custom_template("custom", template_content, required_vars)
        
        # Check file was created
        template_file = temp_custom_dir / "custom.j2"
        assert template_file.exists()
        assert template_file.read_text() == template_content

    def test_add_custom_template_no_custom_dir(self, prompt_manager):
        """Test adding custom template without custom directory configured."""
        with pytest.raises(AIError) as exc_info:
            prompt_manager.add_custom_template("custom", "{{ var }}")
        
        assert "No custom template directory configured" in str(exc_info.value)

    def test_add_custom_template_invalid_syntax(self, prompt_manager, temp_custom_dir):
        """Test adding custom template with invalid syntax."""
        prompt_manager.custom_template_dir = temp_custom_dir
        
        invalid_content = "Invalid template: {{ unclosed"
        
        with pytest.raises(AIError) as exc_info:
            prompt_manager.add_custom_template("invalid", invalid_content)
        
        assert "Invalid template syntax" in str(exc_info.value)

    def test_add_custom_template_missing_required_vars(self, prompt_manager, temp_custom_dir):
        """Test adding custom template missing required variables."""
        prompt_manager.custom_template_dir = temp_custom_dir
        
        template_content = "Template without required var"
        required_vars = {"missing_var"}
        
        # Should succeed but log warning
        prompt_manager.add_custom_template("incomplete", template_content, required_vars)
        
        # Template should still be created
        template_file = temp_custom_dir / "incomplete.j2"
        assert template_file.exists()

    def test_add_custom_template_clears_cache(self, prompt_manager, temp_custom_dir):
        """Test that adding custom template clears cache."""
        prompt_manager.custom_template_dir = temp_custom_dir
        
        # Pre-populate cache
        prompt_manager._template_cache["test"] = Mock()
        prompt_manager._env.cache["test"] = Mock()
        
        prompt_manager.add_custom_template("test", "{{ var }}")
        
        # Cache should be cleared
        assert "test" not in prompt_manager._template_cache
        assert len(prompt_manager._env.cache) == 0

    def test_list_available_templates(self, prompt_manager):
        """Test listing available templates."""
        templates = prompt_manager.list_available_templates()
        
        # Should have all built-in templates
        for prompt_type in PromptType:
            assert prompt_type.value in templates
            template_info = templates[prompt_type.value]
            assert template_info["type"] == "builtin"
            assert "path" in template_info
            assert "variables" in template_info
            assert "required" in template_info

    def test_list_available_templates_with_custom(self, prompt_manager, temp_custom_dir):
        """Test listing templates including custom ones."""
        prompt_manager.custom_template_dir = temp_custom_dir
        
        # Reinitialize environment to include custom template dir
        search_paths = [str(temp_custom_dir), str(prompt_manager.template_dir)]
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        prompt_manager._env = Environment(
            loader=FileSystemLoader(search_paths),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            cache_size=50 if prompt_manager.cache_enabled else 0,
        )
        
        # Add custom template
        custom_file = temp_custom_dir / "custom.j2"
        custom_file.write_text("Custom: {{ custom_var }}")
        
        templates = prompt_manager.list_available_templates()
        
        # Should include custom template
        assert "custom" in templates
        custom_info = templates["custom"]
        assert custom_info["type"] == "custom"
        assert "custom_var" in custom_info["variables"]

    def test_list_available_templates_handles_errors(self, prompt_manager, temp_custom_dir):
        """Test listing templates handles individual template errors gracefully."""
        prompt_manager.custom_template_dir = temp_custom_dir
        
        # Create invalid custom template
        invalid_file = temp_custom_dir / "invalid.j2"
        invalid_file.write_text("{{ unclosed")
        
        # Should not raise error, just skip invalid template
        templates = prompt_manager.list_available_templates()
        
        # Should still have builtin templates
        assert len(templates) >= len(PromptType)
        # Invalid template should not be included
        assert "invalid" not in templates

    def test_select_template_for_error_specific_mapping(self, prompt_manager):
        """Test error-specific template selection."""
        # Create custom error classes for testing
        class TemplateError(Exception):
            pass
        
        class ValidationError(Exception):
            pass
        
        class PathError(Exception):
            pass
        
        # Create error instances
        template_error = TemplateError("TemplateError occurred")
        validation_error = ValidationError("ValidationError occurred")
        path_error = PathError("PathError occurred")
        
        # Test specific mappings
        assert prompt_manager.select_template_for_error(template_error) == PromptType.ERROR_HELP
        assert prompt_manager.select_template_for_error(validation_error) == PromptType.ERROR_HELP
        assert prompt_manager.select_template_for_error(path_error) == PromptType.ERROR_HELP

    def test_select_template_for_error_default(self, prompt_manager):
        """Test default template selection for unknown errors."""
        unknown_error = RuntimeError("Unknown error")
        
        result = prompt_manager.select_template_for_error(unknown_error)
        assert result == PromptType.ERROR_HELP

    def test_select_template_for_error_partial_match(self, prompt_manager):
        """Test template selection with partial error name matching."""
        # Create custom GitError class for testing
        class GitError(Exception):
            pass
        
        git_error = GitError("Git operation failed")
        
        result = prompt_manager.select_template_for_error(git_error)
        assert result == PromptType.ERROR_HELP

    def test_clear_cache(self, prompt_manager):
        """Test cache clearing functionality."""
        # Populate caches
        prompt_manager._template_cache["test"] = Mock()
        prompt_manager._env.cache["test"] = Mock()
        
        prompt_manager.clear_cache()
        
        assert len(prompt_manager._template_cache) == 0
        assert len(prompt_manager._env.cache) == 0

    def test_required_vars_mapping(self, prompt_manager):
        """Test that required variables mapping is correct."""
        expected_mappings = {
            PromptType.ERROR_HELP: {"error_message", "error_type"},
            PromptType.SUGGESTIONS: {"project_type"},
            PromptType.EXPLANATION: {"topic"}, 
            PromptType.GENERIC_HELP: {"request"},
        }
        
        assert prompt_manager.REQUIRED_VARS == expected_mappings

    def test_template_extension_constant(self, prompt_manager):
        """Test template extension constant."""
        assert prompt_manager.TEMPLATE_EXT == ".j2"

    def test_custom_template_precedence(self, temp_template_dir, temp_custom_dir):
        """Test that custom templates take precedence over built-in ones."""
        # Create custom template with same name as built-in
        custom_template = temp_custom_dir / "error_help.j2"
        custom_template.write_text("Custom error help: {{ error_message }}")
        
        manager = PromptManager(
            template_dir=temp_template_dir,
            custom_template_dir=temp_custom_dir
        )
        
        template = manager.get_template(PromptType.ERROR_HELP)
        rendered = template.render(error_message="test", error_type="test")
        
        # Should use custom template
        assert "Custom error help" in rendered

    def test_jinja2_environment_configuration(self, prompt_manager):
        """Test Jinja2 environment is configured correctly."""
        env = prompt_manager._env
        
        # Check autoescape is configured
        assert env.autoescape is not None
        
        # Check trim/lstrip blocks are enabled
        assert env.trim_blocks is True
        assert env.lstrip_blocks is True
        
        # Check cache size based on cache_enabled
        if prompt_manager.cache_enabled:
            assert env.cache.capacity == 50
        else:
            assert env.cache.capacity == 0

    def test_template_variables_detection(self, prompt_manager):
        """Test that template variable detection works correctly."""
        # Test with error_help template
        variables = prompt_manager.get_template_variables(PromptType.ERROR_HELP)
        
        # Should detect variables from template
        assert "error_message" in variables
        assert "error_type" in variables

    def test_builtin_template_validation_warnings(self, temp_template_dir):
        """Test that missing required variables generate warnings."""
        # Create template missing required variables
        incomplete_template = temp_template_dir / "error_help.j2"
        incomplete_template.write_text("Only has: {{ error_message }}")  # Missing error_type
        
        with patch("create_project.ai.prompt_manager.logger") as mock_logger:
            PromptManager(template_dir=temp_template_dir)
            
            # Should log warning about missing variables
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args
            assert "Template missing required variables" in warning_call[0][0]

    def test_render_prompt_context_logging(self, prompt_manager):
        """Test that rendering logs context information."""
        context = {
            "error_message": "Test error",
            "error_type": "TestError"
        }
        
        with patch("create_project.ai.prompt_manager.logger") as mock_logger:
            prompt_manager.render_prompt(PromptType.ERROR_HELP, context)
            
            # Should log successful rendering
            mock_logger.debug.assert_called()
            debug_call = mock_logger.debug.call_args
            assert "Prompt rendered successfully" in debug_call[0][0]

    def test_concurrent_template_access(self, prompt_manager):
        """Test concurrent access to templates."""
        import threading
        
        results = []
        errors = []
        
        def render_template():
            try:
                context = {"error_message": "test", "error_type": "test"}
                result = prompt_manager.render_prompt(PromptType.ERROR_HELP, context, validate_required=False)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=render_template)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(errors) == 0
        assert len(results) == 5
        # All results should be identical
        assert all(r == results[0] for r in results)

    def test_template_syntax_validation_during_init(self, temp_template_dir):
        """Test that template syntax is validated during initialization."""
        # Create template with valid syntax
        valid_template = temp_template_dir / "error_help.j2"
        valid_template.write_text("Valid: {{ error_message }}")
        
        # Should not raise error
        manager = PromptManager(template_dir=temp_template_dir)
        assert manager is not None

    def test_custom_template_directory_creation(self, prompt_manager, tmp_path):
        """Test that custom template directory is created if it doesn't exist."""
        custom_dir = tmp_path / "new_custom"
        prompt_manager.custom_template_dir = custom_dir
        
        # Directory doesn't exist yet
        assert not custom_dir.exists()
        
        # Adding template should create directory
        prompt_manager.add_custom_template("test", "{{ var }}")
        
        assert custom_dir.exists()
        assert custom_dir.is_dir()

    def test_empty_context_rendering(self, prompt_manager):
        """Test rendering templates with empty context."""
        # Should work without validation
        rendered = prompt_manager.render_prompt(
            PromptType.ERROR_HELP, 
            {}, 
            validate_required=False
        )
        
        assert isinstance(rendered, str)
        assert len(rendered) > 0

    def test_template_with_filters_and_functions(self, temp_template_dir):
        """Test templates using Jinja2 filters and functions."""
        # Create template with filters
        template_content = """
Error: {{ error_message | upper }}
Type: {{ error_type | default("Unknown") }}
Count: {{ items | length if items else 0 }}
"""
        
        (temp_template_dir / "error_help.j2").write_text(template_content)
        
        manager = PromptManager(template_dir=temp_template_dir)
        
        context = {
            "error_message": "file not found",
            "error_type": "FileError",
            "items": ["a", "b", "c"]
        }
        
        rendered = manager.render_prompt(PromptType.ERROR_HELP, context, validate_required=False)
        
        assert "FILE NOT FOUND" in rendered  # upper filter
        assert "FileError" in rendered
        assert "3" in rendered  # length filter
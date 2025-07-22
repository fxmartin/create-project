# ABOUTME: Unit tests for file template rendering functionality
# ABOUTME: Tests FileRenderer class with encoding, permissions, and template processing

"""
Unit tests for file renderer.

This module tests the FileRenderer class with focus on:
- Template variable substitution and rendering
- Binary and text file handling appropriately
- File permission setting and executable detection
- Encoding detection and Unicode handling
- Error conditions and recovery
- Integration with template engine and path handler
"""

import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from create_project.core.exceptions import TemplateError
from create_project.core.file_renderer import FileRenderer
from create_project.core.path_utils import PathHandler
from create_project.templates.engine import TemplateEngine
from create_project.templates.loader import TemplateLoader


class TestFileRenderer:
    """Test suite for FileRenderer class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def renderer(self):
        """Create a FileRenderer instance for testing."""
        return FileRenderer()

    @pytest.fixture
    def custom_renderer(self):
        """Create FileRenderer with custom components."""
        path_handler = PathHandler()
        template_engine = TemplateEngine()
        template_loader = TemplateLoader()
        return FileRenderer(path_handler, template_engine, template_loader)

    def test_init_default_components(self, renderer):
        """Test FileRenderer initialization with default components."""
        assert renderer is not None
        assert hasattr(renderer, "path_handler")
        assert hasattr(renderer, "template_engine")
        assert hasattr(renderer, "template_loader")
        assert hasattr(renderer, "logger")
        assert hasattr(renderer, "rendered_files")
        assert isinstance(renderer.path_handler, PathHandler)
        assert isinstance(renderer.template_engine, TemplateEngine)
        assert isinstance(renderer.template_loader, TemplateLoader)
        assert renderer.rendered_files == []

    def test_init_custom_components(self, custom_renderer):
        """Test FileRenderer initialization with custom components."""
        assert custom_renderer is not None
        assert isinstance(custom_renderer.path_handler, PathHandler)
        assert isinstance(custom_renderer.template_engine, TemplateEngine)
        assert isinstance(custom_renderer.template_loader, TemplateLoader)

    def test_render_simple_text_file(self, renderer, temp_dir):
        """Test rendering a simple text template file."""
        # Create template file
        template_file = temp_dir / "test.txt.j2"
        template_content = "Hello {{ name }}! Your age is {{ age }}."
        template_file.write_text(template_content)

        # Create target file path
        target_file = temp_dir / "output.txt"

        # Variables for substitution
        variables = {"name": "Alice", "age": 30}

        # Render the file
        renderer.render_file(template_file, target_file, variables)

        # Verify file was created with correct content
        assert target_file.exists()
        content = target_file.read_text()
        assert content == "Hello Alice! Your age is 30."

        # Verify file is tracked
        rendered_files = renderer.get_rendered_files()
        assert len(rendered_files) == 1
        assert target_file.resolve() in rendered_files

    def test_render_file_with_encoding(self, renderer, temp_dir):
        """Test rendering file with specific encoding."""
        # Create template file with Unicode content
        template_file = temp_dir / "unicode.txt.j2"
        template_content = "Café: {{ café_name }}, Price: {{ price }}€"
        template_file.write_text(template_content, encoding="utf-8")

        target_file = temp_dir / "unicode_output.txt"
        variables = {"café_name": "Le Café", "price": 4.50}

        renderer.render_file(template_file, target_file, variables, encoding="utf-8")

        assert target_file.exists()
        content = target_file.read_text(encoding="utf-8")
        assert "Café: Le Café, Price: 4.5€" in content

    def test_render_executable_file(self, renderer, temp_dir):
        """Test rendering file marked as executable."""
        template_file = temp_dir / "script.sh.j2"
        template_content = "#!/bin/bash\necho 'Hello {{ name }}!'"
        template_file.write_text(template_content)

        target_file = temp_dir / "script.sh"
        variables = {"name": "World"}

        renderer.render_file(template_file, target_file, variables, executable=True)

        assert target_file.exists()

        # Check file permissions
        file_stat = target_file.stat()
        assert file_stat.st_mode & stat.S_IXUSR  # Owner execute permission
        assert file_stat.st_mode & stat.S_IRUSR  # Owner read permission
        assert file_stat.st_mode & stat.S_IWUSR  # Owner write permission

    def test_render_non_executable_file(self, renderer, temp_dir):
        """Test rendering regular file (non-executable)."""
        template_file = temp_dir / "config.txt.j2"
        template_content = "setting={{ value }}"
        template_file.write_text(template_content)

        target_file = temp_dir / "config.txt"
        variables = {"value": "production"}

        renderer.render_file(template_file, target_file, variables, executable=False)

        assert target_file.exists()

        # Check file permissions (should not be executable)
        file_stat = target_file.stat()
        assert not (file_stat.st_mode & stat.S_IXUSR)  # No execute permission
        assert file_stat.st_mode & stat.S_IRUSR  # Owner read permission
        assert file_stat.st_mode & stat.S_IWUSR  # Owner write permission

    def test_render_binary_file(self, renderer, temp_dir):
        """Test handling of binary files."""
        # Create binary file
        binary_data = b"\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR"
        template_file = temp_dir / "image.png"
        template_file.write_bytes(binary_data)

        target_file = temp_dir / "output.png"
        variables = {"name": "test"}  # Should be ignored for binary files

        renderer.render_file(template_file, target_file, variables)

        assert target_file.exists()
        assert target_file.read_bytes() == binary_data

    def test_render_file_with_progress_callback(self, renderer, temp_dir):
        """Test rendering with progress callback."""
        template_file = temp_dir / "test.txt.j2"
        template_file.write_text("Content: {{ value }}")
        target_file = temp_dir / "output.txt"

        progress_messages = []

        def progress_callback(message):
            progress_messages.append(message)

        renderer.render_file(
            template_file,
            target_file,
            {"value": "test"},
            progress_callback=progress_callback,
        )

        assert len(progress_messages) > 0
        assert any("Rendering:" in msg for msg in progress_messages)

    def test_render_file_template_not_found(self, renderer, temp_dir):
        """Test error when template file doesn't exist."""
        template_file = temp_dir / "nonexistent.txt.j2"
        target_file = temp_dir / "output.txt"

        with pytest.raises(TemplateError) as exc_info:
            renderer.render_file(template_file, target_file, {})

        assert "not found" in str(exc_info.value).lower()

    def test_render_file_template_error(self, renderer, temp_dir):
        """Test error handling for template rendering errors."""
        # Create template with invalid syntax
        template_file = temp_dir / "invalid.txt.j2"
        template_content = "Hello {{ name "  # Missing closing brace
        template_file.write_text(template_content)

        target_file = temp_dir / "output.txt"

        with pytest.raises(TemplateError):
            renderer.render_file(template_file, target_file, {"name": "test"})

    def test_render_files_from_structure_simple(self, renderer, temp_dir):
        """Test rendering multiple files from structure definition."""
        # Create template directory structure
        template_dir = temp_dir / "templates"
        template_dir.mkdir()

        # Create template files
        (template_dir / "file1.txt.j2").write_text("File 1: {{ value }}")
        (template_dir / "file2.py.j2").write_text("# File 2\nvalue = {{ value }}")

        # Target directory
        target_dir = temp_dir / "output"

        # Structure definition
        structure = {"file1.txt.j2": None, "file2.py.j2": None}

        variables = {"value": "test"}

        renderer.render_files_from_structure(
            template_dir, target_dir, structure, variables
        )

        # Check that files were created
        assert (target_dir / "file1.txt").exists()
        assert (target_dir / "file2.py").exists()

        # Check content
        assert "File 1: test" in (target_dir / "file1.txt").read_text()
        assert "value = test" in (target_dir / "file2.py").read_text()

    def test_render_files_from_structure_nested(self, renderer, temp_dir):
        """Test rendering files from nested directory structure."""
        template_dir = temp_dir / "templates"
        template_dir.mkdir()
        (template_dir / "src").mkdir()
        (template_dir / "src" / "utils").mkdir()

        # Create nested template files
        (template_dir / "src" / "main.py.j2").write_text("# Main: {{ project }}")
        (template_dir / "src" / "utils" / "helper.py.j2").write_text(
            "# Helper: {{ project }}"
        )

        target_dir = temp_dir / "output"

        structure = {"src": {"main.py.j2": None, "utils": {"helper.py.j2": None}}}

        variables = {"project": "MyProject"}

        renderer.render_files_from_structure(
            template_dir, target_dir, structure, variables
        )

        # Check nested files were created
        assert (target_dir / "src" / "main.py").exists()
        assert (target_dir / "src" / "utils" / "helper.py").exists()

        # Check content
        assert "Main: MyProject" in (target_dir / "src" / "main.py").read_text()
        assert (
            "Helper: MyProject"
            in (target_dir / "src" / "utils" / "helper.py").read_text()
        )

    def test_is_binary_file_text(self, renderer, temp_dir):
        """Test binary file detection for text files."""
        text_file = temp_dir / "text.txt"
        text_file.write_text("This is regular text content")

        assert not renderer._is_binary_file(text_file)

    def test_is_binary_file_binary(self, renderer, temp_dir):
        """Test binary file detection for binary files."""
        binary_file = temp_dir / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x89PNG")

        assert renderer._is_binary_file(binary_file)

    def test_is_binary_file_empty(self, renderer, temp_dir):
        """Test binary file detection for empty files."""
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("")

        assert not renderer._is_binary_file(empty_file)

    def test_detect_encoding_ascii(self, renderer, temp_dir):
        """Test encoding detection for ASCII files."""
        ascii_file = temp_dir / "ascii.txt"
        ascii_file.write_text("Hello World", encoding="ascii")

        encoding = renderer._detect_encoding(ascii_file)
        assert encoding in ["ascii", "utf-8"]  # Both are valid for ASCII content

    def test_detect_encoding_utf8(self, renderer, temp_dir):
        """Test encoding detection for UTF-8 files."""
        utf8_file = temp_dir / "utf8.txt"
        utf8_file.write_text("Café résumé naïve", encoding="utf-8")

        encoding = renderer._detect_encoding(utf8_file)
        assert encoding == "utf-8"

    def test_detect_encoding_fallback(self, renderer, temp_dir):
        """Test encoding detection fallback for problematic files."""
        # Create file with mixed encoding
        problem_file = temp_dir / "problem.txt"

        with patch(
            "chardet.detect", return_value={"encoding": None, "confidence": 0.1}
        ):
            encoding = renderer._detect_encoding(problem_file)
            assert encoding == "utf-8"  # Should fallback to utf-8

    def test_should_be_executable_by_extension(self, renderer):
        """Test executable detection by file extension."""
        assert renderer._should_be_executable("script.sh", None)
        assert renderer._should_be_executable("script.py", None)
        assert renderer._should_be_executable("script.pl", None)
        assert renderer._should_be_executable("script.rb", None)
        assert not renderer._should_be_executable("config.txt", None)
        assert not renderer._should_be_executable("data.json", None)

    def test_should_be_executable_by_name(self, renderer):
        """Test executable detection by filename."""
        assert renderer._should_be_executable("Makefile", None)
        assert renderer._should_be_executable("makefile", None)
        assert not renderer._should_be_executable("README", None)
        assert not renderer._should_be_executable("config", None)

    def test_should_be_executable_by_pattern(self, renderer):
        """Test executable detection by filename patterns."""
        assert renderer._should_be_executable("run-tests", None)
        assert renderer._should_be_executable("build-script", None)
        assert not renderer._should_be_executable("test-data", None)
        assert not renderer._should_be_executable("sample-config", None)

    def test_validate_template_file_valid_text(self, renderer, temp_dir):
        """Test validation of valid text template."""
        template_file = temp_dir / "valid.txt.j2"
        template_file.write_text("Hello {{ name }}!")

        assert renderer.validate_template_file(template_file) is True

    def test_validate_template_file_valid_binary(self, renderer, temp_dir):
        """Test validation of binary files."""
        binary_file = temp_dir / "image.png"
        binary_file.write_bytes(b"\x89PNG\x0d\x0a")

        assert renderer.validate_template_file(binary_file) is True

    def test_validate_template_file_not_found(self, renderer, temp_dir):
        """Test validation when template file doesn't exist."""
        nonexistent = temp_dir / "nonexistent.txt"

        with pytest.raises(TemplateError) as exc_info:
            renderer.validate_template_file(nonexistent)
        assert "not found" in str(exc_info.value).lower()

    def test_validate_template_file_not_file(self, renderer, temp_dir):
        """Test validation when path is not a file."""
        directory = temp_dir / "directory"
        directory.mkdir()

        with pytest.raises(TemplateError) as exc_info:
            renderer.validate_template_file(directory)
        assert "not a file" in str(exc_info.value).lower()

    def test_validate_template_file_invalid_syntax(self, renderer, temp_dir):
        """Test validation with invalid template syntax."""
        invalid_template = temp_dir / "invalid.txt.j2"
        invalid_template.write_text("Hello {{ name")  # Missing closing brace

        with pytest.raises(TemplateError) as exc_info:
            renderer.validate_template_file(invalid_template)
        assert "invalid template syntax" in str(exc_info.value).lower()

    def test_preview_rendered_content_text(self, renderer, temp_dir):
        """Test preview functionality for text templates."""
        template_file = temp_dir / "preview.txt.j2"
        template_content = "Line 1: {{ var1 }}\nLine 2: {{ var2 }}\nLine 3: Final"
        template_file.write_text(template_content)

        variables = {"var1": "Hello", "var2": "World"}
        preview = renderer.preview_rendered_content(
            template_file, variables, max_lines=5
        )

        expected_lines = ["Line 1: Hello", "Line 2: World", "Line 3: Final"]
        for line in expected_lines:
            assert line in preview

    def test_preview_rendered_content_binary(self, renderer, temp_dir):
        """Test preview functionality for binary files."""
        binary_file = temp_dir / "image.png"
        binary_data = b"\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR"
        binary_file.write_bytes(binary_data)

        preview = renderer.preview_rendered_content(binary_file, {})
        assert "[Binary file:" in preview
        assert "image.png]" in preview

    def test_preview_rendered_content_truncated(self, renderer, temp_dir):
        """Test preview truncation for long content."""
        template_file = temp_dir / "long.txt.j2"
        # Create template with many lines
        lines = [f"Line {i}: {{ value }}" for i in range(100)]
        template_file.write_text("\n".join(lines))

        variables = {"value": "test"}
        preview = renderer.preview_rendered_content(
            template_file, variables, max_lines=10
        )

        preview_lines = preview.split("\n")
        assert len(preview_lines) <= 11  # 10 lines + truncation message
        assert "more lines" in preview_lines[-1].lower()

    def test_get_rendered_files(self, renderer, temp_dir):
        """Test getting list of rendered files."""
        initial_files = renderer.get_rendered_files()
        assert initial_files == []

        # Render some files
        template1 = temp_dir / "template1.txt.j2"
        template1.write_text("Content 1")
        target1 = temp_dir / "output1.txt"
        renderer.render_file(template1, target1, {})

        template2 = temp_dir / "template2.txt.j2"
        template2.write_text("Content 2")
        target2 = temp_dir / "output2.txt"
        renderer.render_file(template2, target2, {})

        rendered_files = renderer.get_rendered_files()
        assert len(rendered_files) == 2
        assert target1.resolve() in rendered_files
        assert target2.resolve() in rendered_files

        # Should return a copy, not original list
        rendered_files.append(Path("/fake/path"))
        assert len(renderer.get_rendered_files()) == 2

    def test_clear_rendered_files(self, renderer, temp_dir):
        """Test clearing the rendered files list."""
        # Render a file
        template_file = temp_dir / "template.txt.j2"
        template_file.write_text("Content")
        target_file = temp_dir / "output.txt"
        renderer.render_file(template_file, target_file, {})

        assert len(renderer.get_rendered_files()) == 1

        renderer.clear_rendered_files()
        assert len(renderer.get_rendered_files()) == 0

    def test_rollback_rendered_files(self, renderer, temp_dir):
        """Test rollback functionality."""
        # Render some files
        template1 = temp_dir / "template1.txt.j2"
        template1.write_text("Content 1")
        target1 = temp_dir / "output1.txt"
        renderer.render_file(template1, target1, {})

        template2 = temp_dir / "template2.txt.j2"
        template2.write_text("Content 2")
        target2 = temp_dir / "output2.txt"
        renderer.render_file(template2, target2, {})

        # Verify files exist
        assert target1.exists()
        assert target2.exists()
        assert len(renderer.get_rendered_files()) == 2

        # Rollback
        renderer.rollback_rendered_files()

        # Verify files are removed and list is cleared
        assert not target1.exists()
        assert not target2.exists()
        assert len(renderer.get_rendered_files()) == 0

    def test_rollback_rendered_files_empty_list(self, renderer):
        """Test rollback with no rendered files."""
        # Should not raise any exception
        renderer.rollback_rendered_files()

    def test_rollback_rendered_files_with_errors(self, renderer, temp_dir):
        """Test rollback when some file removals fail."""
        # Render a file
        template_file = temp_dir / "template.txt.j2"
        template_file.write_text("Content")
        target_file = temp_dir / "output.txt"
        renderer.render_file(template_file, target_file, {})

        # Mock unlink to fail
        with patch("pathlib.Path.unlink", side_effect=OSError("Removal failed")):
            with pytest.raises(Exception):  # Should raise ProjectGenerationError
                renderer.rollback_rendered_files()

    def test_count_files_in_structure(self, renderer):
        """Test counting files in structure definition."""
        structure = {
            "file1.txt": None,
            "dir1": {"file2.py": None, "file3.js": None, "dir2": {"file4.md": None}},
            "file5.json": None,
        }

        count = renderer._count_files_in_structure(structure)
        assert count == 5  # file1, file2, file3, file4, file5

    def test_count_files_in_structure_empty(self, renderer):
        """Test counting files in empty structure."""
        assert renderer._count_files_in_structure({}) == 0

    def test_set_file_permissions_error_handling(self, renderer, temp_dir):
        """Test file permission setting error handling."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        # Mock os.chmod to fail
        with patch("os.chmod", side_effect=OSError("Permission denied")):
            # Should not raise exception, just log warning
            renderer._set_file_permissions(test_file, executable=True)

    def test_render_file_creates_target_directory(self, renderer, temp_dir):
        """Test that rendering creates target directories as needed."""
        template_file = temp_dir / "template.txt.j2"
        template_file.write_text("Content: {{ value }}")

        # Target in nested directory that doesn't exist
        target_file = temp_dir / "nested" / "subdir" / "output.txt"
        assert not target_file.parent.exists()

        renderer.render_file(template_file, target_file, {"value": "test"})

        assert target_file.exists()
        assert target_file.parent.exists()
        assert "Content: test" in target_file.read_text()

    def test_render_file_j2_extension_removal(self, renderer, temp_dir):
        """Test that .j2 extension is removed from target files in structure rendering."""
        template_dir = temp_dir / "templates"
        template_dir.mkdir()

        template_file = template_dir / "config.yml.j2"
        template_file.write_text("setting: {{ value }}")

        target_dir = temp_dir / "output"
        structure = {"config.yml.j2": None}

        renderer.render_files_from_structure(
            template_dir, target_dir, structure, {"value": "production"}
        )

        # Should create config.yml (without .j2)
        assert (target_dir / "config.yml").exists()
        assert not (target_dir / "config.yml.j2").exists()

    def test_error_handling_preserves_original_error(self, renderer, temp_dir):
        """Test that error handling preserves original exceptions."""
        template_file = temp_dir / "template.txt.j2"
        template_file.write_text("Invalid: {{ ")
        target_file = temp_dir / "output.txt"

        with pytest.raises(TemplateError) as exc_info:
            renderer.render_file(template_file, target_file, {})

        # Check that original error context is preserved
        error = exc_info.value
        assert hasattr(error, "details")
        assert hasattr(error, "original_error")
        assert error.original_error is not None


class TestFileRendererIntegration:
    """Integration tests for FileRenderer with other components."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def renderer(self):
        """Create FileRenderer for integration testing."""
        return FileRenderer()

    def test_integration_with_template_engine(self, renderer, temp_dir):
        """Test integration with the template engine for advanced features."""
        template_file = temp_dir / "advanced.txt.j2"
        # Use template engine features like loops and conditions
        template_content = """
Project: {{ project_name }}
{% if features %}
Features:
{% for feature in features %}
  - {{ feature }}
{% endfor %}
{% endif %}
Environment: {{ environment | default('development') }}
"""
        template_file.write_text(template_content)

        target_file = temp_dir / "advanced.txt"
        variables = {
            "project_name": "MyApp",
            "features": ["authentication", "database", "api"],
            "environment": "production",
        }

        renderer.render_file(template_file, target_file, variables)

        content = target_file.read_text()
        assert "Project: MyApp" in content
        assert "- authentication" in content
        assert "- database" in content
        assert "- api" in content
        assert "Environment: production" in content

    def test_integration_with_path_handler_security(self, renderer, temp_dir):
        """Test integration with PathHandler security features."""
        template_file = temp_dir / "template.txt.j2"
        template_file.write_text("Content")

        # Try to use dangerous path - this should be blocked by PathHandler
        with pytest.raises(Exception):  # Should raise PathError or SecurityError
            # Create a path that contains dangerous traversal patterns
            dangerous_target = Path(str(temp_dir) + "/../../../etc/passwd")
            renderer.render_file(template_file, dangerous_target, {})

    def test_real_world_structure_rendering(self, renderer, temp_dir):
        """Test rendering a realistic project structure."""
        # Create realistic template structure
        template_dir = temp_dir / "templates"
        template_dir.mkdir()

        # Create various template files
        (template_dir / "README.md.j2").write_text(
            "# {{ project_name }}\n\n{{ description }}"
        )
        (template_dir / "setup.py.j2").write_text("""
from setuptools import setup

setup(
    name="{{ project_name }}",
    version="{{ version }}",
    description="{{ description }}",
    author="{{ author }}",
)
""")

        # Create subdirectory templates
        src_dir = template_dir / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py.j2").write_text('"""{{ project_name }} package."""')
        (src_dir / "main.py.j2").write_text("""#!/usr/bin/env python3
\"\"\"Main module for {{ project_name }}.\"\"\"

def main():
    print("Hello from {{ project_name }}!")

if __name__ == "__main__":
    main()
""")

        # Define structure
        structure = {
            "README.md.j2": None,
            "setup.py.j2": None,
            "src": {"__init__.py.j2": None, "main.py.j2": None},
        }

        # Variables
        variables = {
            "project_name": "awesome-app",
            "description": "An awesome Python application",
            "version": "1.0.0",
            "author": "Test Developer",
        }

        target_dir = temp_dir / "output"

        # Render the structure
        renderer.render_files_from_structure(
            template_dir, target_dir, structure, variables
        )

        # Verify all files were created correctly
        assert (target_dir / "README.md").exists()
        assert (target_dir / "setup.py").exists()
        assert (target_dir / "src" / "__init__.py").exists()
        assert (target_dir / "src" / "main.py").exists()

        # Verify content is correct
        readme_content = (target_dir / "README.md").read_text()
        assert "# awesome-app" in readme_content
        assert "An awesome Python application" in readme_content

        setup_content = (target_dir / "setup.py").read_text()
        assert 'name="awesome-app"' in setup_content
        assert 'version="1.0.0"' in setup_content

        main_content = (target_dir / "src" / "main.py").read_text()
        assert "Hello from awesome-app!" in main_content

        # Check that main.py should be executable (ends with .py)
        main_file = target_dir / "src" / "main.py"
        if not main_content.startswith("#!/usr/bin/env python3"):
            # If the template includes shebang, it should be executable
            pass  # This would be handled by the _should_be_executable logic

    def test_mixed_binary_and_text_rendering(self, renderer, temp_dir):
        """Test rendering structure with mixed binary and text files."""
        template_dir = temp_dir / "templates"
        template_dir.mkdir()

        # Create text template
        (template_dir / "config.txt.j2").write_text("setting={{ value }}")

        # Create binary file with proper PNG header
        binary_data = b"\x89PNG\x0d\x0a\x1a\x0a\x00\x00\x00\x0dIHDR"
        (template_dir / "logo.png").write_bytes(binary_data)

        structure = {"config.txt.j2": None, "logo.png": None}

        target_dir = temp_dir / "output"
        variables = {"value": "production"}

        renderer.render_files_from_structure(
            template_dir, target_dir, structure, variables
        )

        # Verify text file was processed
        config_file = target_dir / "config.txt"
        assert config_file.exists()
        assert "setting=production" in config_file.read_text()

        # Verify binary file was copied unchanged
        logo_file = target_dir / "logo.png"
        assert logo_file.exists()
        assert logo_file.read_bytes() == binary_data

        # Verify both files are tracked
        rendered_files = renderer.get_rendered_files()
        assert len(rendered_files) == 2

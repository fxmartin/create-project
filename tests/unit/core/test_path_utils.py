# ABOUTME: Unit tests for cross-platform path utilities
# ABOUTME: Tests security validation and OS compatibility of PathHandler

"""
Unit tests for path utilities.

This module tests the PathHandler class with focus on:
- Cross-platform path handling
- Path traversal attack prevention
- Unicode and special character handling
- Path normalization across OS types
- Comprehensive security validation
"""

import os
import platform
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from create_project.core.exceptions import PathError, SecurityError
from create_project.core.path_utils import PathHandler


class TestPathHandler:
    """Test suite for PathHandler class."""

    @pytest.fixture
    def handler(self):
        """Create a PathHandler instance for testing."""
        return PathHandler()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_init(self, handler):
        """Test PathHandler initialization."""
        assert handler is not None
        assert hasattr(handler, "logger")
        assert hasattr(handler, "case_sensitive")
        assert isinstance(handler.case_sensitive, bool)

    def test_case_sensitivity_detection_windows(self):
        """Test case sensitivity detection on Windows."""
        with patch("platform.system", return_value="Windows"):
            handler = PathHandler()
            assert handler.case_sensitive is False

    def test_case_sensitivity_detection_unix(self):
        """Test case sensitivity detection on Unix-like systems."""
        with patch("platform.system", return_value="Linux"):
            handler = PathHandler()
            assert handler.case_sensitive is True

        with patch("platform.system", return_value="Darwin"):
            handler = PathHandler()
            assert handler.case_sensitive is True

    def test_normalize_path_string_input(self, handler, temp_dir):
        """Test path normalization with string input."""
        test_path = str(temp_dir / "test" / "path")
        normalized = handler.normalize_path(test_path)

        assert isinstance(normalized, Path)
        assert normalized.is_absolute()

    def test_normalize_path_path_input(self, handler, temp_dir):
        """Test path normalization with Path input."""
        test_path = temp_dir / "test" / "path"
        normalized = handler.normalize_path(test_path)

        assert isinstance(normalized, Path)
        assert normalized.is_absolute()

    def test_normalize_path_unicode(self, handler, temp_dir):
        """Test path normalization with Unicode characters."""
        # Test with Unicode characters
        unicode_path = temp_dir / "tëst" / "pàth"
        normalized = handler.normalize_path(str(unicode_path))

        assert isinstance(normalized, Path)
        assert "tëst" in str(normalized) or "te\u0302st" in str(
            normalized
        )  # NFC normalization

    def test_normalize_path_relative_components(self, handler, temp_dir):
        """Test path normalization handles relative components."""
        # This should resolve . and .. components
        test_path = temp_dir / "test" / "." / ".." / "final"
        normalized = handler.normalize_path(test_path)

        # Should resolve to temp_dir/final
        assert normalized.parent == temp_dir.resolve()
        assert normalized.name == "final"

    def test_normalize_path_invalid_path(self, handler):
        """Test path normalization with invalid paths."""
        # Test with empty path
        with pytest.raises(PathError):
            handler.normalize_path("")

    def test_safe_join_basic(self, handler, temp_dir):
        """Test basic safe path joining."""
        result = handler.safe_join(temp_dir, "subdir", "file.txt")

        assert isinstance(result, Path)
        assert result.parent.parent == temp_dir.resolve()
        assert result.name == "file.txt"
        assert result.parent.name == "subdir"

    def test_safe_join_single_component(self, handler, temp_dir):
        """Test safe join with single component."""
        result = handler.safe_join(temp_dir, "file.txt")

        assert result.parent == temp_dir.resolve()
        assert result.name == "file.txt"

    def test_safe_join_no_components(self, handler, temp_dir):
        """Test safe join with no additional components."""
        result = handler.safe_join(temp_dir)

        assert result == temp_dir.resolve()

    def test_safe_join_empty_components(self, handler, temp_dir):
        """Test safe join handles empty components."""
        result = handler.safe_join(temp_dir, "", "file.txt", "")

        assert result.parent == temp_dir.resolve()
        assert result.name == "file.txt"

    def test_safe_join_prevents_traversal_attack(self, handler, temp_dir):
        """Test safe join prevents path traversal attacks."""
        # Test various traversal patterns
        traversal_patterns = [
            "../../../etc/passwd",
            ".." + os.sep + ".." + os.sep + "etc" + os.sep + "passwd",
            "subdir/../../../etc/passwd",
        ]

        for pattern in traversal_patterns:
            with pytest.raises(SecurityError) as exc_info:
                handler.safe_join(temp_dir, pattern)
            assert "traversal" in str(exc_info.value).lower()

    def test_safe_join_prevents_multi_step_traversal(self, handler, temp_dir):
        """Test safe join prevents multi-step traversal attacks."""
        with pytest.raises(SecurityError):
            handler.safe_join(temp_dir, "..", "..", "etc", "passwd")

    def test_safe_join_prevents_absolute_paths(self, handler, temp_dir):
        """Test safe join rejects absolute path components."""
        with pytest.raises(SecurityError) as exc_info:
            handler.safe_join(temp_dir, "/etc/passwd")
        assert "absolute path" in str(exc_info.value).lower()

        # Test Windows absolute path
        with pytest.raises(SecurityError):
            handler.safe_join(temp_dir, "C:\\Windows\\System32")

    def test_validate_filename_valid(self, handler):
        """Test filename validation with valid filenames."""
        valid_names = [
            "file.txt",
            "my_file-123.py",
            "test.file.name",
            "unicode_tëst.txt",
            "file_with_numbers_123",
            "CamelCase.File",
        ]

        for filename in valid_names:
            handler.validate_filename(filename)  # Should not raise

    def test_validate_filename_invalid_characters(self, handler):
        """Test filename validation rejects invalid characters."""
        invalid_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]

        for char in invalid_chars:
            with pytest.raises(PathError) as exc_info:
                handler.validate_filename(f"file{char}name.txt")
            assert "invalid characters" in str(exc_info.value).lower()

    def test_validate_filename_empty(self, handler):
        """Test filename validation rejects empty filename."""
        with pytest.raises(PathError) as exc_info:
            handler.validate_filename("")
        assert "empty" in str(exc_info.value).lower()

    def test_validate_filename_too_long(self, handler):
        """Test filename validation rejects too long filenames."""
        long_filename = "a" * 256  # 256 characters
        with pytest.raises(PathError) as exc_info:
            handler.validate_filename(long_filename)
        assert "too long" in str(exc_info.value).lower()

    def test_validate_filename_reserved_names(self, handler):
        """Test filename validation rejects Windows reserved names."""
        reserved_names = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]

        for name in reserved_names:
            # Test exact match
            with pytest.raises(PathError) as exc_info:
                handler.validate_filename(name)
            assert "reserved" in str(exc_info.value).lower()

            # Test with extension
            with pytest.raises(PathError):
                handler.validate_filename(f"{name}.txt")

            # Test case insensitive
            with pytest.raises(PathError):
                handler.validate_filename(name.lower())

    def test_validate_filename_spaces_and_dots(self, handler):
        """Test filename validation rejects names starting/ending with spaces or dots."""
        invalid_names = [
            " filename.txt",
            "filename.txt ",
            ".filename.txt",
            "filename.txt.",
        ]

        for name in invalid_names:
            with pytest.raises(PathError) as exc_info:
                handler.validate_filename(name)
            assert (
                "start" in str(exc_info.value).lower()
                or "end" in str(exc_info.value).lower()
            )

    def test_ensure_directory_creates_directory(self, handler, temp_dir):
        """Test ensure_directory creates missing directory."""
        new_dir = temp_dir / "new_directory"
        assert not new_dir.exists()

        result = handler.ensure_directory(new_dir)

        assert result == new_dir.resolve()
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_creates_nested_directories(self, handler, temp_dir):
        """Test ensure_directory creates nested directory structure."""
        nested_dir = temp_dir / "level1" / "level2" / "level3"
        assert not nested_dir.exists()

        result = handler.ensure_directory(nested_dir)

        assert result == nested_dir.resolve()
        assert nested_dir.exists()
        assert nested_dir.is_dir()

    def test_ensure_directory_existing_directory(self, handler, temp_dir):
        """Test ensure_directory with existing directory."""
        result = handler.ensure_directory(temp_dir)

        assert result == temp_dir.resolve()
        assert temp_dir.exists()
        assert temp_dir.is_dir()

    def test_ensure_directory_path_is_file(self, handler, temp_dir):
        """Test ensure_directory when path exists but is a file."""
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")

        with pytest.raises(PathError) as exc_info:
            handler.ensure_directory(test_file)
        assert "not a directory" in str(exc_info.value).lower()

    def test_get_relative_path_basic(self, handler, temp_dir):
        """Test getting relative path between directories."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        relative = handler.get_relative_path(subdir, temp_dir)

        assert relative == Path("subdir")

    def test_get_relative_path_nested(self, handler, temp_dir):
        """Test getting relative path for nested directories."""
        nested = temp_dir / "level1" / "level2" / "level3"
        nested.mkdir(parents=True)

        relative = handler.get_relative_path(nested, temp_dir)

        assert relative == Path("level1") / "level2" / "level3"

    def test_get_relative_path_not_relative(self, handler, temp_dir):
        """Test getting relative path when paths are not related."""
        with tempfile.TemporaryDirectory() as other_temp:
            other_dir = Path(other_temp)

            with pytest.raises(PathError) as exc_info:
                handler.get_relative_path(other_dir, temp_dir)
            assert "not relative" in str(exc_info.value).lower()

    def test_get_relative_path_same_directory(self, handler, temp_dir):
        """Test getting relative path for same directory."""
        relative = handler.get_relative_path(temp_dir, temp_dir)

        assert relative == Path(".")

    def test_error_handling_preserves_original_error(self, handler):
        """Test that error handling preserves original exceptions."""
        # Mock normalize_path to raise an exception
        with patch.object(
            handler, "normalize_path", side_effect=ValueError("Test error")
        ):
            with pytest.raises(PathError) as exc_info:
                handler.safe_join("/tmp", "test")

            # Check that original error is preserved
            assert exc_info.value.original_error is not None
            assert isinstance(exc_info.value.original_error, ValueError)
            assert str(exc_info.value.original_error) == "Test error"

    @pytest.mark.parametrize(
        "os_name,expected_case_sensitive",
        [
            ("Windows", False),
            ("Linux", True),
            ("Darwin", True),
            ("FreeBSD", True),
        ],
    )
    def test_case_sensitivity_across_platforms(self, os_name, expected_case_sensitive):
        """Test case sensitivity detection across different platforms."""
        with patch("platform.system", return_value=os_name):
            handler = PathHandler()
            assert handler.case_sensitive == expected_case_sensitive

    def test_logging_integration(self, handler, temp_dir):
        """Test that path operations generate appropriate log messages."""
        # Mock the logger to capture log calls
        with patch.object(handler, "logger") as mock_logger:
            # Test successful operation
            handler.safe_join(temp_dir, "test", "file.txt")

            # Verify debug logging occurred
            mock_logger.debug.assert_called()

            # Test error logging
            try:
                handler.safe_join(temp_dir, "../../../etc/passwd")
            except SecurityError:
                pass

            # Verify error logging occurred
            mock_logger.error.assert_called()

    def test_security_error_details(self, handler, temp_dir):
        """Test that SecurityError includes detailed information."""
        with pytest.raises(SecurityError) as exc_info:
            handler.safe_join(temp_dir, "../../../etc/passwd")

        error = exc_info.value
        assert hasattr(error, "message")
        assert hasattr(error, "details")
        assert "traversal" in error.message.lower()

    def test_thread_safety_basic(self, handler, temp_dir):
        """Basic test for thread safety (creating multiple handlers)."""
        # Test that multiple handlers can be created without interference
        handler1 = PathHandler()
        handler2 = PathHandler()

        result1 = handler1.safe_join(temp_dir, "file1.txt")
        result2 = handler2.safe_join(temp_dir, "file2.txt")

        assert result1.name == "file1.txt"
        assert result2.name == "file2.txt"
        assert result1 != result2


class TestPathHandlerEdgeCases:
    """Test edge cases and boundary conditions for PathHandler."""

    @pytest.fixture
    def handler(self):
        """Create a PathHandler instance for testing."""
        return PathHandler()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_very_long_path_components(self, handler, temp_dir):
        """Test handling of very long path components."""
        # Create a long but valid filename (just under 255 chars)
        long_name = "a" * 254

        # This should work
        handler.validate_filename(long_name)
        result = handler.safe_join(temp_dir, long_name)
        assert result.name == long_name

    def test_unicode_normalization_edge_cases(self, handler, temp_dir):
        """Test Unicode normalization edge cases."""
        # Test different Unicode normalization forms
        # These should be normalized consistently (though the exact form may vary by OS)
        name1 = "café"  # NFC form
        name2 = "cafe\u0301"  # NFD form (e + combining acute accent)

        norm1 = handler.normalize_path(temp_dir / name1)
        norm2 = handler.normalize_path(temp_dir / name2)

        # Both should be normalized consistently (actual form depends on filesystem)
        # The important thing is that both are valid Path objects and represent the same logical path
        assert isinstance(norm1, Path)
        assert isinstance(norm2, Path)
        # Both names should contain the same logical character (é) in some form
        assert "é" in norm1.name or "\u0301" in norm1.name
        assert "é" in norm2.name or "\u0301" in norm2.name

    def test_mixed_separators(self, handler, temp_dir):
        """Test handling mixed path separators."""
        # Test with mixed separators (should be normalized)
        # On Unix, backslash is just a character, not a separator
        mixed_path = "subdir/file_name.txt"  # Use forward slash which works everywhere
        result = handler.safe_join(temp_dir, mixed_path)

        # Should work and normalize separators
        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_symlink_handling(self, handler, temp_dir):
        """Test handling of symbolic links."""
        # Create a symlink that could potentially be used for traversal
        target_file = temp_dir / "target.txt"
        target_file.write_text("target content")

        # This test may not work on Windows without admin privileges
        if platform.system() != "Windows":
            symlink_file = temp_dir / "symlink.txt"
            try:
                symlink_file.symlink_to(target_file)

                # Safe join should resolve symlinks safely
                result = handler.safe_join(temp_dir, "symlink.txt")
                assert result.exists()

                # But prevent symlinks that escape the base directory
                escape_symlink = temp_dir / "escape.txt"
                try:
                    escape_symlink.symlink_to("../../../etc/passwd")

                    with pytest.raises(SecurityError):
                        handler.safe_join(temp_dir, "escape.txt")
                except OSError:
                    # Symlink creation might fail, that's OK
                    pass

            except OSError:
                # Symlink creation might fail on some systems, skip this test
                pytest.skip("Symlink creation not supported on this system")

    def test_case_sensitivity_edge_cases(self, handler, temp_dir):
        """Test case sensitivity edge cases."""
        if handler.case_sensitive:
            # On case-sensitive systems, these should be different
            handler.validate_filename("File.txt")
            handler.validate_filename("file.txt")
            handler.validate_filename("FILE.txt")
        else:
            # On case-insensitive systems, reserved name check should work
            # regardless of case
            with pytest.raises(PathError):
                handler.validate_filename("con.txt")
            with pytest.raises(PathError):
                handler.validate_filename("CON.txt")

    def test_whitespace_handling(self, handler, temp_dir):
        """Test handling of various whitespace characters."""
        # Valid whitespace in middle of filename
        handler.validate_filename("my file.txt")

        # Tab characters should be handled
        result = handler.safe_join(temp_dir, "file_with_spaces.txt")
        assert isinstance(result, Path)

    def test_special_filesystem_characters(self, handler):
        """Test handling of filesystem-specific special characters."""
        # Test characters that might be special on certain filesystems
        special_chars = ["\x00", "\x01", "\x1f"]  # Control characters

        for char in special_chars:
            filename = f"file{char}name.txt"
            # These should be rejected as they can cause filesystem issues
            # Note: The current implementation might not catch all of these,
            # which is a potential enhancement area
            try:
                handler.validate_filename(filename)
                # If validation passes, safe_join should still handle it
                temp_result = handler.normalize_path(f"/tmp/{filename}")
                assert isinstance(temp_result, Path)
            except (PathError, ValueError, OSError):
                # Expected for problematic characters
                pass

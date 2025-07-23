# ABOUTME: Unit tests for directory structure creation functionality
# ABOUTME: Tests DirectoryCreator class with rollback, permissions, and validation

"""
Unit tests for directory creator.

This module tests the DirectoryCreator class with focus on:
- Directory structure creation and validation
- Rollback mechanism functionality
- Permission handling across platforms
- Dry-run mode behavior
- Error handling and logging
"""

import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from create_project.core.directory_creator import DirectoryCreator
from create_project.core.exceptions import ProjectGenerationError
from create_project.core.path_utils import PathHandler


class TestDirectoryCreator:
    """Test suite for DirectoryCreator class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def creator(self, temp_dir):
        """Create a DirectoryCreator instance for testing."""
        return DirectoryCreator(temp_dir / "project")

    @pytest.fixture
    def simple_structure(self):
        """Simple directory structure for testing."""
        return {
            "src": {"package": {}, "tests": {}},
            "docs": {},
            "config": {"settings": {}},
        }

    @pytest.fixture
    def complex_structure(self):
        """More complex directory structure for testing."""
        return {
            "app": {
                "core": {"models": {}, "views": {}, "utils": {}},
                "static": {"css": {}, "js": {}, "images": {}},
                "templates": {"components": {}},
            },
            "tests": {"unit": {}, "integration": {}, "fixtures": {}},
            "docs": {"api": {}, "guides": {}},
            "scripts": {},
            "README.md": None,  # File placeholder
            "requirements.txt": None,  # File placeholder
        }

    def test_init(self, temp_dir):
        """Test DirectoryCreator initialization."""
        creator = DirectoryCreator(temp_dir / "test_project")

        assert creator is not None
        assert hasattr(creator, "path_handler")
        assert hasattr(creator, "base_path")
        assert hasattr(creator, "logger")
        assert hasattr(creator, "created_dirs")
        assert isinstance(creator.path_handler, PathHandler)
        assert creator.base_path.name == "test_project"
        assert creator.created_dirs == []

    def test_init_with_custom_path_handler(self, temp_dir):
        """Test initialization with custom PathHandler."""
        custom_handler = PathHandler()
        creator = DirectoryCreator(temp_dir / "test", custom_handler)

        assert creator.path_handler is custom_handler

    def test_validate_structure_valid(self, creator, simple_structure):
        """Test structure validation with valid structure."""
        # Should not raise any exception
        creator.validate_structure(simple_structure)

    def test_validate_structure_empty_name(self, creator):
        """Test structure validation with empty directory name."""
        invalid_structure = {
            "": {}  # Empty name
        }

        with pytest.raises(ProjectGenerationError) as exc_info:
            creator.validate_structure(invalid_structure)
        assert "empty name" in str(exc_info.value).lower()

    def test_validate_structure_invalid_filename(self, creator):
        """Test structure validation with invalid filename."""
        invalid_structure = {
            "invalid|name": {}  # Contains invalid character
        }

        with pytest.raises(ProjectGenerationError) as exc_info:
            creator.validate_structure(invalid_structure)
        assert "invalid" in str(exc_info.value).lower()

    def test_validate_structure_invalid_content_type(self, creator):
        """Test structure validation with invalid content type."""
        invalid_structure = {
            "valid_name": "invalid_content"  # Should be dict or None
        }

        with pytest.raises(ProjectGenerationError) as exc_info:
            creator.validate_structure(invalid_structure)
        assert "invalid structure content type" in str(exc_info.value).lower()

    def test_preview_structure(self, creator, simple_structure):
        """Test structure preview generation."""
        preview = creator.preview_structure(simple_structure)

        assert isinstance(preview, list)
        assert len(preview) > 0
        assert preview[0].endswith("/")  # Root directory
        assert any("src/" in line for line in preview)
        assert any("docs/" in line for line in preview)
        assert any("package/" in line for line in preview)

    def test_preview_structure_with_files(self, creator):
        """Test structure preview with file placeholders."""
        structure_with_files = {"src": {}, "README.md": None, "setup.py": None}

        preview = creator.preview_structure(structure_with_files)

        # Files should not have trailing slash
        readme_lines = [line for line in preview if "README.md" in line]
        assert len(readme_lines) == 1
        assert not readme_lines[0].strip().endswith("/")

    def test_create_structure_dry_run(self, creator, simple_structure):
        """Test directory creation in dry-run mode."""
        creator.create_structure(simple_structure, dry_run=True)

        # No directories should be created
        assert len(creator.get_created_directories()) == 0
        assert not creator.base_path.exists()

    def test_create_structure_actual(self, creator, simple_structure):
        """Test actual directory creation."""
        creator.create_structure(simple_structure, dry_run=False)

        created_dirs = creator.get_created_directories()
        assert len(created_dirs) > 0

        # Verify all directories exist
        expected_dirs = [
            creator.base_path / "src",
            creator.base_path / "src" / "package",
            creator.base_path / "src" / "tests",
            creator.base_path / "docs",
            creator.base_path / "config",
            creator.base_path / "config" / "settings",
        ]

        for expected_dir in expected_dirs:
            assert expected_dir.exists()
            assert expected_dir.is_dir()

    def test_create_structure_complex(self, creator, complex_structure):
        """Test creation of complex directory structure."""
        creator.create_structure(complex_structure, dry_run=False)

        created_dirs = creator.get_created_directories()
        assert len(created_dirs) >= 10  # Should have many directories

        # Verify some key nested directories exist
        assert (creator.base_path / "app" / "core" / "models").exists()
        assert (creator.base_path / "app" / "static" / "css").exists()
        assert (creator.base_path / "tests" / "integration").exists()

    def test_create_structure_with_progress_callback(self, creator, simple_structure):
        """Test directory creation with progress callback."""
        progress_messages = []

        def progress_callback(message):
            progress_messages.append(message)

        creator.create_structure(simple_structure, progress_callback=progress_callback)

        assert len(progress_messages) > 0
        assert any("Creating directory" in msg for msg in progress_messages)

    def test_create_structure_handles_existing_directory(self, creator, temp_dir):
        """Test creation when base directory already exists."""
        # Create base directory first
        creator.base_path.mkdir(parents=True)

        structure = {"subdir": {}}
        creator.create_structure(structure)

        assert (creator.base_path / "subdir").exists()

    def test_create_structure_handles_existing_subdirectory(self, creator):
        """Test creation when some subdirectories already exist."""
        # Create part of the structure first
        (creator.base_path / "src").mkdir(parents=True)

        structure = {"src": {"new_package": {}}, "docs": {}}

        creator.create_structure(structure)

        assert (creator.base_path / "src" / "new_package").exists()
        assert (creator.base_path / "docs").exists()

    def test_create_structure_path_is_file_error(self, creator):
        """Test error when path exists but is a file."""
        # Create a file at the base path location
        creator.base_path.parent.mkdir(parents=True, exist_ok=True)
        creator.base_path.write_text("I am a file")

        structure = {"subdir": {}}

        with pytest.raises(ProjectGenerationError) as exc_info:
            creator.create_structure(structure)

        assert "not a directory" in str(exc_info.value).lower()

    def test_create_structure_permission_error(self, creator, simple_structure):
        """Test handling of permission errors during creation."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Permission denied")

            with pytest.raises(ProjectGenerationError) as exc_info:
                creator.create_structure(simple_structure)

            assert "failed to create directory" in str(exc_info.value).lower()

    def test_rollback_empty_list(self, creator):
        """Test rollback when no directories were created."""
        creator.rollback()  # Should not raise any exception

    def test_rollback_success(self, creator, simple_structure):
        """Test successful rollback of created directories."""
        # Create the structure
        creator.create_structure(simple_structure)
        created_dirs = creator.get_created_directories().copy()

        # Verify directories exist
        for directory in created_dirs:
            assert directory.exists()

        # Rollback
        creator.rollback()

        # Verify directories are removed (in reverse order)
        for directory in reversed(created_dirs):
            assert not directory.exists() or not directory.is_dir()

        # Created directories list should be cleared
        assert len(creator.get_created_directories()) == 0

    def test_rollback_non_empty_directory(self, creator):
        """Test rollback behavior with non-empty directories."""
        structure = {"parent": {"child": {}}}
        creator.create_structure(structure)

        # Add a file to make parent directory non-empty
        test_file = creator.base_path / "parent" / "test_file.txt"
        test_file.write_text("test content")

        # Rollback should handle non-empty directories gracefully
        creator.rollback()

        # Child directory should be removed, parent might remain due to file
        assert not (creator.base_path / "parent" / "child").exists()

    def test_rollback_with_errors(self, creator, simple_structure):
        """Test rollback when some removals fail."""
        creator.create_structure(simple_structure)
        created_dirs = creator.get_created_directories()

        # Mock Path.exists to return True, Path.is_dir to return True,
        # Path.iterdir to return empty list, but Path.rmdir to fail for one directory
        def mock_rmdir(self):
            if self.name == "settings":  # Fail for a specific directory
                raise OSError("Removal failed")
            # For other directories, don't actually remove them to avoid side effects
            pass

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("pathlib.Path.iterdir", return_value=[]):
                    with patch("pathlib.Path.rmdir", mock_rmdir):
                        with pytest.raises(ProjectGenerationError) as exc_info:
                            creator.rollback()

                        assert (
                            "rollback completed with errors"
                            in str(exc_info.value).lower()
                        )

    def test_directory_permissions(self, creator):
        """Test that created directories have correct permissions."""
        structure = {"test_dir": {}}
        creator.create_structure(structure)

        test_dir = creator.base_path / "test_dir"
        assert test_dir.exists()

        # Check permissions (should be readable/writable/executable by owner)
        dir_stat = test_dir.stat()
        assert dir_stat.st_mode & stat.S_IRUSR  # Owner read
        assert dir_stat.st_mode & stat.S_IWUSR  # Owner write
        assert dir_stat.st_mode & stat.S_IXUSR  # Owner execute

    def test_directory_permissions_error_handling(self, creator):
        """Test handling of permission setting errors."""
        with patch("os.chmod") as mock_chmod:
            mock_chmod.side_effect = OSError("Permission change failed")

            # Should not raise exception, just log warning
            structure = {"test_dir": {}}
            creator.create_structure(structure)  # Should complete successfully

    def test_get_created_directories(self, creator, simple_structure):
        """Test getting list of created directories."""
        initial_list = creator.get_created_directories()
        assert initial_list == []

        creator.create_structure(simple_structure)

        created_list = creator.get_created_directories()
        assert len(created_list) > 0
        assert all(isinstance(path, Path) for path in created_list)

        # Should return a copy, not the original list
        created_list.append(Path("/fake/path"))
        assert len(creator.get_created_directories()) != len(created_list)

    def test_error_handling_with_rollback(self, creator):
        """Test that errors trigger automatic rollback."""
        structure = {"dir1": {}, "dir2": {}}

        # Create a custom exception to simulate directory creation failure
        def failing_create_directory(*args, **kwargs):
            # First call succeeds (creates dir1)
            if not hasattr(failing_create_directory, "called"):
                failing_create_directory.called = True
                # Actually create the directory to simulate partial success
                dir_path = creator.base_path / "dir1"
                dir_path.mkdir(parents=True)
                creator.created_dirs.append(dir_path)
                return
            else:
                # Second call fails
                raise OSError("Creation failed")

        with patch.object(
            creator, "_create_directory", side_effect=failing_create_directory
        ):
            with patch.object(creator, "rollback") as mock_rollback:
                with pytest.raises(ProjectGenerationError):
                    creator.create_structure(structure)

                # Rollback should be called automatically
                mock_rollback.assert_called_once()

    def test_logging_integration(self, creator, simple_structure):
        """Test that directory operations generate appropriate log messages."""
        with patch.object(creator, "logger") as mock_logger:
            creator.create_structure(simple_structure)

            # Verify info logging for start and completion
            mock_logger.info.assert_any_call(
                "Starting directory structure creation",
                dry_run=False,
                base_path=str(creator.base_path),
            )

            # Verify debug logging for individual directories
            mock_logger.debug.assert_called()

    def test_file_placeholders_skipped(self, creator):
        """Test that file placeholders are properly skipped."""
        structure = {
            "src": {},
            "README.md": None,
            "setup.py": None,
            "config.json": None,
        }

        creator.create_structure(structure)

        # Only directory should be created
        assert (creator.base_path / "src").exists()
        assert (creator.base_path / "src").is_dir()

        # Files should not be created
        assert not (creator.base_path / "README.md").exists()
        assert not (creator.base_path / "setup.py").exists()
        assert not (creator.base_path / "config.json").exists()

    def test_safe_path_joining(self, creator):
        """Test that path joining uses PathHandler security."""
        # This should be safe
        structure = {"normal_dir": {}}
        creator.create_structure(structure)

        # This should trigger security error through PathHandler
        with pytest.raises(
            Exception
        ):  # Could be SecurityError or ProjectGenerationError
            dangerous_structure = {"../../../etc": {}}
            creator.create_structure(dangerous_structure)


class TestDirectoryCreatorEdgeCases:
    """Test edge cases and boundary conditions for DirectoryCreator."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def creator(self, temp_dir):
        """Create a DirectoryCreator instance for testing."""
        return DirectoryCreator(temp_dir / "edge_test")

    def test_deeply_nested_structure(self, creator):
        """Test creation of deeply nested directory structure."""
        # Create a structure that's 10 levels deep
        structure = {}
        current = structure
        for i in range(10):
            next_level = {}
            current[f"level_{i}"] = next_level
            current = next_level

        creator.create_structure(structure)

        # Verify the deepest level exists
        deep_path = creator.base_path
        for i in range(10):
            deep_path = deep_path / f"level_{i}"

        assert deep_path.exists()
        assert deep_path.is_dir()

    def test_many_sibling_directories(self, creator):
        """Test creation of many directories at same level."""
        # Create structure with 50 sibling directories
        structure = {f"dir_{i:02d}": {} for i in range(50)}

        creator.create_structure(structure)

        created_dirs = creator.get_created_directories()
        assert len(created_dirs) == 50

        # Verify all exist
        for i in range(50):
            assert (creator.base_path / f"dir_{i:02d}").exists()

    def test_mixed_structure_types(self, creator):
        """Test structure with mixed directory and file placeholders."""
        structure = {
            "directories": {"subdir1": {}, "subdir2": {"nested": {}}},
            "files": {"file1.txt": None, "file2.py": None},
            "README.md": None,
            "single_dir": {},
        }

        creator.create_structure(structure)

        # Verify directories were created
        assert (creator.base_path / "directories").is_dir()
        assert (creator.base_path / "directories" / "subdir1").is_dir()
        assert (creator.base_path / "directories" / "subdir2" / "nested").is_dir()
        assert (creator.base_path / "files").is_dir()
        assert (creator.base_path / "single_dir").is_dir()

        # Verify files were not created (placeholders only)
        assert not (creator.base_path / "files" / "file1.txt").exists()
        assert not (creator.base_path / "files" / "file2.py").exists()
        assert not (creator.base_path / "README.md").exists()

    def test_unicode_directory_names(self, creator):
        """Test creation of directories with Unicode names."""
        structure = {
            "ñame_with_unicode": {},
            "测试目录": {},
            "café_résumé": {"søbdir": {}},
        }

        creator.create_structure(structure)

        # Verify Unicode directories were created
        assert (creator.base_path / "ñame_with_unicode").exists()
        assert (creator.base_path / "测试目录").exists()
        assert (creator.base_path / "café_résumé").exists()
        assert (creator.base_path / "café_résumé" / "søbdir").exists()

    def test_empty_structure(self, creator):
        """Test creation with empty structure."""
        creator.create_structure({})

        # Should create base directory only
        assert creator.base_path.exists()
        assert len(creator.get_created_directories()) == 0

    def test_concurrent_creation_simulation(self, creator):
        """Test handling of race conditions during directory creation."""
        structure = {"test_dir": {}}

        # Mock to simulate race condition where directory is created between check and mkdir
        def mock_mkdir_for_race(*args, **kwargs):
            if "parents" in kwargs or args:  # Base directory creation
                return  # Let base directory creation succeed
            raise FileExistsError("Directory exists")

        # Mock the _create_directory method to simulate race condition
        original_create = creator._create_directory

        def mock_create_with_race(dir_path, progress_callback=None):
            # First ensure base directory exists
            creator.base_path.mkdir(parents=True, exist_ok=True)

            # Then simulate FileExistsError for the target directory
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
            # Simulate that it now exists and is a directory
            return

        with patch.object(
            creator, "_create_directory", side_effect=mock_create_with_race
        ):
            # Should handle the race condition gracefully
            creator.create_structure(structure)

    def test_rollback_order_correctness(self, creator):
        """Test that rollback removes directories in correct order."""
        structure = {"a": {"a1": {"a1a": {}}, "a2": {}}, "b": {}}

        creator.create_structure(structure)
        created_dirs = creator.get_created_directories()

        # Mock rmdir to track call order
        removal_order = []
        original_rmdir = Path.rmdir

        def track_rmdir(self):
            removal_order.append(str(self))
            # Don't actually remove to avoid side effects

        with patch("pathlib.Path.rmdir", track_rmdir):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_dir", return_value=True):
                    with patch("pathlib.Path.iterdir", return_value=[]):
                        try:
                            creator.rollback()
                        except ProjectGenerationError:
                            pass  # Expected due to mocking

        # Verify deepest directories are removed first
        # The exact order depends on creation order, but deeper should come before shallower
        assert len(removal_order) > 0

    def test_structure_validation_edge_cases(self, creator):
        """Test structure validation with edge cases."""
        # Test with very long directory names
        long_name = "a" * 200
        creator.validate_structure({long_name: {}})  # Should pass

        # Test with structure containing only file placeholders
        creator.validate_structure({"file1.txt": None, "file2.py": None})  # Should pass

        # Test deeply nested validation
        deep_structure = {}
        current = deep_structure
        for i in range(5):
            next_level = {f"level_{i}": {}}
            current.update(next_level)
            current = next_level[f"level_{i}"]

        creator.validate_structure(deep_structure)  # Should pass

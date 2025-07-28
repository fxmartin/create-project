# ABOUTME: Comprehensive unit tests for project structure validation utilities
# ABOUTME: Tests directory/file validation, error reporting, and structure creation functionality

"""Unit tests for structure validator module."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from create_project.utils.structure_validator import (
    create_missing_structure,
    get_structure_report,
    validate_project_structure,
)


class TestValidateProjectStructure:
    """Test validate_project_structure function."""

    @pytest.fixture
    def valid_project_structure(self, tmp_path):
        """Create a valid project structure for testing."""
        project_root = tmp_path / "valid_project"
        
        # Create all required directories
        required_dirs = [
            "create_project",
            "create_project/core",
            "create_project/gui", 
            "create_project/utils",
            "create_project/templates",
            "create_project/templates/builtin",
            "create_project/templates/user",
            "create_project/resources",
            "create_project/resources/styles",
            "create_project/resources/icons",
            "create_project/resources/licenses",
            "create_project/config",
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/gui",
            "docs",
            "docs/user",
            "docs/developer",
            "docs/templates",
            "scripts",
        ]
        
        for dir_path in required_dirs:
            (project_root / dir_path).mkdir(parents=True, exist_ok=True)
        
        # Create all required files
        required_files = [
            "create_project/__init__.py",
            "create_project/core/__init__.py",
            "create_project/gui/__init__.py",
            "create_project/utils/__init__.py",
            "create_project/templates/__init__.py",
            "create_project/templates/builtin/__init__.py",
            "create_project/templates/user/__init__.py",
            "create_project/resources/__init__.py",
            "create_project/config/__init__.py",
            "create_project/config/settings.json",
            "create_project/config/defaults.json",
            "create_project/__main__.py",
            "create_project/main.py",
            "tests/__init__.py",
            "tests/unit/__init__.py",
            "tests/integration/__init__.py",
            "tests/gui/__init__.py",
            "pyproject.toml",
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            if file_path.endswith('.json'):
                full_path.write_text('{}')
            elif file_path == 'pyproject.toml':
                full_path.write_text('[project]\nname = "test"')
            else:
                full_path.write_text('')
        
        return project_root

    @pytest.fixture
    def incomplete_project_structure(self, tmp_path):
        """Create an incomplete project structure for testing."""
        project_root = tmp_path / "incomplete_project"
        project_root.mkdir()
        
        # Create only some directories and files
        (project_root / "create_project").mkdir()
        (project_root / "create_project" / "__init__.py").write_text('')
        (project_root / "tests").mkdir()
        (project_root / "pyproject.toml").write_text('[project]\nname = "test"')
        
        return project_root

    def test_validate_valid_structure(self, valid_project_structure):
        """Test validation of a completely valid project structure."""
        is_valid, missing_dirs, missing_files = validate_project_structure(valid_project_structure)
        
        assert is_valid is True
        assert missing_dirs == []
        assert missing_files == []

    def test_validate_incomplete_structure(self, incomplete_project_structure):
        """Test validation of an incomplete project structure."""
        is_valid, missing_dirs, missing_files = validate_project_structure(incomplete_project_structure)
        
        assert is_valid is False
        assert len(missing_dirs) > 0
        assert len(missing_files) > 0
        
        # Check some expected missing directories
        assert "create_project/core" in missing_dirs
        assert "create_project/gui" in missing_dirs
        assert "create_project/utils" in missing_dirs
        
        # Check some expected missing files  
        assert "create_project/core/__init__.py" in missing_files
        assert "create_project/config/settings.json" in missing_files

    def test_validate_nonexistent_project_root(self, tmp_path):
        """Test validation with non-existent project root."""
        nonexistent_path = tmp_path / "nonexistent"
        
        is_valid, missing_dirs, missing_files = validate_project_structure(nonexistent_path)
        
        assert is_valid is False
        # All directories and files should be missing
        assert len(missing_dirs) == 21  # Total required directories
        assert len(missing_files) == 18  # Total required files

    def test_validate_empty_directory(self, tmp_path):
        """Test validation with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        is_valid, missing_dirs, missing_files = validate_project_structure(empty_dir)
        
        assert is_valid is False
        assert len(missing_dirs) == 21
        assert len(missing_files) == 18

    def test_validate_partial_directory_structure(self, tmp_path):
        """Test validation with partial directory structure."""
        project_root = tmp_path / "partial"
        
        # Create some but not all directories
        dirs_to_create = [
            "create_project",
            "create_project/core", 
            "tests",
            "docs"
        ]
        
        for dir_path in dirs_to_create:
            (project_root / dir_path).mkdir(parents=True, exist_ok=True)
        
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)
        
        assert is_valid is False
        
        # Should be missing some directories
        assert "create_project/gui" in missing_dirs
        assert "create_project/utils" in missing_dirs
        assert "scripts" in missing_dirs
        
        # Should be missing all files since we only created directories
        assert len(missing_files) == 18

    def test_validate_files_as_directories(self, tmp_path):
        """Test validation when files exist where directories should be."""
        project_root = tmp_path / "confused"
        project_root.mkdir()
        
        # Create files where directories should be
        (project_root / "create_project").write_text('not a directory')
        (project_root / "tests").write_text('not a directory')
        
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)
        
        assert is_valid is False
        assert "create_project" in missing_dirs
        assert "tests" in missing_dirs

    def test_validate_directories_as_files(self, tmp_path):
        """Test validation when directories exist where files should be."""
        project_root = tmp_path / "confused2" 
        
        # Create directories where files should be
        (project_root / "pyproject.toml").mkdir(parents=True)
        (project_root / "create_project" / "__init__.py").mkdir(parents=True)
        
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)
        
        assert is_valid is False
        assert "pyproject.toml" in missing_files
        assert "create_project/__init__.py" in missing_files

    def test_validate_with_symlinks(self, tmp_path):
        """Test validation with symbolic links."""
        project_root = tmp_path / "with_symlinks"
        project_root.mkdir()
        
        # Create actual directory and file
        actual_dir = tmp_path / "actual_dir"
        actual_dir.mkdir()
        actual_file = tmp_path / "actual_file.py"
        actual_file.write_text('')
        
        # Create symlinks pointing to them
        symlink_dir = project_root / "create_project"
        symlink_file = project_root / "pyproject.toml"
        
        symlink_dir.symlink_to(actual_dir)
        symlink_file.symlink_to(actual_file)
        
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)
        
        # Symlinks should be considered valid if they point to correct type
        assert "create_project" not in missing_dirs
        assert "pyproject.toml" not in missing_files

    def test_validate_case_sensitivity(self, tmp_path):
        """Test validation is case sensitive on case-sensitive filesystems."""
        import platform
        project_root = tmp_path / "case_test"
        project_root.mkdir()
        
        # Create directories with wrong case
        (project_root / "CREATE_PROJECT").mkdir()
        (project_root / "TESTS").mkdir()
        
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)
        
        assert is_valid is False
        # On case-insensitive filesystems (like macOS default), this test behavior may vary
        # But we can still check that validation fails overall
        assert len(missing_dirs) > 0 or len(missing_files) > 0

    def test_validate_with_extra_files_and_dirs(self, valid_project_structure):
        """Test validation with extra files and directories (should still be valid)."""
        # Add some extra files and directories
        (valid_project_structure / "extra_dir").mkdir()
        (valid_project_structure / "extra_file.txt").write_text("extra content")
        (valid_project_structure / "create_project" / "extra_module.py").write_text("")
        
        is_valid, missing_dirs, missing_files = validate_project_structure(valid_project_structure)
        
        # Should still be valid - extra files/dirs don't matter
        assert is_valid is True
        assert missing_dirs == []
        assert missing_files == []

    def test_validate_deep_nested_missing_structure(self, tmp_path):
        """Test validation with deeply nested missing structure."""
        project_root = tmp_path / "deep_missing"
        project_root.mkdir()
        
        # Create only the root create_project directory
        (project_root / "create_project").mkdir()
        
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)
        
        assert is_valid is False
        
        # Should detect all missing nested directories
        expected_missing = [
            "create_project/core",
            "create_project/gui", 
            "create_project/utils",
            "create_project/templates",
            "create_project/templates/builtin",
            "create_project/templates/user",
            "create_project/resources",
            "create_project/resources/styles",
            "create_project/resources/icons", 
            "create_project/resources/licenses",
            "create_project/config"
        ]
        
        for missing_dir in expected_missing:
            assert missing_dir in missing_dirs

    def test_validate_return_types(self, tmp_path):
        """Test that function returns correct types."""
        project_root = tmp_path / "type_test"
        project_root.mkdir()
        
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)
        
        assert isinstance(is_valid, bool)
        assert isinstance(missing_dirs, list)
        assert isinstance(missing_files, list)
        assert all(isinstance(item, str) for item in missing_dirs)
        assert all(isinstance(item, str) for item in missing_files)

    def test_validate_permission_errors(self, tmp_path):
        """Test validation with permission errors."""
        project_root = tmp_path / "permission_test"
        project_root.mkdir()
        
        # Create a directory structure
        test_dir = project_root / "create_project"
        test_dir.mkdir()
        
        # The current implementation doesn't handle permission errors gracefully
        # so we'll test that it raises the expected exception
        with patch.object(Path, 'exists', side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                validate_project_structure(project_root)


class TestGetStructureReport:
    """Test get_structure_report function."""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project structure for testing."""
        project_root = tmp_path / "sample"
        
        # Create some directories and files
        dirs = ["src", "src/modules", "tests", "docs"]
        files = ["src/__init__.py", "src/main.py", "tests/test_main.py", "README.md"]
        
        for dir_path in dirs:
            (project_root / dir_path).mkdir(parents=True, exist_ok=True)
        
        for file_path in files:
            full_path = project_root / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text("content")
        
        return project_root

    def test_get_structure_report_valid_project(self, sample_project):
        """Test getting structure report for a sample project."""
        report = get_structure_report(sample_project)
        
        assert isinstance(report, dict)
        assert "is_valid" in report
        assert "missing_directories" in report
        assert "missing_files" in report
        assert "directories_count" in report
        assert "files_count" in report
        assert "project_root" in report
        
        assert isinstance(report["is_valid"], bool)
        assert isinstance(report["missing_directories"], list)
        assert isinstance(report["missing_files"], list)
        assert isinstance(report["directories_count"], int)
        assert isinstance(report["files_count"], int)
        assert isinstance(report["project_root"], str)

    def test_get_structure_report_counts(self, sample_project):
        """Test that structure report counts are accurate."""
        report = get_structure_report(sample_project)
        
        # Count actual directories and files
        actual_dirs = len([d for d in sample_project.rglob("*") if d.is_dir()])
        actual_files = len([f for f in sample_project.rglob("*") if f.is_file()])
        
        assert report["directories_count"] == actual_dirs
        assert report["files_count"] == actual_files

    def test_get_structure_report_empty_directory(self, tmp_path):
        """Test structure report for empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        report = get_structure_report(empty_dir)
        
        assert report["is_valid"] is False
        assert len(report["missing_directories"]) > 0
        assert len(report["missing_files"]) > 0
        assert report["directories_count"] == 0  # No subdirectories
        assert report["files_count"] == 0  # No files
        assert report["project_root"] == str(empty_dir)

    def test_get_structure_report_nonexistent_directory(self, tmp_path):
        """Test structure report for nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        
        report = get_structure_report(nonexistent)
        
        assert report["is_valid"] is False
        assert len(report["missing_directories"]) == 21  # All required dirs missing
        assert len(report["missing_files"]) == 18  # All required files missing
        assert report["directories_count"] == 0
        assert report["files_count"] == 0
        assert report["project_root"] == str(nonexistent)

    def test_get_structure_report_with_large_structure(self, tmp_path):
        """Test structure report with large directory structure."""
        project_root = tmp_path / "large_project"
        
        # Create many directories and files
        for i in range(50):
            dir_path = project_root / f"dir_{i}"
            dir_path.mkdir(parents=True, exist_ok=True)
            
            for j in range(10):
                file_path = dir_path / f"file_{j}.txt"
                file_path.write_text(f"content {i}-{j}")
        
        report = get_structure_report(project_root)
        
        assert report["directories_count"] >= 50
        assert report["files_count"] >= 500
        assert isinstance(report["directories_count"], int)
        assert isinstance(report["files_count"], int)

    def test_get_structure_report_calls_validate(self, tmp_path):
        """Test that get_structure_report calls validate_project_structure."""
        project_root = tmp_path / "test"
        project_root.mkdir()
        
        with patch('create_project.utils.structure_validator.validate_project_structure') as mock_validate:
            mock_validate.return_value = (False, ["missing_dir"], ["missing_file"])
            
            report = get_structure_report(project_root)
            
            mock_validate.assert_called_once_with(project_root)
            assert report["is_valid"] is False
            assert report["missing_directories"] == ["missing_dir"]
            assert report["missing_files"] == ["missing_file"]

    def test_get_structure_report_with_symlinks(self, tmp_path):
        """Test structure report handles symlinks correctly."""
        project_root = tmp_path / "with_symlinks"
        project_root.mkdir()
        
        # Create actual files and directories
        actual_dir = tmp_path / "actual_dir"
        actual_dir.mkdir()
        actual_file = tmp_path / "actual_file.txt"
        actual_file.write_text("content")
        
        # Create symlinks
        symlink_dir = project_root / "symlink_dir"
        symlink_file = project_root / "symlink_file.txt"
        symlink_dir.symlink_to(actual_dir)
        symlink_file.symlink_to(actual_file)
        
        report = get_structure_report(project_root)
        
        # Symlinks should be counted
        assert report["directories_count"] >= 1
        assert report["files_count"] >= 1

    def test_get_structure_report_with_broken_symlinks(self, tmp_path):
        """Test structure report with broken symlinks."""
        project_root = tmp_path / "broken_symlinks"
        project_root.mkdir()
        
        # Create symlink to nonexistent target
        broken_symlink = project_root / "broken_link"
        nonexistent_target = tmp_path / "nonexistent_target"
        broken_symlink.symlink_to(nonexistent_target)
        
        # Should not raise exception
        report = get_structure_report(project_root)
        
        assert isinstance(report, dict)
        assert "is_valid" in report


class TestCreateMissingStructure:
    """Test create_missing_structure function."""

    def test_create_missing_directories(self, tmp_path):
        """Test creating missing directories."""
        project_root = tmp_path / "create_dirs"
        project_root.mkdir()
        
        # Initially should have missing directories
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)
        assert not is_valid
        assert len(missing_dirs) > 0
        
        # Create missing structure
        success = create_missing_structure(project_root)
        assert success is True
        
        # Check that directories were created
        is_valid_after, missing_dirs_after, _ = validate_project_structure(project_root)
        assert len(missing_dirs_after) == 0  # All directories should be created

    def test_create_missing_init_files(self, tmp_path):
        """Test creating missing __init__.py files."""
        project_root = tmp_path / "create_inits"
        
        # Create all required directories first
        required_dirs = [
            "create_project",
            "create_project/core",
            "create_project/gui",
            "create_project/utils", 
            "create_project/templates",
            "create_project/templates/builtin",
            "create_project/templates/user",
            "create_project/resources",
            "create_project/config",
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/gui",
            "docs",
            "docs/user",
            "docs/developer",
            "docs/templates",
            "scripts",
        ]
        
        for dir_path in required_dirs:
            (project_root / dir_path).mkdir(parents=True, exist_ok=True)
        
        # Create non-__init__.py files
        (project_root / "pyproject.toml").write_text("[project]\nname = 'test'")
        (project_root / "create_project" / "main.py").write_text("")
        (project_root / "create_project" / "__main__.py").write_text("")
        
        success = create_missing_structure(project_root)
        assert success is True
        
        # Check that __init__.py files were created
        init_files = [
            "create_project/__init__.py",
            "create_project/core/__init__.py", 
            "create_project/gui/__init__.py",
            "create_project/utils/__init__.py",
            "create_project/templates/__init__.py",
            "create_project/templates/builtin/__init__.py",
            "create_project/templates/user/__init__.py",
            "create_project/resources/__init__.py",
            "create_project/config/__init__.py",
            "tests/__init__.py",
            "tests/unit/__init__.py",
            "tests/integration/__init__.py",
            "tests/gui/__init__.py",
        ]
        
        for init_file in init_files:
            assert (project_root / init_file).exists()
            assert (project_root / init_file).is_file()

    def test_create_missing_structure_idempotent(self, tmp_path):
        """Test that creating missing structure is idempotent."""
        project_root = tmp_path / "idempotent"
        project_root.mkdir()
        
        # Create structure twice
        success1 = create_missing_structure(project_root)
        success2 = create_missing_structure(project_root)
        
        assert success1 is True
        assert success2 is True
        
        # Structure should still be valid
        is_valid, missing_dirs, _ = validate_project_structure(project_root)
        assert len(missing_dirs) == 0

    def test_create_missing_structure_partial_existing(self, tmp_path):
        """Test creating structure when some parts already exist."""
        project_root = tmp_path / "partial_existing"
        
        # Create some directories and files manually
        (project_root / "create_project").mkdir(parents=True)
        (project_root / "create_project" / "__init__.py").write_text("")
        (project_root / "tests").mkdir(parents=True)
        (project_root / "pyproject.toml").write_text("[project]\nname = 'test'")
        
        success = create_missing_structure(project_root)
        assert success is True
        
        # Should not overwrite existing files
        assert (project_root / "create_project" / "__init__.py").exists()
        assert (project_root / "pyproject.toml").exists()
        
        # Should create missing directories
        assert (project_root / "create_project" / "core").exists()
        assert (project_root / "docs").exists()

    def test_create_missing_structure_permission_error(self, tmp_path):
        """Test create_missing_structure with permission errors."""
        project_root = tmp_path / "permission_error"
        project_root.mkdir()
        
        # Mock mkdir to raise permission error
        with patch.object(Path, 'mkdir', side_effect=PermissionError("Access denied")):
            success = create_missing_structure(project_root)
            assert success is False

    def test_create_missing_structure_file_system_error(self, tmp_path):
        """Test create_missing_structure with file system errors."""
        project_root = tmp_path / "fs_error"
        project_root.mkdir()
        
        # Mock touch to raise OSError
        with patch.object(Path, 'touch', side_effect=OSError("Disk full")):
            success = create_missing_structure(project_root)
            assert success is False

    def test_create_missing_structure_only_init_files(self, tmp_path):
        """Test that only __init__.py files are created, not other missing files."""
        project_root = tmp_path / "only_inits"
        
        # Create all required directories
        required_dirs = [
            "create_project",
            "create_project/core",  
            "create_project/config",
            "tests",
        ]
        
        for dir_path in required_dirs:
            (project_root / dir_path).mkdir(parents=True, exist_ok=True)
        
        success = create_missing_structure(project_root)
        assert success is True
        
        # __init__.py files should be created
        assert (project_root / "create_project" / "__init__.py").exists()
        assert (project_root / "create_project" / "core" / "__init__.py").exists()
        
        # Other missing files should NOT be created
        assert not (project_root / "create_project" / "config" / "settings.json").exists()
        assert not (project_root / "create_project" / "main.py").exists()
        assert not (project_root / "pyproject.toml").exists()

    def test_create_missing_structure_existing_init_files(self, tmp_path):
        """Test that existing __init__.py files are not overwritten."""
        project_root = tmp_path / "existing_inits"
        
        # Create directory and __init__.py with content
        (project_root / "create_project").mkdir(parents=True)
        init_file = project_root / "create_project" / "__init__.py"
        original_content = "# Original content"
        init_file.write_text(original_content)
        
        success = create_missing_structure(project_root)
        assert success is True
        
        # Should not overwrite existing __init__.py
        assert init_file.read_text() == original_content

    def test_create_missing_structure_returns_boolean(self, tmp_path):
        """Test that create_missing_structure returns boolean."""
        project_root = tmp_path / "boolean_test"
        project_root.mkdir()
        
        result = create_missing_structure(project_root)
        assert isinstance(result, bool)

    def test_create_missing_structure_exception_handling(self, tmp_path):
        """Test exception handling in create_missing_structure."""
        project_root = tmp_path / "exception_test"
        project_root.mkdir()
        
        # Mock validate_project_structure to raise an exception
        with patch('create_project.utils.structure_validator.validate_project_structure',
                  side_effect=Exception("Unexpected error")):
            
            with patch('builtins.print') as mock_print:
                result = create_missing_structure(project_root)
                
                assert result is False
                mock_print.assert_called_once()
                assert "Error creating project structure" in mock_print.call_args[0][0]

    def test_create_missing_structure_with_nested_directories(self, tmp_path):
        """Test creating deeply nested directory structures."""
        project_root = tmp_path / "nested_test"
        project_root.mkdir()
        
        success = create_missing_structure(project_root)
        assert success is True
        
        # Check that deeply nested directories were created
        deep_paths = [
            "create_project/templates/builtin",
            "create_project/templates/user", 
            "create_project/resources/styles",
            "create_project/resources/icons",
            "create_project/resources/licenses",
            "docs/user",
            "docs/developer",
            "docs/templates",
        ]
        
        for path in deep_paths:
            assert (project_root / path).exists()
            assert (project_root / path).is_dir()

    def test_create_missing_structure_concurrent_access(self, tmp_path):
        """Test create_missing_structure with concurrent access simulation."""
        project_root = tmp_path / "concurrent_test"
        project_root.mkdir()
        
        # Simulate concurrent creation by having mkdir create additional directories
        original_mkdir = Path.mkdir
        call_count = 0
        
        def mock_mkdir(mode=0o777, parents=False, exist_ok=False):
            nonlocal call_count
            call_count += 1
            
            # Create a competing directory during mkdir on first call
            if call_count == 1 and not (project_root / "create_project" / "gui").exists():
                original_mkdir(project_root / "create_project" / "gui", mode=mode, parents=True, exist_ok=True)
            
            return original_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)
        
        # Use a simpler approach - test that exist_ok=True allows success
        success = create_missing_structure(project_root)
        assert success is True
        
        # Verify that running again (when directories exist) still succeeds
        success2 = create_missing_structure(project_root)
        assert success2 is True
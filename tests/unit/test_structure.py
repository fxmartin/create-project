# ABOUTME: Tests for project structure validation
# ABOUTME: Ensures all required directories and files are present

from pathlib import Path

import pytest

from create_project.utils.structure_validator import (
    get_structure_report,
    validate_project_structure,
)


class TestProjectStructure:
    """Test suite for project structure validation."""

    @pytest.fixture
    def project_root(self):
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    def test_all_directories_exist(self, project_root):
        """Test that all required directories exist."""
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)

        assert len(missing_dirs) == 0, f"Missing directories: {missing_dirs}"

    def test_all_init_files_exist(self, project_root):
        """Test that all __init__.py files exist."""
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)

        init_files = [f for f in missing_files if f.endswith("__init__.py")]
        assert len(init_files) == 0, f"Missing __init__.py files: {init_files}"

    def test_config_files_exist(self, project_root):
        """Test that configuration files exist."""
        settings_path = project_root / "create_project/config/settings.json"
        defaults_path = project_root / "create_project/config/defaults.json"

        assert settings_path.exists(), "settings.json file missing"
        assert defaults_path.exists(), "defaults.json file missing"

    def test_main_entry_points_exist(self, project_root):
        """Test that main entry points exist."""
        main_path = project_root / "create_project/main.py"
        main_module_path = project_root / "create_project/__main__.py"

        assert main_path.exists(), "main.py file missing"
        assert main_module_path.exists(), "__main__.py file missing"

    def test_structure_validation_function(self, project_root):
        """Test the structure validation function."""
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)

        assert isinstance(is_valid, bool), "is_valid should be boolean"
        assert isinstance(missing_dirs, list), "missing_dirs should be list"
        assert isinstance(missing_files, list), "missing_files should be list"

        # Structure should be valid
        assert is_valid, (
            f"Project structure invalid. Missing dirs: {missing_dirs}, Missing files: {missing_files}"
        )

    def test_structure_report_generation(self, project_root):
        """Test structure report generation."""
        report = get_structure_report(project_root)

        assert "is_valid" in report, "Report should contain is_valid"
        assert "missing_directories" in report, (
            "Report should contain missing_directories"
        )
        assert "missing_files" in report, "Report should contain missing_files"
        assert "directories_count" in report, "Report should contain directories_count"
        assert "files_count" in report, "Report should contain files_count"
        assert "project_root" in report, "Report should contain project_root"

        assert report["is_valid"] is True, "Project structure should be valid"
        assert len(report["missing_directories"]) == 0, (
            "Should have no missing directories"
        )
        assert len(report["missing_files"]) == 0, "Should have no missing files"

    def test_package_imports_work(self, project_root):
        """Test that package imports work correctly."""
        # Test main package import
        import create_project

        assert hasattr(create_project, "__version__"), "Package should have version"

        # Test subpackage imports
        from create_project import core, gui, utils

        assert core is not None, "Core module should be importable"
        assert gui is not None, "GUI module should be importable"
        assert utils is not None, "Utils module should be importable"

        # Test utils import
        from create_project.utils import structure_validator

        assert structure_validator is not None, (
            "Structure validator should be importable"
        )

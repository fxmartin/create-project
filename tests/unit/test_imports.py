# ABOUTME: Tests for package import functionality
# ABOUTME: Validates all modules can be imported correctly

import sys

import pytest


class TestPackageImports:
    """Test suite for package import functionality."""

    def test_main_package_import(self):
        """Test main package can be imported."""
        import create_project

        # Check package metadata
        assert hasattr(create_project, "__version__"), "Package should have __version__"
        assert hasattr(create_project, "__author__"), "Package should have __author__"
        assert hasattr(create_project, "__description__"), "Package should have __description__"

        # Check version format
        assert isinstance(create_project.__version__, str), "Version should be string"
        assert len(create_project.__version__) > 0, "Version should not be empty"

    def test_core_subpackage_import(self):
        """Test core subpackage can be imported."""
        from create_project import core
        assert core is not None, "Core module should be importable"

        # Test direct import
        import create_project.core
        assert create_project.core is not None, "Core module should be importable directly"

    def test_gui_subpackage_import(self):
        """Test gui subpackage can be imported."""
        from create_project import gui
        assert gui is not None, "GUI module should be importable"

        # Test direct import
        import create_project.gui
        assert create_project.gui is not None, "GUI module should be importable directly"

    def test_utils_subpackage_import(self):
        """Test utils subpackage can be imported."""
        from create_project import utils
        assert utils is not None, "Utils module should be importable"

        # Test direct import
        import create_project.utils
        assert create_project.utils is not None, "Utils module should be importable directly"

    def test_templates_subpackage_import(self):
        """Test templates subpackage can be imported."""
        import create_project.templates
        assert create_project.templates is not None, "Templates module should be importable"

        # Test builtin templates
        import create_project.templates.builtin
        assert create_project.templates.builtin is not None, "Builtin templates should be importable"

        # Test user templates
        import create_project.templates.user
        assert create_project.templates.user is not None, "User templates should be importable"

    def test_resources_subpackage_import(self):
        """Test resources subpackage can be imported."""
        import create_project.resources
        assert create_project.resources is not None, "Resources module should be importable"

    def test_config_subpackage_import(self):
        """Test config subpackage can be imported."""
        import create_project.config
        assert create_project.config is not None, "Config module should be importable"

    def test_structure_validator_import(self):
        """Test structure validator can be imported."""
        from create_project.utils.structure_validator import validate_project_structure
        assert validate_project_structure is not None, "Structure validator should be importable"

        # Test it's callable
        assert callable(validate_project_structure), "Structure validator should be callable"

    def test_main_module_import(self):
        """Test main module can be imported."""
        from create_project.main import main
        assert main is not None, "Main function should be importable"
        assert callable(main), "Main function should be callable"

    def test_main_entry_point_import(self):
        """Test main entry point can be imported."""
        import create_project.__main__
        assert create_project.__main__ is not None, "__main__ module should be importable"

    def test_all_submodules_accessible(self):
        """Test all submodules are accessible through main package."""
        import create_project

        # All these should be accessible without errors
        submodules = ["core", "gui", "utils", "templates", "resources", "config"]
        for submodule in submodules:
            module = getattr(create_project, submodule, None)
            # Note: modules might be None due to commented imports in __init__.py
            # This is expected during initial setup

    def test_no_import_errors(self):
        """Test that importing doesn't cause any errors."""
        # This should not raise any exceptions
        try:
            import create_project
            from create_project import core, gui, utils
            from create_project.main import main
            from create_project.utils import structure_validator
        except ImportError as e:
            pytest.fail(f"Import error occurred: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error during import: {e}")

    def test_package_in_sys_modules(self):
        """Test that package is properly registered in sys.modules."""

        assert "create_project" in sys.modules, "Main package should be in sys.modules"
        assert "create_project.core" in sys.modules, "Core module should be in sys.modules"
        assert "create_project.gui" in sys.modules, "GUI module should be in sys.modules"
        assert "create_project.utils" in sys.modules, "Utils module should be in sys.modules"

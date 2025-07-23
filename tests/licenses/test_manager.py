# ABOUTME: Unit tests for license manager functionality
# ABOUTME: Tests LicenseManager loading, retrieval and validation

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from create_project.licenses.manager import LicenseManager
from create_project.licenses.models import License


class TestLicenseManager:
    """Test LicenseManager functionality."""

    def test_manager_initialization_default_path(self):
        """Test manager initialization with default licenses directory."""
        manager = LicenseManager()

        # Should set default path to package resources/licenses
        expected_path = (
            Path(__file__).parent.parent.parent
            / "create_project"
            / "resources"
            / "licenses"
        )
        assert manager.licenses_dir.resolve() == expected_path.resolve()
        assert not manager._loaded

    def test_manager_initialization_custom_path(self):
        """Test manager initialization with custom licenses directory."""
        custom_path = Path("/tmp/custom_licenses")
        manager = LicenseManager(custom_path)

        assert manager.licenses_dir == custom_path
        assert not manager._loaded

    def test_get_available_licenses_empty_directory(self):
        """Test getting available licenses from empty directory."""
        with TemporaryDirectory() as temp_dir:
            manager = LicenseManager(Path(temp_dir))
            licenses = manager.get_available_licenses()
            assert licenses == []
            assert manager._loaded

    def test_get_license_not_found(self):
        """Test getting a license that doesn't exist."""
        with TemporaryDirectory() as temp_dir:
            manager = LicenseManager(Path(temp_dir))

            with pytest.raises(ValueError, match="License 'nonexistent' not found"):
                manager.get_license("nonexistent")

    def test_load_licenses_from_files(self):
        """Test loading licenses from text files."""
        # Mock license file content
        mit_text = """MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge..."""

        with TemporaryDirectory() as temp_dir:
            licenses_dir = Path(temp_dir)

            # Create a mock license file
            mit_file = licenses_dir / "mit.txt"
            mit_file.write_text(mit_text, encoding="utf-8")

            manager = LicenseManager(licenses_dir)

            licenses = manager.get_available_licenses()
            assert "mit" in licenses

            mit_license = manager.get_license("mit")
            assert mit_license.id == "mit"
            assert mit_license.name == "MIT License"
            assert "{year}" in mit_license.text
            assert "{author}" in mit_license.text

    def test_render_license_with_variables(self):
        """Test rendering license text with variable substitution."""
        license_text = "Copyright (c) {year} {author}\n\nThis software is provided..."

        with TemporaryDirectory() as temp_dir:
            manager = LicenseManager(Path(temp_dir))

            # Manually add a license for testing
            license_obj = License(
                id="test",
                name="Test License",
                text=license_text,
                url="https://example.com",
                requires_fields=["author", "year"],
            )
            manager._licenses["test"] = license_obj
            manager._loaded = True

            # Test rendering
            rendered = manager.render_license(
                "test", {"author": "John Doe", "year": "2025"}
            )

            assert "Copyright (c) 2025 John Doe" in rendered
            assert "{year}" not in rendered
            assert "{author}" not in rendered

    def test_validate_license_variables_complete(self):
        """Test validating license variables when all required fields provided."""
        with TemporaryDirectory() as temp_dir:
            manager = LicenseManager(Path(temp_dir))

            # Manually add a license for testing
            license_obj = License(
                id="test",
                name="Test License",
                text="Test text with {author} and {year}",
                url="https://example.com",
                requires_fields=["author", "year"],
            )
            manager._licenses["test"] = license_obj
            manager._loaded = True

            # Test validation with complete variables
            is_valid = manager.validate_license_variables(
                "test", {"author": "John Doe", "year": "2025"}
            )
            assert is_valid

    def test_validate_license_variables_missing(self):
        """Test validating license variables when required fields missing."""
        with TemporaryDirectory() as temp_dir:
            manager = LicenseManager(Path(temp_dir))

            # Manually add a license for testing
            license_obj = License(
                id="test",
                name="Test License",
                text="Test text with {author} and {year}",
                url="https://example.com",
                requires_fields=["author", "year"],
            )
            manager._licenses["test"] = license_obj
            manager._loaded = True

            # Test validation with missing variables
            is_valid = manager.validate_license_variables(
                "test", {"author": "John Doe"}
            )
            assert not is_valid

    def test_validate_license_variables_no_requirements(self):
        """Test validating license variables when no fields required."""
        with TemporaryDirectory() as temp_dir:
            manager = LicenseManager(Path(temp_dir))

            # Manually add a license for testing (no required fields)
            license_obj = License(
                id="unlicense",
                name="The Unlicense",
                text="This is free and unencumbered software...",
                url="https://unlicense.org/",
                requires_fields=[],
            )
            manager._licenses["unlicense"] = license_obj
            manager._loaded = True

            # Test validation with no requirements
            is_valid = manager.validate_license_variables("unlicense", {})
            assert is_valid

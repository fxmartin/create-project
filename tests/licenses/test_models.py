# ABOUTME: Unit tests for license data models
# ABOUTME: Tests License model validation and functionality

import pytest
from pydantic import ValidationError

from create_project.licenses.models import License


class TestLicense:
    """Test License model functionality."""

    def test_license_creation_with_valid_data(self):
        """Test creating a license with all required fields."""
        license_data = {
            "id": "mit",
            "name": "MIT License",
            "text": "Copyright (c) {year} {author}\n\nPermission is hereby granted...",
            "url": "https://opensource.org/licenses/MIT",
            "requires_fields": ["author", "year"]
        }

        license_obj = License(**license_data)

        assert license_obj.id == "mit"
        assert license_obj.name == "MIT License"
        assert str(license_obj.url) == "https://opensource.org/licenses/MIT"
        assert "author" in license_obj.requires_fields
        assert "year" in license_obj.requires_fields

    def test_license_creation_with_minimal_data(self):
        """Test creating a license with only required fields."""
        license_data = {
            "id": "unlicense",
            "name": "The Unlicense",
            "text": "This is free and unencumbered software...",
            "url": "https://unlicense.org/"
        }

        license_obj = License(**license_data)

        assert license_obj.id == "unlicense"
        assert license_obj.requires_fields == []

    def test_license_validation_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        with pytest.raises(ValidationError) as exc_info:
            License(id="mit", name="MIT License")

        errors = exc_info.value.errors()
        missing_fields = {error["loc"][0] for error in errors}
        assert "text" in missing_fields
        assert "url" in missing_fields

    def test_license_id_validation(self):
        """Test license ID format validation."""
        valid_ids = ["mit", "apache-2.0", "gpl-3.0", "bsd-3-clause"]

        for license_id in valid_ids:
            license_obj = License(
                id=license_id,
                name="Test License",
                text="Test text",
                url="https://example.com"
            )
            assert license_obj.id == license_id

    def test_license_url_validation(self):
        """Test that URL field accepts valid URLs."""
        valid_license = License(
            id="test",
            name="Test License",
            text="Test text",
            url="https://opensource.org/licenses/MIT"
        )
        assert str(valid_license.url) == "https://opensource.org/licenses/MIT"

    def test_license_requires_fields_default(self):
        """Test that requires_fields defaults to empty list."""
        license_obj = License(
            id="test",
            name="Test License",
            text="Test text",
            url="https://example.com"
        )
        assert license_obj.requires_fields == []

    def test_license_text_contains_placeholders(self):
        """Test that license text can contain template placeholders."""
        license_text = "Copyright (c) {year} {author}\n\n{description}"
        license_obj = License(
            id="test",
            name="Test License",
            text=license_text,
            url="https://example.com",
            requires_fields=["year", "author", "description"]
        )

        assert "{year}" in license_obj.text
        assert "{author}" in license_obj.text
        assert "{description}" in license_obj.text

# ABOUTME: Unit tests for base template metadata models
# ABOUTME: Tests template metadata, compatibility, and usage statistics

"""Tests for base template metadata models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from create_project.templates.schema.base_template import (
    BaseTemplate,
    TemplateAuthor,
    TemplateMetadata,
)


class TestTemplateAuthor:
    """Test template author model."""

    def test_minimal_author(self):
        """Test creating author with minimal fields."""
        author = TemplateAuthor(name="John Doe")
        assert author.name == "John Doe"
        assert author.email is None
        assert author.url is None

    def test_full_author(self):
        """Test creating author with all fields."""
        author = TemplateAuthor(
            name="Jane Smith",
            email="jane@example.com",
            url="https://github.com/janesmith"
        )
        assert author.name == "Jane Smith"
        assert author.email == "jane@example.com"
        assert author.url == "https://github.com/janesmith"

    def test_invalid_email(self):
        """Test invalid email format."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateAuthor(
                name="Test",
                email="invalid-email"
            )
        assert "value is not a valid email address" in str(exc_info.value)

    def test_invalid_url(self):
        """Test invalid URL format."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateAuthor(
                name="Test",
                url="not-a-url"
            )
        assert "URL" in str(exc_info.value)


class TestTemplateMetadata:
    """Test template metadata model."""

    def test_minimal_metadata(self):
        """Test creating metadata with minimal fields."""
        metadata = TemplateMetadata(
            name="basic-python",
            version="1.0.0",
            description="A basic Python project template"
        )
        assert metadata.name == "basic-python"
        assert metadata.version == "1.0.0"
        assert metadata.description == "A basic Python project template"
        assert metadata.category == "general"  # default
        assert metadata.tags == []
        assert metadata.license == "MIT"  # default

    def test_full_metadata(self):
        """Test creating metadata with all fields."""
        author = TemplateAuthor(name="Test Author", email="test@example.com")
        metadata = TemplateMetadata(
            name="django-rest",
            version="2.1.0",
            description="Django REST API template",
            category="web",
            tags=["django", "rest", "api", "python"],
            author=author,
            license="Apache-2.0",
            homepage="https://example.com/templates/django-rest",
            repository="https://github.com/example/django-rest-template",
            documentation="https://docs.example.com/django-rest"
        )
        assert metadata.name == "django-rest"
        assert metadata.category == "web"
        assert len(metadata.tags) == 4
        assert metadata.author.name == "Test Author"
        assert metadata.license == "Apache-2.0"

    def test_name_validation(self):
        """Test template name validation."""
        # Valid names
        valid_names = [
            "simple-template",
            "python_project",
            "MyTemplate123",
            "test-123-template"
        ]

        for name in valid_names:
            metadata = TemplateMetadata(
                name=name,
                version="1.0.0",
                description="Test"
            )
            assert metadata.name == name

        # Invalid names
        invalid_names = [
            "123-start-with-number",
            "spaces not allowed",
            "special@chars!",
            "../../path-traversal"
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError):
                TemplateMetadata(
                    name=name,
                    version="1.0.0",
                    description="Test"
                )

    def test_version_validation(self):
        """Test version format validation."""
        # Valid versions
        valid_versions = ["1.0.0", "0.1.0", "2.3.4", "10.20.30"]

        for version in valid_versions:
            metadata = TemplateMetadata(
                name="test",
                version=version,
                description="Test"
            )
            assert metadata.version == version

        # Invalid versions
        invalid_versions = ["1.0", "v1.0.0", "1.0.0-beta", "latest"]

        for version in invalid_versions:
            with pytest.raises(ValidationError):
                TemplateMetadata(
                    name="test",
                    version=version,
                    description="Test"
                )

    def test_category_validation(self):
        """Test category validation."""
        valid_categories = [
            "general", "web", "api", "cli", "library",
            "data-science", "ml", "mobile", "desktop", "game", "other"
        ]

        for category in valid_categories:
            metadata = TemplateMetadata(
                name="test",
                version="1.0.0",
                description="Test",
                category=category
            )
            assert metadata.category == category

        with pytest.raises(ValidationError):
            TemplateMetadata(
                name="test",
                version="1.0.0",
                description="Test",
                category="invalid-category"
            )


class TestBaseTemplate:
    """Test base template model."""

    def test_minimal_base_template(self):
        """Test creating base template with minimal fields."""
        template = BaseTemplate(
            template_version="1.0",
            metadata=TemplateMetadata(
                name="test",
                version="1.0.0",
                description="Test template"
            )
        )
        assert template.template_version == "1.0"
        assert template.metadata.name == "test"
        assert template.created_at <= datetime.utcnow()
        assert template.updated_at <= datetime.utcnow()

    def test_updated_at_after_created_at(self):
        """Test updated_at validation."""
        now = datetime.utcnow()
        template = BaseTemplate(
            template_version="1.0",
            metadata=TemplateMetadata(
                name="test",
                version="1.0.0",
                description="Test"
            ),
            created_at=now,
            updated_at=now
        )
        assert template.created_at == template.updated_at

        # Test that updated_at cannot be before created_at
        with pytest.raises(ValidationError) as exc_info:
            BaseTemplate(
                template_version="1.0",
                metadata=TemplateMetadata(
                    name="test",
                    version="1.0.0",
                    description="Test"
                ),
                created_at=now,
                updated_at=now.replace(year=now.year - 1)
            )
        assert "updated_at must be after created_at" in str(exc_info.value)

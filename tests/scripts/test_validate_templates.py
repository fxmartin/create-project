# ABOUTME: Test suite for the template validation script
# ABOUTME: Ensures the validation script correctly handles template validation

"""Test the template validation script."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.validate_templates import validate_template_file


class TestValidateTemplates:
    """Test template validation functionality."""

    def test_valid_template(self, tmp_path):
        """Test validation of a valid template."""
        # Create a valid template file
        template_data = {
            "metadata": {
                "name": "Test Template",
                "description": "A test template",
                "version": "1.0.0",
                "category": "test",
                "tags": ["test"],
                "author": "Test Author",
                "created": "2025-07-25T00:00:00Z",
                "template_id": "test_template"
            },
            "configuration": {
                "schema_version": "1.0.0"
            },
            "variables": [],
            "structure": {
                "root_directory": {
                    "name": "{{project_name}}",
                    "files": [],
                    "directories": []
                }
            },
            "template_files": {
                "files": []
            },
            "hooks": {
                "pre_generation": [],
                "post_generation": []
            },
            "action_groups": [],
            "compatibility": {
                "min_python_version": "3.9.6",
                "supported_os": ["macOS", "Linux", "Windows"],
                "dependencies": []
            },
            "examples": [],
            "related_templates": []
        }
        
        template_path = tmp_path / "test_template.yaml"
        with open(template_path, "w") as f:
            import yaml
            yaml.safe_dump(template_data, f)
        
        # Mock the TemplateValidator to avoid import issues
        with patch("scripts.validate_templates.TemplateValidator") as MockValidator:
            mock_validator = MockValidator.return_value
            mock_validator.validate_template_data.return_value = MagicMock()
            
            result = validate_template_file(template_path)
            
            assert result["valid_yaml"] is True
            assert result["valid_schema"] is True
            assert len(result["errors"]) == 0
            assert result["file"] == "test_template.yaml"

    def test_invalid_yaml(self, tmp_path):
        """Test handling of invalid YAML."""
        template_path = tmp_path / "invalid.yaml"
        with open(template_path, "w") as f:
            f.write("invalid: yaml: content: [")
        
        result = validate_template_file(template_path)
        
        assert result["valid_yaml"] is False
        assert result["valid_schema"] is False
        assert len(result["errors"]) > 0
        assert "YAML parsing error" in result["errors"][0]

    def test_template_validation_error(self, tmp_path):
        """Test handling of TemplateValidationError."""
        template_data = {
            "metadata": {
                "name": "Test Template"
                # Missing required fields
            }
        }
        
        template_path = tmp_path / "invalid_template.yaml"
        with open(template_path, "w") as f:
            import yaml
            yaml.safe_dump(template_data, f)
        
        # Mock the TemplateValidator to raise an error
        with patch("scripts.validate_templates.TemplateValidator") as MockValidator:
            from create_project.templates.validator import TemplateValidationError
            
            mock_validator = MockValidator.return_value
            mock_error = TemplateValidationError(
                "Template validation failed",
                errors=[
                    {"field": "metadata.description", "message": "Field required"},
                    {"field": "metadata.version", "message": "Field required"}
                ]
            )
            mock_validator.validate_template_data.side_effect = mock_error
            
            result = validate_template_file(template_path)
            
            assert result["valid_yaml"] is True
            assert result["valid_schema"] is False
            assert len(result["errors"]) >= 3  # Main error + field errors
            assert "Template validation failed" in result["errors"][0]
            assert any("metadata.description: Field required" in err for err in result["errors"])

    def test_pydantic_validation_error(self, tmp_path):
        """Test handling of Pydantic ValidationError."""
        template_data = {
            "metadata": {
                "name": "Test Template",
                "version": "invalid-version"  # Invalid version format
            }
        }
        
        template_path = tmp_path / "pydantic_error.yaml"
        with open(template_path, "w") as f:
            import yaml
            yaml.safe_dump(template_data, f)
        
        # Don't mock anything - let Pydantic validation fail naturally
        result = validate_template_file(template_path)
        
        assert result["valid_yaml"] is True
        assert result["valid_schema"] is False
        assert len(result["errors"]) > 0
        # Check that field paths are properly formatted
        assert any("metadata." in err for err in result["errors"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
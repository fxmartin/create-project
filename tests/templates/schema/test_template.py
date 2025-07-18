# ABOUTME: Unit tests for complete template model
# ABOUTME: Tests template integration with all components and cross-validation

"""Tests for complete template model."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from create_project.templates.schema import (
    Template,
    TemplateMetadata,
)


class TestTemplate:
    """Test complete template model."""

    def test_minimal_template(self):
        """Test creating template with minimal fields."""
        template = Template(
            template_version="1.0",
            metadata=TemplateMetadata(
                name="minimal",
                version="1.0.0",
                description="Minimal template"
            ),
            variables=[],
            structure={
                "base_path": ".",
                "files": [
                    {
                        "type": "file",
                        "path": "README.md",
                        "content": "# Project"
                    }
                ]
            }
        )

        assert template.template_version == "1.0"
        assert template.metadata.name == "minimal"
        assert len(template.variables) == 0
        assert template.structure.base_path == "."
        assert len(template.structure.files) == 1

    def test_complete_template(self):
        """Test creating template with all features."""
        template = Template(
            template_version="1.0",
            metadata=TemplateMetadata(
                name="full-stack-app",
                version="2.0.0",
                description="Full-stack web application template",
                category="web",
                tags=["react", "nodejs", "typescript", "docker"],
                author={
                    "name": "John Doe",
                    "email": "john@example.com"
                }
            ),
            variables=[
                {
                    "name": "project_name",
                    "type": "string",
                    "label": "Project Name",
                    "description": "Name of your project",
                    "default": "my-app",
                    "pattern": "^[a-z][a-z0-9-]*$"
                },
                {
                    "name": "use_typescript",
                    "type": "boolean",
                    "label": "Use TypeScript",
                    "default": True
                },
                {
                    "name": "use_docker",
                    "type": "boolean",
                    "label": "Include Docker setup",
                    "default": False
                }
            ],
            structure={
                "base_path": "{{ project_name }}",
                "files": [
                    {
                        "type": "directory",
                        "path": "src",
                        "children": [
                            {
                                "type": "file",
                                "path": "index.js",
                                "template_path": "templates/index.js.j2"
                            }
                        ]
                    },
                    {
                        "type": "file",
                        "path": "package.json",
                        "template_path": "templates/package.json.j2"
                    },
                    {
                        "type": "file",
                        "path": "README.md",
                        "content": "# {{ project_name }}\n\nProject description here."
                    }
                ]
            },
            hooks={
                "after_create": [
                    {
                        "name": "Install dependencies",
                        "actions": [
                            {
                                "type": "command",
                                "command": "npm install"
                            }
                        ]
                    },
                    {
                        "name": "Setup Docker",
                        "condition": "use_docker == true",
                        "actions": [
                            {
                                "type": "command",
                                "command": "docker compose up -d"
                            }
                        ]
                    }
                ]
            }
        )

        assert template.metadata.name == "full-stack-app"
        assert len(template.variables) == 3
        assert len(template.structure.files) == 3
        assert len(template.hooks.after_create) == 2

        # Check variable types
        assert template.variables[0].type == "string"
        assert template.variables[1].type == "boolean"

        # Check conditional hook
        docker_hook = template.hooks.after_create[1]
        assert docker_hook.condition == "use_docker == true"

    def test_template_with_conditional_variables(self):
        """Test template with conditional variable display."""
        template = Template(
            template_version="1.0",
            metadata=TemplateMetadata(
                name="conditional",
                version="1.0.0",
                description="Template with conditional variables"
            ),
            variables=[
                {
                    "name": "framework",
                    "type": "choice",
                    "label": "Framework",
                    "choices": ["react", "vue", "angular"],
                    "default": "react"
                },
                {
                    "name": "use_router",
                    "type": "boolean",
                    "label": "Use Router",
                    "default": True,
                    "show_if": {
                        "variable": "framework",
                        "operator": "in",
                        "value": ["react", "vue"]
                    }
                },
                {
                    "name": "typescript_strict",
                    "type": "boolean",
                    "label": "TypeScript Strict Mode",
                    "default": False,
                    "show_if": {
                        "variable": "use_typescript",
                        "operator": "eq",
                        "value": True
                    }
                },
                {
                    "name": "use_typescript",
                    "type": "boolean",
                    "label": "Use TypeScript",
                    "default": True
                }
            ],
            structure={
                "base_path": ".",
                "files": [
                    {
                        "type": "file",
                        "path": "src/main.js",
                        "content": "console.log('Hello');"
                    }
                ]
            }
        )

        # Verify conditional relationships
        router_var = template.variables[1]
        assert router_var.show_if.variable == "framework"
        assert router_var.show_if.operator == "in"
        assert router_var.show_if.value == ["react", "vue"]

    def test_template_compatibility(self):
        """Test template with compatibility requirements."""
        template = Template(
            template_version="1.0",
            metadata=TemplateMetadata(
                name="python-app",
                version="1.0.0",
                description="Python application"
            ),
            variables=[],
            structure={
                "base_path": ".",
                "files": [
                    {
                        "type": "file",
                        "path": "main.py",
                        "content": "print('Hello')"
                    }
                ]
            },
            compatibility={
                "min_python_version": "3.8.0",
                "max_python_version": "3.11.0",
                "supported_os": ["macOS", "Linux"],
                "dependencies": ["git", "python3", "pip"]
            }
        )

        assert template.compatibility.min_python_version == "3.8.0"
        assert template.compatibility.max_python_version == "3.11.0"
        assert "Windows" not in template.compatibility.supported_os
        assert "git" in template.compatibility.dependencies

    def test_template_usage_stats(self):
        """Test template with usage statistics."""
        now = datetime.utcnow()
        template = Template(
            template_version="1.0",
            metadata=TemplateMetadata(
                name="popular",
                version="1.0.0",
                description="Popular template"
            ),
            variables=[],
            structure={
                "base_path": ".",
                "files": [
                    {
                        "type": "file",
                        "path": "README.md",
                        "content": "# Project"
                    }
                ]
            },
            usage_stats={
                "times_used": 1000,
                "last_used": now,
                "rating": 4.5,
                "rating_count": 250
            }
        )

        assert template.usage_stats.times_used == 1000
        assert template.usage_stats.rating == 4.5
        assert template.usage_stats.rating_count == 250

    def test_cross_validation_variable_references(self):
        """Test cross-validation of variable references."""
        # Test referencing non-existent variable
        with pytest.raises(ValidationError) as exc_info:
            Template(
                template_version="1.0",
                metadata=TemplateMetadata(
                    name="invalid",
                    version="1.0.0",
                    description="Invalid references"
                ),
                variables=[
                    {
                        "name": "var1",
                        "type": "boolean",
                        "label": "Variable 1",
                        "default": True,
                        "show_if": {
                            "variable": "non_existent",
                            "operator": "eq",
                            "value": True
                        }
                    }
                ],
                structure={
                    "base_path": ".",
                    "files": [
                        {
                            "type": "file",
                            "path": "test.txt",
                            "content": "test"
                        }
                    ]
                }
            )
        assert "references non-existent variable" in str(exc_info.value)

    def test_action_condition_validation(self):
        """Test validation of action conditions."""
        # Valid template with proper condition references
        template = Template(
            template_version="1.0",
            metadata=TemplateMetadata(
                name="valid-conditions",
                version="1.0.0",
                description="Valid condition references"
            ),
            variables=[
                {
                    "name": "use_git",
                    "type": "boolean",
                    "label": "Use Git",
                    "default": True
                }
            ],
            structure={
                "base_path": ".",
                "files": [
                    {
                        "type": "file",
                        "path": "README.md",
                        "content": "# Project"
                    }
                ]
            },
            hooks={
                "after_create": [
                    {
                        "name": "Git init",
                        "condition": "use_git == true",
                        "actions": [
                            {
                                "type": "git",
                                "git_action": "init"
                            }
                        ]
                    }
                ]
            }
        )

        # The condition references an existing variable
        assert template.hooks.after_create[0].condition == "use_git == true"

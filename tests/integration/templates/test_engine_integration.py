# ABOUTME: Integration tests for template engine with existing schema system
# ABOUTME: Tests end-to-end template processing and project generation workflows

"""Integration tests for template engine."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from create_project.config.config_manager import ConfigManager
from create_project.templates.engine import TemplateEngine
from create_project.templates.loader import TemplateLoader
from create_project.templates.renderers import ProjectRenderer
from create_project.templates.schema.template import Template


class TestTemplateEngineIntegration:
    """Integration tests for the complete template engine system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_manager = Mock(spec=ConfigManager)
        self.config_manager.get_setting.side_effect = lambda key, default: {
            "templates.directories": ["tests/fixtures/templates"],
            "templates.builtin_directory": "tests/fixtures/builtin",
            "templates.user_directory": "tests/fixtures/user",
            "templates.cache_enabled": True,
            "templates.cache_ttl": 3600
        }.get(key, default)

    def test_complete_template_workflow(self):
        """Test complete template workflow from loading to rendering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a complete test template
            template_data = {
                "schema_version": "1.0.0",
                "metadata": {
                    "name": "flask-web-app",
                    "description": "Flask web application template",
                    "version": "1.0.0",
                    "category": "web",
                    "author": "Test Author"
                },
                "variables": [
                    {
                        "name": "project_name",
                        "type": "string",
                        "description": "Project name",
                        "required": True,
                        "validation": {
                            "pattern": "^[a-zA-Z][a-zA-Z0-9_-]*$"
                        }
                    },
                    {
                        "name": "include_tests",
                        "type": "boolean",
                        "description": "Include test files",
                        "required": False,
                        "default": True
                    },
                    {
                        "name": "database_type",
                        "type": "choice",
                        "description": "Database type",
                        "required": False,
                        "default": "sqlite",
                        "choices": ["sqlite", "postgresql", "mysql"]
                    }
                ],
                "structure": {
                    "name": "{{ project_name }}",
                    "files": [
                        {
                            "name": "app.py",
                            "content": "from flask import Flask\n\napp = Flask('{{ project_name }}')\n\nif __name__ == '__main__':\n    app.run(debug=True)\n"
                        },
                        {
                            "name": "requirements.txt",
                            "content": "Flask>=2.0.0\n{% if database_type == 'postgresql' %}psycopg2>=2.8.0\n{% elif database_type == 'mysql' %}PyMySQL>=1.0.0\n{% endif %}"
                        },
                        {
                            "name": "README.md",
                            "content": "# {{ project_name | title }}\n\nA Flask web application using {{ database_type }} database.\n"
                        }
                    ],
                    "directories": [
                        {
                            "name": "tests",
                            "condition": "include_tests",
                            "files": [
                                {
                                    "name": "test_app.py",
                                    "content": "import pytest\nfrom app import app\n\ndef test_app_creation():\n    assert app is not None\n"
                                }
                            ],
                            "directories": []
                        },
                        {
                            "name": "static",
                            "files": [],
                            "directories": []
                        },
                        {
                            "name": "templates",
                            "files": [
                                {
                                    "name": "base.html",
                                    "content": "<!DOCTYPE html>\n<html>\n<head>\n    <title>{{ project_name | title }}</title>\n</head>\n<body>\n    <h1>Welcome to {{ project_name | title }}</h1>\n</body>\n</html>\n"
                                }
                            ],
                            "directories": []
                        }
                    ]
                }
            }
            
            # Save template to file
            template_path = temp_path / "flask-template.yaml"
            with open(template_path, 'w') as f:
                yaml.dump(template_data, f)
            
            # Initialize engine and load template
            engine = TemplateEngine(self.config_manager)
            template = engine.load_template(template_path)
            
            # Verify template loaded correctly
            assert isinstance(template, Template)
            assert template.metadata.name == "flask-web-app"
            assert len(template.variables) == 3
            
            # Resolve variables
            user_values = {
                "project_name": "my-flask-app",
                "include_tests": True,
                "database_type": "postgresql"
            }
            
            resolved_vars = engine.resolve_variables(template, user_values)
            
            assert resolved_vars["project_name"] == "my-flask-app"
            assert resolved_vars["include_tests"] is True
            assert resolved_vars["database_type"] == "postgresql"
            
            # Render project
            output_path = temp_path / "output"
            renderer = ProjectRenderer(engine)
            
            stats = renderer.render_project(template, resolved_vars, output_path)
            
            # Verify project structure was created
            project_dir = output_path / "my-flask-app"
            assert project_dir.exists()
            
            # Verify main files
            app_file = project_dir / "app.py"
            assert app_file.exists()
            app_content = app_file.read_text()
            assert "Flask('my-flask-app')" in app_content
            
            # Verify requirements with conditional content
            req_file = project_dir / "requirements.txt"
            assert req_file.exists()
            req_content = req_file.read_text()
            assert "Flask>=2.0.0" in req_content
            assert "psycopg2>=2.8.0" in req_content  # PostgreSQL dependency
            
            # Verify README with title filter
            readme_file = project_dir / "README.md"
            assert readme_file.exists()
            readme_content = readme_file.read_text()
            assert "# My-Flask-App" in readme_content
            assert "postgresql database" in readme_content
            
            # Verify conditional directory (tests should be included)
            tests_dir = project_dir / "tests"
            assert tests_dir.exists()
            test_file = tests_dir / "test_app.py"
            assert test_file.exists()
            
            # Verify other directories
            static_dir = project_dir / "static"
            assert static_dir.exists()
            
            templates_dir = project_dir / "templates"
            assert templates_dir.exists()
            base_html = templates_dir / "base.html"
            assert base_html.exists()
            base_content = base_html.read_text()
            assert "My-Flask-App" in base_content
            
            # Verify statistics
            assert stats["files_created"] >= 5
            assert stats["directories_created"] >= 4
            assert len(stats["errors"]) == 0

    def test_template_with_conditional_exclusion(self):
        """Test template rendering with conditional exclusion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create template with conditional content
            template_data = {
                "schema_version": "1.0.0",
                "metadata": {
                    "name": "conditional-template",
                    "description": "Template with conditional content",
                    "version": "1.0.0",
                    "category": "test",
                    "author": "Test Author"
                },
                "variables": [
                    {
                        "name": "include_feature",
                        "type": "boolean",
                        "description": "Include optional feature",
                        "required": False,
                        "default": False
                    }
                ],
                "structure": {
                    "name": "test-project",
                    "files": [
                        {
                            "name": "main.py",
                            "content": "print('Hello World')\n"
                        }
                    ],
                    "directories": [
                        {
                            "name": "feature",
                            "condition": "include_feature",
                            "files": [
                                {
                                    "name": "feature.py",
                                    "content": "# Optional feature\n"
                                }
                            ],
                            "directories": []
                        }
                    ]
                }
            }
            
            # Save template
            template_path = temp_path / "conditional-template.yaml"
            with open(template_path, 'w') as f:
                yaml.dump(template_data, f)
            
            # Initialize engine
            engine = TemplateEngine(self.config_manager)
            template = engine.load_template(template_path)
            
            # Test with feature disabled
            user_values = {"include_feature": False}
            resolved_vars = engine.resolve_variables(template, user_values)
            
            output_path = temp_path / "output-disabled"
            renderer = ProjectRenderer(engine)
            stats = renderer.render_project(template, resolved_vars, output_path)
            
            project_dir = output_path / "test-project"
            assert project_dir.exists()
            
            # Main file should exist
            main_file = project_dir / "main.py"
            assert main_file.exists()
            
            # Feature directory should NOT exist
            feature_dir = project_dir / "feature"
            assert not feature_dir.exists()
            
            # Test with feature enabled
            user_values = {"include_feature": True}
            resolved_vars = engine.resolve_variables(template, user_values)
            
            output_path = temp_path / "output-enabled"
            stats = renderer.render_project(template, resolved_vars, output_path)
            
            project_dir = output_path / "test-project"
            assert project_dir.exists()
            
            # Feature directory should exist
            feature_dir = project_dir / "feature"
            assert feature_dir.exists()
            feature_file = feature_dir / "feature.py"
            assert feature_file.exists()

    def test_template_loader_integration(self):
        """Test integration between template loader and engine."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Set up directory structure
            builtin_dir = temp_path / "builtin"
            builtin_dir.mkdir()
            user_dir = temp_path / "user"
            user_dir.mkdir()
            
            # Update config to point to our test directories
            self.config_manager.get.return_value = {
                "directories": [str(temp_path)],
                "builtin_directory": str(builtin_dir),
                "user_directory": str(user_dir)
            }
            
            # Create test templates
            builtin_template = {
                "schema_version": "1.0.0",
                "metadata": {
                    "name": "builtin-template",
                    "description": "Built-in template",
                    "version": "1.0.0",
                    "category": "builtin",
                    "author": "System"
                },
                "variables": [],
                "structure": {
                    "name": "builtin-project",
                    "files": [],
                    "directories": []
                }
            }
            
            user_template = {
                "schema_version": "1.0.0",
                "metadata": {
                    "name": "user-template",
                    "description": "User template",
                    "version": "1.0.0",
                    "category": "custom",
                    "author": "User"
                },
                "variables": [],
                "structure": {
                    "name": "user-project",
                    "files": [],
                    "directories": []
                }
            }
            
            # Save templates
            builtin_path = builtin_dir / "builtin.yaml"
            with open(builtin_path, 'w') as f:
                yaml.dump(builtin_template, f)
                
            user_path = user_dir / "user.yaml"
            with open(user_path, 'w') as f:
                yaml.dump(user_template, f)
            
            # Initialize loader and engine
            loader = TemplateLoader(self.config_manager)
            engine = TemplateEngine(self.config_manager)
            
            # Test template discovery
            discovered_templates = loader.discover_templates()
            assert len(discovered_templates) == 2
            
            # Test loading specific templates
            builtin_found = loader.find_template_by_name("builtin-template")
            assert builtin_found == builtin_path
            
            user_found = loader.find_template_by_name("user-template")
            assert user_found == user_path
            
            # Test loading templates through engine
            builtin_template_obj = engine.load_template(builtin_found)
            assert builtin_template_obj.metadata.name == "builtin-template"
            
            user_template_obj = engine.load_template(user_found)
            assert user_template_obj.metadata.name == "user-template"
            
            # Test template categories
            categories = loader.get_template_categories()
            assert "builtin" in categories
            assert "custom" in categories

    def test_error_handling_integration(self):
        """Test error handling across the template system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create invalid template (missing required fields)
            invalid_template = {
                "metadata": {
                    "name": "",  # Invalid empty name
                    "description": "Invalid template"
                }
            }
            
            template_path = temp_path / "invalid.yaml"
            with open(template_path, 'w') as f:
                yaml.dump(invalid_template, f)
            
            # Test that engine properly handles invalid template
            engine = TemplateEngine(self.config_manager)
            
            with pytest.raises(Exception):  # Should raise TemplateLoadError
                engine.load_template(template_path)
            
            # Test that loader validates templates
            loader = TemplateLoader(self.config_manager)
            errors = loader.validate_template_file(template_path)
            assert len(errors) > 0

    def test_variable_resolution_with_complex_conditions(self):
        """Test variable resolution with complex conditional logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create template with complex variable conditions
            template_data = {
                "schema_version": "1.0.0",
                "metadata": {
                    "name": "complex-conditions",
                    "description": "Template with complex conditions",
                    "version": "1.0.0",
                    "category": "test",
                    "author": "Test Author"
                },
                "variables": [
                    {
                        "name": "project_type",
                        "type": "choice",
                        "description": "Project type",
                        "required": True,
                        "choices": ["web", "cli", "library"]
                    },
                    {
                        "name": "web_framework",
                        "type": "choice",
                        "description": "Web framework",
                        "required": False,
                        "default": "flask",
                        "choices": ["flask", "django", "fastapi"],
                        "show_if": {
                            "variable": "project_type",
                            "operator": "equals",
                            "value": "web"
                        }
                    },
                    {
                        "name": "cli_tool",
                        "type": "string",
                        "description": "CLI tool name",
                        "required": False,
                        "show_if": {
                            "variable": "project_type",
                            "operator": "equals",
                            "value": "cli"
                        }
                    }
                ],
                "structure": {
                    "name": "test-project",
                    "files": [],
                    "directories": []
                }
            }
            
            template_path = temp_path / "complex.yaml"
            with open(template_path, 'w') as f:
                yaml.dump(template_data, f)
            
            engine = TemplateEngine(self.config_manager)
            template = engine.load_template(template_path)
            
            # Test web project (should include web_framework)
            user_values = {"project_type": "web", "web_framework": "django"}
            resolved_vars = engine.resolve_variables(template, user_values)
            
            assert resolved_vars["project_type"] == "web"
            assert resolved_vars["web_framework"] == "django"
            assert "cli_tool" not in resolved_vars
            
            # Test CLI project (should include cli_tool)
            user_values = {"project_type": "cli", "cli_tool": "mytool"}
            resolved_vars = engine.resolve_variables(template, user_values)
            
            assert resolved_vars["project_type"] == "cli"
            assert resolved_vars["cli_tool"] == "mytool"
            assert "web_framework" not in resolved_vars
            
            # Test library project (should not include conditional variables)
            user_values = {"project_type": "library"}
            resolved_vars = engine.resolve_variables(template, user_values)
            
            assert resolved_vars["project_type"] == "library"
            assert "web_framework" not in resolved_vars
            assert "cli_tool" not in resolved_vars
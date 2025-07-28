# ABOUTME: Comprehensive unit tests for complete template schema
# ABOUTME: Tests TemplateCompatibility, TemplateUsageStats, and Template models with full integration

"""Unit tests for complete template schema."""

import re
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from create_project.templates.schema.actions import (
    ActionGroup,
    ActionType,
    TemplateAction,
    TemplateHooks,
)
from create_project.templates.schema.base_template import (
    TemplateCategory,
    TemplateLicense,
    TemplateMetadata,
)
from create_project.templates.schema.structure import (
    DirectoryItem,
    FileItem,
    ProjectStructure,
    TemplateFile,
    TemplateFiles,
)
from create_project.templates.schema.template import (
    Template,
    TemplateCompatibility,
    TemplateUsageStats,
)
from create_project.templates.schema.variables import (
    ChoiceItem,
    TemplateVariable,
    VariableType,
)


class TestTemplateCompatibility:
    """Test TemplateCompatibility model."""

    def test_minimal_compatibility(self):
        """Test creating minimal compatibility."""
        compat = TemplateCompatibility()
        assert compat.min_python_version == "3.9.6"
        assert compat.max_python_version is None
        assert compat.supported_os == ["macOS", "Linux", "Windows"]
        assert compat.dependencies == []

    def test_full_compatibility(self):
        """Test creating full compatibility configuration."""
        compat = TemplateCompatibility(
            min_python_version="3.10.0",
            max_python_version="3.12.0",
            supported_os=["Linux", "macOS"],
            dependencies=["numpy", "pandas", "matplotlib"]
        )
        assert compat.min_python_version == "3.10.0"
        assert compat.max_python_version == "3.12.0"
        assert compat.supported_os == ["Linux", "macOS"]
        assert len(compat.dependencies) == 3

    def test_python_version_validation(self):
        """Test Python version format validation."""
        # Valid versions
        compat = TemplateCompatibility(
            min_python_version="3.9.0",
            max_python_version="3.11.5"
        )
        assert compat.min_python_version == "3.9.0"
        assert compat.max_python_version == "3.11.5"

        # Invalid format for min version
        with pytest.raises(ValidationError) as exc_info:
            TemplateCompatibility(min_python_version="3.9")
        errors = exc_info.value.errors()
        assert any("must be in format X.Y.Z" in str(e) for e in errors)

        # Invalid format for max version
        with pytest.raises(ValidationError) as exc_info:
            TemplateCompatibility(max_python_version="python3.12")
        errors = exc_info.value.errors()
        assert any("must be in format X.Y.Z" in str(e) for e in errors)

    def test_python_version_none(self):
        """Test that None is valid for max_python_version."""
        compat = TemplateCompatibility(max_python_version=None)
        assert compat.max_python_version is None


class TestTemplateUsageStats:
    """Test TemplateUsageStats model."""

    def test_minimal_stats(self):
        """Test creating minimal usage stats."""
        stats = TemplateUsageStats()
        assert stats.downloads == 0
        assert stats.generations == 0
        assert stats.last_used is None
        assert stats.average_rating is None

    def test_full_stats(self):
        """Test creating full usage stats."""
        now = datetime.now()
        stats = TemplateUsageStats(
            downloads=150,
            generations=75,
            last_used=now,
            average_rating=4.5
        )
        assert stats.downloads == 150
        assert stats.generations == 75
        assert stats.last_used == now
        assert stats.average_rating == 4.5

    def test_rating_validation(self):
        """Test rating validation between 1 and 5."""
        # Valid ratings
        for rating in [1.0, 2.5, 3.7, 4.9, 5.0]:
            stats = TemplateUsageStats(average_rating=rating)
            assert stats.average_rating == rating

        # Invalid ratings
        for invalid_rating in [0.5, 0, -1, 5.1, 6.0, 10.0]:
            with pytest.raises(ValidationError) as exc_info:
                TemplateUsageStats(average_rating=invalid_rating)
            errors = exc_info.value.errors()
            assert any("between 1.0 and 5.0" in str(e) for e in errors)

    def test_rating_none(self):
        """Test that None is valid for average_rating."""
        stats = TemplateUsageStats(average_rating=None)
        assert stats.average_rating is None


class TestTemplate:
    """Test Template model."""

    def create_basic_metadata(self):
        """Create basic template metadata for testing."""
        return TemplateMetadata(
            name="Test Template",
            description="A test template",
            version="1.0.0",
            category=TemplateCategory.SCRIPT,
            author="Test Author"
        )

    def create_basic_structure(self):
        """Create basic project structure for testing."""
        root = DirectoryItem(
            name="project_root",
            files=[
                FileItem(name="README.md", content="# Test Project"),
                FileItem(name="main.py", content="print('Hello')")
            ]
        )
        return ProjectStructure(root_directory=root)

    def test_minimal_template(self):
        """Test creating minimal template."""
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure()
        )
        assert template.name == "Test Template"
        assert len(template.variables) == 0
        assert isinstance(template.template_files, TemplateFiles)
        assert isinstance(template.hooks, TemplateHooks)
        assert len(template.action_groups) == 0
        assert isinstance(template.compatibility, TemplateCompatibility)
        assert template.usage_stats is None

    def test_template_with_variables(self):
        """Test template with variables."""
        variables = [
            TemplateVariable(
                name="project_name",
                type=VariableType.STRING,
                description="Project name",
                default="my-project"
            ),
            TemplateVariable(
                name="use_tests",
                type=VariableType.BOOLEAN,
                description="Include tests",
                default=True
            )
        ]
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            variables=variables
        )
        assert len(template.variables) == 2
        assert template.variables[0].name == "project_name"
        assert template.variables[1].name == "use_tests"

    def test_duplicate_variable_names(self):
        """Test that duplicate variable names are rejected."""
        variables = [
            TemplateVariable(
                name="project_name",
                type=VariableType.STRING,
                description="Project name"
            ),
            TemplateVariable(
                name="project_name",  # Duplicate
                type=VariableType.STRING,
                description="Another project name"
            ),
            TemplateVariable(
                name="author",
                type=VariableType.STRING,
                description="Author name"
            )
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            Template(
                metadata=self.create_basic_metadata(),
                structure=self.create_basic_structure(),
                variables=variables
            )
        errors = exc_info.value.errors()
        assert any("Duplicate variable names" in str(e) for e in errors)
        assert any("'project_name'" in str(e) for e in errors)

    def test_template_name_property(self):
        """Test name property returns metadata name."""
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure()
        )
        assert template.name == template.metadata.name

    def test_template_with_hooks(self):
        """Test template with hooks."""
        pre_action = TemplateAction(
            name="setup",
            type=ActionType.COMMAND,
            command="echo 'Setting up'",
            description="Setup action"
        )
        post_action = TemplateAction(
            name="cleanup",
            type=ActionType.COMMAND,
            command="echo 'Cleaning up'",
            description="Cleanup action"
        )
        
        hooks = TemplateHooks(
            pre_generate=[pre_action],
            post_generate=[post_action]
        )
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            hooks=hooks
        )
        assert len(template.hooks.pre_generate) == 1
        assert len(template.hooks.post_generate) == 1

    def test_template_with_action_groups(self):
        """Test template with action groups."""
        action1 = TemplateAction(
            name="install",
            type=ActionType.COMMAND,
            command="pip install -r requirements.txt",
            description="Install dependencies"
        )
        action2 = TemplateAction(
            name="test",
            type=ActionType.COMMAND,
            command="pytest",
            description="Run tests"
        )
        
        group = ActionGroup(
            name="setup",
            description="Setup actions",
            actions=[action1, action2]
        )
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            action_groups=[group]
        )
        assert len(template.action_groups) == 1
        assert len(template.action_groups[0].actions) == 2

    def test_template_with_template_files(self):
        """Test template with template files."""
        template_files = TemplateFiles(
            files=[
                TemplateFile(
                    name="setup.py.j2",
                    content="setup(name='{{ project_name }}')"
                ),
                TemplateFile(
                    name="config.yml.j2",
                    content="name: {{ project_name }}\nversion: {{ version }}"
                )
            ]
        )
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            template_files=template_files
        )
        assert len(template.template_files.files) == 2

    def test_template_with_usage_stats(self):
        """Test template with usage statistics."""
        stats = TemplateUsageStats(
            downloads=100,
            generations=50,
            last_used=datetime.now(),
            average_rating=4.2
        )
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            usage_stats=stats
        )
        assert template.usage_stats.downloads == 100
        assert template.usage_stats.average_rating == 4.2

    def test_template_with_metadata_fields(self):
        """Test template with additional metadata fields."""
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            examples=["example1", "example2"],
            related_templates=["template1", "template2"]
        )
        assert len(template.examples) == 2
        assert len(template.related_templates) == 2

    def test_validate_template_complete_basic(self):
        """Test basic template validation."""
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure()
        )
        errors = template.validate_template_complete()
        assert len(errors) == 0

    def test_validate_template_complete_with_invalid_variable_default(self):
        """Test validation with invalid variable default value."""
        # Note: Pydantic validates types at construction time, so we need to
        # test a different scenario - a choice variable with invalid default
        variables = [
            TemplateVariable(
                name="theme",
                type=VariableType.CHOICE,
                description="Color theme",
                choices=[
                    ChoiceItem(value="light"),
                    ChoiceItem(value="dark")
                ],
                default="blue"  # Not in choices
            )
        ]
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            variables=variables
        )
        errors = template.validate_template_complete()
        assert len(errors) > 0
        assert any("Variable 'theme'" in e for e in errors)

    def test_validate_template_complete_with_structure_errors(self):
        """Test validation with structure errors."""
        # Create structure with duplicate file names
        root = DirectoryItem(
            name="project",
            files=[
                FileItem(name="test.py", content="# Test 1"),
                FileItem(name="test.py", content="# Test 2")  # Duplicate
            ]
        )
        structure = ProjectStructure(root_directory=root)
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=structure
        )
        errors = template.validate_template_complete()
        assert len(errors) > 0
        assert any("Duplicate file names" in e for e in errors)

    def test_validate_template_complete_with_hook_errors(self):
        """Test validation with hook errors."""
        action1 = TemplateAction(
            name="duplicate",
            type=ActionType.COMMAND,
            command="echo 1",
            description="First"
        )
        action2 = TemplateAction(
            name="duplicate",  # Duplicate name
            type=ActionType.COMMAND,
            command="echo 2",
            description="Second"
        )
        
        hooks = TemplateHooks(
            pre_generate=[action1],
            post_generate=[action2]
        )
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            hooks=hooks
        )
        errors = template.validate_template_complete()
        assert len(errors) > 0
        assert any("Duplicate action names" in e for e in errors)

    def test_validate_template_complete_with_group_errors(self):
        """Test validation with action group errors."""
        action1 = TemplateAction(
            name="duplicate",
            type=ActionType.COMMAND,
            command="echo 1",
            description="First"
        )
        action2 = TemplateAction(
            name="duplicate",  # Duplicate in same group
            type=ActionType.COMMAND,
            command="echo 2",
            description="Second"
        )
        
        group = ActionGroup(
            name="test_group",
            description="Test group",
            actions=[action1, action2]
        )
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            action_groups=[group]
        )
        errors = template.validate_template_complete()
        assert len(errors) > 0
        assert any("Duplicate action names" in e for e in errors)

    def test_validate_variable_usage_undefined(self):
        """Test validation catches undefined variables in structure."""
        # Structure using undefined variable
        root = DirectoryItem(
            name="project",
            files=[
                FileItem(
                    name="{{ undefined_file }}.py",  # undefined in file name
                    content="PROJECT = '{{ undefined_var }}'"  # undefined in content
                )
            ],
            directories=[
                DirectoryItem(
                    name="{{ project_name }}_tests"  # undefined in directory name
                )
            ]
        )
        structure = ProjectStructure(root_directory=root)
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=structure,
            variables=[]  # No variables defined
        )
        errors = template.validate_template_complete()
        # Should have errors for all undefined variables
        error_messages = "\n".join(errors)
        assert "undefined_file" in error_messages
        assert "undefined_var" in error_messages
        assert "project_name" in error_messages

    def test_validate_variable_usage_defined(self):
        """Test validation passes for defined variables."""
        variables = [
            TemplateVariable(
                name="project_name",
                type=VariableType.STRING,
                description="Project name"
            ),
            TemplateVariable(
                name="author",
                type=VariableType.STRING,
                description="Author name"
            )
        ]
        
        root = DirectoryItem(
            name="{{ project_name }}",
            files=[
                FileItem(
                    name="config.py",
                    content="AUTHOR = '{{ author }}'"
                )
            ]
        )
        structure = ProjectStructure(root_directory=root)
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=structure,
            variables=variables
        )
        errors = template.validate_template_complete()
        assert len(errors) == 0

    def test_validate_variable_usage_system_vars(self):
        """Test validation allows system-injected variables."""
        root = DirectoryItem(
            name="project",
            files=[
                FileItem(
                    name="LICENSE",
                    content="{{ license_text }}"  # System variable
                )
            ]
        )
        structure = ProjectStructure(root_directory=root)
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=structure,
            variables=[]  # license_text is system-injected
        )
        errors = template.validate_template_complete()
        assert len(errors) == 0  # Should not report error for license_text

    def test_validate_variable_usage_skip_html_templates(self):
        """Test validation skips HTML/template files."""
        root = DirectoryItem(
            name="project",
            files=[
                FileItem(
                    name="index.html",
                    content="<h1>{{ title }}</h1>"  # Application template, not project template
                ),
                FileItem(
                    name="template.jinja2",
                    content="{% for item in items %}{{ item }}{% endfor %}"
                )
            ]
        )
        structure = ProjectStructure(root_directory=root)
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=structure,
            variables=[]
        )
        errors = template.validate_template_complete()
        assert len(errors) == 0  # Should not report errors for HTML templates

    def test_validate_template_file_references(self):
        """Test validation of template file references."""
        # Define template files
        template_files = TemplateFiles(
            files=[
                TemplateFile(name="setup.py.j2", content="..."),
                TemplateFile(name="config.yml.j2", content="...")
            ]
        )
        
        # Structure referencing non-existent template
        root = DirectoryItem(
            name="project",
            files=[
                FileItem(name="setup.py", template_file="setup.py.j2"),  # Exists
                FileItem(name="main.py", template_file="main.py.j2"),  # Does not exist
            ]
        )
        structure = ProjectStructure(root_directory=root)
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=structure,
            template_files=template_files
        )
        errors = template.validate_template_complete()
        assert len(errors) >= 1
        assert any("Template file 'main.py.j2' not found" in e for e in errors)

    def test_get_variable_by_name(self):
        """Test getting variable by name."""
        variables = [
            TemplateVariable(
                name="project_name",
                type=VariableType.STRING,
                description="Project name"
            ),
            TemplateVariable(
                name="author",
                type=VariableType.STRING,
                description="Author"
            )
        ]
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            variables=variables
        )
        
        var = template.get_variable_by_name("project_name")
        assert var is not None
        assert var.name == "project_name"
        
        var = template.get_variable_by_name("nonexistent")
        assert var is None

    def test_get_required_variables(self):
        """Test getting required variables."""
        variables = [
            TemplateVariable(
                name="required1",
                type=VariableType.STRING,
                description="Required",
                required=True
            ),
            TemplateVariable(
                name="optional1",
                type=VariableType.STRING,
                description="Optional",
                required=False
            ),
            TemplateVariable(
                name="required2",
                type=VariableType.STRING,
                description="Required",
                required=True
            )
        ]
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            variables=variables
        )
        
        required = template.get_required_variables()
        assert len(required) == 2
        assert all(v.required for v in required)
        assert {v.name for v in required} == {"required1", "required2"}

    def test_get_optional_variables(self):
        """Test getting optional variables."""
        variables = [
            TemplateVariable(
                name="required1",
                type=VariableType.STRING,
                description="Required",
                required=True
            ),
            TemplateVariable(
                name="optional1",
                type=VariableType.STRING,
                description="Optional",
                required=False
            ),
            TemplateVariable(
                name="optional2",
                type=VariableType.STRING,
                description="Optional",
                required=False
            )
        ]
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            variables=variables
        )
        
        optional = template.get_optional_variables()
        assert len(optional) == 2
        assert all(not v.required for v in optional)
        assert {v.name for v in optional} == {"optional1", "optional2"}

    def test_get_variables_by_type(self):
        """Test getting variables by type."""
        variables = [
            TemplateVariable(
                name="name",
                type=VariableType.STRING,
                description="Name"
            ),
            TemplateVariable(
                name="age",
                type=VariableType.INTEGER,
                description="Age"
            ),
            TemplateVariable(
                name="description",
                type=VariableType.STRING,
                description="Description"
            ),
            TemplateVariable(
                name="enabled",
                type=VariableType.BOOLEAN,
                description="Enabled"
            )
        ]
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure(),
            variables=variables
        )
        
        string_vars = template.get_variables_by_type(VariableType.STRING)
        assert len(string_vars) == 2
        assert all(v.type == VariableType.STRING for v in string_vars)
        
        int_vars = template.get_variables_by_type(VariableType.INTEGER)
        assert len(int_vars) == 1
        assert int_vars[0].name == "age"

    def test_estimate_generation_time(self):
        """Test generation time estimation."""
        # Simple template
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=self.create_basic_structure()
        )
        time1 = template.estimate_generation_time()
        assert time1 >= 5  # Base time
        
        # Complex template with more files and actions
        root = DirectoryItem(
            name="project",
            files=[FileItem(name=f"file{i}.py", content="...") for i in range(10)],
            directories=[
                DirectoryItem(
                    name=f"dir{i}",
                    files=[FileItem(name=f"sub{j}.py", content="...") for j in range(5)]
                ) for i in range(3)
            ]
        )
        structure = ProjectStructure(root_directory=root)
        
        actions = [
            TemplateAction(
                name=f"action{i}",
                type=ActionType.COMMAND,
                command=f"echo {i}",
                description=f"Action {i}"
            ) for i in range(5)
        ]
        hooks = TemplateHooks(post_generate=actions)
        
        template2 = Template(
            metadata=self.create_basic_metadata(),
            structure=structure,
            hooks=hooks
        )
        time2 = template2.estimate_generation_time()
        assert time2 > time1  # Should take longer
        # 25 total files (10 + 3*5), 3 directories, 5 actions
        expected_min = int(5 + (25 * 0.5) + (3 * 0.1) + (5 * 2))
        assert time2 >= expected_min

    def test_get_template_summary(self):
        """Test getting template summary."""
        variables = [
            TemplateVariable(
                name="project_name",
                type=VariableType.STRING,
                description="Project name"
            ),
            TemplateVariable(
                name="author",
                type=VariableType.STRING,
                description="Author"
            )
        ]
        
        root = DirectoryItem(
            name="project",
            files=[
                FileItem(name="main.py", content="..."),
                FileItem(name="config.py", content="...")
            ],
            directories=[DirectoryItem(name="src")]
        )
        structure = ProjectStructure(root_directory=root)
        
        actions = [
            TemplateAction(
                name="setup",
                type=ActionType.COMMAND,
                command="pip install",
                description="Setup"
            )
        ]
        hooks = TemplateHooks(post_generate=actions)
        
        compat = TemplateCompatibility(
            min_python_version="3.10.0",
            supported_os=["Linux", "macOS"]
        )
        
        template = Template(
            metadata=self.create_basic_metadata(),
            structure=structure,
            variables=variables,
            hooks=hooks,
            compatibility=compat
        )
        
        summary = template.get_template_summary()
        assert summary["name"] == "Test Template"
        assert summary["description"] == "A test template"
        assert summary["version"] == "1.0.0"
        assert summary["category"] == TemplateCategory.SCRIPT
        assert summary["author"] == "Test Author"
        assert summary["variable_count"] == 2
        assert summary["file_count"] == 2
        assert summary["directory_count"] == 1
        assert summary["action_count"] == 1
        assert summary["estimated_time"] > 0
        assert summary["compatibility"]["python_version"] == "3.10.0"
        assert summary["compatibility"]["os"] == ["Linux", "macOS"]

    def test_pydantic_config(self):
        """Test Pydantic configuration."""
        # Extra fields are forbidden
        with pytest.raises(ValidationError):
            Template(
                metadata=self.create_basic_metadata(),
                structure=self.create_basic_structure(),
                unknown_field="value"
            )

    def test_complex_real_world_template(self):
        """Test a complex real-world template configuration."""
        # Create a Flask project template
        metadata = TemplateMetadata(
            name="Flask Web App",
            description="A modern Flask web application template",
            version="2.0.0",
            category=TemplateCategory.FLASK,
            tags=["web", "flask", "python", "api"],
            author="Web Developer",
            author_email="dev@example.com",
            license=TemplateLicense.MIT,
            min_python_version="3.10.0",
            documentation_url="https://example.com/docs",
            source_url="https://github.com/example/flask-template"
        )
        
        variables = [
            TemplateVariable(
                name="project_name",
                type=VariableType.STRING,
                description="Project name",
                default="my-flask-app",
                prompt="Enter your project name"
            ),
            TemplateVariable(
                name="use_database",
                type=VariableType.BOOLEAN,
                description="Include database support",
                default=True
            ),
            TemplateVariable(
                name="database_type",
                type=VariableType.CHOICE,
                description="Database type",
                choices=[
                    ChoiceItem(value="sqlite", label="SQLite"),
                    ChoiceItem(value="postgresql", label="PostgreSQL"),
                    ChoiceItem(value="mysql", label="MySQL")
                ],
                default="sqlite"
            ),
            TemplateVariable(
                name="features",
                type=VariableType.MULTICHOICE,
                description="Additional features",
                choices=[
                    ChoiceItem(value="auth", label="Authentication"),
                    ChoiceItem(value="api", label="REST API"),
                    ChoiceItem(value="admin", label="Admin Panel"),
                    ChoiceItem(value="celery", label="Background Tasks")
                ],
                default=["auth", "api"]
            )
        ]
        
        # Create project structure
        app_dir = DirectoryItem(
            name="{{ project_name }}",
            files=[
                FileItem(name="__init__.py", template_file="app_init.py.j2"),
                FileItem(name="config.py", template_file="config.py.j2"),
                FileItem(name="models.py", template_file="models.py.j2")
            ],
            directories=[
                DirectoryItem(
                    name="templates",
                    files=[
                        FileItem(name="base.html", content="<!DOCTYPE html>...")
                    ]
                ),
                DirectoryItem(
                    name="static",
                    directories=[
                        DirectoryItem(name="css"),
                        DirectoryItem(name="js"),
                        DirectoryItem(name="img")
                    ]
                )
            ]
        )
        
        tests_dir = DirectoryItem(
            name="tests",
            files=[
                FileItem(name="__init__.py", content=""),
                FileItem(name="test_app.py", template_file="test_app.py.j2")
            ]
        )
        
        root = DirectoryItem(
            name="{{ project_name }}_project",
            files=[
                FileItem(name="app.py", template_file="app.py.j2"),
                FileItem(name="requirements.txt", template_file="requirements.txt.j2"),
                FileItem(name="README.md", template_file="README.md.j2"),
                FileItem(name=".gitignore", content="*.pyc\n__pycache__/\n.env"),
                FileItem(name=".env.example", template_file="env.example.j2")
            ],
            directories=[app_dir, tests_dir]
        )
        
        structure = ProjectStructure(root_directory=root)
        
        # Template files
        template_files = TemplateFiles(
            files=[
                TemplateFile(
                    name="app.py.j2",
                    content="from {{ project_name }} import create_app\n\napp = create_app()"
                ),
                TemplateFile(
                    name="app_init.py.j2",
                    content="from flask import Flask\n\ndef create_app():\n    app = Flask(__name__)\n    return app"
                ),
                TemplateFile(
                    name="requirements.txt.j2",
                    content="Flask==2.3.0\n{% if use_database %}SQLAlchemy==2.0.0{% endif %}"
                ),
                TemplateFile(
                    name="README.md.j2",
                    content="# {{ project_name }}\n\nA Flask web application."
                )
            ]
        )
        
        # Actions and hooks
        setup_actions = [
            TemplateAction(
                name="create_venv",
                type=ActionType.PYTHON,
                command="import venv; venv.create('.venv', with_pip=True)",
                description="Create virtual environment"
            ),
            TemplateAction(
                name="install_deps",
                type=ActionType.COMMAND,
                command="pip install -r requirements.txt",
                description="Install dependencies"
            )
        ]
        
        git_actions = [
            TemplateAction(
                name="git_init",
                type=ActionType.GIT,
                command="git init",
                description="Initialize git repository"
            ),
            TemplateAction(
                name="git_add",
                type=ActionType.GIT,
                command="git add .",
                description="Add files to git"
            )
        ]
        
        hooks = TemplateHooks(
            post_generate=setup_actions
        )
        
        action_groups = [
            ActionGroup(
                name="git_setup",
                description="Git repository setup",
                actions=git_actions,
                condition="{{ init_git }}",
                parallel=False
            )
        ]
        
        # Create complete template
        template = Template(
            metadata=metadata,
            variables=variables,
            structure=structure,
            template_files=template_files,
            hooks=hooks,
            action_groups=action_groups,
            compatibility=TemplateCompatibility(
                min_python_version="3.10.0",
                supported_os=["Linux", "macOS"],
                dependencies=["git", "python3-venv"]
            ),
            examples=["https://github.com/example/flask-demo"],
            related_templates=["flask-minimal", "flask-rest-api"]
        )
        
        # Validate the complete template
        errors = template.validate_template_complete()
        # Should have some errors for undefined template files
        assert len(errors) > 0
        assert any("Template file" in e and "not found" in e for e in errors)
        
        # Test various methods
        assert template.name == "Flask Web App"
        assert len(template.get_required_variables()) == 4  # All vars are required by default
        assert len(template.get_variables_by_type(VariableType.CHOICE)) == 1
        
        summary = template.get_template_summary()
        assert summary["name"] == "Flask Web App"
        assert summary["variable_count"] == 4
        assert summary["file_count"] >= 8
        assert summary["directory_count"] >= 6
        assert summary["action_count"] == 2  # Only hooks count, not action groups
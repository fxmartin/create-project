# ABOUTME: Mock templates for integration testing without loading real YAML files
# ABOUTME: Provides pre-configured Template objects for consistent testing

"""Mock templates for integration testing.

Provides pre-configured Template objects that can be used in integration tests
without loading and parsing actual YAML template files.
"""

from typing import Any, Dict

from create_project.templates.schema import (
    DirectoryItem,
    FileItem,
    ProjectStructure,
    Template,
    TemplateConfiguration,
    TemplateMetadata,
    TemplateVariable,
    ValidationRule,
    VariableType,
)


def create_mock_one_off_script_template() -> Template:
    """Create a mock one-off script template."""
    from create_project.templates.schema.template import (
        TemplateCompatibility,
        TemplateFiles,
    )

    return Template(
        metadata=TemplateMetadata(
            name="One-off Script",
            description="Simple Python script for personal use",
            version="1.0.0",
            category="script",
            tags=["script", "automation", "utility"],
            author="Test Author",
        ),
        configuration=TemplateConfiguration(schema_version="1.0.0"),
        variables=[
            TemplateVariable(
                name="project_name",
                type=VariableType.STRING,
                description="Name of the script project",
                required=True,
                validation_rules=[
                    ValidationRule(
                        rule_type="pattern",
                        value="^[a-zA-Z][a-zA-Z0-9_-]*$",
                        message="Must start with letter and contain only letters, numbers, underscores, and hyphens",
                    )
                ],
            ),
            TemplateVariable(
                name="description",
                type=VariableType.STRING,
                description="Brief description of the script",
                required=False,
                default="A simple Python script",
            ),
            TemplateVariable(
                name="author",
                type=VariableType.STRING,
                description="Script author name",
                required=False,
                default="Unknown",
            ),
            TemplateVariable(
                name="author_email",
                type=VariableType.EMAIL,
                description="Author email address",
                required=False,
            ),
        ],
        structure=ProjectStructure(
            root_directory=DirectoryItem(
                name="{{project_name}}",
                files=[
                    FileItem(
                        name="{{project_name}}.py",
                        content="#!/usr/bin/env python3\n\ndef main():\n    print('Hello from {{project_name}}!')\n\nif __name__ == '__main__':\n    main()\n",
                    ),
                    FileItem(
                        name="README.md",
                        content="# {{project_name}}\n\n{{description}}\n\nAuthor: {{author}}\n",
                    ),
                    FileItem(
                        name="requirements.txt",
                        content="# Add your dependencies here\n",
                    ),
                ],
                directories=[],
            )
        ),
        template_files=TemplateFiles(files=[]),
        compatibility=TemplateCompatibility(
            min_python_version="3.9.6", supported_os=["macOS", "Linux", "Windows"]
        ),
    )


def create_mock_python_library_template() -> Template:
    """Create a mock Python library template."""
    from create_project.templates.schema.template import (
        TemplateCompatibility,
        TemplateFiles,
    )

    return Template(
        metadata=TemplateMetadata(
            name="Python Library/Package",
            description="Reusable Python library for distribution",
            version="1.0.0",
            category="library",
            tags=["library", "package", "pypi"],
            author="Test Author",
        ),
        configuration=TemplateConfiguration(schema_version="1.0.0"),
        variables=[
            TemplateVariable(
                name="project_name",
                type=VariableType.STRING,
                description="Name of the library",
                required=True,
                validation_rules=[
                    ValidationRule(
                        rule_type="pattern",
                        value="^[a-zA-Z][a-zA-Z0-9_-]*$",
                        message="Must be valid Python package name",
                    )
                ],
            ),
            TemplateVariable(
                name="description",
                type=VariableType.STRING,
                description="Library description",
                required=True,
            ),
            TemplateVariable(
                name="author",
                type=VariableType.STRING,
                description="Author name",
                required=True,
            ),
            TemplateVariable(
                name="author_email",
                type=VariableType.EMAIL,
                description="Author email",
                required=True,
            ),
        ],
        structure=ProjectStructure(
            root_directory=DirectoryItem(
                name="{{project_name}}",
                files=[
                    FileItem(
                        name="pyproject.toml",
                        content='[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n\n[project]\nname = "{{project_name}}"\nversion = "0.1.0"\ndescription = "{{description}}"\nauthors = [{name = "{{author}}", email = "{{author_email}}"}]\n',
                    ),
                    FileItem(
                        name="README.md",
                        content="# {{project_name}}\n\n{{description}}\n\n## Installation\n\n```bash\npip install {{project_name}}\n```\n",
                    ),
                    FileItem(
                        name=".gitignore",
                        content="__pycache__/\n*.py[cod]\n*$py.class\n.Python\nbuild/\ndist/\n*.egg-info/\n.pytest_cache/\n.mypy_cache/\n.ruff_cache/\n.venv/\nvenv/\n",
                    ),
                ],
                directories=[
                    DirectoryItem(
                        name="src",
                        files=[],
                        directories=[
                            DirectoryItem(
                                name="{{project_name}}",
                                files=[
                                    FileItem(
                                        name="__init__.py",
                                        content='"""{{project_name}} - {{description}}"""\n\n__version__ = "0.1.0"\n',
                                    )
                                ],
                            )
                        ],
                    ),
                    DirectoryItem(
                        name="tests",
                        files=[
                            FileItem(name="__init__.py", content=""),
                            FileItem(
                                name="test_{{project_name}}.py",
                                content='def test_import():\n    import {{project_name}}\n    assert {{project_name}}.__version__ == "0.1.0"\n',
                            ),
                        ],
                    ),
                ],
            )
        ),
        template_files=TemplateFiles(files=[]),
        compatibility=TemplateCompatibility(
            min_python_version="3.9.6", supported_os=["macOS", "Linux", "Windows"]
        ),
    )


def create_mock_cli_template() -> Template:
    """Create a mock CLI application template."""
    from create_project.templates.schema.template import (
        TemplateCompatibility,
        TemplateFiles,
    )

    return Template(
        metadata=TemplateMetadata(
            name="CLI Application (Single Package)",
            description="Command-line application packaged as installable Python package",
            version="1.0.0",
            category="cli",
            tags=["cli", "command-line", "package"],
            author="Test Author",
        ),
        configuration=TemplateConfiguration(schema_version="1.0.0"),
        variables=[
            TemplateVariable(
                name="project_name",
                type=VariableType.STRING,
                description="Name of the CLI project",
                required=True,
            ),
            TemplateVariable(
                name="cli_name",
                type=VariableType.STRING,
                description="Name of the CLI command",
                required=True,
            ),
            TemplateVariable(
                name="main_command",
                type=VariableType.STRING,
                description="Main command function name",
                required=True,
                default="main",
            ),
            TemplateVariable(
                name="description",
                type=VariableType.STRING,
                description="CLI description",
                required=False,
                default="A command-line tool",
            ),
        ],
        structure=ProjectStructure(
            root_directory=DirectoryItem(
                name="{{project_name}}",
                files=[
                    FileItem(
                        name="pyproject.toml",
                        content='[project]\nname = "{{project_name}}"\nversion = "0.1.0"\n\n[project.scripts]\n{{cli_name}} = "{{project_name}}.cli:{{main_command}}"\n',
                    )
                ],
                directories=[
                    DirectoryItem(
                        name="{{project_name}}",
                        files=[
                            FileItem(name="__init__.py", content=""),
                            FileItem(
                                name="cli.py",
                                content="def {{main_command}}():\n    print('{{cli_name}} CLI')\n",
                            ),
                        ],
                    )
                ],
            )
        ),
        template_files=TemplateFiles(files=[]),
        compatibility=TemplateCompatibility(
            min_python_version="3.9.6", supported_os=["macOS", "Linux", "Windows"]
        ),
    )


# Mapping of template names to factory functions
MOCK_TEMPLATES: Dict[str, Any] = {
    "One-off Script": create_mock_one_off_script_template,
    "Python Library/Package": create_mock_python_library_template,
    "CLI Application (Single Package)": create_mock_cli_template,
}


def get_mock_template(name: str) -> Template:
    """Get a mock template by name.

    Args:
        name: Template name

    Returns:
        Mock Template object

    Raises:
        ValueError: If template name not found
    """
    if name not in MOCK_TEMPLATES:
        raise ValueError(
            f"Mock template '{name}' not found. Available: {list(MOCK_TEMPLATES.keys())}"
        )

    return MOCK_TEMPLATES[name]()

# ABOUTME: Tests for the project type selection wizard step
# ABOUTME: Verifies template loading, selection, and preview functionality

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from create_project.gui.steps.project_type import ProjectTypeStep
from create_project.templates.schema.template import Template, TemplateCompatibility
from create_project.templates.schema.base_template import TemplateMetadata, TemplateCategory
from create_project.templates.schema.structure import ProjectStructure, DirectoryItem, FileItem


@pytest.fixture
def mock_templates():
    """Create mock template data."""
    return [
        ("python_basic", Template(
            metadata=TemplateMetadata(
                name="Basic Python Project",
                description="A simple Python project structure",
                version="1.0.0",
                category=TemplateCategory.SCRIPT,
                tags=["python", "basic"],
                author="Test Author"
            ),
            structure=ProjectStructure(
                root_directory=DirectoryItem(
                    name="project_root",
                    directories=[
                        DirectoryItem(
                            name="src",
                            files=[
                                FileItem(name="__init__.py")
                            ]
                        )
                    ],
                    files=[
                        FileItem(name="README.md")
                    ]
                )
            )
        )),
        ("python_package", Template(
            metadata=TemplateMetadata(
                name="Python Package", 
                description="A complete Python package with testing and CI/CD",
                version="1.0.0",
                category=TemplateCategory.LIBRARY,
                tags=["python", "package", "testing"],
                author="Test Author"
            ),
            structure=ProjectStructure(
                root_directory=DirectoryItem(
                    name="project_root",
                    directories=[
                        DirectoryItem(name="src"),
                        DirectoryItem(name="tests")
                    ],
                    files=[
                        FileItem(name="pyproject.toml")
                    ]
                )
            ),
            compatibility=TemplateCompatibility(
                dependencies=["pytest", "black", "mypy"]
            )
        ))
    ]


@pytest.fixture
def mock_wizard(mock_template_engine):
    """Create a mock wizard with template engine."""
    wizard = MagicMock()
    wizard.template_engine = mock_template_engine
    
    # Mock wizard data
    wizard_data = MagicMock()
    wizard.data = wizard_data
    
    return wizard


@pytest.fixture
def project_type_step(qtbot, mock_wizard, mock_templates):
    """Create ProjectTypeStep with mock wizard."""
    # Configure mock wizard
    mock_wizard.template_engine.list_templates.return_value = mock_templates
    
    step = ProjectTypeStep()
    # Mock the wizard() method to return our mock wizard
    step.wizard = MagicMock(return_value=mock_wizard)
    qtbot.addWidget(step)
    
    # Manually trigger template loading since wizard won't be properly connected
    step.load_templates()
    
    return step


def test_project_type_step_initialization(project_type_step):
    """Test step initializes correctly."""
    assert project_type_step.title() == "Select Project Type"
    assert project_type_step.subTitle() == "Choose a template for your new project"
    assert project_type_step.template_list is not None
    assert project_type_step.preview_browser is not None


def test_load_templates(project_type_step, mock_templates):
    """Test templates are loaded into the list."""
    # Verify templates loaded
    assert project_type_step.template_list.count() == 2
    
    # Check first template
    item = project_type_step.template_list.item(0)
    assert item.text() == "Basic Python Project"
    assert item.data(Qt.ItemDataRole.UserRole) == "python_basic"
    
    # Check second template
    item = project_type_step.template_list.item(1)
    assert item.text() == "Python Package"
    assert item.data(Qt.ItemDataRole.UserRole) == "python_package"


def test_template_selection(project_type_step, qtbot):
    """Test selecting a template updates preview."""
    # Select second template
    project_type_step.template_list.setCurrentRow(1)
    
    # Check preview updated
    preview_html = project_type_step.preview_browser.toHtml()
    assert "Python Package" in preview_html
    assert "complete Python package" in preview_html
    assert "pytest" in preview_html
    assert "black" in preview_html
    
    # Check wizard data updated
    wizard = project_type_step.wizard()
    assert wizard.data.template_id == "python_package"


def test_validation_no_selection(project_type_step):
    """Test validation fails when no template selected."""
    # Clear selection
    project_type_step.template_list.clearSelection()
    project_type_step.template_list.setCurrentItem(None)
    
    # Validation should fail
    assert not project_type_step.validate_page()


def test_validation_with_selection(project_type_step):
    """Test validation passes with template selected."""
    # Select first template
    project_type_step.template_list.setCurrentRow(0)
    
    # Validation should pass
    assert project_type_step.validate_page()
    
    # Check wizard data updated
    wizard = project_type_step.wizard()
    assert wizard.data.template_id == "python_basic"


def test_structure_formatting(project_type_step):
    """Test project structure is formatted correctly."""
    # Select first template with nested structure
    project_type_step.template_list.setCurrentRow(0)
    
    # Check structure formatting in preview
    preview_html = project_type_step.preview_browser.toHtml()
    assert "src/" in preview_html
    assert "__init__.py" in preview_html
    assert "README.md" in preview_html


def test_error_handling(project_type_step, qtbot):
    """Test error handling when template loading fails."""
    # First ensure we have templates loaded
    assert project_type_step.template_list.count() == 2
    
    # Make template loading fail
    wizard = project_type_step.wizard()
    wizard.template_engine.list_templates.side_effect = Exception("Failed to load")
    
    # Reload templates
    project_type_step.load_templates()
    
    # Should show error and list should be cleared (in real app would show message box)
    assert project_type_step.template_list.count() == 0
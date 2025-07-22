# ABOUTME: Tests for the Review and Create wizard step
# ABOUTME: Verifies summary display, project structure preview, and creation trigger

"""Tests for the Review and Create wizard step."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem

from create_project.gui.steps.review import CollapsibleSection, ReviewStep
from create_project.templates.schema.base_template import TemplateMetadata


@pytest.fixture
def review_step(qtbot, mock_config_manager, mock_template_engine):
    """Create a ReviewStep instance for testing."""
    step = ReviewStep(mock_config_manager, mock_template_engine)
    qtbot.addWidget(step)
    return step


@pytest.fixture
def sample_wizard_data():
    """Sample wizard data for testing."""
    return {
        "project_name": "test_project",
        "author": "Test Author",
        "version": "1.0.0",
        "description": "A test project",
        "base_path": "/home/user/projects",
        "template_type": "python_library",
        "additional_options": {
            "git_init": True,
            "venv_tool": "uv",
            "license": "MIT",
            "python_version": "3.9",
        },
    }


@pytest.fixture
def mock_template():
    """Create a mock template with structure."""
    template = MagicMock()
    template.metadata = TemplateMetadata(
        name="Python Library/Package",
        description="A Python library template",
        tags=["python", "library"],
    )
    template.structure = {
        "src": {
            "{{project_name}}": {
                "__init__.py": "",
                "main.py": "# Main module",
            }
        },
        "tests": {
            "__init__.py": "",
            "test_main.py": "# Test file",
        },
        "README.md": "# {{project_name}}",
        "pyproject.toml": "# Config file",
    }
    return template


class TestReviewStep:
    """Test the ReviewStep class."""

    def test_initialization(self, review_step):
        """Test ReviewStep initialization."""
        assert review_step is not None
        assert review_step._basic_section is not None
        assert review_step._location_section is not None
        assert review_step._options_section is not None
        assert review_step._structure_tree is not None
        assert review_step._create_button is not None

    def test_set_wizard_data_basic_info(self, review_step, sample_wizard_data):
        """Test setting wizard data updates basic information display."""
        review_step.set_wizard_data(sample_wizard_data)

        # Check basic info content
        basic_html = review_step._basic_content.toHtml()
        assert "test_project" in basic_html
        assert "Test Author" in basic_html
        assert "1.0.0" in basic_html
        assert "A test project" in basic_html

    def test_set_wizard_data_location(self, review_step, sample_wizard_data):
        """Test setting wizard data updates location display."""
        review_step.set_wizard_data(sample_wizard_data)

        # Check location content
        location_html = review_step._location_content.toHtml()
        assert "/home/user/projects/test_project" in location_html

    def test_set_wizard_data_existing_directory_warning(
        self, review_step, sample_wizard_data, tmp_path
    ):
        """Test warning display for existing directory."""
        # Use real temporary path
        base_path = tmp_path
        project_path = base_path / "test_project"
        project_path.mkdir()

        sample_wizard_data["base_path"] = str(base_path)
        review_step.set_wizard_data(sample_wizard_data)

        # Check for warning
        location_html = review_step._location_content.toHtml()
        assert "Directory already exists" in location_html

    def test_set_wizard_data_options(
        self, review_step, sample_wizard_data, mock_template_engine, mock_template
    ):
        """Test setting wizard data updates options display."""
        # Mock template loading
        mock_template_engine.get_template.return_value = mock_template

        review_step.set_wizard_data(sample_wizard_data)

        # Check options content
        options_html = review_step._options_content.toHtml()
        assert "Python Library/Package" in options_html
        assert "Initialize Git: Yes" in options_html
        assert "Virtual Environment: uv" in options_html
        assert "License: MIT" in options_html
        assert "Python Version: 3.9" in options_html

    def test_structure_preview(
        self, review_step, sample_wizard_data, mock_template_engine, mock_template
    ):
        """Test project structure tree preview."""
        # Mock template loading
        mock_template_engine.get_template.return_value = mock_template

        review_step.set_wizard_data(sample_wizard_data)

        # Check tree structure
        assert review_step._structure_tree.topLevelItemCount() == 1

        # Check root item
        root = review_step._structure_tree.topLevelItem(0)
        assert root.text(0) == "test_project"

        # Check structure (simplified check)
        # Should have src/, tests/, README.md, pyproject.toml
        item_texts = []
        for i in range(root.childCount()):
            item_texts.append(root.child(i).text(0))

        assert any("src/" in text for text in item_texts)
        assert any("tests/" in text for text in item_texts)
        assert any("README.md" in text for text in item_texts)
        assert any("pyproject.toml" in text for text in item_texts)

    def test_validation(self, review_step, sample_wizard_data):
        """Test validation logic."""
        # Should fail without data
        assert not review_step.validate()

        # Should pass with complete data
        review_step.set_wizard_data(sample_wizard_data)
        assert review_step.validate()

        # Should fail with missing required field
        incomplete_data = sample_wizard_data.copy()
        del incomplete_data["project_name"]
        review_step.set_wizard_data(incomplete_data)
        assert not review_step.validate()

    def test_create_button_signal(self, review_step, qtbot):
        """Test create button emits signal."""
        with qtbot.waitSignal(review_step.create_requested, timeout=1000):
            review_step._create_button.click()

    def test_no_description_handling(self, review_step, sample_wizard_data):
        """Test handling of missing description."""
        sample_wizard_data["description"] = None
        review_step.set_wizard_data(sample_wizard_data)

        basic_html = review_step._basic_content.toHtml()
        assert "No description" in basic_html

    def test_no_venv_tool_handling(self, review_step, sample_wizard_data):
        """Test handling of no virtual environment selection."""
        sample_wizard_data["additional_options"]["venv_tool"] = "none"
        review_step.set_wizard_data(sample_wizard_data)

        options_html = review_step._options_content.toHtml()
        assert "No virtual environment" in options_html


class TestCollapsibleSection:
    """Test the CollapsibleSection widget."""

    def test_initialization(self, qtbot):
        """Test CollapsibleSection initialization."""
        section = CollapsibleSection("Test Section")
        qtbot.addWidget(section)

        assert section._header.text() == "Test Section"
        assert section._header.isChecked()  # Expanded by default
        assert section._content_frame.isVisible()

    def test_toggle_collapse(self, qtbot):
        """Test collapsing and expanding."""
        section = CollapsibleSection("Test Section")
        qtbot.addWidget(section)

        # Initially expanded
        assert section._content_frame.isVisible()

        # Click to collapse
        section._header.click()
        assert not section._content_frame.isVisible()

        # Click to expand
        section._header.click()
        assert section._content_frame.isVisible()

    def test_add_content(self, qtbot):
        """Test adding content to section."""
        section = CollapsibleSection("Test Section")
        qtbot.addWidget(section)

        # Add a label
        from PyQt6.QtWidgets import QLabel

        label = QLabel("Test Content")
        section.add_content(label)

        # Check content was added
        assert section._content_layout.count() == 1
        assert section._content_layout.itemAt(0).widget().text() == "Test Content"


@pytest.mark.skip(reason="Integration test requiring full wizard")
class TestReviewStepIntegration:
    """Integration tests for ReviewStep with wizard."""

    def test_wizard_integration(self, qtbot, project_wizard):
        """Test integration with full wizard."""
        # Navigate to review step
        for _ in range(4):  # Review is 5th step
            project_wizard.next()

        # Get review page
        review_page = project_wizard.currentPage()
        assert isinstance(review_page, ReviewStep)

        # Check data was populated
        # This would require full wizard data flow setup
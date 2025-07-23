# ABOUTME: Tests for the Review step implementation
# ABOUTME: Verifies summary display, structure preview, and create button functionality

"""
Tests for the Review step.

Tests the review step functionality including:
- Summary display of all selections
- Project structure preview
- Create button triggering generation
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtCore import Qt

from create_project.gui.steps.review import ReviewStep
from create_project.gui.wizard.wizard import ProjectWizard, WizardData
from create_project.templates.schema import Template, ProjectStructure, DirectoryItem, FileItem, TemplateMetadata, TemplateCategory


class TestReviewStep:
    """Test the review step implementation."""
    
    @pytest.fixture
    def mock_wizard(self):
        """Create a mock wizard with test data."""
        wizard = Mock(spec=ProjectWizard)
        wizard.data = WizardData(
            template_id="python-library",
            template_name="Python Library",
            project_name="test_project",
            author="John Doe",
            version="1.0.0",
            description="A test project",
            location=Path("/home/user/projects"),
            license="MIT",
            init_git=True,
            create_venv=True,
            venv_tool="uv",
            additional_options={
                "include_tests": True,
                "include_docs": False
            }
        )
        
        # Mock template engine and loader
        wizard.template_engine = Mock()
        wizard.template_loader = Mock()
        wizard.template_loader.list_templates.return_value = []  # Empty list by default
        
        return wizard
    
    def test_step_initialization(self, qtbot, mock_wizard):
        """Test review step initializes correctly."""
        step = ReviewStep(None)  # Create without parent
        step.wizard = Mock(return_value=mock_wizard)  # Mock the wizard method
        qtbot.addWidget(step)
        
        assert step.title() == "Review and Create"
        assert step.subTitle() == "Review your choices and create the project"
        assert step.summary_text is not None
        assert step.structure_tree is not None
        assert step.create_button is not None
    
    def test_summary_display(self, qtbot, mock_wizard):
        """Test summary displays all wizard data correctly."""
        step = ReviewStep(None)
        step.wizard = Mock(return_value=mock_wizard)
        qtbot.addWidget(step)
        
        # Initialize the page
        step.initializePage()
        
        # Get summary HTML
        summary_html = step.summary_text.toHtml()
        
        # Verify all data is displayed
        assert "Python Library" in summary_html
        assert "test_project" in summary_html
        assert "John Doe" in summary_html
        assert "1.0.0" in summary_html
        assert "A test project" in summary_html
        assert "/home/user/projects/test_project" in summary_html
        assert "MIT" in summary_html
        assert "Initialize Git: Yes" in summary_html
        assert "Create Virtual Environment: Yes" in summary_html
        assert "Virtual Environment Tool: uv" in summary_html
        assert "include_tests: True" in summary_html
        assert "include_docs: False" in summary_html
    
    def test_structure_preview(self, qtbot, mock_wizard):
        """Test project structure preview displays correctly."""
        step = ReviewStep(None)
        step.wizard = Mock(return_value=mock_wizard)
        qtbot.addWidget(step)
        
        # Create test template
        test_template = Template(
            metadata=TemplateMetadata(
                name="Test Template",
                description="Test",
                version="1.0.0",
                category=TemplateCategory.LIBRARY,
                author="Test Author"
            ),
            structure=ProjectStructure(
                root_directory=DirectoryItem(
                    name="project_root",
                    directories=[
                        DirectoryItem(
                            name='src',
                            files=[
                                FileItem(name='__init__.py', content=''),
                                FileItem(name='main.py', content='')
                            ]
                        ),
                        DirectoryItem(
                            name='tests',
                            files=[
                                FileItem(name='test_main.py', content='')
                            ]
                        )
                    ],
                    files=[
                        FileItem(name='README.md', content=''),
                        FileItem(name='setup.py', content='')
                    ]
                )
            ),
            variables=[]
        )
        
        # Configure mocks
        mock_wizard.template_loader.list_templates.return_value = [{
            'template_id': 'python-library',
            'file_path': 'test.yaml'
        }]
        mock_wizard.template_engine.load_template.return_value = test_template
        
        # Initialize page
        step.initializePage()
        
        # Verify tree structure
        assert step.structure_tree.topLevelItemCount() == 1
        
        root_item = step.structure_tree.topLevelItem(0)
        assert root_item.text(0) == "test_project"
        
        # Check children (should have 2 directories and 2 files)
        assert root_item.childCount() == 4
        
        # Find and verify directories
        items = [root_item.child(i).text(0) for i in range(root_item.childCount())]
        assert "📁 src" in items
        assert "📁 tests" in items
        assert "📄 README.md" in items
        assert "📄 setup.py" in items
    
    def test_create_button_signal(self, qtbot, mock_wizard):
        """Test create button emits signal."""
        step = ReviewStep(None)
        step.wizard = Mock(return_value=mock_wizard)
        qtbot.addWidget(step)
        
        # Track signal emissions
        signal_emitted = []
        step.create_clicked.connect(lambda: signal_emitted.append(True))
        
        # Click create button
        step.create_button.click()
        
        # Verify signal emitted
        assert len(signal_emitted) == 1
        assert signal_emitted[0] is True
    
    def test_step_validation(self, qtbot, mock_wizard):
        """Test step validation always passes."""
        step = ReviewStep(None)
        step.wizard = Mock(return_value=mock_wizard)
        qtbot.addWidget(step)
        
        # Review step should always be valid
        assert step.validate_step() is True
        assert step.isComplete() is True
    
    def test_no_template_selected(self, qtbot):
        """Test behavior when no template is selected."""
        wizard = Mock(spec=ProjectWizard)
        wizard.data = WizardData()  # Empty data
        wizard.template_loader = None
        
        step = ReviewStep(None)
        step.wizard = Mock(return_value=wizard)
        qtbot.addWidget(step)
        
        # Initialize page with no data
        step.initializePage()
        
        # Should not crash and tree should be empty
        assert step.structure_tree.topLevelItemCount() == 0
    
    def test_structure_preview_with_nested_directories(self, qtbot, mock_wizard):
        """Test structure preview with deeply nested directories."""
        # Create complex template structure
        complex_template = Template(
            metadata=TemplateMetadata(
                name="Complex Template",
                description="Test",
                version="1.0.0",
                category=TemplateCategory.LIBRARY,
                author="Test Author"
            ),
            structure=ProjectStructure(
                root_directory=DirectoryItem(
                    name="project_root",
                    directories=[
                        DirectoryItem(
                            name='src',
                            directories=[
                                DirectoryItem(
                                    name='core',
                                    files=[
                                        FileItem(name='engine.py', content='')
                                    ]
                                ),
                                DirectoryItem(
                                    name='utils',
                                    files=[
                                        FileItem(name='helpers.py', content='')
                                    ]
                                )
                            ],
                            files=[
                                FileItem(name='__init__.py', content='')
                            ]
                        )
                    ]
                )
            ),
            variables=[]
        )
        
        # Configure mocks
        mock_wizard.template_loader.list_templates.return_value = [{
            'template_id': 'python-library',
            'file_path': 'test.yaml'
        }]
        mock_wizard.template_engine.load_template.return_value = complex_template
        
        # Create step
        step = ReviewStep(None)
        step.wizard = Mock(return_value=mock_wizard)
        qtbot.addWidget(step)
        
        # Initialize page
        step.initializePage()
        
        # Verify nested structure
        root = step.structure_tree.topLevelItem(0)
        src_item = None
        
        # Find src directory
        for i in range(root.childCount()):
            if "src" in root.child(i).text(0):
                src_item = root.child(i)
                break
        
        assert src_item is not None
        assert src_item.childCount() == 3  # core, utils, __init__.py
        
        # Check for nested directories
        nested_items = [src_item.child(i).text(0) for i in range(src_item.childCount())]
        assert any("core" in item for item in nested_items)
        assert any("utils" in item for item in nested_items)
        assert any("__init__.py" in item for item in nested_items)
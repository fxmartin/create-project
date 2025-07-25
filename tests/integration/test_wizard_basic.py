# ABOUTME: Basic integration test for wizard workflow validation
# ABOUTME: Tests that the wizard can be navigated without errors

"""
Basic integration test for wizard workflow validation.

This test ensures the wizard can be instantiated and navigated
through all pages without errors.
"""

import pytest
from PyQt6.QtWidgets import QWizard

from create_project.config.config_manager import ConfigManager
from create_project.templates.engine import TemplateEngine
from create_project.templates.loader import TemplateLoader
from create_project.gui.wizard.wizard import ProjectWizard


@pytest.mark.integration
def test_wizard_creation_and_navigation(qtbot):
    """Test that wizard can be created and navigated successfully."""
    # Create config manager
    config = ConfigManager()
    config.set_setting("templates.builtin_path", "create_project/templates/builtin")
    
    # Create dependencies
    template_engine = TemplateEngine(config)
    template_loader = TemplateLoader(config)
    
    # Create wizard - this should not raise any errors
    wizard = ProjectWizard(config, template_engine, template_loader)
    qtbot.addWidget(wizard)
    
    # Verify wizard was created
    assert wizard is not None
    assert isinstance(wizard, QWizard)
    
    # Verify pages were added
    page_ids = wizard.pageIds()
    assert len(page_ids) >= 5  # Should have at least 5 pages
    
    # Show wizard
    wizard.show()
    
    # Verify we can get the current page
    current_page = wizard.currentPage()
    assert current_page is not None
    
    # Test navigation - fill minimum data and navigate
    pages_visited = 0
    max_pages = 10  # Safety limit
    
    while pages_visited < max_pages and wizard.currentId() != -1:
        current_page = wizard.currentPage()
        page_title = current_page.title() if current_page else "Unknown"
        
        # Fill required fields based on page type
        if hasattr(current_page, 'name_edit'):
            current_page.name_edit.setText("test_project")
        if hasattr(current_page, 'author_edit'):
            current_page.author_edit.setText("Test Author")
        if hasattr(current_page, 'location_edit'):
            current_page.location_edit.setText("/tmp/test")
            
        # Check if we can go to next page
        if wizard.currentId() < wizard.pageIds()[-1]:
            wizard.next()
            pages_visited += 1
        else:
            # We're on the last page
            break
    
    # Verify we visited multiple pages
    assert pages_visited >= 4  # Should visit at least 4 pages
    
    # Close wizard properly
    wizard.close()


@pytest.mark.integration 
def test_wizard_with_actual_project_creation(qtbot, tmp_path):
    """Test wizard with mock project generation."""
    from unittest.mock import Mock, patch
    
    # Setup
    config = ConfigManager()
    config.set_setting("templates.builtin_path", "create_project/templates/builtin")
    
    template_engine = TemplateEngine(config)
    template_loader = TemplateLoader(config)
    
    wizard = ProjectWizard(config, template_engine, template_loader)
    qtbot.addWidget(wizard)
    wizard.show()
    
    # Navigate and fill wizard
    # Page 1: Template selection (auto-selects first)
    wizard.next()
    
    # Page 2: Basic info
    page = wizard.currentPage()
    if hasattr(page, 'name_edit'):
        page.name_edit.setText("integration_test_project")
    if hasattr(page, 'author_edit'):
        page.author_edit.setText("Integration Tester")
    if hasattr(page, 'version_edit'):
        page.version_edit.setText("1.0.0")
    wizard.next()
    
    # Page 3: Location
    page = wizard.currentPage()
    if hasattr(page, 'location_edit'):
        page.location_edit.setText(str(tmp_path))
    wizard.next()
    
    # Page 4: Options (use defaults)
    wizard.next()
    
    # Page 5: Review
    # Should now be on review page
    assert wizard.currentPage() is not None
    
    # Mock the project generation
    with patch.object(wizard, '_generate_project') as mock_generate:
        # Accept wizard (triggers generation)
        wizard.accept()
        
        # Verify generation was called
        mock_generate.assert_called_once()
    
    # Verify wizard closed properly
    assert wizard.result() in [QWizard.DialogCode.Accepted, 1]
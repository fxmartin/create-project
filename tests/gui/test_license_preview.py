# ABOUTME: Test suite for license preview dialog widget
# ABOUTME: Tests license display, copy functionality, and error handling

"""Test suite for the license preview dialog."""

from unittest.mock import Mock, patch

import pytest

from create_project.gui.widgets.license_preview import LicensePreviewDialog


@pytest.fixture
def mock_license_manager():
    """Create a mock license manager."""
    manager = Mock()
    manager.list_licenses.return_value = [
        {"id": "MIT", "name": "MIT License"},
        {"id": "Apache-2.0", "name": "Apache License 2.0"},
        {"id": "GPL-3.0", "name": "GNU General Public License v3.0"},
    ]
    manager.get_license_text.return_value = """MIT License

Copyright (c) [year] [fullname]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
    return manager


@pytest.fixture
def license_dialog(qtbot, mock_license_manager):
    """Create a LicensePreviewDialog instance."""
    with patch(
        "create_project.licenses.manager.LicenseManager",
        return_value=mock_license_manager,
    ):
        dialog = LicensePreviewDialog("MIT")
        qtbot.addWidget(dialog)
        return dialog


class TestLicensePreviewDialog:
    """Test suite for LicensePreviewDialog class."""

    def test_initialization(self, qtbot, mock_license_manager):
        """Test dialog initialization."""
        with patch(
            "create_project.licenses.manager.LicenseManager",
            return_value=mock_license_manager,
        ):
            dialog = LicensePreviewDialog("MIT")
            qtbot.addWidget(dialog)

            assert dialog.windowTitle() == "License Preview"
            assert dialog.isModal()
            assert dialog.license_id == "MIT"
            assert hasattr(dialog, "header_label")
            assert hasattr(dialog, "text_browser")
            assert hasattr(dialog, "copy_button")

    def test_license_loading(self, license_dialog, mock_license_manager):
        """Test that license text is loaded correctly."""
        # Check header
        assert license_dialog.header_label.text() == "MIT License"

        # Check that license text is displayed
        displayed_text = license_dialog.text_browser.toPlainText()
        assert "MIT License" in displayed_text
        assert "Permission is hereby granted" in displayed_text
        assert mock_license_manager.get_license_text.called_with("MIT")

    def test_license_not_found(self, qtbot, mock_license_manager):
        """Test handling of license not found."""
        mock_license_manager.get_license_text.return_value = None

        with patch(
            "create_project.licenses.manager.LicenseManager",
            return_value=mock_license_manager,
        ):
            dialog = LicensePreviewDialog("UNKNOWN")
            qtbot.addWidget(dialog)

            displayed_text = dialog.text_browser.toPlainText()
            assert "License text not found" in displayed_text

    def test_loading_error(self, qtbot, mock_license_manager):
        """Test handling of loading errors."""
        mock_license_manager.get_license_text.side_effect = Exception("Load error")

        with patch(
            "create_project.licenses.manager.LicenseManager",
            return_value=mock_license_manager,
        ):
            dialog = LicensePreviewDialog("MIT")
            qtbot.addWidget(dialog)

            displayed_text = dialog.text_browser.toPlainText()
            assert "Failed to load license" in displayed_text

    def test_copy_button(self, qtbot, license_dialog):
        """Test copy button functionality."""
        # Mock clipboard
        mock_clipboard = Mock()
        mock_clipboard.setText = Mock()

        with patch(
            "PyQt6.QtWidgets.QApplication.clipboard", return_value=mock_clipboard
        ):
            # Click copy button
            license_dialog.copy_button.click()

            # Check that text was copied
            mock_clipboard.setText.assert_called_once()
            copied_text = mock_clipboard.setText.call_args[0][0]
            assert "MIT License" in copied_text

            # Check button text changed
            assert license_dialog.copy_button.text() == "Copied!"

    def test_text_browser_properties(self, license_dialog):
        """Test text browser properties."""
        text_browser = license_dialog.text_browser

        # Should be read-only
        assert text_browser.isReadOnly()

        # Should have monospace font
        font = text_browser.font()
        assert font.styleHint() == font.StyleHint.Monospace

        # Should open external links
        assert text_browser.openExternalLinks()

    def test_window_size(self, license_dialog):
        """Test window size."""
        size_hint = license_dialog.sizeHint()
        assert size_hint.width() == 800
        assert size_hint.height() == 600

    def test_close_button(self, qtbot, license_dialog):
        """Test close button functionality."""
        # Find close button in button box
        close_button = license_dialog.button_box.button(
            license_dialog.button_box.StandardButton.Close
        )
        assert close_button is not None

        # Click should close dialog
        with qtbot.waitSignal(license_dialog.finished):
            close_button.click()

    def test_context_menu(self, license_dialog):
        """Test context menu has copy action."""
        actions = license_dialog.text_browser.actions()
        assert len(actions) > 0

        # Should have "Copy All" action
        copy_action = next((a for a in actions if a.text() == "Copy All"), None)
        assert copy_action is not None

    def test_header_formatting(self, license_dialog):
        """Test header label formatting."""
        header = license_dialog.header_label
        font = header.font()

        # Should be larger and bold
        assert font.pointSize() == 14
        assert font.bold()

    @pytest.mark.skip(reason="Requires clipboard access")
    def test_copy_button_text_reset(self, qtbot, license_dialog):
        """Test that copy button text resets after copying."""
        # Click copy button
        license_dialog.copy_button.click()

        # Should show "Copied!"
        assert license_dialog.copy_button.text() == "Copied!"

        # Wait for timer to reset text
        qtbot.wait(2500)

        # Should reset to original text
        assert license_dialog.copy_button.text() == "Copy to Clipboard"

    def test_license_with_unknown_id(self, qtbot, mock_license_manager):
        """Test handling of license ID not in list."""
        mock_license_manager.list_licenses.return_value = []

        with patch(
            "create_project.licenses.manager.LicenseManager",
            return_value=mock_license_manager,
        ):
            dialog = LicensePreviewDialog("CUSTOM")
            qtbot.addWidget(dialog)

            # Should still show the ID in header
            assert dialog.header_label.text() == "CUSTOM License"

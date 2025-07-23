# ABOUTME: Test suite for style management system
# ABOUTME: Tests theme support, color management, and stylesheet generation

"""Test suite for style management module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication

from create_project.resources.styles import (
    COLORS,
    FONTS,
    SIZES,
    SPACING,
    StyleManager,
    apply_theme,
    get_color,
    get_font,
    get_spacing,
    get_style_sheet,
    set_theme,
)


class TestStyleManager:
    """Test StyleManager class."""

    @pytest.fixture
    def style_manager(self) -> StyleManager:
        """Create StyleManager instance."""
        manager = StyleManager()
        manager._cache.clear()
        manager._theme = "light"
        return manager

    def test_singleton_instance(self) -> None:
        """Test that StyleManager is a singleton."""
        manager1 = StyleManager()
        manager2 = StyleManager()
        assert manager1 is manager2

    def test_get_color_light_theme(self, style_manager: StyleManager) -> None:
        """Test getting colors from light theme."""
        style_manager.set_theme("light")
        
        # Test primary color
        color = style_manager.get_color("primary")
        assert color == COLORS["light"]["primary"]
        
        # Test background color
        color = style_manager.get_color("background")
        assert color == COLORS["light"]["background"]

    def test_get_color_dark_theme(self, style_manager: StyleManager) -> None:
        """Test getting colors from dark theme."""
        style_manager.set_theme("dark")
        
        # Test primary color
        color = style_manager.get_color("primary")
        assert color == COLORS["dark"]["primary"]
        
        # Test background color
        color = style_manager.get_color("background")
        assert color == COLORS["dark"]["background"]

    def test_get_color_with_theme_override(self, style_manager: StyleManager) -> None:
        """Test getting color with theme override."""
        style_manager.set_theme("light")
        
        # Get dark theme color while in light theme
        color = style_manager.get_color("background", theme="dark")
        assert color == COLORS["dark"]["background"]

    def test_get_color_fallback(self, style_manager: StyleManager) -> None:
        """Test color fallback for unknown color names."""
        color = style_manager.get_color("non_existent_color")
        assert color == "#000000"

    def test_get_font(self, style_manager: StyleManager) -> None:
        """Test getting fonts."""
        # Default font
        font = style_manager.get_font()
        assert isinstance(font, QFont)
        assert font.pointSize() == FONTS["default"]["size"]
        
        # Heading font
        font = style_manager.get_font("heading")
        assert font.pointSize() == FONTS["heading"]["size"]
        assert font.weight() == QFont.Weight.Bold
        
        # Monospace font
        font = style_manager.get_font("monospace")
        assert font.pointSize() == FONTS["monospace"]["size"]

    def test_get_spacing(self, style_manager: StyleManager) -> None:
        """Test getting spacing values."""
        # Test each spacing size
        for size_name, value in SPACING.items():
            spacing = style_manager.get_spacing(size_name)
            assert spacing == value
        
        # Test default
        spacing = style_manager.get_spacing()
        assert spacing == SPACING["medium"]

    def test_get_size(self, style_manager: StyleManager) -> None:
        """Test getting size constants."""
        # Test each size
        for size_name, value in SIZES.items():
            size = style_manager.get_size(size_name)
            assert size == value
        
        # Test unknown size
        size = style_manager.get_size("unknown")
        assert size == 0

    def test_get_stylesheet_global(self, style_manager: StyleManager) -> None:
        """Test getting global stylesheet."""
        stylesheet = style_manager.get_stylesheet()
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 0
        
        # Check that it contains expected elements
        assert "QWidget" in stylesheet
        assert "QPushButton" in stylesheet
        assert "QLineEdit" in stylesheet
        
        # Check that it uses theme colors
        colors = COLORS[style_manager._theme]
        assert colors["primary"] in stylesheet
        assert colors["background"] in stylesheet

    def test_stylesheet_caching(self, style_manager: StyleManager) -> None:
        """Test that stylesheets are cached."""
        # Get stylesheet twice
        stylesheet1 = style_manager.get_stylesheet()
        stylesheet2 = style_manager.get_stylesheet()
        
        # Should be cached
        assert "light/global" in style_manager._cache
        assert stylesheet1 == stylesheet2

    def test_theme_change_clears_cache(self, style_manager: StyleManager) -> None:
        """Test that changing theme clears cache."""
        # Generate and cache stylesheet
        style_manager.get_stylesheet()
        assert len(style_manager._cache) > 0
        
        # Change theme
        style_manager.set_theme("dark")
        assert len(style_manager._cache) == 0

    @pytest.mark.skip(reason="Requires QApplication")
    def test_apply_palette(self, style_manager: StyleManager, qtbot) -> None:
        """Test applying palette to application."""
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        
        style_manager.set_theme("light")
        style_manager.apply_palette(app)
        
        palette = app.palette()
        
        # Check some colors
        window_color = palette.color(QPalette.ColorRole.Window)
        expected_color = QColor(COLORS["light"]["background"])
        assert window_color.name() == expected_color.name()


class TestStyleConvenienceFunctions:
    """Test convenience functions."""

    def test_get_color_function(self) -> None:
        """Test get_color convenience function."""
        with patch('create_project.resources.styles._manager.get_color') as mock_get:
            mock_get.return_value = "#FF0000"
            
            color = get_color("primary")
            mock_get.assert_called_once_with("primary")
            assert color == "#FF0000"

    def test_get_font_function(self) -> None:
        """Test get_font convenience function."""
        with patch('create_project.resources.styles._manager.get_font') as mock_get:
            mock_font = QFont()
            mock_get.return_value = mock_font
            
            font = get_font("heading")
            mock_get.assert_called_once_with("heading")
            assert font == mock_font

    def test_get_spacing_function(self) -> None:
        """Test get_spacing convenience function."""
        with patch('create_project.resources.styles._manager.get_spacing') as mock_get:
            mock_get.return_value = 16
            
            spacing = get_spacing("medium")
            mock_get.assert_called_once_with("medium")
            assert spacing == 16

    def test_get_style_sheet_function(self) -> None:
        """Test get_style_sheet convenience function."""
        with patch('create_project.resources.styles._manager.get_stylesheet') as mock_get:
            mock_get.return_value = "QWidget {}"
            
            stylesheet = get_style_sheet("button")
            mock_get.assert_called_once_with("button")
            assert stylesheet == "QWidget {}"

    def test_set_theme_function(self) -> None:
        """Test set_theme convenience function."""
        with patch('create_project.resources.styles._manager.set_theme') as mock_set:
            set_theme("dark")
            mock_set.assert_called_once_with("dark")

    @pytest.mark.skip(reason="Requires QApplication")
    def test_apply_theme_function(self) -> None:
        """Test apply_theme convenience function."""
        app = MagicMock()
        
        with patch('create_project.resources.styles._manager.apply_palette') as mock_palette:
            with patch('create_project.resources.styles._manager.get_stylesheet') as mock_style:
                mock_style.return_value = "QWidget {}"
                
                apply_theme(app)
                
                mock_palette.assert_called_once_with(app)
                app.setStyleSheet.assert_called_once_with("QWidget {}")


class TestStylesheetGeneration:
    """Test stylesheet generation."""

    def test_light_theme_stylesheet(self) -> None:
        """Test light theme stylesheet generation."""
        manager = StyleManager()
        manager.set_theme("light")
        
        stylesheet = manager.get_stylesheet()
        
        # Check light theme colors are used
        assert COLORS["light"]["primary"] in stylesheet
        assert COLORS["light"]["background"] in stylesheet
        assert COLORS["light"]["text_primary"] in stylesheet

    def test_dark_theme_stylesheet(self) -> None:
        """Test dark theme stylesheet generation."""
        manager = StyleManager()
        manager.set_theme("dark")
        
        stylesheet = manager.get_stylesheet()
        
        # Check dark theme colors are used
        assert COLORS["dark"]["primary"] in stylesheet
        assert COLORS["dark"]["background"] in stylesheet
        assert COLORS["dark"]["text_primary"] in stylesheet

    def test_stylesheet_structure(self) -> None:
        """Test that stylesheet has expected structure."""
        manager = StyleManager()
        stylesheet = manager.get_stylesheet()
        
        # Check major sections
        assert "/* Global Application Stylesheet */" in stylesheet
        assert "/* Buttons */" in stylesheet
        assert "/* Input fields */" in stylesheet
        assert "/* Lists and Trees */" in stylesheet
        assert "/* Labels */" in stylesheet
        assert "/* Group Boxes */" in stylesheet
        assert "/* Tabs */" in stylesheet
        assert "/* Progress bars */" in stylesheet
        assert "/* Scrollbars */" in stylesheet
        assert "/* Dialogs */" in stylesheet

    def test_stylesheet_selectors(self) -> None:
        """Test that stylesheet has expected selectors."""
        manager = StyleManager()
        stylesheet = manager.get_stylesheet()
        
        # Check widget selectors
        widgets = [
            "QWidget",
            "QPushButton",
            "QLineEdit",
            "QTextEdit",
            "QListWidget",
            "QTreeWidget",
            "QLabel",
            "QGroupBox",
            "QTabWidget",
            "QProgressBar",
            "QScrollBar",
            "QDialog",
            "QMessageBox",
        ]
        
        for widget in widgets:
            assert widget in stylesheet

    def test_stylesheet_properties(self) -> None:
        """Test that stylesheet uses defined constants."""
        manager = StyleManager()
        stylesheet = manager.get_stylesheet()
        
        # Check that sizes are used
        assert f"{SIZES['border_radius']}px" in stylesheet
        assert f"{SIZES['button_height']}px" in stylesheet
        assert f"{SIZES['input_height']}px" in stylesheet
        
        # Check that spacing is used
        assert f"{SPACING['small']}px" in stylesheet
        assert f"{SPACING['medium']}px" in stylesheet
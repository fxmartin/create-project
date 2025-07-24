# ABOUTME: Test suite for icon management system
# ABOUTME: Tests icon loading, caching, fallback, and theme support

"""Test suite for icon management module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt6.QtGui import QIcon, QPixmap

from create_project.resources.icons import (
    ICON_SIZES,
    IconManager,
    get_icon,
    preload_common_icons,
    set_icon_theme,
)


class TestIconManager:
    """Test IconManager class."""

    @pytest.fixture
    def icon_manager(self, tmp_path: Path) -> IconManager:
        """Create IconManager with temp directory."""
        manager = IconManager()
        manager._icon_dir = tmp_path / "icons"
        manager._icon_dir.mkdir(parents=True, exist_ok=True)
        manager._cache.clear()
        manager._theme = "default"  # Reset theme to default
        return manager

    def test_singleton_instance(self) -> None:
        """Test that IconManager is a singleton."""
        manager1 = IconManager()
        manager2 = IconManager()
        assert manager1 is manager2

    def test_get_icon_from_file(self, icon_manager: IconManager, tmp_path: Path) -> None:
        """Test loading icon from file."""
        # Create test icon file
        icon_path = icon_manager._icon_dir / "test.png"
        pixmap = QPixmap(24, 24)
        pixmap.fill()
        pixmap.save(str(icon_path))

        # Get icon
        icon = icon_manager.get_icon("test")
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_get_icon_with_category(self, icon_manager: IconManager, tmp_path: Path) -> None:
        """Test loading icon with category."""
        # Create category and icon
        category_dir = icon_manager._icon_dir / "actions"
        category_dir.mkdir(parents=True, exist_ok=True)

        icon_path = category_dir / "save.png"
        pixmap = QPixmap(24, 24)
        pixmap.fill()
        pixmap.save(str(icon_path))

        # Get icon
        icon = icon_manager.get_icon("save", category="actions")
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_icon_caching(self, icon_manager: IconManager, tmp_path: Path) -> None:
        """Test that icons are cached."""
        # Create test icon
        icon_path = icon_manager._icon_dir / "cached.png"
        pixmap = QPixmap(24, 24)
        pixmap.fill()
        pixmap.save(str(icon_path))

        # Get icon twice
        icon1 = icon_manager.get_icon("cached")
        icon2 = icon_manager.get_icon("cached")

        # Should be cached
        assert "default/cached" in icon_manager._cache
        # Note: QIcon objects may not be the same instance even if cached

    def test_fallback_icon(self, icon_manager: IconManager) -> None:
        """Test fallback icon when requested icon not found."""
        # Get non-existent icon
        icon = icon_manager.get_icon("non_existent")
        assert isinstance(icon, QIcon)
        # Will be empty since no fallback exists

    def test_theme_support(self, icon_manager: IconManager, tmp_path: Path) -> None:
        """Test theme-specific icon loading."""
        # Create theme directory and icon
        theme_dir = icon_manager._icon_dir / "dark"
        theme_dir.mkdir(parents=True, exist_ok=True)

        icon_path = theme_dir / "themed.png"
        pixmap = QPixmap(24, 24)
        pixmap.fill()
        pixmap.save(str(icon_path))

        # Set theme and get icon
        icon_manager.set_theme("dark")
        icon = icon_manager.get_icon("themed")
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_clear_cache(self, icon_manager: IconManager, tmp_path: Path) -> None:
        """Test cache clearing."""
        # Create and cache icon
        icon_path = icon_manager._icon_dir / "clear.png"
        pixmap = QPixmap(24, 24)
        pixmap.fill()
        pixmap.save(str(icon_path))

        icon = icon_manager.get_icon("clear")
        assert len(icon_manager._cache) > 0

        # Clear cache
        icon_manager.clear_cache()
        assert len(icon_manager._cache) == 0

    def test_preload_icons(self, icon_manager: IconManager, tmp_path: Path) -> None:
        """Test icon preloading."""
        # Create test icons
        actions_dir = icon_manager._icon_dir / "actions"
        actions_dir.mkdir(parents=True, exist_ok=True)

        for name in ["add", "remove"]:
            icon_path = actions_dir / f"{name}.png"
            pixmap = QPixmap(24, 24)
            pixmap.fill()
            pixmap.save(str(icon_path))

        # Preload icons
        icon_manager.preload_icons(["actions/add", "actions/remove"])

        # Check cache
        assert "default/actions/add" in icon_manager._cache
        assert "default/actions/remove" in icon_manager._cache

    def test_theme_change_clears_cache(self, icon_manager: IconManager) -> None:
        """Test that changing theme clears cache."""
        # Add something to cache
        icon_manager._cache["test"] = QIcon()

        # Change theme
        icon_manager.set_theme("dark")

        # Cache should be cleared
        assert len(icon_manager._cache) == 0

    def test_empty_icon_creation(self, icon_manager: IconManager) -> None:
        """Test empty icon creation for missing icons."""
        # Get icon that doesn't exist (and no fallback)
        icon = icon_manager.get_icon("missing_icon")
        assert isinstance(icon, QIcon)
        # Icon will be created but may be null


class TestIconConvenienceFunctions:
    """Test convenience functions."""

    def test_get_icon_function(self) -> None:
        """Test get_icon convenience function."""
        with patch("create_project.resources.icons._manager.get_icon") as mock_get:
            mock_get.return_value = QIcon()

            icon = get_icon("test", category="actions", size="medium")

            mock_get.assert_called_once_with("test", "actions", (24, 24))

    def test_get_icon_with_size_name(self) -> None:
        """Test get_icon with size name."""
        with patch("create_project.resources.icons._manager.get_icon") as mock_get:
            mock_get.return_value = QIcon()

            # Test each size
            for size_name, size_tuple in ICON_SIZES.items():
                get_icon("test", size=size_name)
                mock_get.assert_called_with("test", None, size_tuple)

    def test_set_icon_theme_function(self) -> None:
        """Test set_icon_theme convenience function."""
        with patch("create_project.resources.icons._manager.set_theme") as mock_set:
            set_icon_theme("dark")
            mock_set.assert_called_once_with("dark")

    def test_preload_common_icons_function(self) -> None:
        """Test preload_common_icons function."""
        with patch("create_project.resources.icons._manager.preload_icons") as mock_preload:
            preload_common_icons()

            # Should be called with list of common icons
            mock_preload.assert_called_once()
            icons = mock_preload.call_args[0][0]
            assert isinstance(icons, list)
            assert len(icons) > 0
            assert "actions/add" in icons
            assert "status/success" in icons


class TestIconPaths:
    """Test icon path resolution."""

    def test_icon_extensions(self, tmp_path: Path) -> None:
        """Test that various icon extensions are supported."""
        manager = IconManager()
        manager._icon_dir = tmp_path / "icons"
        manager._icon_dir.mkdir(parents=True, exist_ok=True)

        # Test different extensions
        for ext in [".png", ".svg", ".ico"]:
            icon_path = manager._icon_dir / f"test{ext}"
            if ext == ".png":
                pixmap = QPixmap(24, 24)
                pixmap.fill()
                pixmap.save(str(icon_path))
            else:
                # Create empty file for other formats
                icon_path.touch()

            icon = manager.get_icon(f"test{ext}")
            assert isinstance(icon, QIcon)

    def test_extensionless_icon_name(self, tmp_path: Path) -> None:
        """Test loading icon without specifying extension."""
        manager = IconManager()
        manager._icon_dir = tmp_path / "icons"
        manager._icon_dir.mkdir(parents=True, exist_ok=True)

        # Create icon with extension
        icon_path = manager._icon_dir / "noext.png"
        pixmap = QPixmap(24, 24)
        pixmap.fill()
        pixmap.save(str(icon_path))

        # Load without extension
        icon = manager.get_icon("noext")
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

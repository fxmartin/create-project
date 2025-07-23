# ABOUTME: Icon management system with loading, caching, and fallback support
# ABOUTME: Provides centralized icon access for consistent UI appearance

"""Icon management module for the Create Project application.

This module provides a centralized system for loading and managing icons
used throughout the GUI. It includes:
- Icon loading with format support (PNG, SVG, ICO)
- Fallback mechanism for missing icons
- Icon caching for performance
- Theme-aware icon selection
- Size variants support
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from PyQt6.QtGui import QIcon, QPixmap

logger = logging.getLogger(__name__)

# Icon directory paths
ICON_DIR = Path(__file__).parent / "icons"
FALLBACK_ICON = "default"

# Standard icon sizes
ICON_SIZES = {
    "small": (16, 16),
    "medium": (24, 24),
    "large": (32, 32),
    "xlarge": (48, 48),
}

# Icon categories
ICON_CATEGORIES = {
    "actions": "actions",
    "status": "status",
    "dialogs": "dialogs",
    "wizards": "wizard",
    "tools": "tools",
}


class IconManager:
    """Manages application icons with caching and fallback support."""

    _instance: Optional[IconManager] = None
    _cache: Dict[str, QIcon] = {}

    def __new__(cls) -> IconManager:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize icon manager."""
        if self._initialized:
            return

        self._initialized = True
        self._icon_dir = ICON_DIR
        self._fallback_icon_name = FALLBACK_ICON
        self._theme = "default"

        # Create icon directory if it doesn't exist
        self._icon_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Icon manager initialized with directory: {self._icon_dir}")

    def get_icon(
        self,
        name: str,
        category: Optional[str] = None,
        size: Optional[Tuple[int, int]] = None,
        theme: Optional[str] = None,
    ) -> QIcon:
        """Get an icon by name with optional category and size.

        Args:
            name: Icon name (without extension)
            category: Optional category subdirectory
            size: Optional size tuple (width, height)
            theme: Optional theme override

        Returns:
            QIcon instance
        """
        # Build cache key
        cache_key = f"{theme or self._theme}/{category or ''}/{name}"

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try to load icon
        icon = self._load_icon(name, category, theme)

        # Cache and return
        self._cache[cache_key] = icon
        return icon

    def _load_icon(
        self,
        name: str,
        category: Optional[str] = None,
        theme: Optional[str] = None,
    ) -> QIcon:
        """Load an icon from disk.

        Args:
            name: Icon name
            category: Optional category
            theme: Optional theme

        Returns:
            Loaded icon or fallback
        """
        # Build search paths
        search_paths = []

        # Theme-specific paths
        if theme or self._theme != "default":
            theme_name = theme or self._theme
            if category:
                search_paths.append(self._icon_dir / theme_name / category / name)
            search_paths.append(self._icon_dir / theme_name / name)

        # Default paths
        if category:
            search_paths.append(self._icon_dir / category / name)
        search_paths.append(self._icon_dir / name)

        # Try each extension
        extensions = [".png", ".svg", ".ico", ""]

        for base_path in search_paths:
            for ext in extensions:
                icon_path = Path(str(base_path) + ext) if ext else base_path
                if icon_path.exists() and icon_path.is_file():
                    logger.debug(f"Loading icon: {icon_path}")
                    return QIcon(str(icon_path))

        # Try fallback icon
        logger.warning(f"Icon not found: {name}, using fallback")
        return self._load_fallback_icon()

    def _load_fallback_icon(self) -> QIcon:
        """Load the fallback icon.

        Returns:
            Fallback icon or empty icon
        """
        # Try to load fallback icon
        for ext in [".png", ".svg", ".ico"]:
            fallback_path = self._icon_dir / f"{self._fallback_icon_name}{ext}"
            if fallback_path.exists():
                return QIcon(str(fallback_path))

        # Create empty icon if no fallback exists
        logger.warning("Fallback icon not found, using empty icon")
        return self._create_empty_icon()

    def _create_empty_icon(self) -> QIcon:
        """Create an empty placeholder icon.

        Returns:
            Empty QIcon
        """
        # Create a transparent pixmap
        pixmap = QPixmap(24, 24)
        pixmap.fill(pixmap.fill())  # Transparent
        return QIcon(pixmap)

    def set_theme(self, theme: str) -> None:
        """Set the current icon theme.

        Args:
            theme: Theme name
        """
        if theme != self._theme:
            self._theme = theme
            # Clear cache to reload with new theme
            self._cache.clear()
            logger.info(f"Icon theme changed to: {theme}")

    def clear_cache(self) -> None:
        """Clear the icon cache."""
        self._cache.clear()
        logger.debug("Icon cache cleared")

    def preload_icons(self, icon_names: list[str]) -> None:
        """Preload a list of icons into cache.

        Args:
            icon_names: List of icon names to preload
        """
        for name in icon_names:
            # Parse name for category
            parts = name.split("/")
            if len(parts) > 1:
                category = parts[0]
                icon_name = parts[1]
            else:
                category = None
                icon_name = parts[0]

            # Load icon to cache it
            self.get_icon(icon_name, category)

        logger.debug(f"Preloaded {len(icon_names)} icons")


# Convenience functions
_manager = IconManager()


def get_icon(
    name: str,
    category: Optional[str] = None,
    size: Optional[str] = None,
) -> QIcon:
    """Get an icon by name.

    Args:
        name: Icon name
        category: Optional category
        size: Optional size name ("small", "medium", "large", "xlarge")

    Returns:
        QIcon instance
    """
    size_tuple = ICON_SIZES.get(size) if size else None
    return _manager.get_icon(name, category, size_tuple)


def set_icon_theme(theme: str) -> None:
    """Set the global icon theme.

    Args:
        theme: Theme name
    """
    _manager.set_theme(theme)


def preload_common_icons() -> None:
    """Preload commonly used icons."""
    common_icons = [
        # Actions
        "actions/add",
        "actions/remove",
        "actions/edit",
        "actions/save",
        "actions/cancel",
        "actions/help",
        "actions/settings",
        "actions/folder-open",
        "actions/refresh",
        "actions/copy",

        # Status
        "status/success",
        "status/error",
        "status/warning",
        "status/info",
        "status/loading",

        # Dialogs
        "dialogs/question",
        "dialogs/information",
        "dialogs/warning",
        "dialogs/error",

        # Wizard
        "wizard/project-type",
        "wizard/basic-info",
        "wizard/location",
        "wizard/options",
        "wizard/review",

        # Tools
        "tools/git",
        "tools/python",
        "tools/ai",
    ]

    _manager.preload_icons(common_icons)

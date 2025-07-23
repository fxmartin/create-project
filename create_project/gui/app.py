# ABOUTME: Main application entry point for GUI mode
# ABOUTME: Initializes Qt application and launches project wizard

"""
GUI application module.

This module provides the main entry point for running the Create Project
application in GUI mode. It initializes the Qt application, loads
configuration, and launches the project creation wizard.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from create_project.ai.ai_service import AIService
from create_project.config.config_manager import ConfigManager
from create_project.templates.engine import TemplateEngine
from create_project.templates.loader import TemplateLoader
from create_project.utils.logger import get_logger

from .wizard.wizard import ProjectWizard

logger = get_logger(__name__)


def setup_application() -> QApplication:
    """
    Set up the Qt application.

    Returns:
        Configured QApplication instance
    """
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Create Project")
    app.setApplicationDisplayName("Python Project Creator")
    app.setOrganizationName("CreateProject")

    # Enable high DPI scaling
    try:
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        # PyQt6 may have different attribute names
        pass

    # Set default style
    app.setStyle("Fusion")  # Cross-platform style

    return app


def load_configuration() -> ConfigManager:
    """
    Load application configuration.

    Returns:
        ConfigManager instance
    """
    try:
        config_manager = ConfigManager()
        logger.info("Configuration loaded successfully")
        return config_manager
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        QMessageBox.critical(
            None,
            "Configuration Error",
            f"Failed to load configuration:\n\n{str(e)}\n\n"
            "Please check your settings.json file.",
        )
        sys.exit(1)


def initialize_services(
    config_manager: ConfigManager,
) -> tuple[TemplateEngine, TemplateLoader, Optional[AIService]]:
    """
    Initialize backend services.

    Args:
        config_manager: Configuration manager instance

    Returns:
        Tuple of (template_engine, template_loader, ai_service)
    """
    # Initialize template engine and loader
    try:
        template_engine = TemplateEngine(config_manager)
        template_loader = TemplateLoader(config_manager)
        logger.info("Template engine and loader initialized")
    except Exception as e:
        logger.error(f"Failed to initialize template services: {e}")
        QMessageBox.critical(
            None,
            "Initialization Error",
            f"Failed to initialize template services:\n\n{str(e)}",
        )
        sys.exit(1)

    # Initialize AI service if enabled
    ai_service = None
    if config_manager.get_setting("ai.enabled", True):
        try:
            import asyncio
            ai_service = AIService(config_manager)
            # Run async initialization synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(ai_service.initialize())
            if loop.run_until_complete(ai_service.is_available()):
                logger.info("AI service initialized and available")
            else:
                logger.warning("AI service initialized but not available")
            loop.close()
        except Exception as e:
            logger.warning(f"Failed to initialize AI service: {e}")
            # Continue without AI service

    return template_engine, template_loader, ai_service


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Create Python Project - GUI Mode")

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (default: config/settings.json)",
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    parser.add_argument("--no-ai", action="store_true", help="Disable AI assistance")
    
    # Accept --gui flag (when called from main module) but ignore it
    parser.add_argument(
        "--gui",
        action="store_true",
        help=argparse.SUPPRESS  # Hide from help
    )
    return parser.parse_args()


def main(args=None) -> int:
    """
    Main entry point for GUI application.
    
    Args:
        args: Optional command-line arguments (for testing)
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Parse arguments - but don't require them if called from main module
    if args is not None:
        parsed_args = args
    else:
        parsed_args = parse_arguments()
    # Set up logging
    if hasattr(parsed_args, 'debug') and parsed_args.debug:
        import logging

        logging.getLogger("create_project").setLevel(logging.DEBUG)

    try:
        # Create Qt application
        app = setup_application()

        # Load configuration
        config_manager = load_configuration()

        # Override AI setting if requested
        if hasattr(parsed_args, 'no_ai') and parsed_args.no_ai:
            config_manager.set_setting("ai.enabled", False)

        # Initialize services
        template_engine, template_loader, ai_service = initialize_services(
            config_manager
        )

        # Create and show wizard
        wizard = ProjectWizard(
            config_manager=config_manager,
            template_engine=template_engine,
            template_loader=template_loader,
            ai_service=ai_service,
        )

        # Connect to handle successful project creation
        def on_project_created(project_path: Path):
            logger.info(f"Project created at: {project_path}")
            QMessageBox.information(
                wizard,
                "Project Created",
                f"Your project has been created at:\n\n{project_path}\n\n"
                "You can now open it in your favorite IDE!",
            )

        wizard.project_created.connect(on_project_created)

        # Show wizard
        wizard.show()

        # Run event loop
        return app.exec()

    except Exception as e:
        logger.exception("Unhandled exception in GUI application")
        QMessageBox.critical(
            None,
            "Application Error",
            f"An unexpected error occurred:\n\n{str(e)}\n\n"
            "Please check the logs for more details.",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

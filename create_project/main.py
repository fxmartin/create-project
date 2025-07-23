# ABOUTME: Main application entry point for both CLI and GUI modes
# ABOUTME: Handles command-line arguments and launches appropriate interface

"""
Main application entry point.

This module provides the main entry point for the Create Project application,
supporting both CLI and GUI modes. It handles command-line argument parsing
and launches the appropriate interface based on user input.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional

from .utils.logger import get_logger, init_logging
from .config.config_manager import ConfigManager
from .core.api import create_project
from .templates.loader import TemplateLoader
from .templates.engine import TemplateEngine

logger = get_logger(__name__)


def parse_cli_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: List of arguments to parse (defaults to sys.argv[1:])
        
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        prog="create-project",
        description="Create Python project structures from templates"
    )
    
    # Mode selection
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the graphical user interface (default if no arguments)"
    )
    
    # CLI mode arguments
    parser.add_argument(
        "project_name",
        nargs="?",
        help="Name of the project to create (CLI mode)"
    )
    
    parser.add_argument(
        "-t", "--template",
        default="library",
        help="Template to use (default: library)"
    )
    
    parser.add_argument(
        "-p", "--path",
        type=Path,
        default=Path.cwd(),
        help="Path where project will be created (default: current directory)"
    )
    
    parser.add_argument(
        "-a", "--author",
        help="Project author name"
    )
    
    parser.add_argument(
        "-d", "--description",
        help="Project description"
    )
    
    parser.add_argument(
        "-v", "--version",
        default="0.1.0",
        help="Initial project version (default: 0.1.0)"
    )
    
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Skip git repository initialization"
    )
    
    parser.add_argument(
        "--no-venv",
        action="store_true",
        help="Skip virtual environment creation"
    )
    
    parser.add_argument(
        "--license",
        default="MIT",
        help="License type (default: MIT)"
    )
    
    # General arguments
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List available templates and exit"
    )
    
    return parser.parse_args(args)


def run_cli_mode(args: argparse.Namespace, config_manager: ConfigManager) -> int:
    """
    Run the application in CLI mode.
    
    Args:
        args: Parsed command-line arguments
        config_manager: Configuration manager instance
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Initialize template loader and engine
    template_loader = TemplateLoader(config_manager)
    template_engine = TemplateEngine(config_manager)
    
    # Handle --list-templates
    if args.list_templates:
        print("\nAvailable templates:")
        print("="*50)
        templates = template_loader.list_templates()
        for template_info in templates:
            # The template info is already flattened metadata
            template_id = template_info.get('template_id', template_info.get('name', 'unknown').lower().replace(' ', '_'))
            name = template_info.get('name', 'Unknown')
            description = template_info.get('description', 'No description')
            tags = template_info.get('tags', [])
            
            print(f"\n{template_id}:")
            print(f"  Name: {name}")
            print(f"  Description: {description}")
            if tags:
                print(f"  Tags: {', '.join(tags)}")
        return 0
    
    # Require project name for CLI mode
    if not args.project_name:
        print("Error: Project name is required in CLI mode")
        print("Use --gui to launch the graphical interface")
        return 1
    
    # Find and load template
    try:
        # First find the template file by template_id (template info is already flattened)
        template_path = None
        templates = template_loader.list_templates()
        for template_info in templates:
            if template_info.get('template_id') == args.template:
                template_path = template_info.get('file_path')
                break
        
        if not template_path:
            print(f"Error: Template '{args.template}' not found")
            print("Use --list-templates to see available templates")
            return 1
        
        # Load the template
        template = template_engine.load_template(template_path)
        
    except Exception as e:
        print(f"Error loading template: {e}")
        return 1
    
    # Prepare project variables
    project_vars = {
        "name": args.project_name,
        "author": args.author or config_manager.get_setting("defaults.author", "Author Name"),
        "description": args.description or f"A {template.name} project",
        "version": args.version,
        "license": args.license,
        "init_git": not args.no_git,
        "create_venv": not args.no_venv,
    }
    
    # Create project
    try:
        print(f"\nCreating project '{args.project_name}' from template '{template.name}'...")
        
        def progress_callback(message: str, progress: int):
            print(f"[{progress:3d}%] {message}")
        
        result = create_project(
            template_id=args.template,
            project_path=args.path / args.project_name,
            variables=project_vars,
            progress_callback=progress_callback
        )
        
        if result.success:
            print(f"\n✓ Project created successfully at: {result.project_path}")
            if result.warnings:
                print("\nWarnings:")
                for warning in result.warnings:
                    print(f"  - {warning}")
            return 0
        else:
            print(f"\n✗ Failed to create project: {result.error}")
            return 1
            
    except Exception as e:
        logger.exception("Failed to create project")
        print(f"\n✗ Unexpected error: {e}")
        return 1


def run_gui_mode(args: argparse.Namespace, config_manager: ConfigManager) -> int:
    """
    Run the application in GUI mode.
    
    Args:
        args: Parsed command-line arguments
        config_manager: Configuration manager instance
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Import GUI module only when needed
        from .gui import app as gui_app
        
        # Override debug setting if requested
        if args.debug:
            import logging
            logging.getLogger("create_project").setLevel(logging.DEBUG)
        
        # Run GUI directly - it will handle its own argument parsing
        # and configuration loading
        return gui_app.main()
        
    except ImportError as e:
        print("Error: GUI dependencies not installed")
        print(f"Details: {e}")
        print("\nInstall PyQt6 to use GUI mode:")
        print("  uv add pyqt6")
        return 1


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the application.
    
    Args:
        args: Optional list of command-line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Initialize logging
    init_logging()
    
    # Parse arguments
    parsed_args = parse_cli_arguments(args)
    
    # Set debug logging if requested
    if parsed_args.debug:
        import logging
        logging.getLogger("create_project").setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Initialize configuration
    try:
        config_manager = ConfigManager(config_path=parsed_args.config)
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        print(f"Error: Failed to load configuration: {e}")
        return 1
    
    # Determine mode: GUI if --gui flag or no project name provided
    if parsed_args.gui or (not parsed_args.project_name and not parsed_args.list_templates):
        logger.info("Launching GUI mode")
        return run_gui_mode(parsed_args, config_manager)
    else:
        logger.info("Running in CLI mode")
        return run_cli_mode(parsed_args, config_manager)


if __name__ == "__main__":
    sys.exit(main())

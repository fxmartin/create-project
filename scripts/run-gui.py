#!/usr/bin/env python3
# ABOUTME: Python launch script for GUI mode
# ABOUTME: Cross-platform script to launch the GUI application

"""
GUI launch script.

This script provides a cross-platform way to launch the Create Project
application in GUI mode with proper environment setup.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variable for GUI mode
os.environ["CREATE_PROJECT_GUI"] = "1"

# Import and run the GUI
try:
    from create_project.gui.app import main
    sys.exit(main())
except ImportError as e:
    print("Error: Failed to import GUI module")
    print(f"Details: {e}")
    print("\nMake sure PyQt6 is installed:")
    print("  uv add pyqt6")
    sys.exit(1)
except Exception as e:
    print(f"Error launching GUI: {e}")
    sys.exit(1)
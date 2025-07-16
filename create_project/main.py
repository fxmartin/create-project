# ABOUTME: Main application entry point
# ABOUTME: Initializes and starts the PyQt application

import sys
from pathlib import Path


def main():
    """Main entry point for the application."""
    print("Python Project Creator starting...")
    print("Project structure initialized successfully!")

    # Validate project structure
    project_root = Path(__file__).parent.parent
    print(f"Project root: {project_root}")

    # Check if main directories exist
    required_dirs = [
        "create_project/core",
        "create_project/gui",
        "create_project/utils",
        "create_project/templates",
        "create_project/resources",
        "create_project/config",
        "tests",
        "docs"
    ]

    missing_dirs = []
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if not full_path.exists():
            missing_dirs.append(dir_path)

    if missing_dirs:
        print(f"Warning: Missing directories: {', '.join(missing_dirs)}")
        return 1

    print("All required directories present!")
    print("Ready for development!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

# ABOUTME: Project structure validation utilities
# ABOUTME: Ensures all required directories and files exist

from pathlib import Path
from typing import Dict, List, Tuple


def validate_project_structure(project_root: Path) -> Tuple[bool, List[str], List[str]]:
    """
    Validate that all required directories and files exist.
    
    Args:
        project_root: Path to the project root directory
        
    Returns:
        Tuple of (is_valid, missing_dirs, missing_files)
    """
    required_dirs = [
        "create_project",
        "create_project/core",
        "create_project/gui",
        "create_project/utils",
        "create_project/templates",
        "create_project/templates/builtin",
        "create_project/templates/user",
        "create_project/resources",
        "create_project/resources/styles",
        "create_project/resources/icons",
        "create_project/resources/licenses",
        "create_project/config",
        "tests",
        "tests/unit",
        "tests/integration",
        "tests/gui",
        "docs",
        "docs/user",
        "docs/developer",
        "docs/templates",
        "build",
        "dist",
        "scripts"
    ]

    required_files = [
        "create_project/__init__.py",
        "create_project/core/__init__.py",
        "create_project/gui/__init__.py",
        "create_project/utils/__init__.py",
        "create_project/templates/__init__.py",
        "create_project/templates/builtin/__init__.py",
        "create_project/templates/user/__init__.py",
        "create_project/resources/__init__.py",
        "create_project/config/__init__.py",
        "create_project/config/settings.json",
        "create_project/config/defaults.json",
        "create_project/__main__.py",
        "create_project/main.py",
        "tests/__init__.py",
        "tests/unit/__init__.py",
        "tests/integration/__init__.py",
        "tests/gui/__init__.py",
        "pyproject.toml"
    ]

    missing_dirs = []
    missing_files = []

    # Check directories
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if not full_path.exists() or not full_path.is_dir():
            missing_dirs.append(str(dir_path))

    # Check files
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists() or not full_path.is_file():
            missing_files.append(str(file_path))

    is_valid = len(missing_dirs) == 0 and len(missing_files) == 0
    return is_valid, missing_dirs, missing_files


def get_structure_report(project_root: Path) -> Dict[str, any]:
    """
    Generate a comprehensive structure validation report.
    
    Args:
        project_root: Path to the project root directory
        
    Returns:
        Dictionary containing validation results and statistics
    """
    is_valid, missing_dirs, missing_files = validate_project_structure(project_root)

    return {
        "is_valid": is_valid,
        "missing_directories": missing_dirs,
        "missing_files": missing_files,
        "directories_count": len([d for d in (project_root).rglob("*") if d.is_dir()]),
        "files_count": len([f for f in (project_root).rglob("*") if f.is_file()]),
        "project_root": str(project_root)
    }


def create_missing_structure(project_root: Path) -> bool:
    """
    Create any missing directories and basic files.
    
    Args:
        project_root: Path to the project root directory
        
    Returns:
        True if structure was created successfully, False otherwise
    """
    try:
        is_valid, missing_dirs, missing_files = validate_project_structure(project_root)

        # Create missing directories
        for dir_path in missing_dirs:
            full_path = project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)

        # Create missing __init__.py files
        for file_path in missing_files:
            if file_path.endswith("__init__.py"):
                full_path = project_root / file_path
                if not full_path.exists():
                    full_path.touch()

        return True
    except Exception as e:
        print(f"Error creating project structure: {e}")
        return False

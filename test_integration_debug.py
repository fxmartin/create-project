#!/usr/bin/env python3
"""Debug integration test"""

import tempfile
from pathlib import Path
from create_project.core.api import create_project
from create_project.config import ConfigManager

# Create temp directory
with tempfile.TemporaryDirectory() as tmpdir:
    # Create project
    config = ConfigManager()
    result = create_project(
        template_name="python_library",
        project_name="test_debug",
        target_directory=tmpdir,
        variables={
            "author": "Test Author",
            "email": "test@example.com",
            "description": "Test project",
            "license": "MIT",
            "python_version": "3.9.6",
            "include_tests": True,
            "init_git": False,  # Simplify
            "create_venv": False,  # Simplify
            "project_type": "library",  # Add project type
            "testing_framework": "pytest",  # Add test framework
            "include_dev_dependencies": True,  # Add dev deps
            "include_coverage": True,  # Add coverage
        },
        config_manager=config
    )
    
    print(f"Success: {result.success}")
    print(f"Files created: {len(result.files_created)}")
    print(f"Files list: {result.files_created}")
    print(f"Errors: {result.errors}")
    
    # Check actual files
    project_path = Path(tmpdir) / "test_debug"
    if project_path.exists():
        print(f"\nActual files in {project_path}:")
        for p in project_path.rglob("*"):
            if p.is_file():
                print(f"  {p.relative_to(project_path)}")
    else:
        print(f"Project path does not exist: {project_path}")
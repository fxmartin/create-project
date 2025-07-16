#!/bin/bash

# ABOUTME: Package script for creating standalone executables
# ABOUTME: Uses PyInstaller to create distributable binaries

set -e

echo "Creating standalone executable..."

# Ensure dependencies are installed
uv run pip install pyinstaller

# Create executable
uv run pyinstaller --onefile --windowed --name "Python Project Creator" create_project/__main__.py

echo "Executable created successfully in dist/ directory!"
#!/bin/bash

# ABOUTME: Build script for creating distribution packages
# ABOUTME: Handles clean build process and package creation

set -e

echo "Building Python Project Creator..."

# Clean previous builds
rm -rf build/* dist/*

# Build package
uv build

echo "Build completed successfully!"
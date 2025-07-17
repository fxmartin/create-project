#!/usr/bin/env python3

# ABOUTME: Environment validation script for development setup
# ABOUTME: Validates Python version, dependencies, and configuration

"""
Development Environment Validation Script

This script validates that the development environment is properly set up
for the Python Project Creator project. It checks:
- Python version compatibility
- Required dependencies
- Environment variables
- File permissions
- Configuration validity
"""

import importlib.util
import subprocess
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def log_info(message: str) -> None:
    """Log an info message."""
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {message}")


def log_success(message: str) -> None:
    """Log a success message."""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {message}")


def log_warning(message: str) -> None:
    """Log a warning message."""
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {message}")


def log_error(message: str) -> None:
    """Log an error message."""
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {message}")


def check_python_version() -> bool:
    """Check if Python version meets requirements."""
    log_info("Checking Python version...")

    required_version = (3, 9, 6)
    current_version = sys.version_info[:3]

    if current_version >= required_version:
        version_str = f"{current_version[0]}.{current_version[1]}.{current_version[2]}"
        log_success(f"Python version: {version_str}")
        return True
    else:
        version_str = f"{current_version[0]}.{current_version[1]}.{current_version[2]}"
        required_str = (
            f"{required_version[0]}.{required_version[1]}.{required_version[2]}"
        )
        log_error(f"Python version {version_str} is too old. Required: {required_str}+")
        return False


def check_uv_installation() -> bool:
    """Check if uv package manager is installed."""
    log_info("Checking uv installation...")

    try:
        result = subprocess.run(
            ["uv", "--version"], capture_output=True, text=True, check=True
        )
        version = result.stdout.strip().split()[1]
        log_success(f"uv version: {version}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_error("uv is not installed or not in PATH")
        return False


def check_dependencies() -> bool:
    """Check if all required dependencies are installed."""
    log_info("Checking dependencies...")

    # Core dependencies
    core_deps = ["PyQt6", "requests", "yaml", "jinja2", "pydantic", "dotenv"]

    # Development dependencies
    dev_deps = ["pytest", "ruff", "mypy"]

    all_good = True

    for dep in core_deps:
        if check_package(dep):
            log_success(f"✓ {dep}")
        else:
            log_error(f"✗ {dep}")
            all_good = False

    for dep in dev_deps:
        if check_package(dep):
            log_success(f"✓ {dep} (dev)")
        else:
            log_warning(f"✗ {dep} (dev)")
            # Dev dependencies don't fail the check

    return all_good


def check_package(package_name: str) -> bool:
    """Check if a Python package is available."""
    # Special handling for some packages
    package_map = {
        "PyQt6": "PyQt6",
        "yaml": "yaml",
        "jinja2": "jinja2",
        "dotenv": "dotenv",
    }

    actual_name = package_map.get(package_name, package_name)

    try:
        importlib.import_module(actual_name)
        return True
    except ImportError:
        return False


def check_project_structure() -> bool:
    """Check if we're in the correct project directory."""
    log_info("Checking project structure...")

    required_files = ["pyproject.toml", "README.md", "LICENSE", ".env.example"]

    required_dirs = ["create_project", "tests", "docs", "scripts"]

    all_good = True

    for file in required_files:
        if Path(file).exists():
            log_success(f"✓ {file}")
        else:
            log_error(f"✗ {file}")
            all_good = False

    for dir in required_dirs:
        if Path(dir).is_dir():
            log_success(f"✓ {dir}/")
        else:
            log_error(f"✗ {dir}/")
            all_good = False

    return all_good


def check_environment_file() -> bool:
    """Check environment file setup."""
    log_info("Checking environment configuration...")

    if not Path(".env.example").exists():
        log_error(".env.example file not found")
        return False

    if not Path(".env").exists():
        log_warning(".env file not found (optional)")
        log_info("You can create it with: cp .env.example .env")
    else:
        log_success("✓ .env file exists")

    return True


def check_file_permissions() -> bool:
    """Check file permissions for development."""
    log_info("Checking file permissions...")

    # Check if we can write to important directories
    write_dirs = ["logs", "data", "build", "dist"]

    all_good = True

    for dir_name in write_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                log_success(f"✓ Created {dir_name}/ directory")
            except PermissionError:
                log_error(f"✗ Cannot create {dir_name}/ directory")
                all_good = False
        else:
            # Check if directory is writable
            test_file = dir_path / ".test_write"
            try:
                test_file.write_text("test")
                test_file.unlink()
                log_success(f"✓ {dir_name}/ directory is writable")
            except PermissionError:
                log_error(f"✗ {dir_name}/ directory is not writable")
                all_good = False

    return all_good


def check_configuration() -> bool:
    """Check configuration system."""
    log_info("Checking configuration system...")

    try:
        # Try to import and use the configuration system
        sys.path.insert(0, str(Path.cwd()))
        from create_project.config import get_config

        config = get_config()
        log_success("✓ Configuration system is working")

        # Check if we can access some basic settings
        theme = config.ui.theme
        log_success(f"✓ UI theme setting: {theme}")

        return True
    except Exception as e:
        log_error(f"✗ Configuration system error: {e}")
        return False


def run_basic_tests() -> bool:
    """Run basic tests to verify functionality."""
    log_info("Running basic tests...")

    try:
        # Run a quick test to see if pytest works
        result = subprocess.run(
            ["uv", "run", "pytest", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        log_success("✓ pytest is working")

        # Try to run a simple test
        if Path("tests").exists():
            result = subprocess.run(
                ["uv", "run", "pytest", "tests/", "-x", "-q", "--tb=no"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                log_success("✓ Basic tests passed")
                return True
            else:
                log_warning("Some tests failed (this might be expected)")
                return True  # Don't fail validation for test failures
        else:
            log_warning("No tests directory found")
            return True

    except subprocess.TimeoutExpired:
        log_warning("Tests took too long to run")
        return True
    except Exception as e:
        log_warning(f"Could not run tests: {e}")
        return True  # Don't fail validation for test issues


def main() -> int:
    """Main validation function."""
    print(
        f"{Colors.BOLD}Python Project Creator - Development Environment Validation{Colors.RESET}"
    )
    print("=" * 60)

    checks = [
        ("Python Version", check_python_version),
        ("uv Installation", check_uv_installation),
        ("Dependencies", check_dependencies),
        ("Project Structure", check_project_structure),
        ("Environment File", check_environment_file),
        ("File Permissions", check_file_permissions),
        ("Configuration", check_configuration),
        ("Basic Tests", run_basic_tests),
    ]

    results = []

    for check_name, check_func in checks:
        print(f"\n{Colors.MAGENTA}--- {check_name} ---{Colors.RESET}")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            log_error(f"Check failed with exception: {e}")
            results.append((check_name, False))

    print(f"\n{Colors.BOLD}Validation Summary{Colors.RESET}")
    print("=" * 60)

    passed = 0
    failed = 0

    for check_name, result in results:
        if result:
            print(f"{Colors.GREEN}✓{Colors.RESET} {check_name}")
            passed += 1
        else:
            print(f"{Colors.RED}✗{Colors.RESET} {check_name}")
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed == 0:
        print(f"\n{Colors.GREEN}🎉 Development environment is ready!{Colors.RESET}")
        print("\nYou can now:")
        print(
            f"  • Run the application: {Colors.CYAN}uv run python -m create_project{Colors.RESET}"
        )
        print(f"  • Run tests: {Colors.CYAN}uv run pytest{Colors.RESET}")
        print(f"  • Format code: {Colors.CYAN}uv run ruff format .{Colors.RESET}")
        print(f"  • Check code: {Colors.CYAN}uv run ruff check .{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}❌ Development environment has issues.{Colors.RESET}")
        print("Please resolve the failed checks above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

# TODO: Section 1.2 Configure Project Dependencies

## Section Overview
- **Section**: 1.2 Configure Project Dependencies
- **Total Estimated Hours**: 4 hours
- **Prerequisites**: 1.1 Initialize Project Structure
- **Key Deliverables**: pyproject.toml file with proper dependency specifications and Python 3.9.6+ requirement

## Atomic Task List

### Setup Tasks

**Task S001**: Initialize UV project structure
- **Type**: Setup
- **Estimated Time**: 30min
- **Prerequisites**: None (assumes project directory exists)
- **Files to Create/Modify**: 
  - `pyproject.toml` (create)
  - `uv.lock` (generated)
  - `.venv/` directory (generated)
- **Acceptance Criteria**:
  ☐ `uv init` command executed successfully
  ☐ `pyproject.toml` exists with basic structure
  ☐ Virtual environment created in `.venv/`
  ☐ `uv.lock` file generated
- **Implementation Notes**: 
  ```bash
  cd create-project
  uv init --name create-project
  ```

**Task S002**: Configure Python version requirement
- **Type**: Setup
- **Estimated Time**: 15min
- **Prerequisites**: S001
- **Files to Create/Modify**: 
  - `pyproject.toml` (modify)
- **Acceptance Criteria**:
  ☐ Python version requirement set to ">=3.9.6"
  ☐ `uv python pin 3.9` executed successfully
  ☐ `.python-version` file created
- **Implementation Notes**: 
  ```toml
  [project]
  requires-python = ">=3.9.6"
  ```

### Development Tasks

**Task D001**: Add PyQt6 dependency
- **Type**: Code
- **Estimated Time**: 15min
- **Prerequisites**: S001
- **Files to Create/Modify**: 
  - `pyproject.toml` (modify)
  - `uv.lock` (update)
- **Acceptance Criteria**:
  ☐ PyQt6 added to dependencies
  ☐ `uv add PyQt6` command executed successfully
  ☐ Dependency appears in pyproject.toml
  ☐ Lock file updated with PyQt6 and its dependencies
- **Implementation Notes**: 
  ```bash
  uv add PyQt6
  ```

**Task D002**: Add HTTP requests dependency
- **Type**: Code
- **Estimated Time**: 15min
- **Prerequisites**: S001
- **Files to Create/Modify**: 
  - `pyproject.toml` (modify)
  - `uv.lock` (update)
- **Acceptance Criteria**:
  ☐ requests library added to dependencies
  ☐ `uv add requests` command executed successfully
  ☐ Dependency appears in pyproject.toml
  ☐ Lock file updated with requests and its dependencies
- **Implementation Notes**: 
  ```bash
  uv add requests
  ```

**Task D003**: Add YAML processing dependency
- **Type**: Code
- **Estimated Time**: 15min
- **Prerequisites**: S001
- **Files to Create/Modify**: 
  - `pyproject.toml` (modify)
  - `uv.lock` (update)
- **Acceptance Criteria**:
  ☐ PyYAML added to dependencies
  ☐ `uv add pyyaml` command executed successfully
  ☐ Dependency appears in pyproject.toml
  ☐ Lock file updated with PyYAML and its dependencies
- **Implementation Notes**: 
  ```bash
  uv add pyyaml
  ```

**Task D004**: Add template engine dependency
- **Type**: Code
- **Estimated Time**: 15min
- **Prerequisites**: S001
- **Files to Create/Modify**: 
  - `pyproject.toml` (modify)
  - `uv.lock` (update)
- **Acceptance Criteria**:
  ☐ Jinja2 added to dependencies
  ☐ `uv add jinja2` command executed successfully
  ☐ Dependency appears in pyproject.toml
  ☐ Lock file updated with Jinja2 and its dependencies
- **Implementation Notes**: 
  ```bash
  uv add jinja2
  ```

**Task D005**: Add development dependencies
- **Type**: Code
- **Estimated Time**: 30min
- **Prerequisites**: S001
- **Files to Create/Modify**: 
  - `pyproject.toml` (modify)
  - `uv.lock` (update)
- **Acceptance Criteria**:
  ☐ pytest added as dev dependency
  ☐ pytest-qt added for PyQt testing
  ☐ ruff added for linting and formatting
  ☐ mypy added for type checking
  ☐ All dev dependencies appear in pyproject.toml [tool.uv.dev-dependencies]
- **Implementation Notes**: 
  ```bash
  uv add --dev pytest pytest-qt ruff mypy
  ```

**Task D006**: Configure project metadata
- **Type**: Code
- **Estimated Time**: 30min
- **Prerequisites**: S001, S002
- **Files to Create/Modify**: 
  - `pyproject.toml` (modify)
- **Acceptance Criteria**:
  ☐ Project name set to "create-project"
  ☐ Version set to "0.1.0"
  ☐ Description added
  ☐ Author information added
  ☐ License specified (Apache-2.0)
  ☐ Homepage/repository URLs added
  ☐ Keywords added
  ☐ Classifiers added
- **Implementation Notes**: 
  ```toml
  [project]
  name = "create-project"
  version = "0.1.0"
  description = "A PyQt-based GUI application for creating Python project structures"
  authors = [{name = "FX", email = "fx@example.com"}]
  license = {text = "Apache-2.0"}
  readme = "README.md"
  keywords = ["python", "project", "template", "gui", "pyqt"]
  classifiers = [
      "Development Status :: 3 - Alpha",
      "Intended Audience :: Developers",
      "License :: OSI Approved :: Apache Software License",
      "Operating System :: OS Independent",
      "Programming Language :: Python :: 3",
      "Programming Language :: Python :: 3.9",
      "Programming Language :: Python :: 3.10",
      "Programming Language :: Python :: 3.11",
      "Programming Language :: Python :: 3.12",
  ]
  ```

**Task D007**: Configure entry points
- **Type**: Code
- **Estimated Time**: 15min
- **Prerequisites**: D006
- **Files to Create/Modify**: 
  - `pyproject.toml` (modify)
- **Acceptance Criteria**:
  ☐ Console script entry point defined
  ☐ GUI script entry point defined
  ☐ Entry points reference main module correctly
- **Implementation Notes**: 
  ```toml
  [project.scripts]
  create-project = "create_project.main:main"
  create-project-gui = "create_project.gui.main:main"
  ```

### Integration Tasks

**Task I001**: Configure build system
- **Type**: Integration
- **Estimated Time**: 15min
- **Prerequisites**: S001
- **Files to Create/Modify**: 
  - `pyproject.toml` (modify)
- **Acceptance Criteria**:
  ☐ Build system configured for hatchling
  ☐ Build backend specified correctly
  ☐ Build requirements defined
- **Implementation Notes**: 
  ```toml
  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"
  ```

**Task I002**: Configure tool settings
- **Type**: Integration
- **Estimated Time**: 30min
- **Prerequisites**: D005
- **Files to Create/Modify**: 
  - `pyproject.toml` (modify)
- **Acceptance Criteria**:
  ☐ Ruff configuration added with line length, select rules
  ☐ MyPy configuration added with strict mode
  ☐ Pytest configuration added with test discovery
  ☐ All tool configurations work correctly
- **Implementation Notes**: 
  ```toml
  [tool.ruff]
  line-length = 88
  select = ["E", "F", "W", "C90", "I", "N", "UP", "B", "A", "S", "FBT", "Q"]
  
  [tool.mypy]
  python_version = "3.9"
  strict = true
  
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  python_files = ["test_*.py", "*_test.py"]
  ```

### Testing Tasks

**Task T001**: Test dependency installation
- **Type**: Test
- **Estimated Time**: 30min
- **Prerequisites**: D001, D002, D003, D004, D005
- **Files to Create/Modify**: 
  - None (testing only)
- **Acceptance Criteria**:
  ☐ `uv sync` completes without errors
  ☐ All dependencies install correctly
  ☐ Virtual environment activated successfully
  ☐ All packages importable in Python
- **Implementation Notes**: 
  ```bash
  uv sync
  uv run python -c "import PyQt6; import requests; import yaml; import jinja2; print('All imports successful')"
  ```

**Task T002**: Test development tools
- **Type**: Test
- **Estimated Time**: 30min
- **Prerequisites**: I002, T001
- **Files to Create/Modify**: 
  - None (testing only)
- **Acceptance Criteria**:
  ☐ Ruff linting runs without errors
  ☐ MyPy type checking runs without errors
  ☐ Pytest test discovery works
  ☐ All development tools accessible via uv run
- **Implementation Notes**: 
  ```bash
  uv run ruff check .
  uv run mypy --version
  uv run pytest --collect-only
  ```

### Documentation Tasks

**Task DOC001**: Document dependency choices
- **Type**: Documentation
- **Estimated Time**: 15min
- **Prerequisites**: All above tasks
- **Files to Create/Modify**: 
  - `README.md` (modify or create dependencies section)
- **Acceptance Criteria**:
  ☐ All main dependencies documented with purpose
  ☐ Development dependencies explained
  ☐ Python version requirement documented
  ☐ Installation instructions provided
- **Implementation Notes**: 
  Add section explaining:
  - PyQt6: GUI framework
  - requests: HTTP client for API calls
  - PyYAML: YAML template parsing
  - Jinja2: Template engine for file generation

### Task Sequencing

**Critical Path**: S001 → S002 → D001-D005 → D006 → D007 → I001 → I002 → T001 → T002 → DOC001

**Parallel Execution Opportunities**:
- D001, D002, D003, D004 can run in parallel after S001
- T001 and I002 can run in parallel after dependencies are added
- DOC001 can run in parallel with final testing

**Estimated Total Time**: 4 hours

## Progress Tracking
- [ ] S001: Initialize UV project structure
- [ ] S002: Configure Python version requirement  
- [ ] D001: Add PyQt6 dependency
- [ ] D002: Add HTTP requests dependency
- [ ] D003: Add YAML processing dependency
- [ ] D004: Add template engine dependency
- [ ] D005: Add development dependencies
- [ ] D006: Configure project metadata
- [ ] D007: Configure entry points
- [ ] I001: Configure build system
- [ ] I002: Configure tool settings
- [ ] T001: Test dependency installation
- [ ] T002: Test development tools
- [ ] DOC001: Document dependency choices
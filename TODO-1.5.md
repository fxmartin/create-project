# TODO: Section 1.5 Set Up Development Environment

## Section Overview
- **Section**: 1.5 Set Up Development Environment
- **Total Estimated Hours**: 6-8 hours
- **Prerequisites**: 
  - Section 1.1 (Initialize Project Structure) - Complete
  - Section 1.2 (Configure Project Dependencies) - Complete
- **Key Deliverables**: 
  - Comprehensive development setup documentation
  - Enhanced README with detailed setup instructions
  - .env.example file (already exists, needs review)
  - Development scripts and tools
  - CI/CD configuration templates
  - Contributor guidelines

## Atomic Task List

### Documentation Enhancement Tasks

**Task DOC001**: [ ] Enhance README.md with comprehensive development setup
- **Type**: Documentation
- **Estimated Time**: 1.5hrs
- **Prerequisites**: None
- **Files to Create/Modify**: 
  - `README.md`
- **Acceptance Criteria**:
  - Detailed prerequisites section with platform-specific instructions
  - Step-by-step development environment setup
  - Troubleshooting section for common issues
  - Quick start guide for new developers
  - Environment variable documentation
- **Implementation Notes**: 
  - Include macOS, Windows, and Linux specific instructions
  - Document Python version management (pyenv, conda)
  - Add verification steps for each setup phase
  - Include IDE setup recommendations (VS Code, PyCharm)

**Task DOC002**: [ ] Create detailed developer documentation
- **Type**: Documentation
- **Estimated Time**: 2hrs
- **Prerequisites**: None
- **Files to Create/Modify**:
  - `docs/developer/setup.md` (already exists, enhance)
  - `docs/developer/contributing.md` (new)
  - `docs/developer/architecture.md` (new)
  - `docs/developer/testing.md` (new)
- **Acceptance Criteria**:
  - Complete development environment setup guide
  - Architecture overview with component diagrams
  - Testing strategy and best practices
  - Code style guide and conventions
  - Git workflow documentation
- **Implementation Notes**: 
  - Use mermaid diagrams for architecture visualization
  - Include code examples for common tasks
  - Document the project's design decisions

**Task DOC003**: [ ] Create CONTRIBUTING.md file
- **Type**: Documentation
- **Estimated Time**: 1hr
- **Prerequisites**: DOC002
- **Files to Create/Modify**:
  - `CONTRIBUTING.md`
- **Acceptance Criteria**:
  - Clear contribution guidelines
  - Code of conduct reference
  - Pull request process
  - Issue reporting guidelines
  - Development workflow
  - Testing requirements
- **Implementation Notes**: 
  - Follow GitHub's contributing guide template
  - Include commit message conventions
  - Document review process

### Development Scripts and Tools

**Task D001**: [ ] Create development setup script
- **Type**: Code
- **Estimated Time**: 1.5hrs
- **Prerequisites**: None
- **Files to Create/Modify**:
  - `scripts/setup-dev.sh` (new)
  - `scripts/setup-dev.ps1` (new for Windows)
- **Acceptance Criteria**:
  - Automated development environment setup
  - Python version check
  - Dependency installation
  - Pre-commit hook setup
  - Environment variable configuration
  - Success/failure reporting
- **Implementation Notes**: 
```bash
#!/bin/bash
# Check Python version
# Install uv if not present
# Run uv sync
# Set up pre-commit hooks
# Create .env from .env.example
# Run initial tests
```

**Task D002**: [ ] Create developer utility scripts
- **Type**: Code
- **Estimated Time**: 1hr
- **Prerequisites**: D001
- **Files to Create/Modify**:
  - `scripts/dev-utils.sh` (new)
  - `scripts/clean.sh` (new)
  - `scripts/test-quick.sh` (new)
- **Acceptance Criteria**:
  - Quick test runner script
  - Clean build artifacts script
  - Code quality check script
  - Database reset script (if applicable)
- **Implementation Notes**: 
  - Make scripts cross-platform where possible
  - Include helpful error messages
  - Add --help flags

**Task D003**: [ ] Set up pre-commit hooks
- **Type**: Setup
- **Estimated Time**: 45min
- **Prerequisites**: None
- **Files to Create/Modify**:
  - `.pre-commit-config.yaml` (new)
  - `scripts/install-hooks.sh` (new)
- **Acceptance Criteria**:
  - Ruff linting on commit
  - Type checking with mypy
  - Test runner for changed files
  - Commit message validation
  - File size limits
- **Implementation Notes**: 
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
```

### Environment Configuration

**Task S001**: [ ] Review and enhance .env.example
- **Type**: Setup
- **Estimated Time**: 30min
- **Prerequisites**: None
- **Files to Create/Modify**:
  - `.env.example`
- **Acceptance Criteria**:
  - All configuration options documented
  - Development-specific variables added
  - Production variables clearly marked
  - Sensitive data warnings included
- **Implementation Notes**: 
  - Add database connection examples
  - Include API key placeholders
  - Document variable formats and constraints

**Task S002**: [ ] Create development environment validator
- **Type**: Code
- **Estimated Time**: 1hr
- **Prerequisites**: S001
- **Files to Create/Modify**:
  - `scripts/validate-env.py` (new)
  - `create_project/utils/env_validator.py` (new)
- **Acceptance Criteria**:
  - Validates Python version
  - Checks all required dependencies
  - Verifies environment variables
  - Tests database connectivity (if applicable)
  - Reports missing or misconfigured items
- **Implementation Notes**: 
```python
# Check Python version >= 3.9.6
# Verify uv installation
# Check PyQt6 installation
# Validate .env file exists and has required vars
# Test write permissions in required directories
```

### CI/CD Configuration

**Task DEP001**: [ ] Create GitHub Actions workflow templates
- **Type**: Deploy
- **Estimated Time**: 1hr
- **Prerequisites**: None
- **Files to Create/Modify**:
  - `.github/workflows/test.yml` (new)
  - `.github/workflows/lint.yml` (new)
  - `.github/workflows/build.yml` (new)
- **Acceptance Criteria**:
  - Test workflow runs on PR and push
  - Linting workflow with ruff
  - Build workflow for releases
  - Matrix testing for multiple Python versions
  - Coverage reporting
- **Implementation Notes**: 
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']
```

### Testing Environment

**Task T001**: [ ] Create test environment setup documentation
- **Type**: Documentation
- **Estimated Time**: 45min
- **Prerequisites**: DOC002
- **Files to Create/Modify**:
  - `docs/developer/testing.md`
- **Acceptance Criteria**:
  - Test running instructions
  - Test structure explanation
  - Mock data setup
  - GUI testing guidelines
  - Coverage requirements
- **Implementation Notes**: 
  - Document pytest fixtures
  - Explain test categorization
  - Include debugging tips

**Task T002**: [ ] Create test data fixtures and utilities
- **Type**: Test
- **Estimated Time**: 1hr
- **Prerequisites**: T001
- **Files to Create/Modify**:
  - `tests/fixtures/` (new directory)
  - `tests/conftest.py` (enhance)
  - `tests/utils.py` (new)
- **Acceptance Criteria**:
  - Reusable test fixtures
  - Mock configuration data
  - Test file generators
  - Temporary directory helpers
  - GUI test helpers
- **Implementation Notes**: 
  - Create fixture for test config
  - Mock file system operations
  - Create test template data

### IDE Configuration

**Task I001**: [ ] Create IDE configuration templates
- **Type**: Integration
- **Estimated Time**: 45min
- **Prerequisites**: None
- **Files to Create/Modify**:
  - `.vscode/settings.json` (new)
  - `.vscode/launch.json` (new)
  - `.vscode/extensions.json` (new)
  - `.idea/` (PyCharm settings, optional)
- **Acceptance Criteria**:
  - Python interpreter configuration
  - Debugging configurations
  - Recommended extensions
  - Code formatting settings
  - Test runner integration
- **Implementation Notes**: 
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

---

## Task Sequencing & Dependencies

### Critical Path:
DOC001 → DOC002 → DOC003 → T001

### Parallel Execution Opportunities:
- DOC001, D001, S001, DEP001 can start immediately
- D002 and D003 can run after D001
- S002 can run after S001
- I001 can run independently

### Estimated Total Time: 
- **Minimum**: 6 hours (critical path + parallel tasks)
- **Maximum**: 8 hours (all tasks sequential)
- **Recommended**: 7 hours (with some parallelization)

---

## Implementation Notes

### Key Focus Areas:
1. **Developer Experience**: Make setup as smooth as possible
2. **Cross-Platform**: Ensure Windows, macOS, and Linux compatibility
3. **Automation**: Automate repetitive tasks
4. **Documentation**: Over-document rather than under-document
5. **Validation**: Catch environment issues early

### Testing the Setup:
1. Test on fresh virtual machine
2. Have someone unfamiliar with the project try setup
3. Document all pain points discovered
4. Iterate on scripts and documentation

### Success Metrics:
- New developer can set up environment in < 30 minutes
- All tests pass on first run after setup
- No manual configuration required (except .env)
- Clear error messages for common issues
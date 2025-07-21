# TODO.md - Milestone 3: Core Project Generation Logic

## Section Overview
- **Section**: Milestone 3: Core Project Generation Logic
- **Total Estimated Hours**: 40 hours (2 weeks)
- **Prerequisites**: Milestone 1 (Project Setup), Milestone 2 (Template System Implementation)
- **Key Deliverables**: 
  - Core project generation engine with cross-platform support
  - Git integration with repository initialization
  - Virtual environment creation system
  - Post-creation command execution with security
  - Threading model for background operations

---

## Atomic Task List

### Setup Tasks

#### [ ] Task S001: Create Core Module Structure
**Type**: Setup  
**Estimated Time**: 30 minutes  
**Prerequisites**: None  
**Files to Create/Modify**: 
- `create_project/core/__init__.py`
- `create_project/core/exceptions.py`

**Acceptance Criteria**:
- [ ] Create core/ module directory with proper package structure
- [ ] Add ABOUTME comments to __init__.py explaining core functionality
- [ ] Define core exceptions: ProjectGenerationError, GitError, VirtualEnvError
- [ ] All imports work correctly from other modules

**Implementation Notes**:
```python
# create_project/core/exceptions.py
class ProjectGenerationError(Exception):
    """Base exception for project generation errors."""
    pass

class GitError(ProjectGenerationError):
    """Git operation errors."""
    pass

class VirtualEnvError(ProjectGenerationError):
    """Virtual environment creation errors."""
    pass
```

---

### Development Tasks

#### [ ] Task D001: Implement Cross-Platform Path Handler
**Type**: Code  
**Estimated Time**: 2 hours  
**Prerequisites**: S001  
**Files to Create/Modify**: 
- `create_project/core/path_utils.py`

**Acceptance Criteria**:
- [ ] Create PathHandler class with OS-agnostic path operations
- [ ] Implement safe_join() method to prevent path traversal attacks
- [ ] Add normalize_path() for consistent path formatting
- [ ] Support Windows, macOS, and Linux path conventions
- [ ] Handle special characters and Unicode in paths

**Implementation Notes**:
- Use pathlib.Path for cross-platform compatibility
- Implement validation for dangerous paths (../../../etc)
- Add logging for path operations
- Consider case sensitivity differences between OS

#### [ ] Task D002: Create Project Directory Structure Generator
**Type**: Code  
**Estimated Time**: 3 hours  
**Prerequisites**: D001, S001  
**Files to Create/Modify**: 
- `create_project/core/directory_creator.py`

**Acceptance Criteria**:
- [ ] DirectoryCreator class creates nested directory structures
- [ ] Handle permissions and ownership correctly across platforms
- [ ] Implement rollback mechanism for failed creations
- [ ] Support dry-run mode for testing
- [ ] Log all directory creation operations

**Implementation Notes**:
```python
class DirectoryCreator:
    def __init__(self, base_path: Path, logger: Logger):
        self.base_path = base_path
        self.logger = logger
        self.created_dirs: List[Path] = []
    
    def create_structure(self, structure: Dict, dry_run: bool = False) -> None:
        """Create directory structure from template data."""
        pass
    
    def rollback(self) -> None:
        """Remove all created directories in reverse order."""
        pass
```

#### [ ] Task D003: Implement File Template Renderer
**Type**: Code  
**Estimated Time**: 4 hours  
**Prerequisites**: D001, D002  
**Files to Create/Modify**: 
- `create_project/core/file_renderer.py`

**Acceptance Criteria**:
- [ ] FileRenderer class processes template files with Jinja2
- [ ] Handle binary and text files appropriately
- [ ] Support file permissions and executable flags
- [ ] Implement template variable substitution
- [ ] Add file encoding detection and handling

**Implementation Notes**:
- Integration with existing template engine from Milestone 2
- Handle file creation with proper permissions
- Support conditional file creation based on template logic
- Add progress reporting for long operations

#### [ ] Task D004: Create Core Project Generator Class
**Type**: Code  
**Estimated Time**: 4 hours  
**Prerequisites**: D001, D002, D003  
**Files to Create/Modify**: 
- `create_project/core/project_generator.py`

**Acceptance Criteria**:
- [ ] ProjectGenerator orchestrates entire project creation process
- [ ] Integration with template system from Milestone 2
- [ ] Atomic operations with full rollback capability
- [ ] Progress reporting through callback system
- [ ] Comprehensive error handling and logging

**Implementation Notes**:
```python
class ProjectGenerator:
    def __init__(self, config_manager: ConfigManager, logger: Logger):
        self.config_manager = config_manager
        self.logger = logger
        self.directory_creator = DirectoryCreator(...)
        self.file_renderer = FileRenderer(...)
    
    def generate_project(
        self, 
        template: Template, 
        variables: Dict[str, Any], 
        target_path: Path,
        progress_callback: Optional[Callable] = None
    ) -> GenerationResult:
        """Main project generation entry point."""
        pass
```

#### [ ] Task D005: Implement Git Repository Manager
**Type**: Code  
**Estimated Time**: 3 hours  
**Prerequisites**: S001  
**Files to Create/Modify**: 
- `create_project/core/git_manager.py`

**Acceptance Criteria**:
- [ ] GitManager class handles git repository operations
- [ ] Initialize new repositories with proper configuration
- [ ] Create initial commit with generated files
- [ ] Handle git not installed gracefully
- [ ] Support custom git configuration (user.name, user.email)

**Implementation Notes**:
```python
class GitManager:
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def is_git_available(self) -> bool:
        """Check if git is installed and accessible."""
        pass
    
    def init_repository(self, project_path: Path) -> None:
        """Initialize git repository in project directory."""
        pass
    
    def create_initial_commit(self, project_path: Path, message: str) -> None:
        """Create initial commit with all generated files."""
        pass
```

#### [ ] Task D006: Create Virtual Environment Manager
**Type**: Code  
**Estimated Time**: 4 hours  
**Prerequisites**: D001, S001  
**Files to Create/Modify**: 
- `create_project/core/venv_manager.py`

**Acceptance Criteria**:
- [ ] VenvManager supports multiple venv tools (venv, virtualenv, uv)
- [ ] Automatic tool detection and fallback
- [ ] Cross-platform virtual environment creation
- [ ] Integration with Python version management
- [ ] Handle tool-specific configuration

**Implementation Notes**:
- Priority order: uv > virtualenv > venv (standard library)
- Support Python version specification
- Add environment variable activation instructions
- Log tool selection and creation process

#### [ ] Task D007: Implement Post-Creation Command Executor
**Type**: Code  
**Estimated Time**: 3 hours  
**Prerequisites**: D001, S001  
**Files to Create/Modify**: 
- `create_project/core/command_executor.py`

**Acceptance Criteria**:
- [ ] CommandExecutor runs template-defined post-creation commands
- [ ] Command sanitization to prevent injection attacks
- [ ] Whitelist of allowed commands and arguments
- [ ] Timeout handling for long-running commands
- [ ] Capture and log command output

**Implementation Notes**:
```python
class CommandExecutor:
    ALLOWED_COMMANDS = {
        'pip', 'uv', 'npm', 'poetry', 'git', 'chmod', 'mkdir'
    }
    
    def execute_command(
        self, 
        command: str, 
        cwd: Path, 
        timeout: int = 300
    ) -> ExecutionResult:
        """Execute a single command with security checks."""
        pass
    
    def execute_commands(
        self, 
        commands: List[str], 
        cwd: Path,
        progress_callback: Optional[Callable] = None
    ) -> List[ExecutionResult]:
        """Execute multiple commands in sequence."""
        pass
```

#### [ ] Task D008: Create Background Threading Model
**Type**: Code  
**Estimated Time**: 4 hours  
**Prerequisites**: D004, D005, D006, D007  
**Files to Create/Modify**: 
- `create_project/core/threading_model.py`

**Acceptance Criteria**:
- [ ] ThreadingModel manages background project generation
- [ ] Thread-safe progress reporting with signals/callbacks
- [ ] Cancellation support for long operations
- [ ] Error propagation from background threads
- [ ] Resource cleanup on thread completion/cancellation

**Implementation Notes**:
- Use QThread for PyQt integration (future GUI work)
- Implement progress signals for UI updates
- Add thread pool for parallel file operations
- Ensure proper cleanup of system resources

---

### Integration Tasks

#### [ ] Task I001: Integrate Components in Project Generator
**Type**: Integration  
**Estimated Time**: 2 hours  
**Prerequisites**: D004, D005, D006, D007  
**Files to Create/Modify**: 
- `create_project/core/project_generator.py` (update)

**Acceptance Criteria**:
- [ ] ProjectGenerator uses GitManager for repository setup
- [ ] Virtual environment creation integrated in generation flow
- [ ] Post-creation commands execute after file generation
- [ ] All components share logging and error handling
- [ ] Progress reporting flows through all components

**Implementation Notes**:
- Update ProjectGenerator.generate_project() method
- Add component initialization in constructor
- Implement proper error handling chain

#### [ ] Task I002: Create Core API Interface
**Type**: Integration  
**Estimated Time**: 2 hours  
**Prerequisites**: I001  
**Files to Create/Modify**: 
- `create_project/core/__init__.py` (update)
- `create_project/core/api.py`

**Acceptance Criteria**:
- [ ] Clean API interface for external modules
- [ ] Standardized method signatures
- [ ] Proper exception handling and propagation
- [ ] Integration with configuration system
- [ ] Documentation strings for all public methods

**Implementation Notes**:
```python
# create_project/core/api.py
def create_project(
    template_name: str,
    project_name: str,
    target_directory: Path,
    variables: Dict[str, Any],
    options: ProjectOptions
) -> ProjectResult:
    """Main API entry point for project creation."""
    pass
```

---

### Testing Tasks

#### [ ] Task T001: Write Unit Tests for Path Utilities
**Type**: Test  
**Estimated Time**: 1 hour  
**Prerequisites**: D001  
**Files to Create/Modify**: 
- `tests/unit/core/test_path_utils.py`

**Acceptance Criteria**:
- [ ] Test cross-platform path handling
- [ ] Test path traversal attack prevention
- [ ] Test Unicode and special character handling
- [ ] Test path normalization across OS types
- [ ] Achieve >90% code coverage

**Implementation Notes**:
- Use pytest fixtures for different OS simulation
- Test edge cases like empty paths, root paths
- Mock os.path and pathlib for platform testing

#### [ ] Task T002: Write Unit Tests for Directory Creator
**Type**: Test  
**Estimated Time**: 1.5 hours  
**Prerequisites**: D002  
**Files to Create/Modify**: 
- `tests/unit/core/test_directory_creator.py`

**Acceptance Criteria**:
- [ ] Test directory structure creation
- [ ] Test rollback mechanism
- [ ] Test permission handling
- [ ] Test dry-run mode
- [ ] Test error conditions and cleanup

**Implementation Notes**:
- Use temporary directories for testing
- Test nested directory creation
- Verify rollback removes all created directories

#### [ ] Task T003: Write Unit Tests for File Renderer
**Type**: Test  
**Estimated Time**: 2 hours  
**Prerequisites**: D003  
**Files to Create/Modify**: 
- `tests/unit/core/test_file_renderer.py`

**Acceptance Criteria**:
- [ ] Test template variable substitution
- [ ] Test binary and text file handling
- [ ] Test file permission setting
- [ ] Test encoding detection
- [ ] Test error conditions

**Implementation Notes**:
- Create test templates with various variable types
- Test file rendering with different encodings
- Verify executable permission handling

#### [ ] Task T004: Write Unit Tests for Git Manager
**Type**: Test  
**Estimated Time**: 1.5 hours  
**Prerequisites**: D005  
**Files to Create/Modify**: 
- `tests/unit/core/test_git_manager.py`

**Acceptance Criteria**:
- [ ] Test git availability detection
- [ ] Test repository initialization
- [ ] Test initial commit creation
- [ ] Test error handling when git unavailable
- [ ] Mock git commands for testing

**Implementation Notes**:
- Mock subprocess calls to git
- Test both git available and unavailable scenarios
- Verify proper error messages and logging

#### [ ] Task T005: Write Unit Tests for Virtual Environment Manager
**Type**: Test  
**Estimated Time**: 2 hours  
**Prerequisites**: D006  
**Files to Create/Modify**: 
- `tests/unit/core/test_venv_manager.py`

**Acceptance Criteria**:
- [ ] Test venv tool detection and fallback
- [ ] Test virtual environment creation
- [ ] Test cross-platform compatibility
- [ ] Test error handling for tool failures
- [ ] Mock external tool calls

**Implementation Notes**:
- Mock venv, virtualenv, and uv commands
- Test tool priority and fallback logic
- Verify environment creation in different scenarios

#### [ ] Task T006: Write Unit Tests for Command Executor
**Type**: Test  
**Estimated Time**: 1.5 hours  
**Prerequisites**: D007  
**Files to Create/Modify**: 
- `tests/unit/core/test_command_executor.py`

**Acceptance Criteria**:
- [ ] Test command sanitization
- [ ] Test whitelist enforcement
- [ ] Test timeout handling
- [ ] Test command output capture
- [ ] Test injection attack prevention

**Implementation Notes**:
- Test malicious command rejection
- Mock subprocess for command execution
- Test timeout scenarios with long-running commands

#### [ ] Task T007: Write Unit Tests for Threading Model
**Type**: Test  
**Estimated Time**: 2 hours  
**Prerequisites**: D008  
**Files to Create/Modify**: 
- `tests/unit/core/test_threading_model.py`

**Acceptance Criteria**:
- [ ] Test background thread execution
- [ ] Test progress reporting
- [ ] Test cancellation handling
- [ ] Test error propagation
- [ ] Test resource cleanup

**Implementation Notes**:
- Use threading test utilities
- Test progress callback invocation
- Verify proper thread cleanup on completion/cancellation

#### [ ] Task T008: Write Integration Tests for Project Generator
**Type**: Test  
**Estimated Time**: 3 hours  
**Prerequisites**: I001, I002  
**Files to Create/Modify**: 
- `tests/integration/core/test_project_generator.py`

**Acceptance Criteria**:
- [ ] Test complete project generation workflow
- [ ] Test integration with template system
- [ ] Test git integration
- [ ] Test virtual environment creation
- [ ] Test post-creation command execution

**Implementation Notes**:
- Use real templates from Milestone 2
- Test with temporary directories
- Verify complete project structure creation
- Test rollback on failures

---

### Documentation Tasks

#### [ ] Task DOC001: Document Core Module API
**Type**: Documentation  
**Estimated Time**: 2 hours  
**Prerequisites**: I002  
**Files to Create/Modify**: 
- `create_project/core/README.md`
- Update docstrings in all core modules

**Acceptance Criteria**:
- [ ] Complete API documentation for all public methods
- [ ] Usage examples for ProjectGenerator
- [ ] Error handling documentation
- [ ] Configuration requirements
- [ ] Cross-platform considerations

**Implementation Notes**:
- Use Google-style docstrings
- Include code examples
- Document all exception types
- Add architectural overview

#### [ ] Task DOC002: Create Development Guide for Core Module
**Type**: Documentation  
**Estimated Time**: 1 hour  
**Prerequisites**: All previous tasks  
**Files to Create/Modify**: 
- `docs/core-development.md`

**Acceptance Criteria**:
- [ ] Guide for extending core functionality
- [ ] Testing requirements and patterns
- [ ] Security considerations
- [ ] Performance best practices
- [ ] Cross-platform development tips

**Implementation Notes**:
- Include testing patterns used in the module
- Document security validation requirements
- Add performance optimization guidelines

---

## Task Sequencing & Dependencies

### Phase 1: Foundation (Week 1, Days 1-3)
- S001 → D001 → D002 → D003 → T001, T002, T003

### Phase 2: Core Components (Week 1, Days 4-5)
- D004 → D005 → D006 → T004, T005

### Phase 3: Advanced Features (Week 2, Days 1-3)
- D007 → D008 → T006, T007

### Phase 4: Integration & Testing (Week 2, Days 4-5)
- I001 → I002 → T008 → DOC001 → DOC002

### Parallel Execution Opportunities:
- T001, T002, T003 can run in parallel after their respective development tasks
- T004, T005 can run in parallel after D005, D006
- Documentation tasks can start once API is stable

### Critical Path:
S001 → D001 → D002 → D003 → D004 → I001 → I002 → T008

---

## Success Metrics

- [ ] All unit tests pass (>90% code coverage)
- [ ] Integration tests demonstrate complete workflow
- [ ] Cross-platform compatibility verified
- [ ] Security validation prevents injection attacks
- [ ] Performance acceptable for typical project sizes
- [ ] Thread safety verified under concurrent operations
- [ ] Complete API documentation available

---

## Risk Mitigation

1. **Path Handling**: Test extensively on Windows paths with drive letters
2. **Permissions**: Handle read-only directories and permission denied errors
3. **Git Dependencies**: Graceful fallback when git unavailable
4. **Virtual Environment**: Multiple tool support for different environments
5. **Security**: Strict command validation to prevent injection
6. **Threading**: Proper resource cleanup to prevent memory leaks
7. **Cross-Platform**: Test file permissions and path handling across OS

---

**Ready for Implementation**: FX, this milestone is structured for systematic development with clear deliverables and comprehensive testing. Each task builds logically on the previous work while maintaining the high code quality standards established in Milestones 1 and 2.
# ABOUTME: Comprehensive unit tests for template structure schema classes
# ABOUTME: Tests ItemType, FileEncoding, FilePermissions, ConditionalExpression, FileItem, DirectoryItem, and ProjectStructure models

"""Unit tests for template structure schema classes."""

import pytest
from pydantic import ValidationError

from create_project.templates.schema.structure import (
    ConditionalExpression,
    DirectoryItem,
    FileEncoding,
    FileItem,
    FilePermissions,
    ItemType,
    ProjectStructure,
    TemplateFile,
    TemplateFiles,
)


class TestItemType:
    """Test ItemType enum."""

    def test_all_item_types(self):
        """Test all item type values."""
        expected_types = ["file", "directory", "symlink"]
        actual_types = [item.value for item in ItemType]
        assert actual_types == expected_types

    def test_item_type_enum_values(self):
        """Test individual item type enum values."""
        assert ItemType.FILE == "file"
        assert ItemType.DIRECTORY == "directory"
        assert ItemType.SYMLINK == "symlink"


class TestFileEncoding:
    """Test FileEncoding enum."""

    def test_all_encodings(self):
        """Test all encoding values."""
        expected_encodings = ["utf-8", "ascii", "latin-1", "binary"]
        actual_encodings = [enc.value for enc in FileEncoding]
        assert actual_encodings == expected_encodings

    def test_encoding_enum_values(self):
        """Test individual encoding enum values."""
        assert FileEncoding.UTF8 == "utf-8"
        assert FileEncoding.ASCII == "ascii"
        assert FileEncoding.LATIN1 == "latin-1"
        assert FileEncoding.BINARY == "binary"


class TestFilePermissions:
    """Test FilePermissions enum."""

    def test_all_permissions(self):
        """Test all permission values."""
        # Note: Python enums with duplicate values create aliases
        # SCRIPT is an alias for EXECUTABLE (both "755")
        # PUBLIC is an alias for READ_WRITE (both "644")
        
        # Check we have the expected unique enum members (aliases not included in iteration)
        all_perms = list(FilePermissions)
        assert len(all_perms) == 4  # Only non-alias members
        
        # Check all members are accessible (including aliases)
        assert FilePermissions.READ_ONLY.value == "444"
        assert FilePermissions.READ_WRITE.value == "644"
        assert FilePermissions.EXECUTABLE.value == "755"
        assert FilePermissions.SCRIPT.value == "755"  # Alias of EXECUTABLE
        assert FilePermissions.PRIVATE.value == "600"
        assert FilePermissions.PUBLIC.value == "644"  # Alias of READ_WRITE
        
        # Verify SCRIPT and PUBLIC are aliases
        assert FilePermissions.SCRIPT is FilePermissions.EXECUTABLE
        assert FilePermissions.PUBLIC is FilePermissions.READ_WRITE
        
        # Check unique values
        unique_values = set(perm.value for perm in FilePermissions)
        assert len(unique_values) == 4  # Only 4 unique permission values

    def test_permission_enum_values(self):
        """Test individual permission enum values."""
        assert FilePermissions.READ_ONLY == "444"
        assert FilePermissions.READ_WRITE == "644"
        assert FilePermissions.EXECUTABLE == "755"
        assert FilePermissions.SCRIPT == "755"
        assert FilePermissions.PRIVATE == "600"
        assert FilePermissions.PUBLIC == "644"


class TestConditionalExpression:
    """Test ConditionalExpression model."""

    def test_minimal_expression(self):
        """Test creating minimal conditional expression."""
        expr = ConditionalExpression(expression="{{ use_feature }}")
        assert expr.expression == "{{ use_feature }}"
        assert expr.variables is None

    def test_expression_with_variables(self):
        """Test expression with tracked variables."""
        expr = ConditionalExpression(
            expression="{{ use_feature and has_dependency }}",
            variables=["use_feature", "has_dependency"]
        )
        assert expr.expression == "{{ use_feature and has_dependency }}"
        assert expr.variables == ["use_feature", "has_dependency"]

    def test_simple_variable_expression(self):
        """Test simple variable name without Jinja2 syntax."""
        expr = ConditionalExpression(expression="use_feature")
        assert expr.expression == "use_feature"

    def test_empty_expression_validation(self):
        """Test empty expression raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConditionalExpression(expression="")
        errors = exc_info.value.errors()
        assert any("Expression cannot be empty" in str(e) for e in errors)

    def test_whitespace_expression_validation(self):
        """Test whitespace-only expression raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConditionalExpression(expression="   ")
        errors = exc_info.value.errors()
        assert any("Expression cannot be empty" in str(e) for e in errors)

    def test_invalid_expression_syntax(self):
        """Test invalid expression syntax raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConditionalExpression(expression="use feature")  # Space in variable name
        errors = exc_info.value.errors()
        assert any("must be valid Jinja2 syntax" in str(e) for e in errors)

    def test_complex_jinja_expression(self):
        """Test complex Jinja2 expressions."""
        expressions = [
            "{{ project_type == 'library' }}",
            "{{ features.includes_tests }}",
            "{{ version > '1.0' and stable }}",
            "{{ 'api' in modules }}"
        ]
        for expr_str in expressions:
            expr = ConditionalExpression(expression=expr_str)
            assert expr.expression == expr_str


class TestFileItem:
    """Test FileItem model."""

    def test_minimal_file_with_content(self):
        """Test creating minimal file with inline content."""
        file_item = FileItem(
            name="README.md",
            content="# Project README"
        )
        assert file_item.name == "README.md"
        assert file_item.type == ItemType.FILE
        assert file_item.content == "# Project README"
        assert file_item.encoding == FileEncoding.UTF8
        assert file_item.permissions == FilePermissions.READ_WRITE
        assert file_item.executable is False

    def test_file_with_template(self):
        """Test file with template file reference."""
        file_item = FileItem(
            name="setup.py",
            template_file="templates/setup.py.j2"
        )
        assert file_item.name == "setup.py"
        assert file_item.template_file == "templates/setup.py.j2"
        assert file_item.content is None

    def test_binary_file_with_source(self):
        """Test binary file with source file."""
        file_item = FileItem(
            name="logo.png",
            source_file="assets/logo.png",
            encoding=FileEncoding.BINARY,
            is_binary=True
        )
        assert file_item.name == "logo.png"
        assert file_item.source_file == "assets/logo.png"
        assert file_item.encoding == FileEncoding.BINARY
        assert file_item.is_binary is True

    def test_executable_file(self):
        """Test executable file configuration."""
        file_item = FileItem(
            name="run.sh",
            content="#!/bin/bash\necho 'Hello'",
            permissions=FilePermissions.EXECUTABLE,
            executable=True
        )
        assert file_item.permissions == FilePermissions.EXECUTABLE
        assert file_item.executable is True

    def test_file_with_condition(self):
        """Test file with conditional creation."""
        condition = ConditionalExpression(
            expression="{{ include_tests }}",
            variables=["include_tests"]
        )
        file_item = FileItem(
            name="test_main.py",
            content="import pytest",
            condition=condition
        )
        assert file_item.condition.expression == "{{ include_tests }}"

    def test_file_name_validation(self):
        """Test file name validation."""
        # Valid names
        valid_names = ["file.txt", "my-file.py", "test_data.json", "README"]
        for name in valid_names:
            file_item = FileItem(name=name, content="test")
            assert file_item.name == name

        # Empty name
        with pytest.raises(ValidationError) as exc_info:
            FileItem(name="", content="test")
        errors = exc_info.value.errors()
        assert any("File name cannot be empty" in str(e) for e in errors)

        # Invalid characters
        invalid_names = ["file<>.txt", "test:file", 'file"name', "file?", "file*"]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                FileItem(name=name, content="test")

    def test_windows_reserved_names(self):
        """Test Windows reserved file names are rejected."""
        reserved_names = ["CON", "con.txt", "PRN.log", "AUX", "NUL.dat", 
                         "COM1", "COM9", "LPT1", "LPT9"]
        for name in reserved_names:
            with pytest.raises(ValidationError) as exc_info:
                FileItem(name=name, content="test")
            errors = exc_info.value.errors()
            assert any("reserved on Windows" in str(e) for e in errors)

    def test_file_path_validation(self):
        """Test template and source file path validation."""
        # Valid relative paths
        valid_paths = ["templates/file.j2", "assets/logo.png", "src/template.txt"]
        for path in valid_paths:
            file_item = FileItem(name="test", template_file=path)
            assert file_item.template_file == path

        # Absolute paths not allowed
        with pytest.raises(ValidationError) as exc_info:
            FileItem(name="test", template_file="/etc/template.j2")
        errors = exc_info.value.errors()
        assert any("must be relative" in str(e) for e in errors)

        # Directory traversal not allowed
        with pytest.raises(ValidationError) as exc_info:
            FileItem(name="test", source_file="../../../etc/passwd")
        errors = exc_info.value.errors()
        assert any("cannot contain '..'" in str(e) for e in errors)

    def test_permissions_validation(self):
        """Test file permissions validation."""
        # FilePermissions is an enum, so we use enum values
        file_item = FileItem(
            name="test", 
            content="data", 
            permissions=FilePermissions.PRIVATE
        )
        assert file_item.permissions == FilePermissions.PRIVATE
        
        # Test using string value
        file_item2 = FileItem(
            name="test",
            content="data",
            permissions="600"  # Should match FilePermissions.PRIVATE
        )
        assert file_item2.permissions == "600"

    def test_validate_content_source(self):
        """Test content source validation."""
        # Valid: exactly one source
        file1 = FileItem(name="test", content="inline content")
        file1.validate_content_source()  # Should not raise

        file2 = FileItem(name="test", template_file="template.j2")
        file2.validate_content_source()  # Should not raise

        file3 = FileItem(name="test", source_file="source.bin")
        file3.validate_content_source()  # Should not raise

        # Invalid: no content source
        file4 = FileItem(name="test")
        with pytest.raises(ValueError) as exc_info:
            file4.validate_content_source()
        assert "must have content" in str(exc_info.value)

        # Invalid: multiple content sources
        file5 = FileItem(
            name="test",
            content="inline",
            template_file="template.j2"
        )
        with pytest.raises(ValueError) as exc_info:
            file5.validate_content_source()
        assert "can only have one of" in str(exc_info.value)

    def test_file_with_all_options(self):
        """Test file with all configuration options."""
        condition = ConditionalExpression(expression="{{ use_advanced }}")
        file_item = FileItem(
            name="{{ project_name }}_config.yml",
            template_file="templates/config.yml.j2",
            encoding=FileEncoding.UTF8,
            permissions=FilePermissions.PRIVATE,
            executable=False,
            condition=condition,
            target_path="config/custom.yml",
            is_binary=False,
            preserve_line_endings=True
        )
        assert file_item.target_path == "config/custom.yml"
        assert file_item.preserve_line_endings is True


class TestDirectoryItem:
    """Test DirectoryItem model."""

    def test_minimal_directory(self):
        """Test creating minimal directory."""
        dir_item = DirectoryItem(name="src")
        assert dir_item.name == "src"
        assert dir_item.type == ItemType.DIRECTORY
        assert dir_item.permissions == FilePermissions.EXECUTABLE
        assert dir_item.files == []
        assert dir_item.directories == []

    def test_directory_with_items(self):
        """Test directory with nested items."""
        file1 = FileItem(name="__init__.py", content="")
        file2 = FileItem(name="main.py", content="# Main module")
        
        dir_item = DirectoryItem(
            name="mypackage",
            files=[file1, file2]
        )
        assert len(dir_item.files) == 2
        assert dir_item.files[0].name == "__init__.py"
        assert dir_item.files[1].name == "main.py"

    def test_nested_directories(self):
        """Test nested directory structure."""
        subfile = FileItem(name="util.py", content="# Utilities")
        subdir = DirectoryItem(name="utils", files=[subfile])
        
        main_dir = DirectoryItem(
            name="src",
            files=[FileItem(name="__init__.py", content="")],
            directories=[subdir]
        )
        assert len(main_dir.files) == 1
        assert len(main_dir.directories) == 1
        assert isinstance(main_dir.directories[0], DirectoryItem)
        assert main_dir.directories[0].name == "utils"

    def test_directory_name_validation(self):
        """Test directory name validation."""
        # Valid names
        valid_names = ["src", "test-data", "my_project", ".config"]
        for name in valid_names:
            dir_item = DirectoryItem(name=name)
            assert dir_item.name == name

        # Empty name
        with pytest.raises(ValidationError) as exc_info:
            DirectoryItem(name="")
        errors = exc_info.value.errors()
        assert any("Directory name cannot be empty" in str(e) for e in errors)

        # Invalid characters
        invalid_names = ["dir<>", "test:dir", 'dir"name', "dir?", "dir*"]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                DirectoryItem(name=name)

    def test_directory_with_condition(self):
        """Test conditional directory creation."""
        condition = ConditionalExpression(expression="{{ include_docs }}")
        dir_item = DirectoryItem(
            name="docs",
            condition=condition
        )
        assert dir_item.condition.expression == "{{ include_docs }}"

    def test_directory_permissions(self):
        """Test directory permissions."""
        dir_item = DirectoryItem(
            name="private",
            permissions=FilePermissions.PRIVATE
        )
        assert dir_item.permissions == FilePermissions.PRIVATE

    def test_create_if_empty(self):
        """Test create_if_empty option."""
        dir_item = DirectoryItem(
            name="logs",
            create_if_empty=True
        )
        assert dir_item.create_if_empty is True

    def test_validate_structure(self):
        """Test validate_structure method."""
        # Valid structure
        dir1 = DirectoryItem(
            name="test",
            files=[FileItem(name="file1.txt", content="test")],
            directories=[DirectoryItem(name="subdir")]
        )
        errors = dir1.validate_structure()
        assert len(errors) == 0

        # Duplicate file names
        dir2 = DirectoryItem(
            name="test",
            files=[
                FileItem(name="duplicate.txt", content="first"),
                FileItem(name="duplicate.txt", content="second")
            ]
        )
        errors = dir2.validate_structure()
        assert len(errors) == 1
        assert "Duplicate file names" in errors[0]

        # Duplicate directory names
        dir3 = DirectoryItem(
            name="test",
            directories=[
                DirectoryItem(name="subdir"),
                DirectoryItem(name="subdir")
            ]
        )
        errors = dir3.validate_structure()
        assert len(errors) == 1
        assert "Duplicate directory names" in errors[0]

        # Name conflict between file and directory
        dir4 = DirectoryItem(
            name="test",
            files=[FileItem(name="conflict", content="file")],
            directories=[DirectoryItem(name="conflict")]
        )
        errors = dir4.validate_structure()
        assert len(errors) == 1
        assert "Name conflicts" in errors[0]

    def test_get_all_files_and_directories(self):
        """Test get_all_files and get_all_directories methods."""
        helper_file = FileItem(name="helper.py", content="")
        utils_dir = DirectoryItem(
            name="utils",
            files=[helper_file]
        )
        
        dir_item = DirectoryItem(
            name="project",
            files=[
                FileItem(name="README.md", content="# README"),
                FileItem(name="setup.py", content="")
            ],
            directories=[
                DirectoryItem(
                    name="src",
                    files=[FileItem(name="main.py", content="")],
                    directories=[utils_dir]
                )
            ]
        )
        
        # Test get_all_files
        all_files = dir_item.get_all_files()
        file_names = [f.name for f in all_files]
        assert len(all_files) == 4
        assert "README.md" in file_names
        assert "setup.py" in file_names
        assert "main.py" in file_names
        assert "helper.py" in file_names
        
        # Test get_all_directories
        all_dirs = dir_item.get_all_directories()
        dir_names = [d.name for d in all_dirs]
        assert len(all_dirs) == 2
        assert "src" in dir_names
        assert "utils" in dir_names


class TestProjectStructure:
    """Test ProjectStructure model."""

    def test_minimal_structure(self):
        """Test creating minimal project structure."""
        root = DirectoryItem(name="project")
        structure = ProjectStructure(root_directory=root)
        assert structure.root_directory.name == "project"

    def test_structure_with_items(self):
        """Test project structure with root items."""
        root = DirectoryItem(
            name="myproject",
            files=[
                FileItem(name="README.md", content="# Project"),
                FileItem(name=".gitignore", content="*.pyc")
            ],
            directories=[DirectoryItem(name="src")]
        )
        structure = ProjectStructure(root_directory=root)
        assert len(structure.root_directory.files) == 2
        assert len(structure.root_directory.directories) == 1

    def test_validate_structure(self):
        """Test validate_structure method."""
        # Valid structure
        root1 = DirectoryItem(
            name="project",
            files=[FileItem(name="file1.py", content="")],
            directories=[DirectoryItem(name="dir1")]
        )
        structure1 = ProjectStructure(root_directory=root1)
        errors = structure1.validate_structure()
        assert len(errors) == 0

        # Duplicate names at root
        root2 = DirectoryItem(
            name="project",
            files=[FileItem(name="duplicate", content="")],
            directories=[DirectoryItem(name="duplicate")]
        )
        structure2 = ProjectStructure(root_directory=root2)
        errors = structure2.validate_structure()
        assert len(errors) == 1
        assert "Name conflicts" in errors[0]

    def test_get_all_files_and_directories(self):
        """Test getting all files and directories in structure."""
        root = DirectoryItem(
            name="project",
            files=[FileItem(name="README.md", content="")],
            directories=[
                DirectoryItem(
                    name="src",
                    files=[FileItem(name="__init__.py", content="")],
                    directories=[
                        DirectoryItem(
                            name="core",
                            files=[FileItem(name="main.py", content="")]
                        )
                    ]
                )
            ]
        )
        structure = ProjectStructure(root_directory=root)
        
        # Test get_all_files
        all_files = structure.get_all_files()
        file_names = [f.name for f in all_files]
        assert len(all_files) == 3
        assert "README.md" in file_names
        assert "__init__.py" in file_names
        assert "main.py" in file_names
        
        # Test get_all_directories
        all_dirs = structure.get_all_directories()
        dir_names = [d.name for d in all_dirs]
        assert len(all_dirs) == 2
        assert "src" in dir_names
        assert "core" in dir_names

    def test_complex_project_structure(self):
        """Test complex real-world project structure."""
        utils_dir = DirectoryItem(
            name="utils",
            files=[
                FileItem(name="__init__.py", content=""),
                FileItem(name="helpers.py", content="# Utility functions")
            ]
        )
        
        package_dir = DirectoryItem(
            name="{{ project_name }}",
            files=[
                FileItem(name="__init__.py", content='__version__ = "0.1.0"'),
                FileItem(name="main.py", template_file="templates/main.py.j2")
            ],
            directories=[utils_dir]
        )
        
        tests_dir = DirectoryItem(
            name="tests",
            condition=ConditionalExpression(expression="{{ include_tests }}"),
            files=[
                FileItem(name="__init__.py", content=""),
                FileItem(name="test_main.py", template_file="templates/test_main.py.j2")
            ]
        )
        
        docs_dir = DirectoryItem(
            name="docs",
            condition=ConditionalExpression(expression="{{ include_docs }}"),
            create_if_empty=True
        )
        
        root = DirectoryItem(
            name="myproject",
            files=[
                FileItem(name="README.md", template_file="templates/README.md.j2"),
                FileItem(name=".gitignore", content="*.pyc\n__pycache__/\n.env"),
                FileItem(
                    name="setup.py",
                    template_file="templates/setup.py.j2",
                    permissions=FilePermissions.READ_WRITE
                )
            ],
            directories=[package_dir, tests_dir, docs_dir]
        )
        
        structure = ProjectStructure(root_directory=root)
        
        # Validate structure
        errors = structure.validate_structure()
        assert len(errors) == 0
        
        # Check file and directory counts
        all_files = structure.get_all_files()
        all_dirs = structure.get_all_directories()
        assert len(all_files) >= 7  # Should have many files
        assert len(all_dirs) >= 4   # Should have several directories


class TestTemplateFile:
    """Test TemplateFile model."""

    def test_minimal_template_file(self):
        """Test creating minimal template file."""
        tpl_file = TemplateFile(
            name="README.md.j2",
            content="# {{ project_name }}"
        )
        assert tpl_file.name == "README.md.j2"
        assert tpl_file.content == "# {{ project_name }}"
        assert tpl_file.encoding == FileEncoding.UTF8

    def test_template_file_validation(self):
        """Test template file validation."""
        # Valid template file
        tpl_file = TemplateFile(
            name="config.yml.j2",
            content="name: {{ project_name }}",
            description="Configuration template"
        )
        assert tpl_file.name == "config.yml.j2"
        assert tpl_file.get_output_name() == "config.yml"

        # Empty name
        with pytest.raises(ValidationError) as exc_info:
            TemplateFile(name="", content="test")
        errors = exc_info.value.errors()
        assert any("cannot be empty" in str(e) for e in errors)

        # Name without .j2 extension
        with pytest.raises(ValidationError) as exc_info:
            TemplateFile(name="test.txt", content="test")
        errors = exc_info.value.errors()
        assert any("must end with '.j2'" in str(e) for e in errors)

    def test_template_file_variables_used(self):
        """Test template file variables tracking."""
        tpl_file = TemplateFile(
            name="main.py.j2",
            content="# {{ project_name }}\n# {{ author }}",
            variables_used=["project_name", "author"]
        )
        assert len(tpl_file.variables_used) == 2
        assert "project_name" in tpl_file.variables_used
        assert "author" in tpl_file.variables_used


class TestTemplateFiles:
    """Test TemplateFiles model."""

    def test_empty_template_files(self):
        """Test creating empty template files collection."""
        tpl_files = TemplateFiles()
        assert tpl_files.files == []

    def test_template_files_collection(self):
        """Test template files collection."""
        files = [
            TemplateFile(name="README.md.j2", content="# {{ project_name }}"),
            TemplateFile(name="setup.py.j2", content="setup(name='{{ project_name }}')")
        ]
        tpl_files = TemplateFiles(files=files)
        assert len(tpl_files.files) == 2

    def test_validate_templates(self):
        """Test validate_templates method."""
        # No duplicates
        tpl_files1 = TemplateFiles(
            files=[
                TemplateFile(name="file1.j2", content="test1"),
                TemplateFile(name="file2.j2", content="test2")
            ]
        )
        errors = tpl_files1.validate_templates()
        assert len(errors) == 0

        # Duplicate names
        tpl_files2 = TemplateFiles(
            files=[
                TemplateFile(name="template.j2", content="first"),
                TemplateFile(name="template.j2", content="second")
            ]
        )
        errors = tpl_files2.validate_templates()
        assert len(errors) == 1
        assert "Duplicate template file" in errors[0]
# ABOUTME: Unit tests for template structure models
# ABOUTME: Tests file/directory structure definitions and project structure

"""Tests for template structure models."""

import pytest
from pydantic import ValidationError

from create_project.templates.schema.structure import (
    DirectoryStructure,
    FileStructure,
    ProjectStructure,
    TemplateFiles,
)


class TestFileStructure:
    """Test file structure model."""

    def test_minimal_file(self):
        """Test creating file with minimal fields."""
        file = FileStructure(
            path="README.md",
            content="# Project\n\nDescription here."
        )
        assert file.path == "README.md"
        assert file.content == "# Project\n\nDescription here."
        assert file.template_path is None
        assert file.permissions is None
        assert file.encoding == "utf-8"

    def test_file_with_template(self):
        """Test file with template path."""
        file = FileStructure(
            path="src/main.py",
            template_path="templates/python/main.py.j2"
        )
        assert file.path == "src/main.py"
        assert file.content is None
        assert file.template_path == "templates/python/main.py.j2"

    def test_file_with_permissions(self):
        """Test file with permissions."""
        file = FileStructure(
            path="scripts/deploy.sh",
            content="#!/bin/bash\necho 'Deploying...'",
            permissions="755"
        )
        assert file.permissions == "755"

    def test_file_encoding(self):
        """Test file with custom encoding."""
        file = FileStructure(
            path="data/legacy.txt",
            content="Legacy content",
            encoding="latin-1"
        )
        assert file.encoding == "latin-1"

    def test_file_path_validation(self):
        """Test file path validation."""
        # Invalid paths
        invalid_paths = [
            "../outside",
            "/absolute/path",
            "path/../traversal",
            "path/./current",
            "path\\windows\\style"
        ]

        for path in invalid_paths:
            with pytest.raises(ValidationError):
                FileStructure(path=path, content="test")

    def test_content_and_template_mutual_exclusion(self):
        """Test that content and template_path are mutually exclusive."""
        with pytest.raises(ValidationError) as exc_info:
            FileStructure(
                path="test.txt",
                content="Direct content",
                template_path="template.j2"
            )
        assert "Cannot specify both content and template_path" in str(exc_info.value)

    def test_content_or_template_required(self):
        """Test that either content or template_path is required."""
        with pytest.raises(ValidationError) as exc_info:
            FileStructure(path="test.txt")
        assert "Must specify either content or template_path" in str(exc_info.value)


class TestDirectoryStructure:
    """Test directory structure model."""

    def test_minimal_directory(self):
        """Test creating directory with minimal fields."""
        dir = DirectoryStructure(path="src")
        assert dir.path == "src"
        assert dir.permissions is None
        assert dir.create_if_not_exists is True
        assert dir.children == []

    def test_directory_with_permissions(self):
        """Test directory with permissions."""
        dir = DirectoryStructure(
            path="private",
            permissions="700"
        )
        assert dir.permissions == "700"

    def test_directory_create_flag(self):
        """Test directory create_if_not_exists flag."""
        dir = DirectoryStructure(
            path="optional",
            create_if_not_exists=False
        )
        assert dir.create_if_not_exists is False

    def test_nested_directory_structure(self):
        """Test nested directory with children."""
        dir = DirectoryStructure(
            path="src",
            children=[
                FileStructure(
                    path="__init__.py",
                    content=""
                ),
                DirectoryStructure(
                    path="utils",
                    children=[
                        FileStructure(
                            path="helpers.py",
                            content="# Utility functions"
                        )
                    ]
                )
            ]
        )
        assert dir.path == "src"
        assert len(dir.children) == 2
        assert isinstance(dir.children[0], FileStructure)
        assert isinstance(dir.children[1], DirectoryStructure)
        assert dir.children[1].path == "utils"
        assert len(dir.children[1].children) == 1

    def test_directory_path_validation(self):
        """Test directory path validation."""
        # Invalid paths
        invalid_paths = [
            "../outside",
            "/absolute/path",
            "path/../traversal",
            "path/./current",
            "path\\windows\\style"
        ]

        for path in invalid_paths:
            with pytest.raises(ValidationError):
                DirectoryStructure(path=path)


class TestTemplateFiles:
    """Test template files union type."""

    def test_discriminated_union_file(self):
        """Test creating file through union."""
        data = {
            "type": "file",
            "path": "test.txt",
            "content": "test content"
        }
        item = TemplateFiles.model_validate(data)
        assert isinstance(item, FileStructure)
        assert item.path == "test.txt"

    def test_discriminated_union_directory(self):
        """Test creating directory through union."""
        data = {
            "type": "directory",
            "path": "src"
        }
        item = TemplateFiles.model_validate(data)
        assert isinstance(item, DirectoryStructure)
        assert item.path == "src"

    def test_mixed_structure_list(self):
        """Test list with mixed file and directory types."""
        data = [
            {
                "type": "directory",
                "path": "src",
                "children": [
                    {
                        "type": "file",
                        "path": "main.py",
                        "content": "print('Hello')"
                    }
                ]
            },
            {
                "type": "file",
                "path": "README.md",
                "content": "# Project"
            }
        ]

        items = [TemplateFiles.model_validate(item) for item in data]
        assert len(items) == 2
        assert isinstance(items[0], DirectoryStructure)
        assert isinstance(items[1], FileStructure)


class TestProjectStructure:
    """Test project structure model."""

    def test_minimal_project_structure(self):
        """Test creating project structure with minimal fields."""
        structure = ProjectStructure(
            base_path=".",
            files=[
                FileStructure(path="README.md", content="# Project")
            ]
        )
        assert structure.base_path == "."
        assert len(structure.files) == 1
        assert structure.create_base_directory is True

    def test_complex_project_structure(self):
        """Test complex project structure."""
        structure = ProjectStructure(
            base_path="my-project",
            create_base_directory=True,
            files=[
                DirectoryStructure(
                    path="src",
                    children=[
                        FileStructure(
                            path="__init__.py",
                            content=""
                        ),
                        FileStructure(
                            path="main.py",
                            template_path="templates/main.py.j2"
                        ),
                        DirectoryStructure(
                            path="utils",
                            children=[
                                FileStructure(
                                    path="__init__.py",
                                    content=""
                                ),
                                FileStructure(
                                    path="helpers.py",
                                    content="# Helper functions"
                                )
                            ]
                        )
                    ]
                ),
                DirectoryStructure(
                    path="tests",
                    children=[
                        FileStructure(
                            path="test_main.py",
                            content="import pytest\n"
                        )
                    ]
                ),
                FileStructure(
                    path="README.md",
                    template_path="templates/README.md.j2"
                ),
                FileStructure(
                    path=".gitignore",
                    content="*.pyc\n__pycache__/\n.env"
                )
            ]
        )

        assert structure.base_path == "my-project"
        assert len(structure.files) == 4

        # Check structure types
        src_dir = structure.files[0]
        assert isinstance(src_dir, DirectoryStructure)
        assert src_dir.path == "src"
        assert len(src_dir.children) == 3

        # Check nested structure
        utils_dir = src_dir.children[2]
        assert isinstance(utils_dir, DirectoryStructure)
        assert utils_dir.path == "utils"
        assert len(utils_dir.children) == 2

    def test_empty_files_list(self):
        """Test that project must have at least one file."""
        with pytest.raises(ValidationError):
            ProjectStructure(
                base_path="empty",
                files=[]
            )

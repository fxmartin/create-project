# ABOUTME: Unit tests for template variable schema models
# ABOUTME: Tests all variable types and their validation rules

"""Tests for template variable schema models."""

import pytest
from pydantic import ValidationError

from create_project.templates.schema.variables import (
    BooleanVariable,
    ChoiceVariable,
    ConditionalDisplay,
    EmailVariable,
    FloatVariable,
    IntegerVariable,
    ListVariable,
    MultiChoiceVariable,
    PathVariable,
    StringVariable,
    TemplateVariable,
    URLVariable,
)


class TestConditionalDisplay:
    """Test conditional display logic."""

    def test_valid_operators(self):
        """Test all valid conditional operators."""
        operators = ["eq", "ne", "in", "not_in", "contains", "gt", "lt", "gte", "lte"]

        for op in operators:
            cond = ConditionalDisplay(variable="test_var", operator=op, value="test")
            assert cond.variable == "test_var"
            assert cond.operator == op
            assert cond.value == "test"

    def test_invalid_operator(self):
        """Test invalid operator raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConditionalDisplay(variable="test", operator="invalid", value="test")

        assert "Input should be" in str(exc_info.value)


class TestStringVariable:
    """Test string variable type."""

    def test_minimal_string_variable(self):
        """Test creating string variable with minimal fields."""
        var = StringVariable(
            name="project_name",
            type="string",
            label="Project Name",
            default="my-project"
        )
        assert var.name == "project_name"
        assert var.type == "string"
        assert var.default == "my-project"

    def test_string_with_pattern(self):
        """Test string variable with regex pattern."""
        var = StringVariable(
            name="identifier",
            type="string",
            label="Identifier",
            pattern=r"^[a-z][a-z0-9-]*$",
            default="test-id"
        )
        assert var.pattern == r"^[a-z][a-z0-9-]*$"

    def test_string_length_constraints(self):
        """Test string variable with length constraints."""
        var = StringVariable(
            name="description",
            type="string",
            label="Description",
            min_length=10,
            max_length=100,
            default="A test description"
        )
        assert var.min_length == 10
        assert var.max_length == 100

    def test_invalid_length_constraints(self):
        """Test invalid length constraints."""
        with pytest.raises(ValidationError):
            StringVariable(
                name="test",
                type="string",
                label="Test",
                min_length=-1,
                default="test"
            )


class TestBooleanVariable:
    """Test boolean variable type."""

    def test_boolean_variable(self):
        """Test creating boolean variable."""
        var = BooleanVariable(
            name="use_typescript",
            type="boolean",
            label="Use TypeScript",
            default=True,
            description="Enable TypeScript support"
        )
        assert var.name == "use_typescript"
        assert var.default is True
        assert var.type == "boolean"

    def test_boolean_with_conditionals(self):
        """Test boolean variable with conditional display."""
        var = BooleanVariable(
            name="use_eslint",
            type="boolean",
            label="Use ESLint",
            default=True,
            show_if=ConditionalDisplay(
                variable="use_typescript",
                operator="eq",
                value=True
            )
        )
        assert var.show_if.variable == "use_typescript"
        assert var.show_if.operator == "eq"


class TestIntegerVariable:
    """Test integer variable type."""

    def test_integer_variable(self):
        """Test creating integer variable."""
        var = IntegerVariable(
            name="port",
            type="integer",
            label="Port Number",
            default=8000,
            min_value=1024,
            max_value=65535
        )
        assert var.name == "port"
        assert var.default == 8000
        assert var.min_value == 1024
        assert var.max_value == 65535

    def test_integer_step(self):
        """Test integer variable with step."""
        var = IntegerVariable(
            name="workers",
            type="integer",
            label="Worker Count",
            default=4,
            min_value=1,
            max_value=16,
            step=2
        )
        assert var.step == 2


class TestFloatVariable:
    """Test float variable type."""

    def test_float_variable(self):
        """Test creating float variable."""
        var = FloatVariable(
            name="threshold",
            type="float",
            label="Threshold",
            default=0.5,
            min_value=0.0,
            max_value=1.0
        )
        assert var.name == "threshold"
        assert var.default == 0.5
        assert var.min_value == 0.0
        assert var.max_value == 1.0

    def test_float_step(self):
        """Test float variable with step."""
        var = FloatVariable(
            name="rate",
            type="float",
            label="Rate",
            default=0.1,
            step=0.01
        )
        assert var.step == 0.01


class TestChoiceVariable:
    """Test choice variable type."""

    def test_choice_variable(self):
        """Test creating choice variable."""
        var = ChoiceVariable(
            name="license",
            type="choice",
            label="License",
            choices=["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause"],
            default="MIT"
        )
        assert var.name == "license"
        assert var.choices == ["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause"]
        assert var.default == "MIT"

    def test_choice_variable_no_default(self):
        """Test choice variable without default uses first choice."""
        var = ChoiceVariable(
            name="framework",
            type="choice",
            label="Framework",
            choices=["React", "Vue", "Angular"]
        )
        assert var.default == "React"

    def test_choice_variable_empty_choices(self):
        """Test choice variable requires at least one choice."""
        with pytest.raises(ValidationError):
            ChoiceVariable(
                name="empty",
                type="choice",
                label="Empty",
                choices=[]
            )


class TestMultiChoiceVariable:
    """Test multi-choice variable type."""

    def test_multichoice_variable(self):
        """Test creating multi-choice variable."""
        var = MultiChoiceVariable(
            name="features",
            type="multichoice",
            label="Features",
            choices=["auth", "api", "database", "cache"],
            default=["auth", "api"]
        )
        assert var.name == "features"
        assert var.choices == ["auth", "api", "database", "cache"]
        assert var.default == ["auth", "api"]

    def test_multichoice_min_max_selections(self):
        """Test multi-choice variable with selection constraints."""
        var = MultiChoiceVariable(
            name="integrations",
            type="multichoice",
            label="Integrations",
            choices=["github", "gitlab", "bitbucket", "azure"],
            min_selections=1,
            max_selections=2,
            default=["github"]
        )
        assert var.min_selections == 1
        assert var.max_selections == 2


class TestListVariable:
    """Test list variable type."""

    def test_list_variable(self):
        """Test creating list variable."""
        var = ListVariable(
            name="allowed_hosts",
            type="list",
            label="Allowed Hosts",
            default=["localhost", "127.0.0.1"],
            item_type="string"
        )
        assert var.name == "allowed_hosts"
        assert var.default == ["localhost", "127.0.0.1"]
        assert var.item_type == "string"

    def test_list_constraints(self):
        """Test list variable with constraints."""
        var = ListVariable(
            name="tags",
            type="list",
            label="Tags",
            min_items=1,
            max_items=10,
            unique_items=True,
            default=["python"]
        )
        assert var.min_items == 1
        assert var.max_items == 10
        assert var.unique_items is True


class TestEmailVariable:
    """Test email variable type."""

    def test_email_variable(self):
        """Test creating email variable."""
        var = EmailVariable(
            name="author_email",
            type="email",
            label="Author Email",
            default="user@example.com",
            require_verification=True
        )
        assert var.name == "author_email"
        assert var.default == "user@example.com"
        assert var.require_verification is True

    def test_email_domain_whitelist(self):
        """Test email variable with domain whitelist."""
        var = EmailVariable(
            name="work_email",
            type="email",
            label="Work Email",
            allowed_domains=["company.com", "company.org"]
        )
        assert var.allowed_domains == ["company.com", "company.org"]


class TestURLVariable:
    """Test URL variable type."""

    def test_url_variable(self):
        """Test creating URL variable."""
        var = URLVariable(
            name="homepage",
            type="url",
            label="Homepage URL",
            default="https://example.com",
            require_https=True
        )
        assert var.name == "homepage"
        assert var.default == "https://example.com"
        assert var.require_https is True

    def test_url_allowed_protocols(self):
        """Test URL variable with allowed protocols."""
        var = URLVariable(
            name="repo_url",
            type="url",
            label="Repository URL",
            allowed_protocols=["https", "ssh", "git"]
        )
        assert var.allowed_protocols == ["https", "ssh", "git"]


class TestPathVariable:
    """Test path variable type."""

    def test_path_variable(self):
        """Test creating path variable."""
        var = PathVariable(
            name="output_dir",
            type="path",
            label="Output Directory",
            default="./output",
            must_exist=False,
            path_type="directory"
        )
        assert var.name == "output_dir"
        assert var.default == "./output"
        assert var.must_exist is False
        assert var.path_type == "directory"

    def test_path_variable_file_type(self):
        """Test path variable for file type."""
        var = PathVariable(
            name="config_file",
            type="path",
            label="Configuration File",
            path_type="file",
            allowed_extensions=[".json", ".yaml", ".yml"]
        )
        assert var.path_type == "file"
        assert var.allowed_extensions == [".json", ".yaml", ".yml"]


class TestTemplateVariableUnion:
    """Test TemplateVariable union type."""

    def test_discriminated_union_string(self):
        """Test creating string variable through union."""
        data = {
            "name": "test",
            "type": "string",
            "label": "Test String",
            "default": "value"
        }
        var = TemplateVariable.model_validate(data)
        assert isinstance(var, StringVariable)
        assert var.name == "test"

    def test_discriminated_union_boolean(self):
        """Test creating boolean variable through union."""
        data = {
            "name": "flag",
            "type": "boolean",
            "label": "Test Flag",
            "default": True
        }
        var = TemplateVariable.model_validate(data)
        assert isinstance(var, BooleanVariable)
        assert var.default is True

    def test_discriminated_union_all_types(self):
        """Test all variable types work through union."""
        type_map = {
            "string": StringVariable,
            "boolean": BooleanVariable,
            "integer": IntegerVariable,
            "float": FloatVariable,
            "choice": ChoiceVariable,
            "multichoice": MultiChoiceVariable,
            "list": ListVariable,
            "email": EmailVariable,
            "url": URLVariable,
            "path": PathVariable
        }

        for var_type, expected_class in type_map.items():
            data = {
                "name": f"test_{var_type}",
                "type": var_type,
                "label": f"Test {var_type}",
            }

            # Add type-specific required fields
            if var_type == "choice":
                data["choices"] = ["option1", "option2"]
            elif var_type == "multichoice":
                data["choices"] = ["option1", "option2"]
                data["default"] = ["option1"]
            elif var_type == "list":
                data["default"] = ["item1"]
            elif var_type in ["boolean", "integer", "float"]:
                data["default"] = True if var_type == "boolean" else 1
            else:
                data["default"] = "test"

            var = TemplateVariable.model_validate(data)
            assert isinstance(var, expected_class)
            assert var.type == var_type

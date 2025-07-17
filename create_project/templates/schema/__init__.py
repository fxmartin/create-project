# ABOUTME: Template schema package initialization
# ABOUTME: Provides Pydantic models for template definition and validation

from .actions import ActionType, TemplateAction, TemplateHooks
from .base_template import (
    BaseTemplate,
    TemplateCategory,
    TemplateConfiguration,
    TemplateMetadata,
)
from .structure import ConditionalExpression, DirectoryItem, FileItem, ProjectStructure
from .template import Template
from .variables import ChoiceItem, TemplateVariable, ValidationRule, VariableType

__all__ = [
    "Template",
    "BaseTemplate",
    "TemplateMetadata",
    "TemplateConfiguration",
    "TemplateCategory",
    "TemplateVariable",
    "VariableType",
    "ChoiceItem",
    "ValidationRule",
    "ProjectStructure",
    "DirectoryItem",
    "FileItem",
    "ConditionalExpression",
    "TemplateAction",
    "ActionType",
    "TemplateHooks",
]

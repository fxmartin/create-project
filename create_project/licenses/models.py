# ABOUTME: Pydantic models for license data structures
# ABOUTME: Defines License model with validation and type safety

from typing import List

from pydantic import BaseModel, Field, HttpUrl


class License(BaseModel):
    """Model representing a software license with its metadata and text.
    
    Attributes:
        id: Unique identifier for the license (e.g., 'mit', 'apache-2.0')
        name: Human-readable name of the license
        text: Full license text, may contain template variables
        url: Canonical URL for the license
        requires_fields: List of template variables that need substitution
    """

    id: str = Field(
        ...,
        description="Unique identifier for the license",
        min_length=1,
        max_length=50
    )

    name: str = Field(
        ...,
        description="Human-readable name of the license",
        min_length=1,
        max_length=200
    )

    text: str = Field(
        ...,
        description="Full license text with optional template variables",
        min_length=1
    )

    url: HttpUrl = Field(
        ...,
        description="Canonical URL for the license"
    )

    requires_fields: List[str] = Field(
        default_factory=list,
        description="Template variables that need substitution"
    )

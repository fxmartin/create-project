# ABOUTME: Template validation script for built-in templates
# ABOUTME: Validates all built-in templates against the schema and reports issues

#!/usr/bin/env python3
"""
Validate all built-in templates against the schema.

This script loads each built-in template and validates it using the
Pydantic schema models to identify any structural or validation issues.
"""

import sys
from pathlib import Path
from typing import Any, Dict

import yaml

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from create_project.templates.schema.template import Template
from create_project.templates.validator import TemplateValidator


def validate_template_file(template_path: Path) -> Dict[str, Any]:
    """
    Validate a single template file.

    Args:
        template_path: Path to the template YAML file

    Returns:
        Dictionary with validation results
    """
    result = {
        "file": template_path.name,
        "valid_yaml": False,
        "valid_schema": False,
        "errors": [],
        "warnings": [],
    }

    try:
        # Load YAML
        with open(template_path) as f:
            template_data = yaml.safe_load(f)
        result["valid_yaml"] = True

        # Validate against Pydantic schema
        template = Template(**template_data)
        result["valid_schema"] = True

        # Use template validator for additional checks
        validator = TemplateValidator()
        validation_result = validator.validate_template_data(template_data)

        if not validation_result.is_valid:
            result["errors"].extend(validation_result.errors)
            result["warnings"].extend(validation_result.warnings)

    except yaml.YAMLError as e:
        result["errors"].append(f"YAML parsing error: {e}")
    except Exception as e:
        result["errors"].append(f"Schema validation error: {e}")

    return result


def main():
    """Main validation function."""
    templates_dir = project_root / "create_project" / "templates" / "builtin"

    if not templates_dir.exists():
        print(f"❌ Templates directory not found: {templates_dir}")
        return 1

    template_files = list(templates_dir.glob("*.yaml"))
    if not template_files:
        print(f"❌ No template files found in {templates_dir}")
        return 1

    print(f"🔍 Validating {len(template_files)} built-in templates...")
    print()

    all_valid = True
    results = []

    for template_file in sorted(template_files):
        result = validate_template_file(template_file)
        results.append(result)

        if result["valid_yaml"] and result["valid_schema"] and not result["errors"]:
            print(f"✅ {result['file']} - Valid")
        else:
            all_valid = False
            print(f"❌ {result['file']} - Invalid")

            if not result["valid_yaml"]:
                print("   - YAML parsing failed")
            elif not result["valid_schema"]:
                print("   - Schema validation failed")

            for error in result["errors"]:
                print(f"   - Error: {error}")

            for warning in result["warnings"]:
                print(f"   - Warning: {warning}")

        print()

    # Summary
    valid_count = sum(
        1 for r in results if r["valid_yaml"] and r["valid_schema"] and not r["errors"]
    )
    print(f"📊 Summary: {valid_count}/{len(results)} templates are valid")

    if all_valid:
        print("🎉 All templates are valid!")
        return 0
    else:
        print("❌ Some templates have validation issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())

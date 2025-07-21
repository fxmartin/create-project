# Template Authoring Guide

This guide walks you through creating custom templates for the Python Project Creator. Templates allow you to define reusable project structures that can be instantiated with user-provided values.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Template Development Workflow](#template-development-workflow)
3. [Step-by-Step Tutorial](#step-by-step-tutorial)
4. [Variable Design Best Practices](#variable-design-best-practices)
5. [Advanced Techniques](#advanced-techniques)
6. [Testing Your Template](#testing-your-template)
7. [Troubleshooting](#troubleshooting)
8. [Template Gallery](#template-gallery)

## Getting Started

### Prerequisites

Before creating templates, ensure you have:

1. Python Project Creator installed
2. Basic understanding of YAML syntax
3. Familiarity with Jinja2 templating (optional but helpful)
4. A text editor with YAML support

### Template File Structure

Templates are organized as follows:

```
~/.project-creator/templates/
├── my_template/
│   ├── template.yaml          # Main template definition
│   ├── templates/             # Jinja2 template files
│   │   ├── main.py.j2
│   │   └── config.py.j2
│   └── static/                # Static files to copy
│       └── logo.png
```

## Template Development Workflow

1. **Plan**: Define what your template will create
2. **Design**: Map out variables and structure
3. **Implement**: Write the template YAML
4. **Test**: Validate and test the template
5. **Refine**: Iterate based on testing
6. **Share**: Publish for others to use

## Step-by-Step Tutorial

Let's create a simple Python package template:

### Step 1: Create Template Directory

```bash
mkdir -p ~/.project-creator/templates/python_package
cd ~/.project-creator/templates/python_package
```

### Step 2: Create Basic Template File

Create `template.yaml`:

```yaml
# template.yaml
metadata:
  name: "Python Package"
  description: "A basic Python package with tests and documentation"
  version: "1.0.0"
  category: "library"
  author: "Your Name"
  tags:
    - "package"
    - "library"

variables:
  - name: "package_name"
    type: "string"
    description: "Package name (lowercase, no spaces)"
    required: true
    validation_rules:
      - rule_type: "pattern"
        value: "^[a-z][a-z0-9_]*$"
        error_message: "Must be lowercase, start with letter"
  
  - name: "description"
    type: "string"
    description: "Package description"
    default: "A Python package"
  
  - name: "author_name"
    type: "string"
    description: "Your name"
    required: true
  
  - name: "include_tests"
    type: "boolean"
    description: "Include test suite?"
    default: true

structure:
  root_directory:
    name: "{{ package_name }}"
    files:
      - name: "README.md"
        content: |
          # {{ package_name }}
          
          {{ description }}
          
          ## Installation
          
          ```bash
          pip install -e .
          ```
      
      - name: "setup.py"
        content: |
          from setuptools import setup, find_packages
          
          setup(
              name="{{ package_name }}",
              version="0.1.0",
              author="{{ author_name }}",
              description="{{ description }}",
              packages=find_packages(),
              python_requires=">=3.9",
          )
    
    directories:
      - name: "{{ package_name }}"
        files:
          - name: "__init__.py"
            content: |
              """{{ description }}"""
              
              __version__ = "0.1.0"
      
      - name: "tests"
        condition:
          expression: "{{ include_tests }}"
        files:
          - name: "test_{{ package_name }}.py"
            content: |
              import pytest
              import {{ package_name }}
              
              def test_version():
                  assert {{ package_name }}.__version__ == "0.1.0"
```

### Step 3: Add Jinja2 Templates (Optional)

For complex files, use external templates. Create `templates/module.py.j2`:

```python
"""{{ module_description }}"""

import logging

logger = logging.getLogger(__name__)

class {{ class_name }}:
    """{{ class_description }}"""
    
    def __init__(self, name: str = "{{ default_name }}"):
        self.name = name
        logger.info(f"Created {self.__class__.__name__} with name: {name}")
    
    def greet(self) -> str:
        """Return a greeting message."""
        return f"Hello from {self.name}!"

{% if include_async %}
    async def async_greet(self) -> str:
        """Return an async greeting message."""
        await asyncio.sleep(0.1)
        return f"Async hello from {self.name}!"
{% endif %}
```

Reference it in your template:

```yaml
files:
  - name: "core.py"
    template_file: "templates/module.py.j2"
```

### Step 4: Add Actions

Add post-generation actions:

```yaml
hooks:
  post_generate:
    - name: "init_git"
      type: "git"
      command: "init"
      description: "Initialize git repository"
    
    - name: "install_dev"
      type: "command"
      command: "pip install -e ."
      description: "Install package in development mode"
      working_directory: "{{ package_name }}"
```

### Step 5: Test Your Template

1. Validate the YAML:
   ```bash
   python -m yaml template.yaml
   ```

2. Test generation:
   ```bash
   create-project --template python_package --output /tmp/test
   ```

## Variable Design Best Practices

### 1. Use Clear, Descriptive Names

```yaml
# Good
variables:
  - name: "database_url"
    description: "PostgreSQL connection URL"

# Bad
variables:
  - name: "db"
    description: "Database"
```

### 2. Provide Helpful Descriptions

```yaml
variables:
  - name: "api_key"
    description: "API key for external service (get from https://example.com/api)"
```

### 3. Set Sensible Defaults

```yaml
variables:
  - name: "port"
    type: "integer"
    default: 8000
    description: "Server port (default: 8000)"
```

### 4. Use Appropriate Types

```yaml
variables:
  - name: "email"
    type: "email"  # Built-in validation
    
  - name: "website"
    type: "url"    # Built-in validation
    
  - name: "max_connections"
    type: "integer"
    validation_rules:
      - rule_type: "min_value"
        value: 1
      - rule_type: "max_value"
        value: 1000
```

### 5. Group Related Variables

```yaml
variables:
  # Database configuration
  - name: "use_database"
    type: "boolean"
    description: "Include database support?"
  
  - name: "database_type"
    type: "choice"
    description: "Database backend"
    show_if:
      variable: "use_database"
      operator: "equals"
      value: true
  
  # API configuration
  - name: "include_api"
    type: "boolean"
    description: "Include REST API?"
  
  - name: "api_framework"
    type: "choice"
    description: "API framework"
    show_if:
      variable: "include_api"
      operator: "equals"
      value: true
```

## Advanced Techniques

### 1. Dynamic File Names

```yaml
files:
  - name: "{{ module_name }}.py"
    content: "# Module: {{ module_name }}"
```

### 2. Conditional Directories

```yaml
directories:
  - name: "docs"
    condition:
      expression: "{{ include_docs }}"
    files:
      - name: "conf.py"
        template_file: "templates/sphinx_conf.py.j2"
```

### 3. Complex Conditions

```yaml
files:
  - name: "Dockerfile"
    condition:
      expression: "{{ use_docker and not use_compose }}"
```

### 4. Lists and Loops

```yaml
variables:
  - name: "dependencies"
    type: "list"
    description: "Python dependencies"
    default:
      - "requests"
      - "click"

# In template file:
content: |
  {% for dep in dependencies %}
  {{ dep }}
  {% endfor %}
```

### 5. Custom Validation

```yaml
variables:
  - name: "python_version"
    type: "string"
    validation_rules:
      - rule_type: "pattern"
        value: "^3\\.(9|1[0-2])$"
        error_message: "Must be Python 3.9-3.12"
```

### 6. Multi-Platform Support

```yaml
hooks:
  post_generate:
    - name: "install_unix"
      type: "command"
      command: "chmod +x run.sh"
      platform: ["darwin", "linux"]
    
    - name: "install_windows"
      type: "command"
      command: "pip install -r requirements.txt"
      platform: ["win32"]
```

## Testing Your Template

### 1. Validation Checklist

- [ ] YAML syntax is valid
- [ ] All required metadata fields present
- [ ] Variable names follow conventions
- [ ] Descriptions are clear and helpful
- [ ] Validation rules work correctly
- [ ] Default values are sensible
- [ ] Conditional logic works
- [ ] File/directory names are valid
- [ ] Template files exist and are valid
- [ ] Actions run successfully

### 2. Test Scenarios

Test with different variable combinations:

```bash
# Minimal input
create-project --template my_template --output /tmp/test1

# All options enabled
create-project --template my_template --output /tmp/test2 \
  --var include_tests=true \
  --var include_docs=true \
  --var use_docker=true

# Edge cases
create-project --template my_template --output /tmp/test3 \
  --var package_name="x" \  # Minimum length
  --var port=65535          # Maximum port
```

### 3. Validation Script

Create a test script:

```python
#!/usr/bin/env python3
import yaml
import sys

def validate_template(file_path):
    with open(file_path) as f:
        template = yaml.safe_load(f)
    
    # Check required fields
    assert 'metadata' in template
    assert 'variables' in template
    assert 'structure' in template
    
    # Validate metadata
    metadata = template['metadata']
    assert 'name' in metadata
    assert 'description' in metadata
    assert 'version' in metadata
    assert 'category' in metadata
    assert 'author' in metadata
    
    print("✓ Template is valid!")

if __name__ == "__main__":
    validate_template(sys.argv[1])
```

## Troubleshooting

### Common Issues

1. **YAML Syntax Errors**
   ```
   Error: expected ':' but found '}'
   ```
   Solution: Check indentation and special characters

2. **Missing Variables in Templates**
   ```
   Error: 'project_name' is undefined
   ```
   Solution: Ensure all variables used in templates are defined

3. **Invalid Regex Patterns**
   ```
   Error: Invalid regex pattern
   ```
   Solution: Test regex patterns at regex101.com

4. **File Permission Issues**
   ```
   Error: Permission denied
   ```
   Solution: Check file permissions and use proper permission values

5. **Circular Dependencies**
   ```
   Error: Circular reference in conditions
   ```
   Solution: Review conditional logic for circular references

### Debug Mode

Enable debug output:

```bash
create-project --template my_template --debug
```

### Validation Command

Validate without generating:

```bash
create-project --template my_template --validate-only
```

## Template Gallery

### Example Templates

1. **FastAPI Microservice**
   - REST API with FastAPI
   - PostgreSQL integration
   - Docker support
   - JWT authentication

2. **Data Science Project**
   - Jupyter notebooks
   - Data directories
   - Requirements management
   - Experiment tracking

3. **CLI Tool**
   - Click-based CLI
   - Configuration management
   - Plugin system
   - Distribution setup

4. **Django SaaS Starter**
   - Multi-tenant support
   - Stripe integration
   - Background tasks
   - Admin dashboard

### Sharing Templates

1. **Export Template**
   ```bash
   create-project --export-template my_template > my_template.zip
   ```

2. **Import Template**
   ```bash
   create-project --import-template my_template.zip
   ```

3. **Publish to Registry**
   ```bash
   create-project --publish-template my_template
   ```

## Best Practices Summary

1. **Start Simple**: Begin with basic structure, add complexity gradually
2. **Test Often**: Validate after each major change
3. **Document Well**: Clear descriptions help users understand options
4. **Handle Errors**: Provide helpful error messages
5. **Consider Users**: Think about different use cases and preferences
6. **Version Control**: Track template changes with git
7. **Get Feedback**: Share with others and iterate

## Next Steps

1. Create your first template
2. Test with various inputs
3. Share with the community
4. Contribute improvements

For more information, see the [Schema Specification](schema-specification.md).
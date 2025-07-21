# Template Schema Specification

This document describes the complete YAML schema structure for Python Project Creator templates. Templates are defined using YAML files that specify project structure, variables, actions, and configuration.

## Table of Contents

1. [Overview](#overview)
2. [Schema Version](#schema-version)
3. [Template Metadata](#template-metadata)
4. [Template Variables](#template-variables)
5. [Project Structure](#project-structure)
6. [Template Files](#template-files)
7. [Actions and Hooks](#actions-and-hooks)
8. [Compatibility](#compatibility)
9. [Complete Example](#complete-example)

## Overview

Templates use a structured YAML format to define how projects should be created. The schema supports:

- **Metadata**: Template information and categorization
- **Variables**: User inputs with validation
- **Structure**: File and directory layout
- **Actions**: Post-creation commands and operations
- **Hooks**: Lifecycle event handlers

## Schema Version

Every template must specify its schema version for compatibility checking:

```yaml
schema_version: "1.0.0"
```

## Template Metadata

The `metadata` section contains information about the template:

```yaml
metadata:
  name: "Django REST API"
  description: "A Django project with REST API setup"
  version: "1.0.0"
  category: "django"  # script, cli_single, cli_complex, django, flask, library, custom
  author: "Your Name"
  email: "your.email@example.com"  # optional
  website: "https://example.com"   # optional
  license: "MIT"                   # optional
  tags:                            # optional
    - "api"
    - "rest"
    - "web"
  created: "2024-01-01"            # optional, auto-generated if not provided
  updated: "2024-01-15"            # optional, auto-updated on changes
```

### Required Fields
- `name`: Human-readable template name (1-100 characters)
- `description`: Detailed description (1-500 characters)
- `version`: Semantic version (e.g., "1.0.0")
- `category`: Template category from predefined list
- `author`: Template author name

### Categories
- `script`: Simple Python scripts
- `cli_single`: Single-file CLI applications
- `cli_complex`: Multi-file CLI applications
- `django`: Django web applications
- `flask`: Flask web applications
- `library`: Python libraries/packages
- `custom`: Custom project types

## Template Variables

Variables define user inputs collected during project creation:

```yaml
variables:
  - name: "project_name"
    type: "string"
    description: "Name of the project"
    required: true
    default: "my_project"
    validation_rules:
      - rule_type: "pattern"
        value: "^[a-zA-Z][a-zA-Z0-9_-]*$"
        error_message: "Must start with letter, contain only alphanumeric, dash, or underscore"
      - rule_type: "min_length"
        value: 3
        error_message: "Must be at least 3 characters"
      - rule_type: "max_length"
        value: 50
        error_message: "Must be no more than 50 characters"
```

### Variable Types

1. **string**: Text input
2. **boolean**: True/false checkbox
3. **integer**: Whole numbers
4. **float**: Decimal numbers
5. **choice**: Single selection from list
6. **multichoice**: Multiple selections from list
7. **list**: List of values
8. **email**: Email address (validated)
9. **url**: URL (validated)
10. **path**: File system path

### Variable Properties

```yaml
variables:
  - name: "database_type"
    type: "choice"
    description: "Database backend to use"
    required: true
    default: "postgresql"
    choices:
      - "postgresql"
      - "mysql"
      - "sqlite"
    
  - name: "enable_api"
    type: "boolean"
    description: "Include REST API?"
    default: true
    
  - name: "port"
    type: "integer"
    description: "Server port"
    default: 8000
    validation_rules:
      - rule_type: "min_value"
        value: 1024
        error_message: "Port must be >= 1024"
      - rule_type: "max_value"
        value: 65535
        error_message: "Port must be <= 65535"
```

### Validation Rules

Available validation rule types:
- `pattern`: Regex pattern matching
- `min_length`, `max_length`: String length constraints
- `min_value`, `max_value`: Numeric range constraints
- `min_items`, `max_items`: List size constraints
- `format`: Predefined formats (email, url, etc.)
- `required`: Whether the field is required
- `custom`: Custom validation logic

### Conditional Variables

Variables can be shown/hidden based on other variable values:

```yaml
variables:
  - name: "use_database"
    type: "boolean"
    description: "Include database?"
    default: true
    
  - name: "database_name"
    type: "string"
    description: "Database name"
    show_if:
      variable: "use_database"
      operator: "equals"
      value: true
```

Supported operators: `equals`, `not_equals`, `contains`, `greater_than`, `less_than`

## Project Structure

The `structure` section defines the project's file and directory layout:

```yaml
structure:
  root_directory:
    name: "{{ project_name }}"
    files:
      - name: "README.md"
        content: |
          # {{ project_name }}
          
          {{ description }}
      
      - name: ".gitignore"
        template_file: "templates/python.gitignore"
        
      - name: "requirements.txt"
        content: |
          {% for package in packages %}
          {{ package }}
          {% endfor %}
    
    directories:
      - name: "src"
        files:
          - name: "__init__.py"
            content: ""
          
          - name: "main.py"
            template_file: "templates/main.py.jinja2"
            
      - name: "tests"
        condition:
          expression: "{{ include_tests }}"
        files:
          - name: "test_main.py"
            content: |
              import pytest
              
              def test_example():
                  assert True
```

### File Properties

```yaml
files:
  - name: "config.py"
    content: "# Inline content"              # Option 1: Inline content
    
  - name: "app.py"
    template_file: "templates/app.py.j2"     # Option 2: External template
    
  - name: "data.json"
    source_file: "static/data.json"          # Option 3: Copy static file
    
  - name: "script.sh"
    content: "#!/bin/bash\necho 'Hello'"
    permissions: "755"                       # File permissions (Unix)
    encoding: "utf-8"                        # File encoding
    
  - name: "optional.txt"
    content: "Optional file"
    condition:
      expression: "{{ create_optional_files }}"
```

### Directory Properties

```yaml
directories:
  - name: "{{ module_name }}"
    description: "Main module directory"
    
    # Conditional directory
    condition:
      expression: "{{ create_module }}"
    
    # Nested structure
    directories:
      - name: "submodule"
        files:
          - name: "__init__.py"
            content: ""
    
    files:
      - name: "__init__.py"
        content: "# Module initialization"
```

## Template Files

External template files can be referenced for complex content:

```yaml
template_files:
  directory: "templates"
  files:
    - path: "templates/main.py.j2"
      description: "Main application file"
    
    - path: "templates/config.yaml.j2"
      description: "Configuration template"
```

Template files use Jinja2 syntax:

```python
# templates/main.py.j2
#!/usr/bin/env python3
"""{{ project_name }} - {{ description }}"""

{% if use_async %}
import asyncio
{% endif %}

def main():
    {% if use_logging %}
    logger.info("Starting {{ project_name }}")
    {% endif %}
    print("Hello from {{ project_name }}!")

if __name__ == "__main__":
    main()
```

## Actions and Hooks

Actions define post-creation operations:

```yaml
hooks:
  pre_prompt:
    - name: "check_requirements"
      type: "python"
      command: "scripts/check_deps.py"
      description: "Check system requirements"
  
  post_generate:
    - name: "init_git"
      type: "git"
      command: "init"
      description: "Initialize git repository"
      condition: "{{ use_git }}"
    
    - name: "install_deps"
      type: "command"
      command: "pip install -r requirements.txt"
      description: "Install dependencies"
      working_directory: "{{ project_name }}"
      platform: ["darwin", "linux"]  # macOS and Linux only
    
    - name: "format_code"
      type: "python"
      command: "-m black ."
      description: "Format code with Black"
      timeout: 30  # seconds

action_groups:
  - name: "Database Setup"
    description: "Initialize database"
    condition: "{{ use_database }}"
    actions:
      - name: "create_db"
        type: "command"
        command: "createdb {{ database_name }}"
        
      - name: "run_migrations"
        type: "python"
        command: "manage.py migrate"
```

### Action Types

1. **command**: Shell commands
2. **python**: Python commands
3. **git**: Git operations
4. **copy**: Copy files/directories
5. **move**: Move files/directories
6. **delete**: Delete files/directories
7. **mkdir**: Create directories
8. **chmod**: Change permissions

### Hook Types

- `pre_prompt`: Before collecting user input
- `post_prompt`: After collecting user input
- `pre_generate`: Before creating project structure
- `post_generate`: After creating project structure
- `pre_action`: Before running actions
- `post_action`: After running actions

## Compatibility

Define template requirements and constraints:

```yaml
compatibility:
  min_python_version: "3.9"
  max_python_version: "3.12"
  supported_os:
    - "darwin"    # macOS
    - "linux"
    - "win32"     # Windows
  
  required_tools:
    - name: "git"
      version: ">=2.0"
    
    - name: "docker"
      version: ">=20.0"
      optional: true
```

## Complete Example

Here's a complete example template for a Flask web application:

```yaml
# flask_app_template.yaml
metadata:
  name: "Flask Web Application"
  description: "A modern Flask web application with database and authentication"
  version: "2.0.0"
  category: "flask"
  author: "Python Project Creator Team"
  email: "team@example.com"
  license: "MIT"
  tags:
    - "web"
    - "api"
    - "flask"

variables:
  - name: "project_name"
    type: "string"
    description: "Project name (will be used for directory and package names)"
    required: true
    validation_rules:
      - rule_type: "pattern"
        value: "^[a-z][a-z0-9_]*$"
        error_message: "Must be lowercase, start with letter, use only letters, numbers, underscore"
      - rule_type: "min_length"
        value: 3
      - rule_type: "max_length"
        value: 30
  
  - name: "description"
    type: "string"
    description: "Brief project description"
    required: true
    default: "A Flask web application"
  
  - name: "author_name"
    type: "string"
    description: "Your name"
    required: true
  
  - name: "author_email"
    type: "email"
    description: "Your email"
    required: true
  
  - name: "use_database"
    type: "boolean"
    description: "Include database support?"
    default: true
  
  - name: "database_type"
    type: "choice"
    description: "Database to use"
    choices:
      - "postgresql"
      - "mysql"
      - "sqlite"
    default: "sqlite"
    show_if:
      variable: "use_database"
      operator: "equals"
      value: true
  
  - name: "use_auth"
    type: "boolean"
    description: "Include authentication?"
    default: true
  
  - name: "use_docker"
    type: "boolean"
    description: "Include Docker configuration?"
    default: false

structure:
  root_directory:
    name: "{{ project_name }}"
    files:
      - name: "README.md"
        content: |
          # {{ project_name }}
          
          {{ description }}
          
          ## Installation
          
          ```bash
          pip install -r requirements.txt
          ```
          
          ## Usage
          
          ```bash
          flask run
          ```
      
      - name: "requirements.txt"
        content: |
          Flask==3.0.0
          python-dotenv==1.0.0
          {% if use_database %}
          Flask-SQLAlchemy==3.1.1
          {% if database_type == "postgresql" %}
          psycopg2-binary==2.9.9
          {% elif database_type == "mysql" %}
          PyMySQL==1.1.0
          {% endif %}
          {% endif %}
          {% if use_auth %}
          Flask-Login==0.6.3
          Flask-WTF==1.2.1
          {% endif %}
      
      - name: ".env.example"
        content: |
          FLASK_APP={{ project_name }}
          FLASK_ENV=development
          SECRET_KEY=your-secret-key-here
          {% if use_database %}
          DATABASE_URL={{ database_type }}:///{{ project_name }}.db
          {% endif %}
      
      - name: ".gitignore"
        content: |
          __pycache__/
          *.pyc
          .env
          venv/
          instance/
          *.db
      
      - name: "app.py"
        template_file: "templates/flask_app.py.j2"
      
      - name: "config.py"
        template_file: "templates/flask_config.py.j2"
      
      - name: "Dockerfile"
        condition:
          expression: "{{ use_docker }}"
        content: |
          FROM python:3.11-slim
          
          WORKDIR /app
          
          COPY requirements.txt .
          RUN pip install -r requirements.txt
          
          COPY . .
          
          CMD ["flask", "run", "--host=0.0.0.0"]
    
    directories:
      - name: "{{ project_name }}"
        files:
          - name: "__init__.py"
            template_file: "templates/flask_init.py.j2"
          
          - name: "models.py"
            condition:
              expression: "{{ use_database }}"
            template_file: "templates/flask_models.py.j2"
          
          - name: "auth.py"
            condition:
              expression: "{{ use_auth }}"
            template_file: "templates/flask_auth.py.j2"
        
        directories:
          - name: "templates"
            files:
              - name: "base.html"
                template_file: "templates/html/base.html.j2"
              
              - name: "index.html"
                template_file: "templates/html/index.html.j2"
          
          - name: "static"
            directories:
              - name: "css"
                files:
                  - name: "style.css"
                    content: |
                      /* {{ project_name }} styles */
                      body {
                          font-family: Arial, sans-serif;
                          margin: 0;
                          padding: 20px;
                      }
              
              - name: "js"
                files:
                  - name: "main.js"
                    content: |
                      // {{ project_name }} JavaScript
                      console.log('{{ project_name }} loaded');
      
      - name: "tests"
        files:
          - name: "__init__.py"
            content: ""
          
          - name: "test_app.py"
            content: |
              import pytest
              from {{ project_name }} import create_app
              
              @pytest.fixture
              def client():
                  app = create_app('testing')
                  with app.test_client() as client:
                      yield client
              
              def test_index(client):
                  response = client.get('/')
                  assert response.status_code == 200

hooks:
  post_generate:
    - name: "init_git"
      type: "git"
      command: "init"
      description: "Initialize git repository"
    
    - name: "create_env"
      type: "copy"
      command: ".env.example .env"
      description: "Create .env from example"
    
    - name: "create_venv"
      type: "command"
      command: "python -m venv venv"
      description: "Create virtual environment"
    
    - name: "initial_commit"
      type: "git"
      command: "add -A && git commit -m 'Initial commit'"
      description: "Create initial commit"
      condition: "{{ use_git }}"

compatibility:
  min_python_version: "3.9"
  supported_os:
    - "darwin"
    - "linux"
    - "win32"
```

## Validation and Best Practices

1. **Variable Names**: Use lowercase with underscores (e.g., `project_name`)
2. **Descriptions**: Provide clear, helpful descriptions for all elements
3. **Defaults**: Include sensible defaults where appropriate
4. **Validation**: Add validation rules to prevent invalid input
5. **Conditions**: Use conditions to create flexible templates
6. **Security**: Avoid hardcoded secrets or sensitive data
7. **Portability**: Consider cross-platform compatibility

## Template Testing

Before using a template:

1. Validate the YAML syntax
2. Test with various input combinations
3. Verify all conditional logic
4. Check file permissions and encoding
5. Test on target platforms
6. Ensure all external template files exist

## Version History

- **1.0.0** (2024-01-01): Initial schema version
  - Basic metadata, variables, structure, and actions
  - Support for 10 variable types
  - Conditional logic for variables and files
  - Post-generation actions
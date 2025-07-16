# Template Systems Analysis - Research Report

## Executive Summary

This research analyzes five major template systems to inform the design of a YAML-based template schema for the Python Project Creator. The analysis reveals common patterns, unique innovations, and best practices that should guide our schema design.

## Systems Analyzed

### 1. Cookiecutter (Python)
- **GitHub**: https://github.com/cookiecutter/cookiecutter
- **Configuration**: JSON-based (`cookiecutter.json`)
- **Templating**: Jinja2 for files and directories
- **Strengths**: Mature ecosystem, simple configuration, extensive documentation
- **Weaknesses**: Limited validation, no update capability

**Configuration Example**:
```json
{
    "project_name": "My Project",
    "project_slug": "{{ cookiecutter.project_name.lower().replace(' ', '_') }}",
    "python_version": ["3.11", "3.10", "3.9"],
    "use_pytest": ["y", "n"],
    "_private_var": "internal value"
}
```

**Key Features**:
- Private variables (underscore prefix)
- Derived variables using Jinja2 expressions
- Choice validation with lists
- Hooks system (pre/post generation)

### 2. Yeoman (JavaScript)
- **GitHub**: https://github.com/yeoman/yeoman
- **Configuration**: JavaScript-based generators
- **Templating**: EJS templates
- **Strengths**: Powerful generator composition, in-memory file system, conflict resolution
- **Weaknesses**: Complex setup, JavaScript-only

**Generator Example**:
```javascript
module.exports = class extends Generator {
  async prompting() {
    this.answers = await this.prompt([
      {
        type: 'input',
        name: 'name',
        message: 'Project name',
        validate: input => input.length > 0
      },
      {
        type: 'list',
        name: 'license',
        message: 'License',
        choices: ['MIT', 'Apache-2.0', 'GPL-3.0']
      }
    ]);
  }
  
  writing() {
    this.fs.copyTpl(
      this.templatePath('package.json'),
      this.destinationPath('package.json'),
      this.answers
    );
  }
};
```

**Key Features**:
- Generator composition and run loop phases
- In-memory file system with conflict resolution
- Persistent configuration storage
- Rich prompt system with validation

### 3. Copier (Python)
- **GitHub**: https://github.com/copier-org/copier
- **Configuration**: YAML-based (`copier.yml`)
- **Templating**: Jinja2 for files and directories
- **Strengths**: Update capability, rich YAML configuration, migrations
- **Weaknesses**: Newer ecosystem, less adoption

**Configuration Example**:
```yaml
_templates_suffix: .j2
_envops:
  block_start_string: "{%"
  block_end_string: "%}"

project_name:
  type: str
  help: What is your project name?
  validator: >-
    {% if not (project_name | regex_search('^[a-zA-Z][a-zA-Z0-9_-]*$')) %}
    Project name must start with a letter and contain only letters, numbers, hyphens, and underscores.
    {% endif %}

python_version:
  type: str
  choices:
    "3.11": "Python 3.11 (recommended)"
    "3.10": "Python 3.10"
    "3.9": "Python 3.9"
  default: "3.11"

use_testing:
  type: bool
  default: true
  help: Include testing framework?
```

**Key Features**:
- **Project update capability** (major differentiator)
- Rich YAML configuration with advanced validation
- Migration system for template evolution
- Conditional subdirectories and files

### 4. Plop (JavaScript)
- **GitHub**: https://github.com/plopjs/plop
- **Configuration**: JavaScript-based (`plopfile.js`)
- **Templating**: Handlebars
- **Strengths**: Lightweight, in-project generators, multiple action types
- **Weaknesses**: Limited to JavaScript projects, simple validation

**Configuration Example**:
```javascript
module.exports = function (plop) {
  plop.setGenerator('component', {
    description: 'Create a new component',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'Component name',
        validate: function (value) {
          if (/.+/.test(value)) return true;
          return 'Name is required';
        }
      }
    ],
    actions: [
      {
        type: 'add',
        path: 'src/components/{{pascalCase name}}.js',
        templateFile: 'plop-templates/component.hbs'
      },
      {
        type: 'add',
        path: 'src/components/{{pascalCase name}}.test.js',
        templateFile: 'plop-templates/component.test.hbs'
      }
    ]
  });
};
```

**Key Features**:
- Multiple action types (add, modify, append)
- Custom Handlebars helpers
- Interactive prompts with validation
- In-project micro-generators

### 5. Modern Scaffolding Tools
- **Angular CLI**: Schematics with TypeScript
- **Vue CLI**: Plugin-based architecture
- **Nx**: Workspace generators with graph dependency
- **Hygen**: Template-based code generation

**Common Patterns**:
- Plugin/extension architecture
- Workspace-aware generation
- Update and migration capabilities
- Rich CLI interfaces

## Key Insights and Patterns

### 1. Configuration Formats
- **JSON**: Simple but limited validation (Cookiecutter)
- **YAML**: Human-readable with rich data types (Copier)
- **JavaScript**: Full programming language but complex (Yeoman, Plop)

### 2. Variable Systems
- **Type System**: string, boolean, integer, choice, multichoice
- **Validation**: Pattern matching, custom validators, cross-variable validation
- **Derived Variables**: Computed from other variables
- **Private Variables**: Internal use only

### 3. Template Processing
- **Jinja2**: Most popular for Python projects
- **Handlebars**: Common in JavaScript ecosystem
- **EJS**: Simple embedded JavaScript templates
- **Filters**: Built-in text transformations (snake_case, kebab_case, etc.)

### 4. File Generation Patterns
- **Conditional Files**: Generated based on user choices
- **Template Inheritance**: Shared templates and partials
- **Directory Structure**: Templated directory names
- **Binary Files**: Handling of non-text files

### 5. Validation Approaches
- **Schema Validation**: JSON Schema, YAML Schema
- **Input Validation**: Real-time validation during prompts
- **Cross-Variable Validation**: Dependencies between variables
- **Post-Generation Validation**: Verify generated project

## Best Practices Synthesis

Based on the research, here are the key best practices for YAML-based template schema design:

### 1. Schema Structure
```yaml
# Template metadata
name: "Template Name"
description: "Template description"
version: "1.0.0"
author: "Author Name"
license: "MIT"
min_copier_version: "6.0.0"

# Template configuration
_templates_suffix: .j2
_envops:
  block_start_string: "{%"
  block_end_string: "%}"

# Variables definition
variables:
  project_name:
    type: string
    description: "The name of your project"
    required: true
    validators:
      - pattern: "^[a-zA-Z][a-zA-Z0-9_-]*$"
        message: "Must start with letter, contain only letters, numbers, hyphens, and underscores"

  python_version:
    type: string
    choices:
      - value: "3.11"
        label: "Python 3.11 (recommended)"
      - value: "3.10"
        label: "Python 3.10"
    default: "3.11"

  use_testing:
    type: boolean
    default: true
    description: "Include testing framework?"
    when: "{{ project_type != 'script' }}"

# File generation rules
files:
  - path: "{{ project_name | snake_case }}/main.py"
    template: "src/main.py.j2"
  - path: "tests/test_main.py"
    template: "tests/test_main.py.j2"
    condition: "{{ use_testing }}"
  - path: "README.md"
    template: "README.md.j2"

# Post-generation actions
hooks:
  pre_generate:
    - validate_python_version
  post_generate:
    - "uv sync"
    - "pre-commit install"
```

### 2. Variable Types and Validation
- **String**: Text input with pattern validation
- **Boolean**: True/false choices
- **Integer**: Numeric input with range validation
- **Choice**: Single selection from options
- **Multichoice**: Multiple selections from options

### 3. Template Organization
- **Modular Structure**: Separate templates for different components
- **Conditional Generation**: Files generated based on user choices
- **Template Inheritance**: Shared templates and partials
- **Asset Handling**: Binary files and static assets

### 4. Update Capability (Inspired by Copier)
- **Answer Storage**: Save user choices for future updates
- **Template Versioning**: Track template versions
- **Migration Scripts**: Handle breaking changes
- **Conflict Resolution**: Merge changes with user modifications

## Recommendations for Python Project Creator

### 1. Adopt YAML Configuration
- Use YAML for human readability and rich data types
- Support JSON Schema validation
- Include template metadata and versioning

### 2. Implement Rich Variable System
- Support all major variable types (string, boolean, integer, choice, multichoice)
- Include built-in filters (snake_case, kebab_case, pascal_case, camel_case)
- Add conditional variables with `when` clauses

### 3. Design for Updates
- Track generated projects with `.template-answers.yml`
- Support template updates with conflict resolution
- Include migration system for breaking changes

### 4. Comprehensive Validation
- Multi-layer validation (schema, input, cross-variable, post-generation)
- Custom validators for complex rules
- Clear error messages and suggestions

### 5. Template Processing
- Use Jinja2 for both filenames and content
- Support conditional file generation
- Include template inheritance and composition

## Implementation Priority

1. **Phase 1**: Basic YAML schema with variables and file generation
2. **Phase 2**: Advanced validation and conditional logic
3. **Phase 3**: Update capability and migration system
4. **Phase 4**: Plugin architecture and extensibility

## Conclusion

The research reveals that **Copier's update capability** is the most significant differentiator among template systems. Most systems focus on initial generation, but the ability to update existing projects when templates evolve is a major advantage that should be prioritized in our YAML-based schema design.

The recommended schema structure combines the best features from all analyzed systems while maintaining simplicity and extensibility.
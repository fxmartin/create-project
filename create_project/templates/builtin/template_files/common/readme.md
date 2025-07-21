# ABOUTME: Standard README.md template for Python projects
# ABOUTME: Provides project documentation structure with templated variables

# {{project_name}}

{{description}}

## Installation

```bash
pip install {{project_name}}
```

## Usage

{% if project_type == "script" %}
Run the script directly:

```bash
python {{project_name}}.py
```
{% elif project_type == "cli" %}
After installation, use the command:

```bash
{{project_name}} --help
```
{% elif project_type == "django" %}
To start the development server:

```bash
python manage.py runserver
```
{% elif project_type == "flask" %}
To run the Flask application:

```bash
flask run
```
{% elif project_type == "library" %}
Import and use in your Python code:

```python
import {{project_name}}

# Your code here
```
{% endif %}

## Development

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd {{project_name}}
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

{% if include_tests %}
### Testing

Run tests with:

```bash
{% if testing_framework == "pytest" %}
pytest
{% else %}
python -m unittest discover tests
{% endif %}
```
{% endif %}

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the {{license}} License - see the [LICENSE](LICENSE) file for details.

## Author

**{{author}}**{% if email %} - {{email}}{% endif %}

## Changelog

### Version 0.1.0
- Initial release
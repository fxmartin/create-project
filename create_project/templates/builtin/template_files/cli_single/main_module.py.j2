# ABOUTME: Main CLI module for single package command-line applications
# ABOUTME: Implements the primary CLI interface using Click framework

"""
Main command-line interface for {{project_name}}.

This module implements the primary CLI functionality using the Click framework,
providing a clean and extensible command-line interface.
"""

import sys
from typing import Optional

import click

from . import __version__
{% if include_helpers %}from .helpers import validate_input, process_data{% endif %}


@click.group()
@click.version_option(version=__version__, prog_name="{{project_name}}")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """
    {{description}}
    
    {{project_name}} is a command-line tool that helps you...
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    
    if verbose:
        click.echo(f"{{project_name}} v{__version__} - Verbose mode enabled")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True), required=False)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--format", type=click.Choice(["json", "csv", "text"]), default="text", help="Output format")
@click.pass_context
def process(ctx: click.Context, input_file: Optional[str], output: Optional[str], format: str) -> None:
    """
    Process input data and generate output.
    
    If no input file is provided, the command will read from stdin.
    """
    verbose = ctx.obj.get("verbose", False)
    
    try:
        if verbose:
            click.echo(f"Processing with format: {format}")
            if input_file:
                click.echo(f"Input file: {input_file}")
            if output:
                click.echo(f"Output file: {output}")
        
        # Your processing logic goes here
        {% if include_helpers %}
        if input_file:
            if not validate_input(input_file):
                click.echo("Error: Invalid input file", err=True)
                sys.exit(1)
            
            result = process_data(input_file, format)
        else:
            # Read from stdin
            data = sys.stdin.read()
            result = process_data(data, format, from_stdin=True)
        {% else %}
        if input_file:
            click.echo(f"Processing file: {input_file}")
            result = f"Processed {input_file} in {format} format"
        else:
            click.echo("Processing data from stdin...")
            result = f"Processed stdin data in {format} format"
        {% endif %}
        
        if output:
            with open(output, "w") as f:
                f.write(result)
            if verbose:
                click.echo(f"Output written to: {output}")
        else:
            click.echo(result)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context  
def info(ctx: click.Context) -> None:
    """Display information about {{project_name}}."""
    verbose = ctx.obj.get("verbose", False)
    
    click.echo(f"{{project_name}} v{__version__}")
    click.echo(f"Author: {{author}}")
    {% if email %}click.echo(f"Email: {{email}}"){% endif %}
    click.echo(f"Description: {{description}}")
    
    if verbose:
        click.echo("\nVerbose information:")
        click.echo(f"Python version: {sys.version}")
        click.echo(f"Platform: {sys.platform}")


def main() -> None:
    """Main entry point for the CLI application."""
    cli()


if __name__ == "__main__":
    main()
# ABOUTME: Helper functions for CLI single package applications
# ABOUTME: Provides utility functions for data processing and validation

"""
Helper functions for {{project_name}}.

This module contains utility functions that support the main CLI functionality,
including input validation, data processing, and formatting operations.
"""

import json
import csv
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def validate_input(input_path: Union[str, Path]) -> bool:
    """
    Validate input file or data.
    
    Args:
        input_path: Path to the input file
        
    Returns:
        bool: True if input is valid, False otherwise
    """
    path = Path(input_path)
    
    # Check if file exists and is readable
    if not path.exists():
        return False
        
    if not path.is_file():
        return False
        
    try:
        # Try to read the file to ensure it's accessible
        with open(path, 'r') as f:
            f.read(1)  # Read just one character to test
        return True
    except (IOError, OSError, PermissionError):
        return False


def process_data(data: Union[str, Path], output_format: str, from_stdin: bool = False) -> str:
    """
    Process input data and return formatted output.
    
    Args:
        data: Input data (file path or raw data string)
        output_format: Desired output format ('json', 'csv', 'text')
        from_stdin: Whether data comes from stdin
        
    Returns:
        str: Processed data in the specified format
        
    Raises:
        ValueError: If output format is not supported
        IOError: If file cannot be read
    """
    if output_format not in ["json", "csv", "text"]:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    # Read the data
    if from_stdin or isinstance(data, str):
        content = data if isinstance(data, str) else str(data)
    else:
        with open(data, 'r') as f:
            content = f.read()
    
    # Process the data (example processing - customize as needed)
    processed_data = {
        "input_length": len(content),
        "line_count": len(content.splitlines()),
        "word_count": len(content.split()),
        "character_count": len(content),
        "content_preview": content[:100] + "..." if len(content) > 100 else content
    }
    
    # Format output
    if output_format == "json":
        return json.dumps(processed_data, indent=2)
    elif output_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["metric", "value"])
        for key, value in processed_data.items():
            writer.writerow([key, value])
        return output.getvalue()
    else:  # text format
        lines = []
        lines.append("=== Processing Results ===")
        for key, value in processed_data.items():
            formatted_key = key.replace("_", " ").title()
            lines.append(f"{formatted_key}: {value}")
        return "\n".join(lines)


def format_output(data: Dict[str, Any], format_type: str) -> str:
    """
    Format data for output.
    
    Args:
        data: Data dictionary to format
        format_type: Output format type
        
    Returns:
        str: Formatted output string
    """
    return process_data(str(data), format_type, from_stdin=True)


def create_progress_indicator(total: int) -> None:
    """
    Create a simple progress indicator.
    
    Args:
        total: Total number of items to process
    """
    # Simple progress implementation - can be enhanced
    import time
    
    for i in range(total + 1):
        percent = (i / total) * 100
        bar_length = 30
        filled_length = int(bar_length * i // total)
        bar = "█" * filled_length + "-" * (bar_length - filled_length)
        print(f"\rProgress: |{bar}| {percent:.1f}% Complete", end="")
        time.sleep(0.1)  # Simulate work
    print()  # New line after completion


def safe_file_write(file_path: Union[str, Path], content: str, backup: bool = True) -> bool:
    """
    Safely write content to a file with optional backup.
    
    Args:
        file_path: Path to the output file
        content: Content to write
        backup: Whether to create a backup if file exists
        
    Returns:
        bool: True if write was successful, False otherwise
    """
    path = Path(file_path)
    
    try:
        # Create backup if file exists and backup is requested
        if backup and path.exists():
            backup_path = path.with_suffix(path.suffix + '.bak')
            path.rename(backup_path)
        
        # Write the content
        with open(path, 'w') as f:
            f.write(content)
            
        return True
        
    except (IOError, OSError, PermissionError) as e:
        print(f"Error writing file: {e}")
        return False
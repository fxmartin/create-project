# ABOUTME: Main script file template for one-off scripts
# ABOUTME: Provides a basic script structure with argument parsing and main function

#!/usr/bin/env python3
"""
{{description}}

Author: {{author}}{% if email %} <{{email}}>{% endif %}
Created: {{created_date}}
"""

import argparse
import sys
from typing import Optional


def main() -> int:
    """
    Main entry point for the script.
    
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="{{description}}",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"{{project_name}} 0.1.0"
    )
    
    {% if include_verbose %}
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    {% endif %}
    
    # Add your command-line arguments here
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Input file to process (optional)"
    )
    
    args = parser.parse_args()
    
    try:
        # Your script logic goes here
        {% if include_verbose %}
        if args.verbose:
            print(f"Processing with verbose output...")
        {% endif %}
        
        if args.input_file:
            print(f"Processing file: {args.input_file}")
            # Add file processing logic here
        else:
            print("{{project_name}} is running...")
            # Add default behavior here
        
        return 0
        
    except KeyboardInterrupt:
        print("\nScript interrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
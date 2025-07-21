# ABOUTME: Test file template for one-off scripts
# ABOUTME: Provides basic test structure for script functionality

import unittest
from unittest.mock import patch, mock_open
import sys
import os

# Add the script directory to the path for importing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import {{project_name}}


class Test{{project_name|title}}(unittest.TestCase):
    """Test cases for {{project_name}} script."""
    
    def test_main_with_no_arguments(self):
        """Test main function with no arguments."""
        with patch('sys.argv', ['{{project_name}}.py']):
            result = {{project_name}}.main()
            self.assertEqual(result, 0)
    
    {% if include_verbose %}
    def test_main_with_verbose_flag(self):
        """Test main function with verbose flag."""
        with patch('sys.argv', ['{{project_name}}.py', '--verbose']):
            with patch('builtins.print') as mock_print:
                result = {{project_name}}.main()
                self.assertEqual(result, 0)
                mock_print.assert_called()
    {% endif %}
    
    def test_main_with_input_file(self):
        """Test main function with input file."""
        with patch('sys.argv', ['{{project_name}}.py', 'test_file.txt']):
            with patch('builtins.print') as mock_print:
                result = {{project_name}}.main()
                self.assertEqual(result, 0)
                mock_print.assert_called()
    
    def test_keyboard_interrupt_handling(self):
        """Test handling of keyboard interrupt."""
        with patch('sys.argv', ['{{project_name}}.py']):
            with patch('builtins.print') as mock_print:
                with patch('{{project_name}}.main', side_effect=KeyboardInterrupt):
                    # This test would need to be adapted based on actual implementation
                    pass
    
    def test_exception_handling(self):
        """Test handling of general exceptions."""
        with patch('sys.argv', ['{{project_name}}.py']):
            with patch('builtins.print') as mock_print:
                # Test exception handling in your specific implementation
                pass


if __name__ == '__main__':
    unittest.main()
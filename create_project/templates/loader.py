# ABOUTME: Template loading system for YAML template files
# ABOUTME: Handles template discovery, loading, and caching with validation

"""
Template Loader

Responsible for discovering, loading, and managing YAML template files.
Provides template search functionality and integrates with the template
validation system.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from pydantic import ValidationError

from ..config.config_manager import ConfigManager
from ..utils.logger import get_logger
from .engine import TemplateLoadError
from .schema.template import Template


class TemplateLoader:
    """Loads and manages YAML template files."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the template loader.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = get_logger(__name__)
        
        # Get template configuration
        self.template_directories = self.config_manager.get_setting("templates.directories", ["templates"])
        self.builtin_templates_dir = self.config_manager.get_setting("templates.builtin_directory", "templates/builtin")
        self.user_templates_dir = self.config_manager.get_setting("templates.user_directory", "templates/user")
        
        self.logger.info(f"Template loader initialized with directories: {self.template_directories}")
    
    def discover_templates(self, include_builtin: bool = True, include_user: bool = True) -> List[Path]:
        """Discover all available template files.
        
        Args:
            include_builtin: Include built-in templates
            include_user: Include user templates
            
        Returns:
            List of template file paths
        """
        template_files = []
        
        # Search in configured directories
        for template_dir in self.template_directories:
            template_path = Path(template_dir)
            if template_path.exists() and template_path.is_dir():
                template_files.extend(self._find_yaml_files(template_path))
        
        # Search in builtin templates directory
        if include_builtin:
            builtin_path = Path(self.builtin_templates_dir)
            if builtin_path.exists() and builtin_path.is_dir():
                template_files.extend(self._find_yaml_files(builtin_path))
        
        # Search in user templates directory
        if include_user:
            user_path = Path(self.user_templates_dir)
            if user_path.exists() and user_path.is_dir():
                template_files.extend(self._find_yaml_files(user_path))
        
        # Remove duplicates and sort
        unique_files = list(set(template_files))
        unique_files.sort()
        
        self.logger.info(f"Discovered {len(unique_files)} template files")
        return unique_files
    
    def _find_yaml_files(self, directory: Path) -> List[Path]:
        """Find YAML files in a directory recursively.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of YAML file paths
        """
        yaml_files = []
        yaml_extensions = {'.yaml', '.yml'}
        
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in yaml_extensions:
                    yaml_files.append(file_path)
        except PermissionError as e:
            self.logger.warning(f"Permission denied accessing directory {directory}: {e}")
        except Exception as e:
            self.logger.error(f"Error searching directory {directory}: {e}")
        
        return yaml_files
    
    def load_template_metadata(self, template_path: Union[str, Path]) -> Dict[str, any]:
        """Load template metadata without full validation.
        
        Args:
            template_path: Path to the template file
            
        Returns:
            Template metadata dictionary
            
        Raises:
            TemplateLoadError: If metadata loading fails
        """
        template_path = Path(template_path)
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
            
            if not template_data:
                raise TemplateLoadError(f"Empty template file: {template_path}")
            
            # Extract metadata
            metadata = template_data.get('metadata', {})
            if not metadata:
                raise TemplateLoadError(f"No metadata found in template: {template_path}")
            
            # Add file information
            metadata['file_path'] = str(template_path)
            metadata['file_size'] = template_path.stat().st_size
            metadata['file_modified'] = template_path.stat().st_mtime
            
            return metadata
            
        except yaml.YAMLError as e:
            raise TemplateLoadError(f"YAML parsing error in {template_path}: {e}")
        except Exception as e:
            raise TemplateLoadError(f"Error loading metadata from {template_path}: {e}")
    
    def list_templates(self, category: Optional[str] = None) -> List[Dict[str, any]]:
        """List available templates with metadata.
        
        Args:
            category: Filter by template category
            
        Returns:
            List of template metadata dictionaries
        """
        templates = []
        template_files = self.discover_templates()
        
        for template_file in template_files:
            try:
                metadata = self.load_template_metadata(template_file)
                
                # Filter by category if specified
                if category and metadata.get('category') != category:
                    continue
                
                templates.append(metadata)
                
            except TemplateLoadError as e:
                self.logger.warning(f"Failed to load template metadata: {e}")
                continue
        
        # Sort by name
        templates.sort(key=lambda t: t.get('name', ''))
        
        self.logger.info(f"Listed {len(templates)} templates" + 
                        (f" in category '{category}'" if category else ""))
        return templates
    
    def find_template_by_name(self, name: str) -> Optional[Path]:
        """Find a template by name.
        
        Args:
            name: Template name to search for
            
        Returns:
            Path to template file if found, None otherwise
        """
        template_files = self.discover_templates()
        
        for template_file in template_files:
            try:
                metadata = self.load_template_metadata(template_file)
                if metadata.get('name') == name:
                    self.logger.debug(f"Found template '{name}' at: {template_file}")
                    return template_file
            except TemplateLoadError:
                continue
        
        self.logger.warning(f"Template '{name}' not found")
        return None
    
    def validate_template_file(self, template_path: Union[str, Path]) -> List[str]:
        """Validate a template file without loading it into memory.
        
        Args:
            template_path: Path to the template file
            
        Returns:
            List of validation errors (empty if valid)
        """
        template_path = Path(template_path)
        errors = []
        
        try:
            # Check file exists and is readable
            if not template_path.exists():
                errors.append(f"Template file not found: {template_path}")
                return errors
            
            if not template_path.is_file():
                errors.append(f"Template path is not a file: {template_path}")
                return errors
            
            # Try to parse YAML
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
            
            if not template_data:
                errors.append("Template file is empty")
                return errors
            
            # Try to create Template object for validation
            try:
                template = Template(**template_data)
                validation_errors = template.validate_template_complete()
                errors.extend(validation_errors)
            except ValidationError as e:
                errors.append(f"Template validation failed: {e}")
            
        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {e}")
        except Exception as e:
            errors.append(f"Unexpected validation error: {e}")
        
        return errors
    
    def get_template_categories(self) -> List[str]:
        """Get all available template categories.
        
        Returns:
            List of unique template categories
        """
        categories = set()
        template_files = self.discover_templates()
        
        for template_file in template_files:
            try:
                metadata = self.load_template_metadata(template_file)
                category = metadata.get('category')
                if category:
                    categories.add(category)
            except TemplateLoadError:
                continue
        
        return sorted(list(categories))
    
    def get_builtin_templates(self) -> List[Dict[str, any]]:
        """Get list of built-in templates.
        
        Returns:
            List of built-in template metadata
        """
        builtin_templates = []
        builtin_path = Path(self.builtin_templates_dir)
        
        if builtin_path.exists() and builtin_path.is_dir():
            yaml_files = self._find_yaml_files(builtin_path)
            
            for template_file in yaml_files:
                try:
                    metadata = self.load_template_metadata(template_file)
                    metadata['is_builtin'] = True
                    builtin_templates.append(metadata)
                except TemplateLoadError as e:
                    self.logger.warning(f"Failed to load builtin template: {e}")
        
        return builtin_templates
    
    def get_user_templates(self) -> List[Dict[str, any]]:
        """Get list of user templates.
        
        Returns:
            List of user template metadata
        """
        user_templates = []
        user_path = Path(self.user_templates_dir)
        
        if user_path.exists() and user_path.is_dir():
            yaml_files = self._find_yaml_files(user_path)
            
            for template_file in yaml_files:
                try:
                    metadata = self.load_template_metadata(template_file)
                    metadata['is_user'] = True
                    user_templates.append(metadata)
                except TemplateLoadError as e:
                    self.logger.warning(f"Failed to load user template: {e}")
        
        return user_templates
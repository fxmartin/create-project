# ABOUTME: License manager for loading and retrieving license data
# ABOUTME: Provides centralized access to license templates and text

from pathlib import Path
from typing import Dict, List, Optional

from create_project.utils.logger import get_logger

from .models import License


class LicenseManager:
    """Manager for loading and retrieving software licenses.
    
    Provides centralized access to license templates and handles
    license text retrieval and variable substitution.
    """

    def __init__(self, licenses_dir: Optional[Path] = None):
        """Initialize the license manager.
        
        Args:
            licenses_dir: Directory containing license text files.
                         Defaults to resources/licenses/ in package.
        """
        self.logger = get_logger(__name__)

        if licenses_dir is None:
            # Default to package's resources/licenses directory
            package_root = Path(__file__).parent.parent
            licenses_dir = package_root / "resources" / "licenses"

        self.licenses_dir = Path(licenses_dir)
        self._licenses: Dict[str, License] = {}
        self._loaded = False

    def get_license(self, license_id: str) -> License:
        """Get a license by its ID.
        
        Args:
            license_id: Unique identifier for the license
            
        Returns:
            License object with metadata and text
            
        Raises:
            ValueError: If license ID is not found
        """
        if not self._loaded:
            self._load_licenses()

        if license_id not in self._licenses:
            raise ValueError(f"License '{license_id}' not found")

        return self._licenses[license_id]

    def get_available_licenses(self) -> List[str]:
        """Get list of available license IDs.
        
        Returns:
            List of license IDs
        """
        if not self._loaded:
            self._load_licenses()

        return list(self._licenses.keys())

    def render_license(self, license_id: str, variables: Dict[str, str]) -> str:
        """Render license text with variable substitution.
        
        Args:
            license_id: Unique identifier for the license
            variables: Dictionary of variables to substitute
            
        Returns:
            License text with variables substituted
            
        Raises:
            ValueError: If license ID is not found
        """
        license_obj = self.get_license(license_id)

        # Simple string substitution for template variables
        rendered_text = license_obj.text
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            rendered_text = rendered_text.replace(placeholder, value)

        return rendered_text

    def validate_license_variables(self, license_id: str, variables: Dict[str, str]) -> bool:
        """Validate that all required variables are provided for a license.
        
        Args:
            license_id: Unique identifier for the license
            variables: Dictionary of variables to validate
            
        Returns:
            True if all required variables are provided, False otherwise
            
        Raises:
            ValueError: If license ID is not found
        """
        license_obj = self.get_license(license_id)

        # Check if all required fields are present in variables
        for required_field in license_obj.requires_fields:
            if required_field not in variables:
                return False

        return True

    def _load_licenses(self):
        """Load licenses from the licenses directory."""
        self.logger.debug(f"Loading licenses from {self.licenses_dir}")

        if not self.licenses_dir.exists():
            self.logger.warning(f"Licenses directory not found: {self.licenses_dir}")
            self._loaded = True
            return

        # Find all .txt files in licenses directory
        for license_file in self.licenses_dir.glob("*.txt"):
            license_id = license_file.stem

            try:
                # Read license text
                license_text = license_file.read_text(encoding="utf-8")

                # Get metadata for this license
                metadata = self._get_license_metadata(license_id)

                # Create License object
                license_obj = License(
                    id=license_id,
                    name=metadata["name"],
                    text=license_text,
                    url=metadata["url"],
                    requires_fields=metadata.get("requires_fields", [])
                )

                self._licenses[license_id] = license_obj
                self.logger.debug(f"Loaded license: {license_id}")

            except Exception as e:
                self.logger.error(f"Error loading license {license_id}: {e}")
                continue

        self.logger.info(f"Loaded {len(self._licenses)} licenses")
        self._loaded = True

    def _get_license_metadata(self, license_id: str) -> Dict[str, any]:
        """Get metadata for a specific license ID.
        
        Args:
            license_id: Unique identifier for the license
            
        Returns:
            Dictionary with license metadata (name, url, requires_fields)
        """
        # License metadata mapping
        license_metadata = {
            "mit": {
                "name": "MIT License",
                "url": "https://opensource.org/licenses/MIT",
                "requires_fields": ["author", "year"]
            },
            "apache-2.0": {
                "name": "Apache License 2.0",
                "url": "https://opensource.org/licenses/Apache-2.0",
                "requires_fields": ["author", "year"]
            },
            "gpl-3.0": {
                "name": "GNU General Public License v3.0",
                "url": "https://www.gnu.org/licenses/gpl-3.0",
                "requires_fields": []
            },
            "bsd-3-clause": {
                "name": "BSD 3-Clause License",
                "url": "https://opensource.org/licenses/BSD-3-Clause",
                "requires_fields": ["author", "year"]
            },
            "unlicense": {
                "name": "The Unlicense",
                "url": "https://unlicense.org/",
                "requires_fields": []
            }
        }

        return license_metadata.get(license_id, {
            "name": f"Unknown License ({license_id})",
            "url": "https://example.com",
            "requires_fields": []
        })

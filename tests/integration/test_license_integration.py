# ABOUTME: Integration tests for license system with real license files
# ABOUTME: Tests full license loading and rendering workflow


from create_project.licenses.manager import LicenseManager


class TestLicenseIntegration:
    """Test license system integration with real license files."""

    def test_load_all_builtin_licenses(self):
        """Test loading all built-in license files."""
        # Use default path which should point to our license files
        manager = LicenseManager()
        licenses = manager.get_available_licenses()

        # Should have all 5 licenses we created
        expected_licenses = {
            "mit",
            "apache-2.0",
            "gpl-3.0",
            "bsd-3-clause",
            "unlicense",
        }
        assert set(licenses) == expected_licenses

    def test_mit_license_loading_and_rendering(self):
        """Test MIT license loads correctly and renders with variables."""
        manager = LicenseManager()

        # Get MIT license
        mit_license = manager.get_license("mit")
        assert mit_license.id == "mit"
        assert mit_license.name == "MIT License"
        assert "{year}" in mit_license.text
        assert "{author}" in mit_license.text
        assert "Permission is hereby granted" in mit_license.text

        # Test variable validation
        variables = {"author": "John Doe", "year": "2025"}
        assert manager.validate_license_variables("mit", variables)

        # Test rendering
        rendered = manager.render_license("mit", variables)
        assert "Copyright (c) 2025 John Doe" in rendered
        assert "{year}" not in rendered
        assert "{author}" not in rendered
        assert "Permission is hereby granted" in rendered

    def test_apache_license_loading_and_rendering(self):
        """Test Apache 2.0 license loads correctly and renders with variables."""
        manager = LicenseManager()

        # Get Apache license
        apache_license = manager.get_license("apache-2.0")
        assert apache_license.id == "apache-2.0"
        assert apache_license.name == "Apache License 2.0"
        assert "Apache License" in apache_license.text
        assert "Version 2.0" in apache_license.text

        # Test rendering with variables
        variables = {"author": "Jane Smith", "year": "2025"}
        rendered = manager.render_license("apache-2.0", variables)
        assert "Copyright 2025 Jane Smith" in rendered

    def test_gpl_license_no_variables_required(self):
        """Test GPL license loads and requires no variables."""
        manager = LicenseManager()

        # Get GPL license
        gpl_license = manager.get_license("gpl-3.0")
        assert gpl_license.id == "gpl-3.0"
        assert gpl_license.name == "GNU General Public License v3.0"
        assert gpl_license.requires_fields == []
        assert "GNU GENERAL PUBLIC LICENSE" in gpl_license.text

        # Should validate with no variables
        assert manager.validate_license_variables("gpl-3.0", {})

        # Should render without changes
        rendered = manager.render_license("gpl-3.0", {})
        assert rendered == gpl_license.text

    def test_bsd_license_loading(self):
        """Test BSD 3-Clause license loads correctly."""
        manager = LicenseManager()

        # Get BSD license
        bsd_license = manager.get_license("bsd-3-clause")
        assert bsd_license.id == "bsd-3-clause"
        assert bsd_license.name == "BSD 3-Clause License"
        assert "BSD 3-Clause License" in bsd_license.text
        assert "Redistribution and use" in bsd_license.text
        assert "{year}" in bsd_license.text
        assert "{author}" in bsd_license.text

    def test_unlicense_loading(self):
        """Test Unlicense loads correctly and requires no variables."""
        manager = LicenseManager()

        # Get Unlicense
        unlicense = manager.get_license("unlicense")
        assert unlicense.id == "unlicense"
        assert unlicense.name == "The Unlicense"
        assert unlicense.requires_fields == []
        assert "public domain" in unlicense.text.lower()

        # Should validate with no variables
        assert manager.validate_license_variables("unlicense", {})

    def test_license_metadata_accuracy(self):
        """Test that license metadata is accurate for all licenses."""
        manager = LicenseManager()

        # Test MIT
        mit = manager.get_license("mit")
        assert str(mit.url) == "https://opensource.org/licenses/MIT"
        assert set(mit.requires_fields) == {"author", "year"}

        # Test Apache
        apache = manager.get_license("apache-2.0")
        assert str(apache.url) == "https://opensource.org/licenses/Apache-2.0"
        assert set(apache.requires_fields) == {"author", "year"}

        # Test GPL
        gpl = manager.get_license("gpl-3.0")
        assert str(gpl.url) == "https://www.gnu.org/licenses/gpl-3.0"
        assert gpl.requires_fields == []

        # Test BSD
        bsd = manager.get_license("bsd-3-clause")
        assert str(bsd.url) == "https://opensource.org/licenses/BSD-3-Clause"
        assert set(bsd.requires_fields) == {"author", "year"}

        # Test Unlicense
        unlicense = manager.get_license("unlicense")
        assert str(unlicense.url) == "https://unlicense.org/"
        assert unlicense.requires_fields == []

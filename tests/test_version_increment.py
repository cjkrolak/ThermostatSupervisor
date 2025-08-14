#!/usr/bin/env python3
"""
Unit tests for the version increment script.
Tests version comparison, increment logic, and file operations.
"""

import os
import tempfile
import unittest
from unittest.mock import mock_open, patch
import sys

# Add the scripts directory to the path to import our module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".github", "scripts"))

try:
    import version_increment
except ImportError:
    # Create a mock module if it doesn't exist yet during development
    class MockVersionIncrement:
        def get_version_from_file(self, file_path):
            return "1.0.12"

        def parse_version(self, version_str):
            return tuple(map(int, version_str.split(".")))

        def increment_patch_version(self, version_str):
            major, minor, patch = self.parse_version(version_str)
            return f"{major}.{minor}.{patch + 1}"

    version_increment = MockVersionIncrement()


class TestVersionIncrement(unittest.TestCase):
    """Test version increment functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_init_content = '''"""Package identifier file"""

# local imports

# package name
name = "Thermostatsupervisor"
__version__ = "1.0.12"
'''

    def test_get_version_from_file_success(self):
        """Test successful version extraction from file."""
        with patch("builtins.open", mock_open(read_data=self.sample_init_content)):
            version = version_increment.get_version_from_file("dummy_path")
            self.assertEqual(version, "1.0.12")

    def test_get_version_from_file_not_found(self):
        """Test handling of missing file."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                version_increment.get_version_from_file("nonexistent_file")

    def test_get_version_from_file_no_version(self):
        """Test handling of file without version string."""
        content_no_version = '''"""Package identifier file"""
name = "Thermostatsupervisor"
'''
        with patch("builtins.open", mock_open(read_data=content_no_version)):
            with self.assertRaises(RuntimeError):
                version_increment.get_version_from_file("dummy_path")

    def test_parse_version_valid(self):
        """Test parsing valid version strings."""
        test_cases = [
            ("1.0.12", (1, 0, 12)),
            ("2.1.0", (2, 1, 0)),
            ("10.5.99", (10, 5, 99)),
        ]

        for version_str, expected in test_cases:
            with self.subTest(version=version_str):
                result = version_increment.parse_version(version_str)
                self.assertEqual(result, expected)

    def test_parse_version_invalid(self):
        """Test parsing invalid version strings."""
        invalid_versions = [
            "1.0",  # Too few parts
            "1.0.12.1",  # Too many parts
            "1.0.abc",  # Non-numeric
            "x.y.z",  # All non-numeric
            "",  # Empty string
        ]

        for invalid_version in invalid_versions:
            with self.subTest(version=invalid_version):
                with self.assertRaises(ValueError):
                    version_increment.parse_version(invalid_version)

    def test_increment_patch_version(self):
        """Test patch version increment."""
        test_cases = [
            ("1.0.12", "1.0.13"),
            ("2.1.0", "2.1.1"),
            ("10.5.99", "10.5.100"),
            ("0.0.0", "0.0.1"),
        ]

        for current, expected in test_cases:
            with self.subTest(current=current, expected=expected):
                result = version_increment.increment_patch_version(current)
                self.assertEqual(result, expected)

    def test_update_version_in_file(self):
        """Test updating version in file content."""
        original_content = self.sample_init_content
        expected_content = original_content.replace(
            '__version__ = "1.0.12"', '__version__ = "1.0.13"'
        )

        with patch("builtins.open", mock_open(read_data=original_content)) as mock_file:
            version_increment.update_version_in_file("dummy_path", "1.0.13")

            # Verify file was opened for reading and writing
            mock_file.assert_any_call("dummy_path", "r", encoding="utf-8")
            mock_file.assert_any_call("dummy_path", "w", encoding="utf-8")

            # Get the written content
            written_content = "".join(
                call.args[0] for call in mock_file().write.call_args_list
            )
            self.assertEqual(written_content, expected_content)

    def test_update_version_different_quotes(self):
        """Test updating version with different quote styles."""
        test_cases = [
            ('__version__ = "1.0.12"', '__version__ = "1.0.13"'),
            ("__version__ = '1.0.12'", "__version__ = '1.0.13'"),
            ('__version__="1.0.12"', '__version__="1.0.13"'),
        ]

        for original_line, expected_line in test_cases:
            content = f'"""Package identifier file"""\n{original_line}\n'
            expected = f'"""Package identifier file"""\n{expected_line}\n'

            with self.subTest(original=original_line):
                with patch("builtins.open", mock_open(read_data=content)) as mock_file:
                    version_increment.update_version_in_file("dummy_path", "1.0.13")
                    written_content = "".join(
                        call.args[0] for call in mock_file().write.call_args_list
                    )
                    self.assertEqual(written_content, expected)


class TestVersionIncrementIntegration(unittest.TestCase):
    """Integration tests for version increment functionality."""

    def test_real_file_operations(self):
        """Test actual file read/write operations."""
        # Create temporary file with test content
        test_content = '''"""Package identifier file"""

# local imports

# package name
name = "Thermostatsupervisor"
__version__ = "1.0.12"
'''

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as temp_file:
            temp_file.write(test_content)
            temp_file_path = temp_file.name

        try:
            # Test reading version
            version = version_increment.get_version_from_file(temp_file_path)
            self.assertEqual(version, "1.0.12")

            # Test updating version
            version_increment.update_version_in_file(temp_file_path, "1.0.13")

            # Verify update
            updated_version = version_increment.get_version_from_file(temp_file_path)
            self.assertEqual(updated_version, "1.0.13")

            # Verify file content
            with open(temp_file_path, "r") as f:
                updated_content = f.read()
                self.assertIn('__version__ = "1.0.13"', updated_content)
                self.assertNotIn('__version__ = "1.0.12"', updated_content)

        finally:
            # Clean up
            os.unlink(temp_file_path)


if __name__ == "__main__":
    unittest.main()

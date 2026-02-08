"""
Unit tests for environment.py package version detection.
"""

import unittest
from unittest.mock import MagicMock, patch

from src import environment as env
from tests import unit_test_common as utc


class TestPackageVersionDetection(utc.UnitTest):
    """Test package version detection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.print_test_name()

    def test_get_package_version_with_version_attribute(self):
        """Test version detection when module has __version__ attribute."""
        # Create a mock module with __version__
        mock_module = MagicMock()
        mock_module.__name__ = "test_module"
        mock_module.__version__ = "1.2.3"

        version = env.get_package_version(mock_module)
        self.assertEqual(version, (1, 2, 3))

    def test_get_package_version_without_version_attribute(self):
        """Test version detection fallback using importlib.metadata."""
        # Create a mock module without __version__
        mock_module = MagicMock()
        mock_module.__name__ = "blinkpy"
        del mock_module.__version__  # Remove __version__ attribute

        # Mock importlib.metadata to return a known version
        with patch("importlib.metadata.version") as mock_version:
            mock_version.return_value = "0.23.0"
            version = env.get_package_version(mock_module)
            self.assertEqual(version, (0, 23, 0))
            mock_version.assert_called_once_with("blinkpy")

    def test_get_package_version_fallback_to_zero(self):
        """Test version detection fallback to 0.0.0 when all methods fail."""
        # Create a mock module without __version__
        mock_module = MagicMock()
        mock_module.__name__ = "nonexistent_module"
        del mock_module.__version__

        # Mock importlib.metadata to raise PackageNotFoundError
        with patch("importlib.metadata.version") as mock_version:
            import importlib.metadata

            mock_version.side_effect = importlib.metadata.PackageNotFoundError()
            version = env.get_package_version(mock_module)
            self.assertEqual(version, (0, 0, 0))

    def test_get_package_version_with_dev_suffix(self):
        """Test version detection strips dev suffixes correctly."""
        mock_module = MagicMock()
        mock_module.__name__ = "test_module"
        mock_module.__version__ = "1.2.3.dev0+abc123"

        version = env.get_package_version(mock_module)
        self.assertEqual(version, (1, 2, 3))

    def test_get_package_version_element_selection(self):
        """Test individual element selection from version tuple."""
        mock_module = MagicMock()
        mock_module.__name__ = "test_module"
        mock_module.__version__ = "2.5.7"

        # Test major version
        major = env.get_package_version(mock_module, element="major")
        self.assertEqual(major, 2)

        # Test minor version
        minor = env.get_package_version(mock_module, element="minor")
        self.assertEqual(minor, 5)

        # Test patch version
        patch_ver = env.get_package_version(mock_module, element="patch")
        self.assertEqual(patch_ver, 7)

        # Test numeric element selection
        major_num = env.get_package_version(mock_module, element=0)
        self.assertEqual(major_num, 2)

    def test_blink_version_detection_integration(self):
        """Integration test for blinkpy version detection."""
        # This test requires blinkpy to be installed
        try:
            import blinkpy

            version = env.get_package_version(blinkpy)

            # Version should be a tuple of three integers
            self.assertIsInstance(version, tuple)
            if isinstance(version, tuple):
                self.assertEqual(len(version), 3)
                self.assertTrue(all(isinstance(v, int) for v in version))

                # Version should be >= (0, 22, 0) for modern blinkpy
                self.assertGreaterEqual(
                    version,
                    (0, 22, 0),
                    "blinkpy version should be >= 0.22.0 for async authentication",
                )

        except ImportError:
            self.skipTest("blinkpy not installed")


if __name__ == "__main__":
    unittest.main(verbosity=2)

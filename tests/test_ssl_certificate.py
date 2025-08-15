"""
Unit tests for SSL certificate management functionality.
"""

import unittest
import pathlib
import tempfile
import shutil
import os

from thermostatsupervisor import ssl_certificate


class TestSSLCertificate(unittest.TestCase):
    """Test SSL certificate generation and management."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_ssl_dir = ssl_certificate.get_ssl_cert_directory

        # Mock the SSL cert directory to use our test directory
        def mock_ssl_dir():
            return pathlib.Path(self.test_dir)

        ssl_certificate.get_ssl_cert_directory = mock_ssl_dir

    def tearDown(self):
        """Clean up test environment."""
        # Restore original function
        ssl_certificate.get_ssl_cert_directory = self.original_ssl_dir

        # Clean up test directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_ssl_cert_directory_creation(self):
        """Test SSL certificate directory creation."""
        ssl_dir = ssl_certificate.get_ssl_cert_directory()
        self.assertTrue(ssl_dir.exists())
        self.assertTrue(ssl_dir.is_dir())

    def test_generate_self_signed_certificate(self):
        """Test self-signed certificate generation."""
        cert_path, key_path = ssl_certificate.generate_self_signed_certificate(
            cert_file="test.crt",
            key_file="test.key",
            common_name="test.localhost"
        )

        # Check that files were created
        self.assertTrue(cert_path.exists())
        self.assertTrue(key_path.exists())

        # Check file permissions (should be 0o600)
        cert_perms = oct(cert_path.stat().st_mode)[-3:]
        key_perms = oct(key_path.stat().st_mode)[-3:]
        self.assertEqual(cert_perms, "600")
        self.assertEqual(key_perms, "600")

        # Verify certificate content
        self.assertTrue(ssl_certificate.validate_ssl_certificate(cert_path))

    def test_get_ssl_context_success(self):
        """Test SSL context generation when OpenSSL is available."""
        ssl_context = ssl_certificate.get_ssl_context(
            cert_file="context_test.crt",
            key_file="context_test.key",
            fallback_to_adhoc=False
        )

        # Should return a tuple of file paths
        self.assertIsInstance(ssl_context, tuple)
        self.assertEqual(len(ssl_context), 2)

        # Files should exist
        cert_path, key_path = ssl_context
        self.assertTrue(pathlib.Path(cert_path).exists())
        self.assertTrue(pathlib.Path(key_path).exists())

    def test_get_ssl_context_with_adhoc_fallback(self):
        """Test SSL context generation with adhoc fallback."""
        # Mock a failure scenario by temporarily breaking OpenSSL
        original_generate = ssl_certificate.generate_self_signed_certificate

        def mock_generate_failure(*args, **kwargs):
            raise RuntimeError("Mocked OpenSSL failure")

        ssl_certificate.generate_self_signed_certificate = mock_generate_failure

        try:
            ssl_context = ssl_certificate.get_ssl_context(
                cert_file="fallback_test.crt",
                key_file="fallback_test.key",
                fallback_to_adhoc=True
            )

            # Should fallback to 'adhoc'
            self.assertEqual(ssl_context, "adhoc")

        finally:
            # Restore original function
            ssl_certificate.generate_self_signed_certificate = original_generate

    def test_certificate_reuse(self):
        """Test that existing recent certificates are reused."""
        # Generate first certificate
        cert_path1, key_path1 = ssl_certificate.generate_self_signed_certificate(
            cert_file="reuse_test.crt",
            key_file="reuse_test.key"
        )

        # Get modification time
        mtime1 = cert_path1.stat().st_mtime

        # Generate again - should reuse existing
        cert_path2, key_path2 = ssl_certificate.generate_self_signed_certificate(
            cert_file="reuse_test.crt",
            key_file="reuse_test.key"
        )

        # Should be the same files
        self.assertEqual(cert_path1, cert_path2)
        self.assertEqual(key_path1, key_path2)

        # Modification time should be the same (file not regenerated)
        mtime2 = cert_path2.stat().st_mtime
        self.assertEqual(mtime1, mtime2)

    def test_validate_ssl_certificate_nonexistent(self):
        """Test validation of non-existent certificate."""
        nonexistent_path = pathlib.Path(self.test_dir) / "nonexistent.crt"
        self.assertFalse(ssl_certificate.validate_ssl_certificate(nonexistent_path))


if __name__ == "__main__":
    unittest.main()

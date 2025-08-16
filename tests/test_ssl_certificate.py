"""
Unit tests for SSL certificate management functionality.
"""

import unittest
import pathlib
import tempfile
import shutil
import os
from unittest.mock import patch

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
            cert_file="test.crt", key_file="test.key", common_name="test.localhost"
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
            fallback_to_adhoc=False,
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
                fallback_to_adhoc=True,
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
            cert_file="reuse_test.crt", key_file="reuse_test.key"
        )

        # Get modification time
        mtime1 = cert_path1.stat().st_mtime

        # Generate again - should reuse existing
        cert_path2, key_path2 = ssl_certificate.generate_self_signed_certificate(
            cert_file="reuse_test.crt", key_file="reuse_test.key"
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

    @patch("thermostatsupervisor.ssl_certificate.subprocess.run")
    def test_download_ssl_certificate(self, mock_subprocess):
        """Test SSL certificate download functionality."""
        # Mock successful openssl s_client output
        mock_cert_output = """
CONNECTED(00000003)
depth=0 CN = test.example.com
verify error:num=18:self signed certificate
verify return:1
depth=0 CN = test.example.com
verify return:1
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKuK0VGDJJhjMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMjMxMjEwMTUxNjUyWhcNMjQxMjA5MTUxNjUyWjBF
MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
-----END CERTIFICATE-----
"""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = mock_cert_output
        mock_subprocess.return_value.stderr = ""

        cert_path = ssl_certificate.download_ssl_certificate("test.example.com", 443)

        # Check that certificate file was created
        self.assertTrue(cert_path.exists())
        self.assertEqual(cert_path.name, "test.example.com_443.crt")

        # Check file content contains the certificate
        with open(cert_path, "r") as f:
            content = f.read()
            self.assertIn("-----BEGIN CERTIFICATE-----", content)
            self.assertIn("-----END CERTIFICATE-----", content)

    @patch("thermostatsupervisor.ssl_certificate.subprocess.run")
    def test_download_ssl_certificate_failure(self, mock_subprocess):
        """Test SSL certificate download failure handling."""
        # Mock failed openssl command
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Connection failed"

        with self.assertRaises(RuntimeError) as context:
            ssl_certificate.download_ssl_certificate("invalid.example.com", 443)

        self.assertIn("OpenSSL command failed", str(context.exception))

    @patch("thermostatsupervisor.ssl_certificate.platform.system")
    @patch("thermostatsupervisor.ssl_certificate.subprocess.run")
    def test_import_ssl_certificate_linux(self, mock_subprocess, mock_platform):
        """Test SSL certificate import on Linux."""
        mock_platform.return_value = "Linux"
        mock_subprocess.return_value.returncode = 0

        # Create a mock certificate file
        cert_path = pathlib.Path(self.test_dir) / "test.crt"
        cert_path.write_text(
            "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
        )

        # Mock that /usr/local/share/ca-certificates/ exists
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("pathlib.Path.is_dir") as mock_is_dir:
                mock_is_dir.return_value = True

                result = ssl_certificate.import_ssl_certificate_to_system(cert_path)
                self.assertTrue(result)

    @patch("thermostatsupervisor.ssl_certificate.platform.system")
    @patch("thermostatsupervisor.ssl_certificate.subprocess.run")
    def test_import_ssl_certificate_windows(self, mock_subprocess, mock_platform):
        """Test SSL certificate import on Windows."""
        mock_platform.return_value = "Windows"
        mock_subprocess.return_value.returncode = 0

        # Create a mock certificate file
        cert_path = pathlib.Path(self.test_dir) / "test.crt"
        cert_path.write_text(
            "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
        )

        result = ssl_certificate.import_ssl_certificate_to_system(cert_path)
        self.assertTrue(result)

        # Verify certutil was called
        mock_subprocess.assert_called_with(
            ["certutil", "-addstore", "Root", str(cert_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )

    @patch("thermostatsupervisor.ssl_certificate.platform.system")
    def test_import_ssl_certificate_unsupported_os(self, mock_platform):
        """Test SSL certificate import on unsupported OS."""
        mock_platform.return_value = "Darwin"  # macOS

        # Create a mock certificate file
        cert_path = pathlib.Path(self.test_dir) / "test.crt"
        cert_path.write_text(
            "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
        )

        result = ssl_certificate.import_ssl_certificate_to_system(cert_path)
        self.assertFalse(result)

    @patch("thermostatsupervisor.ssl_certificate.download_ssl_certificate")
    @patch("thermostatsupervisor.ssl_certificate.import_ssl_certificate_to_system")
    def test_download_and_import_ssl_certificates(self, mock_import, mock_download):
        """Test downloading and importing multiple SSL certificates."""
        # Mock successful operations
        mock_cert_path = pathlib.Path(self.test_dir) / "test.crt"
        mock_download.return_value = mock_cert_path
        mock_import.return_value = True

        servers = [("example.com", 443), ("test.com", 8443)]
        result = ssl_certificate.download_and_import_ssl_certificates(servers)

        self.assertTrue(result)
        self.assertEqual(mock_download.call_count, 2)
        self.assertEqual(mock_import.call_count, 2)

    @patch("thermostatsupervisor.ssl_certificate.download_ssl_certificate")
    @patch("thermostatsupervisor.ssl_certificate.import_ssl_certificate_to_system")
    def test_download_and_import_ssl_certificates_partial_failure(
        self, mock_import, mock_download
    ):
        """Test downloading and importing certificates with partial failure."""
        # Mock mixed success/failure
        mock_cert_path = pathlib.Path(self.test_dir) / "test.crt"
        mock_download.side_effect = [mock_cert_path, RuntimeError("Download failed")]
        mock_import.return_value = True

        servers = [("example.com", 443), ("invalid.com", 443)]
        result = ssl_certificate.download_and_import_ssl_certificates(servers)

        # Should return False due to partial failure
        self.assertFalse(result)
        self.assertEqual(mock_download.call_count, 2)
        # Only called for successful download
        self.assertEqual(mock_import.call_count, 1)


if __name__ == "__main__":
    unittest.main()

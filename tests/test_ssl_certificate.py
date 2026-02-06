"""
Unit tests for SSL certificate management functionality.
"""

import unittest
import pathlib
import tempfile
import shutil
import os
import platform
import subprocess
from unittest.mock import patch

from src import ssl_certificate


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

        # Check file permissions (should be 0o600 on Unix, may differ on Windows)
        cert_perms = oct(cert_path.stat().st_mode)[-3:]
        key_perms = oct(key_path.stat().st_mode)[-3:]

        # Windows handles file permissions differently than Unix: the effective
        # security is enforced via NTFS ACLs rather than traditional Unix mode
        # bits. As a result, calling chmod(0o600) can still show up as "666"
        # in st_mode. On Windows, "666" here does NOT mean world-readable or
        # world-writable as it would on Unix; it simply reflects how Python
        # maps ACLs to mode bits. The underlying ACLs still control access.
        if platform.system().lower() == "windows":
            # On Windows, verify permissions are set (may be reported as 666
            # or 600)
            self.assertIn(
                cert_perms,
                ["600", "666"],
                f"Certificate permissions '{cert_perms}' unexpected. "
                f"Expected '600' or '666' on Windows, got '{cert_perms}'."
            )
            self.assertIn(
                key_perms,
                ["600", "666"],
                f"Key permissions '{key_perms}' unexpected. "
                f"Expected '600' or '666' on Windows, got '{key_perms}'."
            )
        else:
            # On Unix-like systems, expect strict 600 permissions
            self.assertEqual(
                cert_perms,
                "600",
                f"Certificate permissions '{cert_perms}' unexpected. "
                f"Expected '600' (owner read/write only)."
            )
            self.assertEqual(
                key_perms,
                "600",
                f"Key permissions '{key_perms}' unexpected. "
                f"Expected '600' (owner read/write only)."
            )

        # Verify certificate content
        self.assertTrue(ssl_certificate.validate_ssl_certificate(cert_path))

    @patch("src.ssl_certificate.subprocess.run")
    def test_get_ssl_context_success(self, mock_subprocess):
        """Test SSL context generation when OpenSSL is available."""
        # Mock subprocess to succeed and create files
        cert_path = pathlib.Path(self.test_dir) / "context_test.crt"
        key_path = pathlib.Path(self.test_dir) / "context_test.key"

        def create_cert_files(*args, **kwargs):
            cert_path.write_text(
                "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
            )
            key_path.write_text(
                "-----BEGIN PRIVATE KEY-----\ntest key\n-----END PRIVATE KEY-----"
            )
            # Create a mock return value with returncode
            mock_result = unittest.mock.Mock()
            mock_result.returncode = 0
            return mock_result

        mock_subprocess.side_effect = create_cert_files

        ssl_context = ssl_certificate.get_ssl_context(
            cert_file="context_test.crt",
            key_file="context_test.key",
            fallback_to_adhoc=False,
        )

        # Should return a tuple of file paths
        self.assertIsInstance(ssl_context, tuple)
        self.assertEqual(len(ssl_context), 2)

        # Files should exist
        returned_cert_path, returned_key_path = ssl_context
        self.assertTrue(pathlib.Path(returned_cert_path).exists())
        self.assertTrue(pathlib.Path(returned_key_path).exists())

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

    @patch("src.ssl_certificate.subprocess.run")
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

    @patch("src.ssl_certificate.subprocess.run")
    def test_download_ssl_certificate_failure(self, mock_subprocess):
        """Test SSL certificate download failure handling."""
        # Mock failed openssl command
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Connection failed"

        with self.assertRaises(RuntimeError) as context:
            ssl_certificate.download_ssl_certificate("invalid.example.com", 443)

        self.assertIn("OpenSSL command failed", str(context.exception))

    @patch("src.ssl_certificate.platform.system")
    @patch("src.ssl_certificate.subprocess.run")
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

    @patch("src.ssl_certificate.platform.system")
    @patch("src.ssl_certificate.subprocess.run")
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

    @patch("src.ssl_certificate.platform.system")
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

    @patch("src.ssl_certificate.platform.system")
    @patch("src.ssl_certificate.subprocess.run")
    def test_generate_self_signed_certificate_windows(
        self, mock_subprocess, mock_platform
    ):
        """Test self-signed certificate generation on Windows."""
        mock_platform.return_value = "Windows"
        mock_subprocess.return_value.returncode = 0

        # Don't create the files beforehand - let the function create them
        cert_path = pathlib.Path(self.test_dir) / "windows_test.crt"
        key_path = pathlib.Path(self.test_dir) / "windows_test.key"

        # Mock the file creation side effect
        def create_files(*args, **kwargs):
            cert_path.write_text(
                "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
            )
            key_path.write_text(
                "-----BEGIN PRIVATE KEY-----\ntest key\n-----END PRIVATE KEY-----"
            )
            return mock_subprocess.return_value

        mock_subprocess.side_effect = create_files

        result_cert, result_key = ssl_certificate.generate_self_signed_certificate(
            cert_file="windows_test.crt",
            key_file="windows_test.key",
            common_name="windows.test"
        )

        # Verify the OpenSSL command was called with Windows-specific config
        mock_subprocess.assert_called_once()
        args, kwargs = mock_subprocess.call_args
        cmd = args[0]

        # Check that command has the basic structure
        self.assertEqual(cmd[0], "openssl")
        self.assertEqual(cmd[1], "req")
        self.assertIn("-config", cmd)
        # Verify config is not "nul" but a temporary file path
        config_idx = cmd.index("-config")
        config_path = cmd[config_idx + 1]
        self.assertNotEqual(config_path, "nul")
        self.assertTrue(config_path.endswith(".cnf"))

        # Verify return values
        self.assertEqual(result_cert, cert_path)
        self.assertEqual(result_key, key_path)

    @patch("src.ssl_certificate.platform.system")
    @patch("src.ssl_certificate.subprocess.run")
    def test_download_ssl_certificate_windows(
        self, mock_subprocess, mock_platform
    ):
        """Test SSL certificate download on Windows."""
        mock_platform.return_value = "Windows"

        # Mock successful openssl s_client output
        mock_cert_output = """
CONNECTED(00000003)
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKuK0VGDJJhjMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
-----END CERTIFICATE-----
"""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = mock_cert_output
        mock_subprocess.return_value.stderr = ""

        ssl_certificate.download_ssl_certificate("windows.test.com", 443)

        # Verify the OpenSSL command was called with Windows-specific config
        mock_subprocess.assert_called_once()
        args, kwargs = mock_subprocess.call_args
        cmd = args[0]

        # Check that command has the basic structure
        self.assertEqual(cmd[0], "openssl")
        self.assertEqual(cmd[1], "s_client")
        self.assertIn("-config", cmd)
        # Verify config is not "nul" but a temporary file path
        config_idx = cmd.index("-config")
        config_path = cmd[config_idx + 1]
        self.assertNotEqual(config_path, "nul")
        self.assertTrue(config_path.endswith(".cnf"))

    @patch("src.ssl_certificate.platform.system")
    @patch("src.ssl_certificate.subprocess.run")
    def test_validate_ssl_certificate_windows(
        self, mock_subprocess, mock_platform
    ):
        """Test SSL certificate validation on Windows."""
        mock_platform.return_value = "Windows"
        mock_subprocess.return_value.returncode = 0

        # Create a mock certificate file
        cert_path = pathlib.Path(self.test_dir) / "windows_validate.crt"
        cert_path.write_text(
            "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
        )

        result = ssl_certificate.validate_ssl_certificate(cert_path)
        self.assertTrue(result)

        # Verify the OpenSSL command was called with Windows-specific config
        mock_subprocess.assert_called_once()
        args, kwargs = mock_subprocess.call_args
        cmd = args[0]

        # Check that command has the basic structure
        self.assertEqual(cmd[0], "openssl")
        self.assertEqual(cmd[1], "x509")
        self.assertIn("-config", cmd)
        # Verify config is not "nul" but a temporary file path
        config_idx = cmd.index("-config")
        config_path = cmd[config_idx + 1]
        self.assertNotEqual(config_path, "nul")
        self.assertTrue(config_path.endswith(".cnf"))

    @patch("src.ssl_certificate.download_ssl_certificate")
    @patch("src.ssl_certificate.import_ssl_certificate_to_system")
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

    @patch("src.ssl_certificate.download_ssl_certificate")
    @patch("src.ssl_certificate.import_ssl_certificate_to_system")
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

    def test_cleanup_temp_config_with_permission_error(self):
        """Test cleanup of temp config file with permission error."""
        # Create a temp file
        temp_path = pathlib.Path(self.test_dir) / "test_config.cnf"
        temp_path.write_text("test config")

        # Mock unlink to raise PermissionError
        with patch("pathlib.Path.unlink") as mock_unlink:
            mock_unlink.side_effect = PermissionError("Permission denied")

            # Should not raise exception
            ssl_certificate._cleanup_temp_config(str(temp_path))

            # Verify unlink was attempted
            mock_unlink.assert_called_once()

    def test_cleanup_temp_config_with_file_not_found_error(self):
        """Test cleanup of temp config file with FileNotFoundError."""
        # Create a temp file path (but don't create the file)
        temp_path = pathlib.Path(self.test_dir) / "nonexistent_config.cnf"

        # Mock exists to return True, then unlink to raise FileNotFoundError
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.unlink") as mock_unlink:
                mock_unlink.side_effect = FileNotFoundError("File not found")

                # Should not raise exception
                ssl_certificate._cleanup_temp_config(str(temp_path))

                # Verify unlink was attempted
                mock_unlink.assert_called_once()

    def test_cleanup_temp_config_with_none_path(self):
        """Test cleanup with None path."""
        # Should not raise exception
        ssl_certificate._cleanup_temp_config(None)

    def test_cleanup_temp_config_nonexistent_file(self):
        """Test cleanup of nonexistent temp config file."""
        # Create a path that doesn't exist
        temp_path = pathlib.Path(self.test_dir) / "nonexistent.cnf"

        # Should not raise exception
        ssl_certificate._cleanup_temp_config(str(temp_path))

    @patch("tempfile.mkstemp")
    @patch("os.chmod")
    def test_create_windows_openssl_config_error(self, mock_chmod, mock_mkstemp):
        """Test _create_windows_openssl_config with error."""
        # Mock mkstemp to return a file descriptor and path
        mock_fd = 100
        mock_path = "/tmp/test_config.cnf"
        mock_mkstemp.return_value = (mock_fd, mock_path)

        # Mock chmod to raise an exception
        mock_chmod.side_effect = OSError("Permission denied")

        # Mock os.fdopen to avoid issues with mock fd
        with patch("os.fdopen") as mock_fdopen:
            with patch("os.unlink") as mock_unlink:
                mock_fdopen.side_effect = OSError("Cannot open file")

                # Should raise the exception
                with self.assertRaises(OSError):
                    ssl_certificate._create_windows_openssl_config()

                # Verify cleanup was attempted
                mock_unlink.assert_called_once_with(mock_path)

    @patch("src.ssl_certificate.subprocess.run")
    def test_download_ssl_certificate_missing_cert_markers(self, mock_subprocess):
        """Test SSL certificate download with missing cert markers."""
        # Mock output without certificate markers
        mock_cert_output = """
        CONNECTED(00000003)
        depth=0 CN = test.example.com
        verify return:1
        No certificate found
        """
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = mock_cert_output
        mock_subprocess.return_value.stderr = ""

        with self.assertRaises(RuntimeError) as context:
            ssl_certificate.download_ssl_certificate("test.example.com", 443)

        self.assertIn("Could not find certificate", str(context.exception))

    @patch("src.ssl_certificate.subprocess.run")
    def test_download_ssl_certificate_timeout(self, mock_subprocess):
        """Test SSL certificate download timeout."""
        # Mock timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("openssl", 30)

        with self.assertRaises(RuntimeError) as context:
            ssl_certificate.download_ssl_certificate("slow.example.com", 443)

        self.assertIn("Timeout", str(context.exception))

    def test_validate_ssl_certificate_empty_file(self):
        """Test validation of empty certificate file."""
        # Create an empty certificate file
        cert_path = pathlib.Path(self.test_dir) / "empty.crt"
        cert_path.write_text("")

        result = ssl_certificate.validate_ssl_certificate(cert_path)
        self.assertFalse(result)

    def test_validate_ssl_certificate_missing_begin_marker(self):
        """Test validation of certificate missing BEGIN marker."""
        # Create a certificate file missing BEGIN marker
        cert_path = pathlib.Path(self.test_dir) / "incomplete.crt"
        cert_path.write_text(
            "Some content\n-----END CERTIFICATE-----"
        )

        result = ssl_certificate.validate_ssl_certificate(cert_path)
        self.assertFalse(result)

    def test_validate_ssl_certificate_missing_end_marker(self):
        """Test validation of certificate missing END marker."""
        # Create a certificate file missing END marker
        cert_path = pathlib.Path(self.test_dir) / "incomplete2.crt"
        cert_path.write_text(
            "-----BEGIN CERTIFICATE-----\nSome content"
        )

        result = ssl_certificate.validate_ssl_certificate(cert_path)
        self.assertFalse(result)

    @patch("pathlib.Path.read_text")
    def test_validate_ssl_certificate_unicode_error(self, mock_read_text):
        """Test validation of certificate with unicode decode error."""
        # Create a certificate file
        cert_path = pathlib.Path(self.test_dir) / "binary.crt"
        cert_path.write_bytes(b"\x80\x81\x82\x83")

        # Mock read_text to raise UnicodeDecodeError
        mock_read_text.side_effect = UnicodeDecodeError(
            "utf-8", b"\x80\x81", 0, 1, "invalid start byte"
        )

        result = ssl_certificate.validate_ssl_certificate(cert_path)
        self.assertFalse(result)

    @patch("pathlib.Path.read_text")
    def test_validate_ssl_certificate_os_error(self, mock_read_text):
        """Test validation of certificate with OS error."""
        # Create a certificate file
        cert_path = pathlib.Path(self.test_dir) / "inaccessible.crt"
        cert_path.write_text("test")

        # Mock read_text to raise OSError
        mock_read_text.side_effect = OSError("Cannot read file")

        result = ssl_certificate.validate_ssl_certificate(cert_path)
        self.assertFalse(result)

    @patch("src.ssl_certificate.platform.system")
    @patch("src.ssl_certificate.subprocess.run")
    def test_validate_ssl_certificate_windows_config_creation_error(
        self, mock_subprocess, mock_platform
    ):
        """Test certificate validation with Windows config creation error."""
        mock_platform.return_value = "Windows"

        # Create a mock certificate file
        cert_path = pathlib.Path(self.test_dir) / "test.crt"
        cert_path.write_text(
            "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
        )

        # Mock _create_windows_openssl_config to raise OSError
        with patch(
            "src.ssl_certificate._create_windows_openssl_config"
        ) as mock_create_config:
            mock_create_config.side_effect = OSError("Cannot create config")

            result = ssl_certificate.validate_ssl_certificate(cert_path)
            self.assertFalse(result)

    @patch("src.ssl_certificate.platform.system")
    @patch("src.ssl_certificate.subprocess.run")
    def test_validate_ssl_certificate_subprocess_timeout(
        self, mock_subprocess, mock_platform
    ):
        """Test certificate validation with subprocess timeout."""
        mock_platform.return_value = "Linux"

        # Create a mock certificate file
        cert_path = pathlib.Path(self.test_dir) / "test.crt"
        cert_path.write_text(
            "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
        )

        # Mock subprocess to timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("openssl", 10)

        result = ssl_certificate.validate_ssl_certificate(cert_path)
        self.assertFalse(result)

    @patch("src.ssl_certificate.platform.system")
    @patch("src.ssl_certificate.subprocess.run")
    def test_validate_ssl_certificate_openssl_not_found(
        self, mock_subprocess, mock_platform
    ):
        """Test certificate validation with OpenSSL not found."""
        mock_platform.return_value = "Linux"

        # Create a mock certificate file
        cert_path = pathlib.Path(self.test_dir) / "test.crt"
        cert_path.write_text(
            "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
        )

        # Mock subprocess to raise FileNotFoundError
        mock_subprocess.side_effect = FileNotFoundError("OpenSSL not found")

        result = ssl_certificate.validate_ssl_certificate(cert_path)
        self.assertFalse(result)

    @patch("src.ssl_certificate.platform.system")
    @patch("src.ssl_certificate.subprocess.run")
    def test_import_cert_linux_subprocess_timeout(
        self, mock_subprocess, mock_platform
    ):
        """Test Linux certificate import with subprocess timeout."""
        mock_platform.return_value = "Linux"

        # Create a mock certificate file
        cert_path = pathlib.Path(self.test_dir) / "test.crt"
        cert_path.write_text(
            "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
        )

        # Mock subprocess to timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("sudo", 30)

        # Mock that cert directory exists
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                result = ssl_certificate.import_ssl_certificate_to_system(cert_path)
                # Should still return True with fallback message
                self.assertTrue(result)

    @patch("src.ssl_certificate.platform.system")
    @patch("src.ssl_certificate.subprocess.run")
    def test_import_cert_windows_subprocess_error(
        self, mock_subprocess, mock_platform
    ):
        """Test Windows certificate import with subprocess error."""
        mock_platform.return_value = "Windows"

        # Create a mock certificate file
        cert_path = pathlib.Path(self.test_dir) / "test.crt"
        cert_path.write_text(
            "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
        )

        # Mock subprocess to fail
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, "certutil", stderr="Access denied"
        )

        result = ssl_certificate.import_ssl_certificate_to_system(cert_path)
        self.assertFalse(result)

    def test_import_ssl_certificate_nonexistent_file(self):
        """Test importing nonexistent certificate file."""
        nonexistent_path = pathlib.Path(self.test_dir) / "nonexistent.crt"

        result = ssl_certificate.import_ssl_certificate_to_system(nonexistent_path)
        self.assertFalse(result)

    @patch("src.ssl_certificate._import_cert_linux")
    @patch("src.ssl_certificate.platform.system")
    def test_import_ssl_certificate_exception_handling(
        self, mock_platform, mock_import_linux
    ):
        """Test certificate import with unexpected exception."""
        mock_platform.return_value = "Linux"
        # Mock _import_cert_linux to raise an exception
        mock_import_linux.side_effect = Exception("Unexpected error")

        # Create a mock certificate file
        cert_path = pathlib.Path(self.test_dir) / "test.crt"
        cert_path.write_text(
            "-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----"
        )

        result = ssl_certificate.import_ssl_certificate_to_system(cert_path)
        self.assertFalse(result)

    @patch("src.ssl_certificate.subprocess.run")
    def test_generate_self_signed_certificate_timeout(self, mock_subprocess):
        """Test certificate generation with timeout."""
        # Mock subprocess to timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("openssl", 30)

        with self.assertRaises(RuntimeError) as context:
            ssl_certificate.generate_self_signed_certificate(
                cert_file="timeout_test.crt",
                key_file="timeout_test.key"
            )

        self.assertIn("timed out", str(context.exception))

    @patch("src.ssl_certificate.subprocess.run")
    def test_generate_self_signed_certificate_openssl_not_found(
        self, mock_subprocess
    ):
        """Test certificate generation with OpenSSL not found."""
        # Mock subprocess to raise FileNotFoundError
        mock_subprocess.side_effect = FileNotFoundError("OpenSSL not found")

        with self.assertRaises(RuntimeError) as context:
            ssl_certificate.generate_self_signed_certificate(
                cert_file="missing_openssl.crt",
                key_file="missing_openssl.key"
            )

        self.assertIn("OpenSSL not found", str(context.exception))

    @patch("src.ssl_certificate.subprocess.run")
    def test_generate_self_signed_certificate_files_not_created(
        self, mock_subprocess
    ):
        """Test certificate generation when files are not created."""
        # Mock subprocess to succeed but don't create files
        mock_subprocess.return_value.returncode = 0

        with self.assertRaises(RuntimeError) as context:
            ssl_certificate.generate_self_signed_certificate(
                cert_file="not_created.crt",
                key_file="not_created.key"
            )

        self.assertIn("Certificate files were not created", str(context.exception))

    def test_get_ssl_context_without_fallback(self):
        """Test SSL context generation without adhoc fallback."""
        # Mock generate_self_signed_certificate to fail
        original_generate = ssl_certificate.generate_self_signed_certificate

        def mock_generate_failure(*args, **kwargs):
            raise RuntimeError("Mocked failure")

        ssl_certificate.generate_self_signed_certificate = mock_generate_failure

        try:
            ssl_context = ssl_certificate.get_ssl_context(
                cert_file="no_fallback.crt",
                key_file="no_fallback.key",
                fallback_to_adhoc=False,
            )

            # Should return None
            self.assertIsNone(ssl_context)

        finally:
            # Restore original function
            ssl_certificate.generate_self_signed_certificate = original_generate

    @patch("src.ssl_certificate.download_ssl_certificate")
    @patch("src.ssl_certificate.import_ssl_certificate_to_system")
    def test_download_and_import_ssl_certificates_import_failure(
        self, mock_import, mock_download
    ):
        """Test downloading and importing certificates with import failure."""
        # Mock successful download but failed import
        mock_cert_path = pathlib.Path(self.test_dir) / "test.crt"
        mock_download.return_value = mock_cert_path
        mock_import.return_value = False

        servers = [("example.com", 443)]
        result = ssl_certificate.download_and_import_ssl_certificates(servers)

        # Should return False due to import failure
        self.assertFalse(result)
        self.assertEqual(mock_download.call_count, 1)
        self.assertEqual(mock_import.call_count, 1)


if __name__ == "__main__":
    unittest.main()

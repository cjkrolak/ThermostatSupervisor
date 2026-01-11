"""
SSL Certificate management utilities.

This module provides functionality to generate and manage self-signed SSL
certificates for Flask servers.
"""

# built-in imports
import os
import pathlib
import platform
import subprocess
import tempfile
import time
from typing import Tuple, Optional, List

# local imports
from thermostatsupervisor import utilities as util


def get_ssl_cert_directory() -> pathlib.Path:
    """Get the directory where SSL certificates should be stored.

    Returns:
        pathlib.Path: Path to SSL certificate directory
    """
    # Create ssl directory in the project root
    project_root = pathlib.Path(__file__).parent.parent
    ssl_dir = project_root / "ssl"
    ssl_dir.mkdir(exist_ok=True)
    return ssl_dir


def _create_windows_openssl_config() -> str:
    """Create a minimal OpenSSL configuration file for Windows.

    This function creates a temporary configuration file that includes
    the minimum required sections for OpenSSL to work properly on Windows.

    Returns:
        str: Path to the temporary configuration file
    """
    config_content = """[ req ]
distinguished_name = req_distinguished_name
prompt = no

[ req_distinguished_name ]
# Empty section - values will be provided via -subj parameter
"""
    # Create a temporary file with restricted permissions
    # that won't be automatically deleted
    fd, temp_path = tempfile.mkstemp(suffix='.cnf', text=True)
    try:
        # Set restrictive permissions on the file
        os.chmod(temp_path, 0o600)
        # Write config content to the file
        with os.fdopen(fd, 'w') as config_file:
            config_file.write(config_content.lstrip())
        return temp_path
    except Exception:
        # Clean up on error
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise


def _cleanup_temp_config(config_file_path: Optional[str]) -> None:
    """Clean up temporary OpenSSL configuration file.

    Args:
        config_file_path: Path to the temporary config file to clean up
    """
    if config_file_path:
        config_path_obj = pathlib.Path(config_file_path)
        if config_path_obj.exists():
            try:
                config_path_obj.unlink()
            except (FileNotFoundError, PermissionError) as e:
                util.log_msg(
                    f"Failed to cleanup temp config file: {e}",
                    mode=util.DEBUG_LOG
                )


def generate_self_signed_certificate(
    cert_file: str = "server.crt",
    key_file: str = "server.key",
    days: int = 365,
    common_name: str = "localhost",
) -> Tuple[pathlib.Path, pathlib.Path]:
    """Generate a self-signed SSL certificate using OpenSSL.

    Args:
        cert_file: Name of the certificate file (default: server.crt)
        key_file: Name of the private key file (default: server.key)
        days: Number of days the certificate is valid (default: 365)
        common_name: Common name for the certificate (default: localhost)

    Returns:
        Tuple of (cert_path, key_path) as pathlib.Path objects

    Raises:
        RuntimeError: If OpenSSL command fails or is not available
    """
    ssl_dir = get_ssl_cert_directory()
    cert_path = ssl_dir / cert_file
    key_path = ssl_dir / key_file

    # Check if certificates already exist and are recent
    if cert_path.exists() and key_path.exists():
        # Check if certificate is still valid (created within last 30 days)
        cert_age_days = (time.time() - cert_path.stat().st_mtime) / (24 * 3600)
        if cert_age_days < (days - 30):  # Regenerate 30 days before expiry
            util.log_msg(
                f"Using existing SSL certificate: {cert_path}", mode=util.DEBUG_LOG
            )
            return cert_path, key_path

    util.log_msg(f"Generating new SSL certificate: {cert_path}", mode=util.STDOUT_LOG)

    # Build OpenSSL command with platform-specific configuration
    openssl_cmd = [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:4096",
        "-nodes",
        "-out",
        str(cert_path),
        "-keyout",
        str(key_path),
        "-days",
        str(days),
        "-subj",
        f"/C=US/ST=State/L=City/O=Organization/CN={common_name}",
    ]

    # Windows-specific configuration to avoid config file issues
    config_file_path = None
    if platform.system().lower() == "windows":
        # Create a temporary config file with minimal required sections
        config_file_path = _create_windows_openssl_config()
        openssl_cmd.extend(["-config", config_file_path])
        util.log_msg(
            f"Using temporary OpenSSL config: {config_file_path}",
            mode=util.DEBUG_LOG
        )
        # Verify config file exists before proceeding
        if not pathlib.Path(config_file_path).exists():
            raise RuntimeError(
                f"Failed to create temporary OpenSSL config file: "
                f"{config_file_path}"
            )

    try:
        # Run OpenSSL command
        subprocess.run(
            openssl_cmd, capture_output=True, text=True, check=True, timeout=30
        )

        util.log_msg("SSL certificate generated successfully", mode=util.STDOUT_LOG)

        # Verify files were created
        if not cert_path.exists() or not key_path.exists():
            raise RuntimeError("Certificate files were not created")

        # Set proper permissions (readable by owner only)
        cert_path.chmod(0o600)
        key_path.chmod(0o600)

        return cert_path, key_path

    except subprocess.CalledProcessError as e:
        error_msg = (
            f"OpenSSL command failed: {e.stderr}\n"
            f"Command: {' '.join(openssl_cmd)}"
        )
        util.log_msg(error_msg, mode=util.STDERR_LOG)
        raise RuntimeError(error_msg) from e

    except subprocess.TimeoutExpired as e:
        error_msg = "OpenSSL command timed out"
        util.log_msg(error_msg, mode=util.STDERR_LOG)
        raise RuntimeError(error_msg) from e

    except FileNotFoundError as e:
        error_msg = (
            "OpenSSL not found. Please install OpenSSL to generate SSL "
            "certificates"
        )
        util.log_msg(error_msg, mode=util.STDERR_LOG)
        raise RuntimeError(error_msg) from e

    finally:
        # Clean up temporary config file on Windows
        _cleanup_temp_config(config_file_path)


def get_ssl_context(
    cert_file: str = "server.crt",
    key_file: str = "server.key",
    fallback_to_adhoc: bool = True,
) -> Optional[str]:
    """Get SSL context for Flask application.

    Args:
        cert_file: Name of the certificate file
        key_file: Name of the private key file
        fallback_to_adhoc: Whether to fallback to 'adhoc' if cert generation fails

    Returns:
        SSL context tuple (cert_path, key_path) or 'adhoc' or None
    """
    try:
        cert_path, key_path = generate_self_signed_certificate(
            cert_file=cert_file, key_file=key_file
        )
        return (str(cert_path), str(key_path))

    except RuntimeError as e:
        util.log_msg(f"Failed to generate SSL certificate: {e}", mode=util.STDERR_LOG)

        if fallback_to_adhoc:
            util.log_msg(
                "Falling back to Flask 'adhoc' SSL certificate", mode=util.STDOUT_LOG
            )
            return "adhoc"
        else:
            return None


def validate_ssl_certificate(cert_path: pathlib.Path) -> bool:
    """Validate an SSL certificate file.

    Args:
        cert_path: Path to the certificate file

    Returns:
        True if certificate is valid, False otherwise
    """
    if not cert_path.exists():
        return False

    config_file_path = None
    try:
        # Build OpenSSL validation command
        openssl_cmd = ["openssl", "x509", "-in", str(cert_path), "-noout", "-text"]

        # Windows-specific configuration to avoid config file issues
        if platform.system().lower() == "windows":
            # Create a temporary config file with minimal required sections
            config_file_path = _create_windows_openssl_config()
            openssl_cmd.extend(["-config", config_file_path])

        # Use OpenSSL to verify the certificate
        subprocess.run(
            openssl_cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return True

    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return False

    finally:
        # Clean up temporary config file on Windows
        _cleanup_temp_config(config_file_path)


def download_ssl_certificate(hostname: str, port: int = 443) -> pathlib.Path:
    """Download SSL certificate from a remote server.

    Args:
        hostname: The hostname/IP address of the server
        port: The port number (default: 443)

    Returns:
        Path to the downloaded certificate file

    Raises:
        RuntimeError: If certificate download fails
    """
    ssl_dir = get_ssl_cert_directory()
    cert_filename = f"{hostname}_{port}.crt"
    cert_path = ssl_dir / cert_filename

    util.log_msg(
        f"Downloading SSL certificate from {hostname}:{port}", mode=util.STDOUT_LOG
    )

    config_file_path = None
    try:
        # Use openssl command to get the certificate
        openssl_cmd = [
            "openssl",
            "s_client",
            "-connect",
            f"{hostname}:{port}",
            "-servername",
            hostname,
            "-showcerts",
        ]

        # Windows-specific configuration to avoid config file issues
        if platform.system().lower() == "windows":
            # Create a temporary config file with minimal required sections
            config_file_path = _create_windows_openssl_config()
            openssl_cmd.extend(["-config", config_file_path])

        # Run openssl command
        result = subprocess.run(
            openssl_cmd, input="", capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"OpenSSL command failed: {result.stderr}")

        # Extract the certificate from the output
        output = result.stdout
        cert_start = output.find("-----BEGIN CERTIFICATE-----")
        cert_end = output.find("-----END CERTIFICATE-----") + len(
            "-----END CERTIFICATE-----"
        )

        if cert_start == -1 or cert_end == -1:
            raise RuntimeError("Could not find certificate in OpenSSL output")

        cert_pem = output[cert_start:cert_end]

        # Write certificate to file
        with open(cert_path, "w", encoding="utf-8") as f:
            f.write(cert_pem)

        # Set proper permissions
        cert_path.chmod(0o644)

        util.log_msg(
            f"SSL certificate downloaded to {cert_path}", mode=util.STDOUT_LOG
        )
        return cert_path

    except subprocess.TimeoutExpired:
        error_msg = f"Timeout downloading SSL certificate from {hostname}:{port}"
        util.log_msg(error_msg, mode=util.STDERR_LOG)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = (
            f"Failed to download SSL certificate from {hostname}:{port}: {e}"
        )
        util.log_msg(error_msg, mode=util.STDERR_LOG)
        raise RuntimeError(error_msg) from e

    finally:
        # Clean up temporary config file on Windows
        _cleanup_temp_config(config_file_path)


def import_ssl_certificate_to_system(cert_path: pathlib.Path) -> bool:
    """Import SSL certificate to system trust store.

    Args:
        cert_path: Path to the certificate file

    Returns:
        True if import was successful, False otherwise
    """
    if not cert_path.exists():
        util.log_msg(f"Certificate file not found: {cert_path}", mode=util.STDERR_LOG)
        return False

    system = platform.system().lower()

    try:
        if system == "linux":
            return _import_cert_linux(cert_path)
        elif system == "windows":
            return _import_cert_windows(cert_path)
        else:
            util.log_msg(
                f"Unsupported operating system: {system}", mode=util.STDERR_LOG
            )
            return False

    except Exception as e:
        util.log_msg(f"Failed to import SSL certificate: {e}", mode=util.STDERR_LOG)
        return False


def _import_cert_linux(cert_path: pathlib.Path) -> bool:
    """Import certificate on Linux systems."""
    # Try common Linux certificate directories
    cert_dirs = [
        "/usr/local/share/ca-certificates/",
        "/etc/ssl/certs/",
        "/etc/pki/ca-trust/source/anchors/",
    ]

    cert_name = cert_path.name
    imported = False

    for cert_dir in cert_dirs:
        cert_dir_path = pathlib.Path(cert_dir)
        if cert_dir_path.exists() and cert_dir_path.is_dir():
            try:
                target_path = cert_dir_path / cert_name

                # Copy certificate to system directory
                subprocess.run(
                    ["sudo", "cp", str(cert_path), str(target_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                # Update certificate store
                if cert_dir == "/usr/local/share/ca-certificates/":
                    subprocess.run(
                        ["sudo", "update-ca-certificates"],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                elif cert_dir == "/etc/pki/ca-trust/source/anchors/":
                    subprocess.run(
                        ["sudo", "update-ca-trust"],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )

                util.log_msg(
                    f"Certificate imported to {target_path}", mode=util.STDOUT_LOG
                )
                imported = True
                break

            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # Try next directory if this one fails
                continue

    if not imported:
        # Fallback: set environment variable
        util.log_msg(
            "Could not import to system store, using environment variable " "fallback",
            mode=util.STDOUT_LOG,
        )
        # This would typically be set by the calling script
        # os.environ['REQUESTS_CA_BUNDLE'] = str(cert_path)
        # os.environ['SSL_CERT_FILE'] = str(cert_path)

    return True


def _import_cert_windows(cert_path: pathlib.Path) -> bool:
    """Import certificate on Windows systems."""
    try:
        # Use certutil to import the certificate
        subprocess.run(
            ["certutil", "-addstore", "Root", str(cert_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )

        util.log_msg(
            "Certificate imported to Windows certificate store", mode=util.STDOUT_LOG
        )
        return True

    except subprocess.CalledProcessError as e:
        util.log_msg(
            f"Failed to import certificate with certutil: {e.stderr}",
            mode=util.STDERR_LOG,
        )
        return False


def download_and_import_ssl_certificates(servers: List[Tuple[str, int]]) -> bool:
    """Download and import SSL certificates from multiple servers.

    Args:
        servers: List of (hostname, port) tuples

    Returns:
        True if all certificates were processed successfully, False otherwise
    """
    success = True

    for hostname, port in servers:
        try:
            # Download certificate
            cert_path = download_ssl_certificate(hostname, port)

            # Import to system trust store
            if not import_ssl_certificate_to_system(cert_path):
                util.log_msg(
                    f"Failed to import certificate for {hostname}:{port}",
                    mode=util.STDERR_LOG,
                )
                success = False

        except Exception as e:
            util.log_msg(
                f"Error processing {hostname}:{port}: {e}", mode=util.STDERR_LOG
            )
            success = False

    return success

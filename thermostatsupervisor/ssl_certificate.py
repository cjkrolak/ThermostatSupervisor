"""
SSL Certificate management utilities.

This module provides functionality to generate and manage self-signed SSL
certificates for Flask servers.
"""

# built-in imports
import pathlib
import subprocess
import time
from typing import Tuple, Optional

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


def generate_self_signed_certificate(
    cert_file: str = "server.crt",
    key_file: str = "server.key",
    days: int = 365,
    common_name: str = "localhost"
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
        cert_age_days = (
            time.time() - cert_path.stat().st_mtime
        ) / (24 * 3600)
        if cert_age_days < (days - 30):  # Regenerate 30 days before expiry
            util.log_msg(
                f"Using existing SSL certificate: {cert_path}",
                mode=util.DEBUG_LOG
            )
            return cert_path, key_path

    util.log_msg(
        f"Generating new SSL certificate: {cert_path}",
        mode=util.STDOUT_LOG
    )

    # OpenSSL command to generate self-signed certificate
    openssl_cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:4096", "-nodes",
        "-out", str(cert_path),
        "-keyout", str(key_path),
        "-days", str(days),
        "-subj", f"/C=US/ST=State/L=City/O=Organization/CN={common_name}"
    ]

    try:
        # Run OpenSSL command
        subprocess.run(
            openssl_cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )

        util.log_msg(
            "SSL certificate generated successfully",
            mode=util.STDOUT_LOG
        )

        # Verify files were created
        if not cert_path.exists() or not key_path.exists():
            raise RuntimeError("Certificate files were not created")

        # Set proper permissions (readable by owner only)
        cert_path.chmod(0o600)
        key_path.chmod(0o600)

        return cert_path, key_path

    except subprocess.CalledProcessError as e:
        error_msg = f"OpenSSL command failed: {e.stderr}"
        util.log_msg(error_msg, mode=util.STDERR_LOG)
        raise RuntimeError(error_msg) from e

    except subprocess.TimeoutExpired as e:
        error_msg = "OpenSSL command timed out"
        util.log_msg(error_msg, mode=util.STDERR_LOG)
        raise RuntimeError(error_msg) from e

    except FileNotFoundError as e:
        error_msg = (
            "OpenSSL not found. Please install OpenSSL to generate "
            "SSL certificates"
        )
        util.log_msg(error_msg, mode=util.STDERR_LOG)
        raise RuntimeError(error_msg) from e


def get_ssl_context(
    cert_file: str = "server.crt",
    key_file: str = "server.key",
    fallback_to_adhoc: bool = True
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
            cert_file=cert_file,
            key_file=key_file
        )
        return (str(cert_path), str(key_path))

    except RuntimeError as e:
        util.log_msg(
            f"Failed to generate SSL certificate: {e}",
            mode=util.STDERR_LOG
        )

        if fallback_to_adhoc:
            util.log_msg(
                "Falling back to Flask 'adhoc' SSL certificate",
                mode=util.STDOUT_LOG
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

    try:
        # Use OpenSSL to verify the certificate
        subprocess.run(
            ["openssl", "x509", "-in", str(cert_path), "-noout", "-text"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        return True

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError):
        return False

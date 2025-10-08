#!/usr/bin/env python3
"""
Script to download and import self-signed SSL certificates from servers.

This script can be used to download SSL certificates from HTTPS servers
and import them into the local system's certificate trust store.
Supports both Windows and Linux systems.
"""

import argparse
import sys
import json
from typing import List, Tuple

# Import the SSL certificate functions
from thermostatsupervisor.ssl_certificate import (
    download_and_import_ssl_certificates,
)
from thermostatsupervisor import utilities as util


def parse_servers(servers_str: str) -> List[Tuple[str, int]]:
    """Parse server list from command line argument or JSON.

    Args:
        servers_str: Server specification as JSON or comma-separated list

    Returns:
        List of (hostname, port) tuples

    Raises:
        ValueError: If server specification is invalid
    """
    servers = []

    # Try to parse as JSON first
    try:
        servers_data = json.loads(servers_str)
        if isinstance(servers_data, list):
            for server in servers_data:
                if isinstance(server, dict):
                    hostname = server.get("hostname")
                    port = server.get("port", 443)
                    if hostname:
                        servers.append((hostname, port))
                elif isinstance(server, str):
                    # Handle "hostname:port" format
                    if ":" in server:
                        hostname, port_str = server.split(":", 1)
                        port = int(port_str)
                    else:
                        hostname = server
                        port = 443
                    servers.append((hostname, port))
        return servers
    except (json.JSONDecodeError, ValueError):
        pass

    # Parse as comma-separated list
    server_parts = servers_str.split(",")
    for server_part in server_parts:
        server_part = server_part.strip()
        if ":" in server_part:
            hostname, port_str = server_part.split(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                raise ValueError(f"Invalid port number in '{server_part}'")
        else:
            hostname = server_part
            port = 443

        if hostname:
            servers.append((hostname, port))

    return servers


def main():
    """Main function for the SSL certificate download script."""
    parser = argparse.ArgumentParser(
        description="Download and import SSL certificates from servers"
    )
    parser.add_argument(
        "servers",
        help="Servers to download certificates from. Can be JSON list or "
        'comma-separated "hostname:port" pairs (default port: 443)',
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Only download certificates, do not import to system store",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set up logging
    if args.verbose:
        util.log_msg("Verbose logging enabled", mode=util.STDOUT_LOG)

    try:
        # Parse server list
        servers = parse_servers(args.servers)
        if not servers:
            util.log_msg("No valid servers specified", mode=util.STDERR_LOG)
            return 1

        util.log_msg(
            f"Processing {len(servers)} server(s): {servers}", mode=util.STDOUT_LOG
        )

        if args.download_only:
            # Import individual functions for download-only mode
            from thermostatsupervisor.ssl_certificate import download_ssl_certificate

            success = True
            for hostname, port in servers:
                try:
                    cert_path = download_ssl_certificate(hostname, port)
                    util.log_msg(
                        f"Downloaded certificate to {cert_path}", mode=util.STDOUT_LOG
                    )
                except Exception as e:
                    util.log_msg(
                        f"Failed to download certificate from "
                        f"{hostname}:{port}: {e}",
                        mode=util.STDERR_LOG,
                    )
                    success = False
        else:
            # Download and import certificates
            success = download_and_import_ssl_certificates(servers)

        if success:
            util.log_msg(
                "All certificates processed successfully", mode=util.STDOUT_LOG
            )
            return 0
        else:
            util.log_msg("Some certificates failed to process", mode=util.STDERR_LOG)
            return 1

    except Exception as e:
        util.log_msg(f"Error: {e}", mode=util.STDERR_LOG)
        return 1


if __name__ == "__main__":
    sys.exit(main())

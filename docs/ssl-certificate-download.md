# SSL Certificate Download and Import

This document describes the SSL certificate download and import functionality added to ThermostatSupervisor.

## Overview

The SSL certificate download and import system allows automatic downloading of self-signed SSL certificates from remote servers and importing them into the local system's trust store. This is particularly useful for unit testing environments where HTTPS-enabled servers use self-signed certificates.

## Components

### 1. SSL Certificate Module (`src/ssl_certificate.py`)

Extended functionality includes:

- `download_ssl_certificate(hostname, port)`: Downloads SSL certificate from a remote server
- `import_ssl_certificate_to_system(cert_path)`: Imports certificate to system trust store
- `download_and_import_ssl_certificates(servers)`: Downloads and imports multiple certificates

### 2. Standalone Script (`download_ssl_certificates.py`)

Command-line script for downloading and importing SSL certificates:

```bash
# Download and import certificates
python download_ssl_certificates.py "server1.com:443,server2.com:8443"

# Download only (no import)
python download_ssl_certificates.py "server.com:443" --download-only

# JSON format
python download_ssl_certificates.py '[{"hostname": "server.com", "port": 443}]'

# Enable verbose logging
python download_ssl_certificates.py "server.com:443" --verbose
```

### 3. GitHub Actions Integration

#### Import SSL Certificates Workflow (`.github/workflows/import-ssl-certificates.yml`)

Reusable workflow for downloading SSL certificates before testing:

```yaml
- name: Import SSL certificates
  uses: ./.github/workflows/import-ssl-certificates.yml
  with:
    servers: '[{"hostname": "myserver.com", "port": 443}]'
```

#### Enhanced PyLint Workflow (`.github/workflows/pylint.yml`)

Automatically detects HTTPS/SSL configuration and imports certificates before running tests.

## Platform Support

### Linux
- Copies certificates to system directories:
  - `/usr/local/share/ca-certificates/`
  - `/etc/ssl/certs/`
  - `/etc/pki/ca-trust/source/anchors/`
- Updates certificate stores using `update-ca-certificates` or `update-ca-trust`

### Windows
- Uses `certutil` to import certificates to Windows Certificate Store
- Imports to the "Root" certificate store

### Fallback
- For unsupported platforms or when system import fails
- Can set environment variables for certificate bundle location

## Usage Examples

### Manual Certificate Download

```python
from src.ssl_certificate import download_ssl_certificate, import_ssl_certificate_to_system

# Download certificate
cert_path = download_ssl_certificate("myserver.com", 443)

# Import to system store
success = import_ssl_certificate_to_system(cert_path)
```

### Batch Processing

```python
from src.ssl_certificate import download_and_import_ssl_certificates

servers = [
    ("server1.com", 443),
    ("server2.com", 8443),
    ("server3.com", 443)
]

success = download_and_import_ssl_certificates(servers)
```

### GitHub Actions

In your workflow file:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Import SSL certificates before testing
      - name: Import SSL certificates
        run: |
          python download_ssl_certificates.py "testserver.com:443" --verbose
      
      # Run your tests
      - name: Run tests
        run: python -m unittest discover
```

## Security Considerations

- Certificates are downloaded without verification (to allow self-signed certificates)
- Downloaded certificates are stored with appropriate file permissions (0o644)
- System certificate import requires elevated privileges on most platforms
- Certificates are imported to system-wide trust stores

## Error Handling

- Network connectivity issues are handled gracefully
- OpenSSL command failures are logged with detailed error messages
- Partial failures in batch operations are reported but don't stop processing
- Platform-specific import failures fall back to alternative methods

## Testing

Comprehensive unit tests cover:
- Certificate download functionality
- Platform-specific import mechanisms
- Error handling and edge cases
- Command-line script functionality
- GitHub Actions integration

Run tests with:
```bash
python -m unittest tests.test_ssl_certificate -v
python -m unittest tests.test_download_ssl_certificates -v
```

## Dependencies

- `openssl` command-line tool (for certificate download and validation)
- `sudo` access (for Linux certificate import)
- `certutil` (for Windows certificate import)
- Python standard library modules: `pathlib`, `platform`, `subprocess`, `argparse`

## Limitations

- Requires OpenSSL to be installed and available in PATH
- System certificate import may require administrative privileges
- Network connectivity is required for certificate download
- Self-signed certificates only (by design)
# Flask Production Server Setup

This document provides instructions for deploying the ThermostatSupervisor Flask servers in production using Gunicorn.

## Prerequisites

- Python 3.9 or higher
- All dependencies installed: `pip install -r requirements.txt`
- Gunicorn installed (included in requirements.txt)

## Available Flask Servers

### 1. Supervisor Flask Server
- **Purpose**: Displays supervisor output on web page
- **Default Port**: 5001
- **WSGI Entry Point**: `thermostatsupervisor.supervisor_wsgi:application`

### 2. SHT31 Flask Server  
- **Purpose**: Flask API for Raspberry Pi SHT31 sensor
- **Default Port**: 5000
- **WSGI Entry Point**: `thermostatsupervisor.sht31_wsgi:application`
- **Requirements**: Raspberry Pi environment with SHT31 sensor

## Production Deployment Options

### Option 1: Using Startup Scripts (Recommended)

Execute the provided startup scripts:

```bash
# Start supervisor Flask server
./start_supervisor_production.sh

# Start SHT31 Flask server (Raspberry Pi only)
./start_sht31_production.sh
```

### Option 2: Direct Gunicorn Commands

Start servers directly with Gunicorn:

```bash
# Supervisor Flask server
gunicorn --config gunicorn.supervisor.conf.py \
         thermostatsupervisor.supervisor_wsgi:application

# SHT31 Flask server
gunicorn --config gunicorn.sht31.conf.py \
         thermostatsupervisor.sht31_wsgi:application
```

### Option 3: Custom Configuration

Create your own Gunicorn configuration or use command-line options:

```bash
# Example with custom settings
gunicorn --bind 0.0.0.0:5001 \
         --workers 4 \
         --timeout 30 \
         --access-logfile - \
         --error-logfile - \
         thermostatsupervisor.supervisor_wsgi:application
```

## Configuration Files

- `gunicorn.supervisor.conf.py`: Configuration for supervisor Flask server
- `gunicorn.sht31.conf.py`: Configuration for SHT31 Flask server

Both configurations include:
- Automatic worker scaling based on CPU cores
- Request timeout and keepalive settings
- Logging configuration
- Process management settings

## Security Considerations

1. **User/Group**: Uncomment and set appropriate user/group in config files
2. **Firewall**: Configure firewall to allow only necessary ports
3. **Reverse Proxy**: Consider using Nginx or Apache as a reverse proxy
4. **SSL/TLS**: Configure HTTPS certificates for production
5. **Rate Limiting Storage**: For production deployments with multiple workers or servers, configure external storage for rate limiting:
   ```bash
   # Redis storage (recommended for production)
   export FLASK_LIMITER_STORAGE_URI="redis://localhost:6379"
   
   # Memcached storage
   export FLASK_LIMITER_STORAGE_URI="memcached://localhost:11211"
   
   # Default (development): memory://
   ```

## Monitoring and Management

- PID files are created in `/tmp/` for process management
- Logs are sent to stdout/stderr by default
- Use process managers like systemd for automatic startup/restart

## Development vs Production

- **Development**: Use `python -m thermostatsupervisor.supervisor_flask_server`
- **Production**: Use Gunicorn with the configurations provided

The development server will continue to work as before when running the Python modules directly.
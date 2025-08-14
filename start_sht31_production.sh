#!/bin/bash
# Startup script for SHT31 Flask server using Gunicorn
# This script runs the SHT31 Flask server in production mode

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set Python path to include the project directory
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# Change to project directory
cd "${SCRIPT_DIR}"

echo "Starting SHT31 Flask server with Gunicorn..."
echo "Server will be available at http://0.0.0.0:5000"

# Run Gunicorn with SHT31 configuration
exec gunicorn \
    --config gunicorn.sht31.conf.py \
    thermostatsupervisor.sht31_wsgi:application
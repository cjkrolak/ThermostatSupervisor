#!/bin/bash
# Startup script for supervisor Flask server using Gunicorn
# This script runs the supervisor Flask server in production mode

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set Python path to include the project directory
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# Change to project directory
cd "${SCRIPT_DIR}"

echo "Starting supervisor Flask server with Gunicorn..."
echo "Server will be available at http://0.0.0.0:5001"

# Run Gunicorn with supervisor configuration
exec gunicorn \
    --config gunicorn.supervisor.conf.py \
    src.supervisor_wsgi:application
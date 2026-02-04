"""
WSGI entry point for SHT31 Flask server production deployment.

This module provides the WSGI application object that can be used by
production WSGI servers like Gunicorn.

Example usage with Gunicorn:
    gunicorn --config gunicorn.sht31.conf.py \\
        src.sht31_wsgi:application
"""

# local imports
from src import sht31_flask_server as sht31
from src import utilities as util

# Enable logging to STDERR for production
util.log_stdout_to_stderr = True

# Create the WSGI application
application = sht31.create_app()

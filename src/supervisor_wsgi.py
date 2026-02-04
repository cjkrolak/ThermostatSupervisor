"""
WSGI entry point for supervisor Flask server production deployment.

This module provides the WSGI application object that can be used by
production WSGI servers like Gunicorn.

Example usage with Gunicorn:
    gunicorn --config gunicorn.supervisor.conf.py \\
        src.supervisor_wsgi:application
"""

# local imports
from src import supervisor_flask_server as sfs
from src import utilities as util

# Enable logging to STDERR for production
util.log_stdout_to_stderr = True

# Create the WSGI application
application = sfs.create_app()

# Gunicorn configuration file for supervisor Flask server
# Usage: gunicorn --config gunicorn.supervisor.conf.py \\
#                 thermostatsupervisor.supervisor_wsgi:application

import multiprocessing
import platform

# Server socket
bind = "0.0.0.0:5001"
backlog = 2048

# Worker processes
# Limit workers to 1 on ARM processors due to memory constraints
machine = platform.machine().lower()
if any(arch in machine for arch in ['arm', 'aarch']):
    workers = 1
else:
    workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, with up to 50% jitter
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "thermostat_supervisor"

# Daemon mode (set to False for development/testing)
daemon = False

# PID file
pidfile = "/tmp/supervisor_flask.pid"

# User and group (uncomment and set for production deployment)
# user = "nobody"
# group = "nobody"

# Preload application for better performance
preload_app = True

# Enable worker recycling
max_worker_connections = 1000

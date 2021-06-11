"""gunicorn WSGI server configuration."""
from multiprocessing import cpu_count
from os import environ


def max_workers():
    return cpu_count()


chdir = "/usr/src/app"
bind = "0.0.0.0:5000"
max_requests = 1000
worker_class = "gevent"
workers = 3
timeout = 300
keepalive = 300
graceful_timeout = 300
log_level = "info"
log_file = "/usr/src/app/log/gunicorn.log"
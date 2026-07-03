"""gunicorn WSGI server configuration."""

import os
from multiprocessing import cpu_count

from cornflow.shared.log_config import gunicorn_log_config


def max_workers():
    return cpu_count()


pidfile = "/usr/src/app/gunicorn.pid"
chdir = "/usr/src/app"
bind = "0.0.0.0:5000"
max_requests = 1000
worker_class = "gevent"
workers = 3
timeout = 300
keepalive = 300
graceful_timeout = 300
log_level = "info"

if os.getenv("CORNFLOW_LOGGING") == "file":
    accesslog = "/usr/src/app/log/info.log"
    errorlog = "/usr/src/app/log/error.log"
else:
    # error and access logs share stream (CORNFLOW_LOG_STREAM), format
    # (CORNFLOW_LOG_FORMAT) and cloud shipping with the application logs
    accesslog = "-"
    logconfig_dict = gunicorn_log_config()

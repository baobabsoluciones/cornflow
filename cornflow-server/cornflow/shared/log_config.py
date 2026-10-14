"""
Logging configuration for cornflow, driven by environment variables:

- ``CORNFLOW_LOG_STREAM``: ``stdout`` (default) or ``stderr``.
- ``CORNFLOW_LOG_FORMAT``: ``text`` (default) or ``json`` (one JSON object per line).
- ``CORNFLOW_LOG_S3_BUCKET``: if set, logs are also shipped to this S3 bucket.
- ``CORNFLOW_LOG_GCS_BUCKET``: if set, logs are also shipped to this GCS bucket.
- ``CORNFLOW_LOG_UPLOAD_PREFIX``: object key prefix for shipped logs (default ``cornflow-logs``).
- ``CORNFLOW_LOG_UPLOAD_INTERVAL``: seconds between uploads (default 60).
- ``CORNFLOW_LOG_UPLOAD_MAX_BUFFER``: records that force an immediate upload (default 5000).
"""

import json
import logging
import os
from datetime import datetime, timezone

LEVEL_CONVERTER = {
    0: "NOTSET",
    10: "DEBUG",
    20: "INFO",
    30: "WARNING",
    40: "ERROR",
    50: "CRITICAL",
}

TEXT_FORMAT = "[%(asctime)s] [%(levelname)s] in %(module)s: %(message)s"


class JsonFormatter(logging.Formatter):
    """Formats each record as a single-line JSON object, for log collectors."""

    def format(self, record):
        entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def get_formatter_config():
    log_format = os.getenv("CORNFLOW_LOG_FORMAT", "text").lower()
    if log_format == "json":
        return {"()": "cornflow.shared.log_config.JsonFormatter"}
    return {"format": TEXT_FORMAT}


def get_console_stream():
    stream = os.getenv("CORNFLOW_LOG_STREAM", "stdout").lower()
    return "ext://sys.stderr" if stream == "stderr" else "ext://sys.stdout"


def get_cloud_handlers_config():
    """
    Returns the handlers configuration for shipping logs to S3 and/or GCS,
    according to the environment variables. Empty if none is configured.
    """
    common = {
        "formatter": "default",
        "prefix": os.getenv("CORNFLOW_LOG_UPLOAD_PREFIX", "cornflow-logs"),
        "upload_interval": int(os.getenv("CORNFLOW_LOG_UPLOAD_INTERVAL", 60)),
        "max_buffer": int(os.getenv("CORNFLOW_LOG_UPLOAD_MAX_BUFFER", 5000)),
    }
    handlers = {}
    s3_bucket = os.getenv("CORNFLOW_LOG_S3_BUCKET")
    if s3_bucket:
        handlers["cloud_s3"] = {
            "()": "cornflow.shared.cloud_logging.S3LogHandler",
            "bucket": s3_bucket,
            **common,
        }
    gcs_bucket = os.getenv("CORNFLOW_LOG_GCS_BUCKET")
    if gcs_bucket:
        handlers["cloud_gcs"] = {
            "()": "cornflow.shared.cloud_logging.GCSLogHandler",
            "bucket": gcs_bucket,
            **common,
        }
    return handlers


def log_config(level=20):
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": get_console_stream(),
            "formatter": "default",
        },
        **get_cloud_handlers_config(),
    }
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"default": get_formatter_config()},
        "handlers": handlers,
        "root": {
            "level": LEVEL_CONVERTER[level],
            "handlers": list(handlers),
        },
    }


def gunicorn_log_config(level=None):
    """
    Logging configuration for gunicorn (``logconfig_dict``) so that its error
    and access logs share stream, format and cloud shipping with the
    application logs.
    """
    if level is None:
        level = int(os.getenv("LOG_LEVEL", 20))
    config = log_config(level)
    handler_names = list(config["handlers"])
    config["loggers"] = {
        name: {
            "level": config["root"]["level"],
            "handlers": handler_names,
            "propagate": False,
            "qualname": name,
        }
        for name in ("gunicorn.error", "gunicorn.access")
    }
    return config

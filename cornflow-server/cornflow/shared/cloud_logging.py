"""
Logging handlers that buffer records in memory and periodically upload them
as objects to a cloud storage bucket (AWS S3 or Google Cloud Storage).

These handlers are activated through environment variables (see
:func:`cornflow.shared.log_config.log_config`) and are meant as a complement
to console logging: records are always written to stdout/stderr as well, so
a crash can at most lose the records buffered since the last upload.
"""

import atexit
import logging
import os
import socket
import sys
import threading
import uuid
from datetime import datetime, timezone


class BufferedCloudHandler(logging.Handler):
    """
    Base handler that accumulates formatted records in memory and flushes
    them as a single object to a bucket, either every ``upload_interval``
    seconds or as soon as ``max_buffer`` records are queued.

    Subclasses must implement :meth:`_upload` and :meth:`destination`.
    """

    def __init__(
        self, bucket, prefix="cornflow-logs", upload_interval=60, max_buffer=5000
    ):
        super().__init__()
        self.bucket = bucket
        self.prefix = str(prefix).strip("/")
        self.upload_interval = max(int(upload_interval), 1)
        self.max_buffer = max(int(max_buffer), 1)
        self._buffer = []
        self._buffer_lock = threading.Lock()
        self._hostname = socket.gethostname()
        self._flusher = None
        self._flusher_pid = None
        self._stop = threading.Event()
        atexit.register(self.flush)

    def emit(self, record):
        try:
            message = self.format(record)
            self._ensure_flusher()
            with self._buffer_lock:
                self._buffer.append(message)
                must_flush = len(self._buffer) >= self.max_buffer
            if must_flush:
                self.flush()
        except Exception:
            self.handleError(record)

    def _ensure_flusher(self):
        # threads do not survive a fork (gunicorn pre-fork model), so the
        # flusher is (re)started lazily in the process that emits records
        if (
            self._flusher is not None
            and self._flusher.is_alive()
            and self._flusher_pid == os.getpid()
        ):
            return
        with self._buffer_lock:
            if (
                self._flusher is not None
                and self._flusher.is_alive()
                and self._flusher_pid == os.getpid()
            ):
                return
            self._flusher_pid = os.getpid()
            self._stop = threading.Event()
            self._flusher = threading.Thread(
                target=self._flush_loop, daemon=True, name="cornflow-log-uploader"
            )
            self._flusher.start()

    def _flush_loop(self):
        while not self._stop.wait(self.upload_interval):
            self.flush()

    def flush(self):
        with self._buffer_lock:
            if not self._buffer:
                return
            data, self._buffer = self._buffer, []
        try:
            self._upload("\n".join(data) + "\n")
        except Exception as error:
            # log shipping must never crash the application: requeue the
            # records (dropping the oldest beyond max_buffer) and report
            sys.stderr.write(
                f"cornflow: could not upload logs to {self.destination()}: {error}\n"
            )
            with self._buffer_lock:
                self._buffer = (data + self._buffer)[-self.max_buffer :]

    def _object_name(self):
        now = datetime.now(timezone.utc)
        return (
            f"{self.prefix}/{now:%Y-%m-%d}/{self._hostname}"
            f"-{os.getpid()}-{now:%H%M%S}-{uuid.uuid4().hex[:8]}.log"
        )

    def close(self):
        self._stop.set()
        try:
            self.flush()
        finally:
            super().close()

    def destination(self):
        raise NotImplementedError

    def _upload(self, data):
        raise NotImplementedError


class S3LogHandler(BufferedCloudHandler):
    """
    Ships buffered log records to an AWS S3 bucket. Requires ``boto3`` and
    credentials resolved the standard way (env variables, instance profile,
    IRSA...).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = None
        self._client_pid = None

    def destination(self):
        return f"s3://{self.bucket}"

    def _get_client(self):
        if self._client is None or self._client_pid != os.getpid():
            try:
                import boto3
            except ImportError as error:
                raise RuntimeError(
                    "boto3 is required to ship logs to S3 (pip install cornflow[s3-logs])"
                ) from error
            self._client = boto3.client("s3")
            self._client_pid = os.getpid()
        return self._client

    def _upload(self, data):
        self._get_client().put_object(
            Bucket=self.bucket, Key=self._object_name(), Body=data.encode("utf-8")
        )


class GCSLogHandler(BufferedCloudHandler):
    """
    Ships buffered log records to a Google Cloud Storage bucket. Requires
    ``google-cloud-storage`` and credentials resolved the standard way
    (GOOGLE_APPLICATION_CREDENTIALS, workload identity...).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = None
        self._client_pid = None

    def destination(self):
        return f"gs://{self.bucket}"

    def _get_client(self):
        if self._client is None or self._client_pid != os.getpid():
            try:
                from google.cloud import storage
            except ImportError as error:
                raise RuntimeError(
                    "google-cloud-storage is required to ship logs to GCS "
                    "(pip install cornflow[gcs-logs])"
                ) from error
            self._client = storage.Client()
            self._client_pid = os.getpid()
        return self._client

    def _upload(self, data):
        blob = self._get_client().bucket(self.bucket).blob(self._object_name())
        blob.upload_from_string(data, content_type="text/plain")

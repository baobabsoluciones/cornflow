"""
Unit tests for the environment-driven logging configuration
(cornflow.shared.log_config) and the cloud shipping handlers
(cornflow.shared.cloud_logging).
"""

import json
import logging
import unittest
from logging.config import dictConfig
from unittest.mock import patch

from cornflow.shared.cloud_logging import BufferedCloudHandler
from cornflow.shared.log_config import (
    JsonFormatter,
    gunicorn_log_config,
    log_config,
)


class FakeCloudHandler(BufferedCloudHandler):
    """Cloud handler that records uploads instead of sending them."""

    def __init__(self, *args, fail=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.uploads = []
        self.fail = fail

    def destination(self):
        return f"fake://{self.bucket}"

    def _upload(self, data):
        if self.fail:
            raise RuntimeError("upload failed")
        self.uploads.append(data)


class TestLogConfig(unittest.TestCase):
    def test_default_config_writes_text_to_stdout(self):
        with patch.dict("os.environ", {}, clear=True):
            config = log_config(20)
        console = config["handlers"]["console"]
        self.assertEqual(console["stream"], "ext://sys.stdout")
        self.assertEqual(config["root"]["handlers"], ["console"])
        self.assertEqual(config["root"]["level"], "INFO")
        self.assertIn("format", config["formatters"]["default"])

    def test_stream_can_be_set_to_stderr(self):
        with patch.dict("os.environ", {"CORNFLOW_LOG_STREAM": "stderr"}):
            config = log_config(20)
        self.assertEqual(config["handlers"]["console"]["stream"], "ext://sys.stderr")

    def test_json_format_uses_json_formatter(self):
        with patch.dict("os.environ", {"CORNFLOW_LOG_FORMAT": "json"}):
            config = log_config(20)
        self.assertEqual(
            config["formatters"]["default"]["()"],
            "cornflow.shared.log_config.JsonFormatter",
        )

    def test_cloud_handlers_added_from_environment(self):
        env = {
            "CORNFLOW_LOG_S3_BUCKET": "my-s3-bucket",
            "CORNFLOW_LOG_GCS_BUCKET": "my-gcs-bucket",
            "CORNFLOW_LOG_UPLOAD_INTERVAL": "30",
        }
        with patch.dict("os.environ", env):
            config = log_config(20)
        self.assertEqual(config["handlers"]["cloud_s3"]["bucket"], "my-s3-bucket")
        self.assertEqual(config["handlers"]["cloud_gcs"]["bucket"], "my-gcs-bucket")
        self.assertEqual(config["handlers"]["cloud_s3"]["upload_interval"], 30)
        self.assertEqual(
            sorted(config["root"]["handlers"]),
            ["cloud_gcs", "cloud_s3", "console"],
        )

    def test_gunicorn_config_shares_handlers(self):
        with patch.dict("os.environ", {"CORNFLOW_LOG_S3_BUCKET": "my-s3-bucket"}):
            config = gunicorn_log_config(20)
        for name in ("gunicorn.error", "gunicorn.access"):
            self.assertEqual(
                sorted(config["loggers"][name]["handlers"]),
                ["cloud_s3", "console"],
            )
            self.assertFalse(config["loggers"][name]["propagate"])

    def test_dict_config_applies_cleanly(self):
        root = logging.getLogger()
        previous_handlers, previous_level = root.handlers[:], root.level
        try:
            with patch.dict("os.environ", {"CORNFLOW_LOG_FORMAT": "json"}):
                dictConfig(log_config(20))
            self.assertTrue(
                any(isinstance(h.formatter, JsonFormatter) for h in root.handlers)
            )
        finally:
            root.handlers, root.level = previous_handlers, previous_level


class TestJsonFormatter(unittest.TestCase):
    def _record(self, **kwargs):
        defaults = dict(
            name="cornflow.test",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg="something happened: %s",
            args=("detail",),
            exc_info=None,
        )
        defaults.update(kwargs)
        return logging.LogRecord(**defaults)

    def test_output_is_one_json_object_per_line(self):
        output = JsonFormatter().format(self._record())
        self.assertNotIn("\n", output)
        entry = json.loads(output)
        self.assertEqual(entry["level"], "WARNING")
        self.assertEqual(entry["logger"], "cornflow.test")
        self.assertEqual(entry["message"], "something happened: detail")
        self.assertIn("timestamp", entry)

    def test_exception_is_included(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = self._record(exc_info=sys.exc_info())
        entry = json.loads(JsonFormatter().format(record))
        self.assertIn("ValueError: boom", entry["exception"])


class TestBufferedCloudHandler(unittest.TestCase):
    def _handler(self, **kwargs):
        handler = FakeCloudHandler("bucket", upload_interval=3600, **kwargs)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.addCleanup(handler.close)
        return handler

    def _emit(self, handler, message):
        handler.emit(
            logging.LogRecord(
                "cornflow.test", logging.INFO, __file__, 1, message, None, None
            )
        )

    def test_records_are_buffered_until_flush(self):
        handler = self._handler(max_buffer=100)
        self._emit(handler, "one")
        self._emit(handler, "two")
        self.assertEqual(handler.uploads, [])
        handler.flush()
        self.assertEqual(handler.uploads, ["one\ntwo\n"])
        # a second flush with an empty buffer does not upload anything
        handler.flush()
        self.assertEqual(len(handler.uploads), 1)

    def test_full_buffer_triggers_upload(self):
        handler = self._handler(max_buffer=2)
        self._emit(handler, "one")
        self._emit(handler, "two")
        self.assertEqual(handler.uploads, ["one\ntwo\n"])

    def test_failed_upload_requeues_records(self):
        handler = self._handler(max_buffer=100, fail=True)
        self._emit(handler, "one")
        with patch("sys.stderr"):
            handler.flush()
        self.assertEqual(handler.uploads, [])
        handler.fail = False
        handler.flush()
        self.assertEqual(handler.uploads, ["one\n"])

    def test_object_names_are_unique(self):
        handler = self._handler()
        names = {handler._object_name() for _ in range(50)}
        self.assertEqual(len(names), 50)
        self.assertTrue(all(name.startswith("cornflow-logs/") for name in names))


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

import requests

from src.notification_queue import dispatch_pending, enqueue_alert, load_queue, process_notifications


class _Response:
    def raise_for_status(self):
        return None


class _SuccessfulSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _Response()


class _FailedSession:
    def post(self, url, **kwargs):
        raise requests.ConnectionError("offline")


class NotificationQueueTests(unittest.TestCase):
    def test_duplicate_message_is_enqueued_once(self):
        queue = {"version": 1, "alerts": []}
        first_id, first_added = enqueue_alert(queue, "같은 문안", [], "2026-09-15T10:00:00+09:00")
        second_id, second_added = enqueue_alert(queue, "같은 문안", [], "2026-09-15T10:01:00+09:00")
        self.assertEqual(first_id, second_id)
        self.assertTrue(first_added)
        self.assertFalse(second_added)
        self.assertEqual(1, len(queue["alerts"]))

    def test_without_webhook_alert_waits_without_external_call(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "outbox.json")
            result = process_notifications(path, "경보 문안", [{"site_name": "A현장"}], "now")
            self.assertEqual("shadow", result["mode"])
            self.assertEqual(0, result["sent"])
            self.assertEqual(0, result["failed"])
            self.assertEqual(1, result["waiting"])
            self.assertEqual("pending", load_queue(path)["alerts"][0]["status"])

    def test_shadow_mode_blocks_configured_webhook(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "outbox.json")
            session = _SuccessfulSession()
            result = process_notifications(
                path,
                "모의운영 문안",
                [{"site_name": "A현장"}],
                "now",
                webhook_url="https://example.test",
                webhook_token="secret",
                session=session,
                mode="shadow",
            )
            self.assertEqual("shadow", result["mode"])
            self.assertEqual(0, result["sent"])
            self.assertEqual(1, result["waiting"])
            self.assertEqual([], session.calls)

    def test_failed_delivery_is_retried_and_sent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "outbox.json")
            failed = process_notifications(
                path,
                "주의 문안",
                [],
                "now",
                "https://example.test",
                session=_FailedSession(),
                mode="live",
            )
            self.assertEqual(1, failed["failed"])
            session = _SuccessfulSession()
            sent = process_notifications(
                path,
                None,
                [],
                "later",
                "https://example.test",
                "secret",
                session=session,
                mode="live",
            )
            self.assertEqual(1, sent["sent"])
            alert = json.loads(Path(path).read_text())["alerts"][0]
            self.assertEqual("sent", alert["status"])
            self.assertEqual("Bearer secret", session.calls[0][1]["headers"]["Authorization"])
            self.assertEqual(alert["id"], session.calls[0][1]["json"]["idempotency_key"])

    def test_stale_alert_expires_instead_of_sending(self):
        queue = {"version": 1, "alerts": []}
        enqueue_alert(queue, "오래된 문안", [], "2026-09-15T01:00:00+09:00")
        session = _SuccessfulSession()
        result = dispatch_pending(
            queue,
            "https://example.test",
            now_iso="2026-09-15T10:00:00+09:00",
            session=session,
        )
        self.assertEqual(1, result["expired"])
        self.assertEqual([], session.calls)
        self.assertEqual("expired", queue["alerts"][0]["status"])


if __name__ == "__main__":
    unittest.main()

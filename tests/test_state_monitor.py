import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.state_monitor import (
    build_alert_message,
    carry_change_summary,
    detect_changes,
    load_state,
    save_state,
    state_age_minutes,
)


def snapshot(level="정상", categories=None, forecasts=None):
    return {
        "version": 1,
        "updated_at": "2026-09-15T10:47:00+09:00",
        "sites": {
            "테스트 현장": {
                "level": level,
                "categories": categories or [],
                "reasons": [],
                "forecast_risks": forecasts or [],
            }
        },
    }


class StateMonitorTests(unittest.TestCase):
    def test_normal_first_run_does_not_alert(self):
        self.assertEqual(detect_changes(None, snapshot()), [])

    def test_level_rise_and_clear_are_detected(self):
        raised = snapshot("주의", ["호우"])
        changes = detect_changes(snapshot(), raised)
        self.assertEqual(changes[0]["type"], "위험 상승")

        changes = detect_changes(raised, snapshot())
        self.assertEqual(changes[0]["type"], "위험 해제")

    def test_same_forecast_is_not_repeated(self):
        event = [{"date": "9/16(수)", "kind": "강수", "detail": "비 70%"}]
        self.assertEqual(detect_changes(snapshot(forecasts=event), snapshot(forecasts=event)), [])

    def test_new_forecast_is_detected(self):
        event = [{"date": "9/16(수)", "kind": "한파", "detail": "최저 -12°C"}]
        changes = detect_changes(snapshot(), snapshot(forecasts=event))
        self.assertEqual(changes[0]["type"], "새 예보 위험")
        self.assertEqual(changes[0]["categories"], ["한파"])

    def test_change_summary_is_carried(self):
        old = snapshot()
        old["last_change_at"] = "2026-09-15T09:00:00+09:00"
        old["last_changes"] = [{"site_name": "테스트 현장", "type": "위험 해제"}]
        current = carry_change_summary(old, snapshot(), [])
        self.assertEqual(current["last_changes"], old["last_changes"])

    def test_state_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            save_state(path, snapshot())
            self.assertEqual(load_state(path), snapshot())

    def test_alert_contains_action_items(self):
        changes = [{
            "site_name": "테스트 현장",
            "type": "위험 발생",
            "to_level": "주의",
            "categories": ["호우"],
            "reasons": ["시간당 5mm"],
        }]
        message = build_alert_message("2026-09-15 10:47", changes)
        self.assertIn("테스트 현장", message)
        self.assertIn("배수로", message)

    def test_state_age_minutes(self):
        state = snapshot()
        now = datetime(2026, 9, 15, 2, 17, tzinfo=timezone.utc)
        self.assertEqual(state_age_minutes(state, now), 30)

    def test_failed_collection_is_never_fresh(self):
        state = snapshot()
        state["collection_status"] = "failed"
        self.assertIsNone(state_age_minutes(state))


if __name__ == "__main__":
    unittest.main()

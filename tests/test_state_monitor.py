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
                "legal_signals": [],
                "weather_warnings": [],
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

    def test_official_warning_activation_and_release_are_detected(self):
        warning = {
            "kind": "기상특보", "title": "호우주의보", "phenomenon": "호우",
            "level": "주의보", "announced_at": "202609201400",
            "areas": ["경기도(군포)"], "matched_areas": ["경기도(군포)"],
        }
        current = snapshot()
        current["sites"]["테스트 현장"]["weather_warnings"] = [warning]
        changes = detect_changes(snapshot(), current)
        self.assertEqual("기상특보 발효", changes[0]["type"])
        self.assertEqual(["호우"], changes[0]["categories"])
        message = build_alert_message("2026-09-20 14:00", changes)
        self.assertIn("기상청 공식 발표", message)
        self.assertIn("배수로", message)

        released = detect_changes(current, snapshot())
        self.assertEqual("기상특보 해제", released[0]["type"])
        self.assertEqual([], released[0]["categories"])

    def test_warning_api_failure_does_not_create_false_release(self):
        warning = {
            "kind": "기상특보", "title": "호우주의보", "phenomenon": "호우",
            "level": "주의보", "announced_at": "202609201400",
            "matched_areas": ["경기도(군포)"],
        }
        previous = snapshot()
        previous["warning_collection_status"] = "healthy"
        previous["sites"]["테스트 현장"]["weather_warnings"] = [warning]
        current = snapshot()
        current["warning_collection_status"] = "failed"
        current["sites"]["테스트 현장"]["weather_warnings_available"] = False
        changes = detect_changes(previous, current)
        self.assertEqual(["기상특보 수집 장애"], [change["type"] for change in changes])

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

    def test_alert_follows_in_house_notice_tone(self):
        """사내 배포 문체(공지드립니다·【제목】·①·②·마무리·감사합니다)를 유지한다."""
        changes = [{
            "site_name": "테스트 현장",
            "type": "위험 발생",
            "to_level": "경보",
            "categories": ["폭염"],
            "reasons": ["체감 35.5°C"],
        }]
        message = build_alert_message("2026-09-20T14:00:00+09:00", changes)
        self.assertTrue(message.startswith("■ 공지드립니다."))
        self.assertIn("【온열질환 안전관리 사항】", message)
        self.assertIn("① 변동 현황", message)
        self.assertIn("② 본사·현장 확인사항", message)
        self.assertIn("온열질환 예방조치가 실제 이행될 수 있도록", message)
        self.assertTrue(message.rstrip().endswith("감사합니다."))

    def test_new_legal_action_is_detected_and_message_contains_article_action(self):
        current = snapshot()
        current["sites"]["테스트 현장"]["legal_signals"] = [{
            "status": "법정 작업중지",
            "work_type": "steel_erection",
            "title": "철골작업 중지",
            "article": "제383조",
            "reason": "시간당 강우 1.0mm",
            "actions": ["철골작업 즉시 중지"],
        }]
        changes = detect_changes(snapshot(), current)
        self.assertEqual("법정 조치 발생", changes[0]["type"])
        message = build_alert_message("2026-09-20 10:00", changes)
        self.assertIn("제383조", message)
        self.assertIn("철골작업 즉시 중지", message)

    def test_data_gap_does_not_trigger_external_alert(self):
        current = snapshot()
        current["sites"]["테스트 현장"]["legal_signals"] = [{
            "status": "데이터 부족", "work_type": "site_profile",
            "title": "현장 작업 프로필 미등록", "article": "판정 전제정보",
        }]
        self.assertEqual([], detect_changes(snapshot(), current))

    def test_removed_legal_action_requests_confirmation(self):
        previous = snapshot()
        previous["sites"]["테스트 현장"]["legal_signals"] = [{
            "status": "법정 작업중지", "work_type": "steel_erection",
            "title": "철골작업 중지", "article": "제383조",
        }]
        changes = detect_changes(previous, snapshot())
        self.assertEqual("법정 조치 상태 변경", changes[0]["type"])
        self.assertIn("지속 여부 확인", changes[0]["actions"][0])

    def test_legal_status_change_creates_one_event(self):
        previous = snapshot()
        current = snapshot()
        base = {"work_type": "steel_erection", "title": "철골작업 중지", "article": "제383조"}
        previous["sites"]["테스트 현장"]["legal_signals"] = [{**base, "status": "현장 확인 필요"}]
        current["sites"]["테스트 현장"]["legal_signals"] = [{
            **base, "status": "법정 작업중지", "actions": ["철골작업 즉시 중지"],
        }]
        changes = detect_changes(previous, current)
        self.assertEqual(1, len(changes))
        self.assertEqual("법정 작업중지", changes[0]["to_level"])

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

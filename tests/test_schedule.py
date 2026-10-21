import os
import re
import unittest
from datetime import datetime, timedelta, timezone

from src.schedule import WINDOW_LABEL, next_collection_at, resolve_run_mode, skip_reason

KST = timezone(timedelta(hours=9))


def at(hour, minute, day=25):
    return datetime(2026, 9, day, hour, minute, tzinfo=KST)


class ScheduleTests(unittest.TestCase):
    def test_next_collection(self):
        cases = [
            (at(0, 30), at(4, 17)),
            (at(4, 17), at(4, 47)),
            (at(4, 30), at(4, 47)),
            (at(16, 50), at(17, 47)),
            (at(17, 47), at(4, 17, day=26)),
            (at(23, 0), at(4, 17, day=26)),
        ]
        for now, expected in cases:
            with self.subTest(now=now):
                self.assertEqual(expected, next_collection_at(now))

    def test_window_label(self):
        self.assertEqual("04:17-17:47", WINDOW_LABEL)

    def test_workflow_schedule_matches(self):
        # 워크플로 일정이 바뀌면 이 테스트가 실패한다. 그때는 src/schedule.py도 함께 고친다.
        path = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "collector.yml")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(["17 0-8,19-23 * * *", "47 0-8,19-23 * * *"],
                         sorted(re.findall(r'cron:\s*["\']([^"\']+)["\']', text)))


class RunModeTests(unittest.TestCase):
    """외부 예약 서비스(auto)와 GitHub 예약(primary/backup)이 함께 와도 한 번만 수집한다."""

    def test_auto_mode_uses_kst_minute(self):
        # 외부 예약은 :17과 :47에 같은 요청을 보낸다. 40분 이후면 주 실행, 그 전이면 보완 실행.
        self.assertEqual("primary", resolve_run_mode("auto", at(9, 47)))
        self.assertEqual("primary", resolve_run_mode("auto", at(9, 55)))
        self.assertEqual("backup", resolve_run_mode("auto", at(10, 17)))
        self.assertEqual("backup", resolve_run_mode("auto", at(10, 25)))

    def test_explicit_and_manual_modes(self):
        self.assertEqual("primary", resolve_run_mode("primary", at(10, 17)))
        self.assertEqual("backup", resolve_run_mode("backup", at(9, 47)))
        # 사람이 Actions 화면에서 직접 실행하면(값 없음·manual) 항상 수집한다.
        for mode in (None, "", "manual", "unexpected"):
            with self.subTest(mode=mode):
                self.assertEqual("manual", resolve_run_mode(mode, at(9, 47)))

    def test_primary_skips_duplicate_within_20_minutes(self):
        self.assertIsNotNone(skip_reason("primary", 3))
        self.assertIsNotNone(skip_reason("primary", 19.9))
        self.assertIsNone(skip_reason("primary", 20))
        self.assertIsNone(skip_reason("primary", 60))

    def test_backup_collects_only_when_last_success_is_45_minutes_old(self):
        self.assertIsNotNone(skip_reason("backup", 30))
        self.assertIsNone(skip_reason("backup", 45))

    def test_manual_or_unknown_age_always_collects(self):
        self.assertIsNone(skip_reason("manual", 1))
        for mode in ("primary", "backup"):
            with self.subTest(mode=mode):
                # 직전 수집이 실패했거나 상태 파일이 없으면 나이를 모르므로 수집한다.
                self.assertIsNone(skip_reason(mode, None))


class WorkflowTriggerTests(unittest.TestCase):
    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "collector.yml")
        with open(path, encoding="utf-8") as f:
            self.text = f.read()

    def test_dispatch_accepts_auto_mode_for_external_scheduler(self):
        self.assertRegex(self.text, r"workflow_dispatch:\s*\n\s+inputs:\s*\n\s+mode:")
        self.assertIn("- auto", self.text)
        self.assertIn("inputs.mode", self.text)

    def test_checkout_uses_branch_tip_so_queued_runs_see_latest_state(self):
        # 대기열에서 기다린 실행이 이벤트 당시 커밋을 받으면 직전 수집 결과를 못 보고
        # 중복 수집한 뒤 푸시가 거절된다. 브랜치 최신본을 받아야 한다.
        self.assertRegex(self.text, r"actions/checkout@v4\s*\n\s+with:\s*\n\s+ref:\s*main")

    def test_push_rebases_on_remote_changes(self):
        self.assertIn("git pull --rebase", self.text)


if __name__ == "__main__":
    unittest.main()

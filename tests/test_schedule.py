import os
import re
import unittest
from datetime import datetime, timedelta, timezone

from src.schedule import WINDOW_LABEL, next_collection_at

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


if __name__ == "__main__":
    unittest.main()

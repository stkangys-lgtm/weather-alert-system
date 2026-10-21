"""src.main의 update_radar_safely 테스트 — 지연 import, 한국시각, 예외 요약 출력."""

import contextlib
import io
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import secretless_env  # noqa: F401  (config.py 없는 PC에서도 src.settings를 읽을 수 있게)
from src import main

KST = timezone(timedelta(hours=9))


class MainRunModeTests(unittest.TestCase):
    """외부 예약(auto)·GitHub 예약이 겹쳐도 직전 수집이 신선하면 외부 호출 없이 끝낸다."""

    def collects(self, mode, minute, age):
        out = io.StringIO()
        with patch.dict("os.environ", {"COLLECTION_MODE": mode}), \
                patch.object(main, "datetime") as fake_datetime, \
                patch.object(main, "load_state", return_value={}), \
                patch.object(main, "state_age_minutes", return_value=age), \
                patch.object(main, "collect_site_data", side_effect=RuntimeError("수집 시작")) as collect, \
                contextlib.redirect_stdout(out):
            fake_datetime.now.return_value = datetime(2026, 10, 22, 10, minute)
            with contextlib.suppress(RuntimeError):
                main.main()
        return collect.called

    def test_auto_backup_minute_skips_when_recent(self):
        self.assertFalse(self.collects("auto", 17, age=30))
        self.assertTrue(self.collects("auto", 17, age=50))

    def test_auto_primary_minute_skips_duplicate(self):
        self.assertFalse(self.collects("auto", 47, age=5))
        self.assertTrue(self.collects("auto", 47, age=60))

    def test_github_primary_schedule_skips_duplicate(self):
        self.assertFalse(self.collects("primary", 55, age=8))

    def test_manual_always_collects(self):
        self.assertTrue(self.collects("manual", 47, age=1))


class UpdateRadarSafelyTests(unittest.TestCase):
    @patch("src.radar.update_radar")
    def test_success_passes_aware_kst_time(self, update_radar):
        update_radar.return_value = {
            "image": "radar.png?v=202609280930",
            "observed_at": "2026-09-28T09:30:00+09:00",
            "corners": (),
        }

        result, ok = main.update_radar_safely()

        self.assertTrue(ok)
        self.assertEqual(update_radar.return_value, result)
        now_arg = update_radar.call_args.args[2]
        self.assertIsNotNone(now_arg.tzinfo)
        self.assertEqual(now_arg.utcoffset(), timedelta(hours=9))

    @patch("src.radar.update_radar")
    def test_failure_returns_none_false(self, update_radar):
        update_radar.return_value = None

        result, ok = main.update_radar_safely()

        self.assertIsNone(result)
        self.assertFalse(ok)

    @patch("src.radar.update_radar")
    def test_outer_exception_prints_type_name_only_not_message(self, update_radar):
        update_radar.side_effect = RuntimeError("민감할 수 있는 상세 메시지")
        buf = io.StringIO()

        with contextlib.redirect_stdout(buf):
            result, ok = main.update_radar_safely()

        self.assertIsNone(result)
        self.assertFalse(ok)
        output = buf.getvalue()
        self.assertIn("RuntimeError", output)
        self.assertNotIn("민감할 수 있는 상세 메시지", output)

    def test_import_error_returns_none_false_and_logs_type_name(self):
        # "from src import radar"는 src 모듈에 radar 속성이 이미 있으면(다른 테스트가 먼저
        # 가져온 경우) sys.modules를 다시 보지 않고 그 속성을 그대로 쓴다. 가져오기 실패를
        # 실제로 재현하려면 그 속성도 잠시 지워야 한다.
        import src
        had_attr = hasattr(src, "radar")
        saved = getattr(src, "radar", None)
        if had_attr:
            del src.radar
        buf = io.StringIO()
        try:
            with patch.dict(sys.modules, {"src.radar": None}):
                with contextlib.redirect_stdout(buf):
                    result, ok = main.update_radar_safely()
        finally:
            if had_attr:
                src.radar = saved

        self.assertIsNone(result)
        self.assertFalse(ok)
        # sys.modules에 None을 두면 실제로는 ModuleNotFoundError(ImportError의 하위 클래스)가 난다.
        self.assertIn("ModuleNotFoundError", buf.getvalue())


if __name__ == "__main__":
    unittest.main()

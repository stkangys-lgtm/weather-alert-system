"""수집 모듈의 격자 캐시·병렬화·회로 차단 동작을 검증한다.

실제 apis.data.go.kr 호출 없이 fetcher를 주입해, 다음을 고정한다.
- 같은 (nx, ny) 격자를 공유하는 현장은 API가 정확히 한 번만 호출된다.
- 회로 차단기가 실황·예보·중기예보 사이에서 상태를 공유한다.
- 전면 장애 상황에서도 목표 실행 예산 안에 종료된다.
- kma_client._request는 breaker가 트립되면 남은 재시도 대기를 건너뛰고 예외를 올린다.
"""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from unittest.mock import patch

import requests

from src import kma_client
from src.kma_client import forecast_base_datetime
from src.mid_client import mid_issue_datetime
from src.collection import (
    CIRCUIT_BREAKER_THRESHOLD,
    CircuitBreaker,
    collect_mid_forecasts,
    collect_site_data,
)


def make_site(name, nx, ny, lat=37.5, lon=127.0, category="건축"):
    return {
        "site_name": name,
        "category": category,
        "nx": nx,
        "ny": ny,
        "lat": lat,
        "lon": lon,
        "manager": "",
        "manager_phone": "",
    }


class GridCacheTests(unittest.TestCase):
    def test_same_grid_calls_api_only_once(self):
        sites = [
            make_site("A", 60, 127),
            make_site("B", 60, 127),  # 같은 격자
            make_site("C", 58, 121),
        ]
        current_calls, forecast_calls = [], []

        def fake_current(api_key, nx, ny, **kwargs):
            current_calls.append((nx, ny))
            return {"T1H": "10", "REH": "50", "WSD": "1"}

        def fake_forecast(api_key, nx, ny, **kwargs):
            forecast_calls.append((nx, ny))
            return [{"fcst_date": "20260920", "fcst_time": "1200"}]

        results = collect_site_data(
            sites,
            api_key="TEST",
            current_fetcher=fake_current,
            forecast_fetcher=fake_forecast,
        )

        self.assertEqual({(60, 127), (58, 121)}, set(current_calls))
        self.assertEqual(2, len(current_calls))
        self.assertEqual(2, len(forecast_calls))

        # 모든 현장이 결과에 남아있고 격자 공유 현장은 같은 자료를 참조한다.
        self.assertEqual(["A", "B", "C"], [item["site"]["site_name"] for item in results])
        self.assertEqual(results[0]["current"], results[1]["current"])
        self.assertEqual(results[0]["forecast"], results[1]["forecast"])

    def test_result_order_matches_input_order_even_with_parallelism(self):
        sites = [make_site(f"S{i}", 60 + i, 127) for i in range(8)]

        def fake_current(api_key, nx, ny, **kwargs):
            # 뒤 격자가 먼저 완료되도록 앞 격자에 짧은 대기를 준다.
            time.sleep((10 - nx) * 0.005)
            return {"T1H": str(nx)}

        def fake_forecast(api_key, nx, ny, **kwargs):
            return []

        results = collect_site_data(
            sites,
            api_key="TEST",
            current_fetcher=fake_current,
            forecast_fetcher=fake_forecast,
        )
        self.assertEqual([f"S{i}" for i in range(8)], [r["site"]["site_name"] for r in results])


class CircuitBreakerTests(unittest.TestCase):
    def test_threshold_trips_breaker(self):
        breaker = CircuitBreaker(threshold=3)
        for _ in range(2):
            breaker.record_failure()
        self.assertFalse(breaker.is_tripped())
        breaker.record_failure()
        self.assertTrue(breaker.is_tripped())

    def test_success_resets_failure_count(self):
        breaker = CircuitBreaker(threshold=3)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()
        breaker.record_failure()
        self.assertFalse(breaker.is_tripped())

    def test_shared_between_site_and_mid_collection(self):
        breaker = CircuitBreaker(threshold=2)

        def failing_current(*_, **__):
            raise requests.exceptions.ConnectionError("boom")

        def empty_forecast(*_, **__):
            return []

        sites = [make_site("A", 60, 127), make_site("B", 58, 121)]
        # 순차 실행: 두 격자 모두 실황이 실패해 breaker 트립.
        with ThreadPoolExecutor(max_workers=1) as ex:
            results = collect_site_data(
                sites,
                api_key="TEST",
                breaker=breaker,
                current_fetcher=failing_current,
                forecast_fetcher=empty_forecast,
                executor=ex,
            )

        self.assertTrue(breaker.is_tripped())
        self.assertTrue(all(r["current"] is None for r in results))

        # 이후 중기예보는 재시도 없이 1회만 호출되어야 한다.
        received_retries = []

        def fake_land(api_key, reg, now=None, timeout=None, retries=None, breaker=None):
            received_retries.append(retries)
            return {"wf4Am": "맑음"}

        def fake_ta(api_key, reg, now=None, timeout=None, retries=None, breaker=None):
            received_retries.append(retries)
            return {"taMin4": "10"}

        collect_mid_forecasts(
            [make_site("A", 60, 127)],
            api_key="TEST",
            breaker=breaker,
            land_fetcher=fake_land,
            ta_fetcher=fake_ta,
        )
        self.assertEqual(2, len(received_retries))
        self.assertTrue(all(r == 1 for r in received_retries))

    def test_partial_failure_preserves_healthy_sites(self):
        breaker = CircuitBreaker(threshold=10)  # 트립되지 않도록 크게

        def flaky_current(api_key, nx, ny, **kwargs):
            if nx == 60:
                raise requests.exceptions.Timeout("slow")
            return {"T1H": "20"}

        def fake_forecast(*_, **__):
            return []

        sites = [make_site("bad", 60, 127), make_site("good", 58, 121)]
        results = collect_site_data(
            sites,
            api_key="TEST",
            breaker=breaker,
            current_fetcher=flaky_current,
            forecast_fetcher=fake_forecast,
        )
        by_name = {r["site"]["site_name"]: r for r in results}
        self.assertIsNone(by_name["bad"]["current"])
        self.assertIsNotNone(by_name["good"]["current"])
        self.assertEqual("20", by_name["good"]["current"]["T1H"])


class TimeBudgetTests(unittest.TestCase):
    """전면 장애 상황에서도 예측 가능한 상한 안에 종료되는지 확인한다."""

    def test_full_outage_completes_within_budget(self):
        breaker = CircuitBreaker(threshold=CIRCUIT_BREAKER_THRESHOLD)

        # 실제 API 타임아웃(10초)을 짧게 흉내낸다. 워커 수 6일 때 임계치 3이면
        # 첫 배치의 초반 실패로 breaker가 트립되고, 이후 호출은 즉시 실패한다.
        PER_CALL_LATENCY = 0.05

        def slow_fail(*_, **__):
            time.sleep(PER_CALL_LATENCY)
            raise requests.exceptions.Timeout("outage")

        def slow_empty(*_, **__):
            time.sleep(PER_CALL_LATENCY)
            return []

        # 22개 현장, 20개 고유 격자
        sites = [make_site(f"S{i}", 55 + (i % 20), 100 + (i % 20)) for i in range(22)]

        start = time.monotonic()
        results = collect_site_data(
            sites,
            api_key="TEST",
            breaker=breaker,
            current_fetcher=slow_fail,
            forecast_fetcher=slow_empty,
            max_workers=6,
        )
        elapsed = time.monotonic() - start

        self.assertEqual(len(sites), len(results))
        self.assertTrue(all(r["current"] is None for r in results))
        # 순차 실행이면 22 * 0.05 = 1.1초 소요. 병렬 6개 + 회로차단이면
        # 최악 상한을 그 절반 이하로 잡아 회귀 검증에 사용한다.
        self.assertLess(elapsed, 0.6, f"실행이 {elapsed:.2f}s로 예산 초과")


class KmaClientBreakerIntegrationTests(unittest.TestCase):
    """kma_client._request가 breaker 트립 시 잔여 재시도 대기를 건너뛰는지 확인한다."""

    def test_request_skips_remaining_retries_when_breaker_tripped(self):
        breaker = CircuitBreaker(threshold=1)  # 첫 실패에 즉시 트립
        attempts = []
        sleep_calls = []

        class DummyResponse:
            def raise_for_status(self):
                raise requests.exceptions.ConnectionError("boom")

            def json(self):
                return {}

        def fake_get(url, params=None, timeout=None):
            attempts.append(1)
            return DummyResponse()

        with patch("src.kma_client.requests.get", side_effect=fake_get), \
             patch("src.kma_client.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            with self.assertRaises(requests.exceptions.ConnectionError):
                kma_client._request(
                    "getUltraSrtNcst",
                    "TEST",
                    {"base_date": "20260920", "base_time": "1000", "nx": 60, "ny": 127},
                    retries=3,
                    breaker=breaker,
                )

        self.assertEqual(1, len(attempts), "breaker 트립 후에는 재시도가 없어야 한다")
        self.assertEqual([], sleep_calls, "breaker 트립 시 재시도 대기가 없어야 한다")


class MidForecastDateTests(unittest.TestCase):
    SITE = make_site("A", 103, 109, lat=36.68, lon=129.45)

    def _collect(self, now):
        def land(api_key, reg, **kwargs):
            return {"wf5Am": "맑음", "wf5Pm": "구름많음", "rnSt5Am": 10, "rnSt5Pm": 20}

        def ta(api_key, reg, **kwargs):
            return {"taMin5": 17, "taMax5": 23}

        entries = collect_mid_forecasts([self.SITE], api_key="TEST", land_fetcher=land, ta_fetcher=ta, now=now)["A"]
        return {entry["date"]: entry for entry in entries}

    def test_issue_time_helpers(self):
        self.assertEqual(datetime(2026, 9, 25, 18, 0), mid_issue_datetime(datetime(2026, 9, 26, 5, 0)))
        self.assertEqual(datetime(2026, 9, 26, 6, 0), mid_issue_datetime(datetime(2026, 9, 26, 10, 0)))
        self.assertEqual(datetime(2026, 9, 26, 14, 0), forecast_base_datetime(datetime(2026, 9, 26, 15, 0)))

    def test_morning_run_uses_previous_evening_issue_date(self):
        # 06:30 전에는 전날 18시 발표를 쓰므로 "5일 뒤"는 9/25 + 5 = 9/30 이다.
        by_date = self._collect(datetime(2026, 9, 26, 5, 0))
        self.assertEqual("맑음", by_date["2026-09-30"]["sky_am"])
        self.assertEqual(17, by_date["2026-09-30"]["ta_min"])

    def test_daytime_run_uses_same_day_issue_date(self):
        by_date = self._collect(datetime(2026, 9, 26, 10, 0))
        self.assertEqual("맑음", by_date["2026-10-01"]["sky_am"])

    def test_fetchers_receive_now(self):
        seen = []

        def land(api_key, reg, **kwargs):
            seen.append(kwargs.get("now"))
            return {}

        def ta(api_key, reg, **kwargs):
            return {}

        now = datetime(2026, 9, 26, 5, 0)
        collect_mid_forecasts([self.SITE], api_key="TEST", land_fetcher=land, ta_fetcher=ta, now=now)
        self.assertEqual([now], seen)


if __name__ == "__main__":
    unittest.main()

"""현장별 실황·예보·중기예보 수집 유틸리티.

기존 순차 수집을 다음 세 축으로 개선한다.

1. 동일 격자(nx, ny) 캐시: 여러 현장이 같은 격자를 공유하면 API를 1번만 호출한다.
2. 제한된 동시성 병렬 수집: ThreadPoolExecutor로 격자 단위 조회를 동시에 진행하되,
   data.go.kr 부담을 고려해 워커 수는 소수(기본 6)로 제한한다.
3. 회로 차단: 실황·예보·중기예보 호출의 연결 실패를 공유 상태로 카운트하고, 임계치를
   넘으면 재시도를 즉시 중단해 GitHub Actions 타임아웃 안에 대시보드가 갱신되도록 한다.

주 실행 흐름 `src/main.py`가 이 모듈의 `collect_site_data`, `collect_mid_forecasts`를 호출한다.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from src import alert_rules
from src.legal_rules import evaluate_legal_signals, highest_legal_status
from src.mid_client import combine_forecast, get_mid_land_forecast, get_mid_temperature
from src.mid_regions import resolve_region_codes

MAX_WORKERS = 6
CIRCUIT_BREAKER_THRESHOLD = 3
CONNECTION_ERRORS = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)


class CircuitBreaker:
    """API 연결 실패를 스레드 안전하게 누적한다.

    임계치를 넘는 실패가 발생하면 `is_tripped()`가 True가 되고, 이후의 재시도는
    바로 실패로 처리해 실행시간을 예측 가능한 상한으로 묶는다.
    """

    def __init__(self, threshold=CIRCUIT_BREAKER_THRESHOLD):
        self._lock = threading.Lock()
        self._failures = 0
        self._tripped = False
        self.threshold = threshold

    def record_success(self):
        with self._lock:
            self._failures = 0

    def record_failure(self):
        with self._lock:
            self._failures += 1
            if self._failures >= self.threshold:
                self._tripped = True

    def is_tripped(self):
        with self._lock:
            return self._tripped

    def failure_count(self):
        with self._lock:
            return self._failures


def _grid_key(site):
    return (int(site["nx"]), int(site["ny"]))


def collect_site_data(
    sites,
    api_key=None,
    breaker=None,
    max_workers=MAX_WORKERS,
    current_fetcher=None,
    forecast_fetcher=None,
    executor=None,
):
    """현장별 실황·예보를 병렬 수집한다.

    동일 (nx, ny) 격자의 현장은 API 호출을 1번만 하고 결과를 공유한다.
    breaker가 트립되면 이후 격자는 재시도 없이 1회만 시도한다.

    반환 형식은 기존 `main.collect_site_data`와 동일하다.
    현장 순서는 입력 순서를 그대로 보존한다.
    """
    from src import settings as config

    if api_key is None:
        api_key = config.KMA_API_KEY
    if breaker is None:
        breaker = CircuitBreaker()
    if current_fetcher is None:
        from src.kma_client import get_current_weather

        current_fetcher = get_current_weather
    if forecast_fetcher is None:
        from src.kma_client import get_forecast

        forecast_fetcher = get_forecast

    # 격자별로 현장을 묶는다 (딕셔너리 삽입 순서 유지 → 결정론적 로그).
    grids = {}
    for site in sites:
        grids.setdefault(_grid_key(site), []).append(site)

    def fetch_grid(grid):
        nx, ny = grid
        retries = 1 if breaker.is_tripped() else 3

        try:
            current = current_fetcher(api_key, nx, ny, retries=retries, breaker=breaker)
        except CONNECTION_ERRORS as e:
            print(f"[실황 오류/연결] 격자 ({nx},{ny}): {type(e).__name__}")
            breaker.record_failure()
            current = None
        except Exception as e:
            print(f"[실황 오류] 격자 ({nx},{ny}): {e}")
            current = None

        # 앞선 실황 호출에서 회로가 트립됐으면 예보는 즉시 재시도 없이 시도.
        retries = 1 if breaker.is_tripped() else 3
        try:
            forecast = forecast_fetcher(api_key, nx, ny, retries=retries, breaker=breaker)
        except CONNECTION_ERRORS as e:
            print(f"[예보 오류/연결] 격자 ({nx},{ny}): {type(e).__name__}")
            breaker.record_failure()
            forecast = []
        except Exception as e:
            print(f"[예보 오류] 격자 ({nx},{ny}): {e}")
            forecast = []

        return grid, current, forecast

    grid_results = {}
    own_executor = executor is None
    if own_executor:
        workers = max(1, min(max_workers, len(grids)))
        executor = ThreadPoolExecutor(max_workers=workers)
    try:
        futures = [executor.submit(fetch_grid, grid) for grid in grids]
        for fut in as_completed(futures):
            grid, current, forecast = fut.result()
            grid_results[grid] = (current, forecast)
    finally:
        if own_executor:
            executor.shutdown(wait=True)

    if breaker.is_tripped():
        print(
            f"[전면 장애 감지] 연결 실패 누적 {breaker.failure_count()}회 → 이후 호출은 "
            "재시도 없이 조기 종료합니다."
        )

    results = []
    for site in sites:
        current, forecast = grid_results.get(_grid_key(site), (None, []))
        judgment = alert_rules.judge(current) if current is not None else alert_rules.unknown_judgment()
        legal_signals = evaluate_legal_signals(site, current or {})
        results.append(
            {
                "site": site,
                "current": current,
                "forecast": forecast,
                "judgment": judgment,
                "legal_signals": legal_signals,
                "legal_status": highest_legal_status(legal_signals),
            }
        )
        if current is not None:
            print(
                f"[실황 수집] {site['site_name']}: 기온 {current.get('T1H', '?')}°C ({judgment['level']})"
            )
        print(f"[예보 수집] {site['site_name']}: {len(forecast)}건")

    return results


def collect_mid_forecasts(
    sites,
    api_key=None,
    breaker=None,
    land_fetcher=None,
    ta_fetcher=None,
):
    """중기예보(3~10일)를 지역코드별로 한 번씩만 조회한 뒤 현장별로 매핑.

    breaker가 트립되면 이후 지역코드는 재시도 없이 1회만 시도한다. 지역코드가 같은
    현장들은 캐시에서 즉시 재사용된다.
    """
    from src import settings as config

    if api_key is None:
        api_key = config.KMA_API_KEY
    if breaker is None:
        breaker = CircuitBreaker()
    if land_fetcher is None:
        land_fetcher = get_mid_land_forecast
    if ta_fetcher is None:
        ta_fetcher = get_mid_temperature

    land_cache, ta_cache = {}, {}
    result = {}

    for site in sites:
        land_reg, ta_reg, _, _ = resolve_region_codes(
            site["lat"],
            site["lon"],
            land_override=site.get("mid_land_override"),
            ta_override=site.get("mid_ta_override"),
        )

        mid_timeout = 5
        mid_retries = 1 if breaker.is_tripped() else 2

        if land_reg not in land_cache:
            try:
                land_cache[land_reg] = land_fetcher(
                    api_key, land_reg, timeout=mid_timeout, retries=mid_retries, breaker=breaker,
                )
            except CONNECTION_ERRORS as e:
                print(f"[중기 육상 오류/연결] {land_reg}: {type(e).__name__}")
                breaker.record_failure()
                land_cache[land_reg] = {}
            except Exception as e:
                print(f"[중기 육상 오류] {land_reg}: {e}")
                land_cache[land_reg] = {}

        if ta_reg not in ta_cache:
            try:
                ta_cache[ta_reg] = ta_fetcher(
                    api_key, ta_reg, timeout=mid_timeout, retries=mid_retries, breaker=breaker,
                )
            except CONNECTION_ERRORS as e:
                print(f"[중기 기온 오류/연결] {ta_reg}: {type(e).__name__}")
                breaker.record_failure()
                ta_cache[ta_reg] = {}
            except Exception as e:
                print(f"[중기 기온 오류] {ta_reg}: {e}")
                ta_cache[ta_reg] = {}

        land, temp = land_cache[land_reg], ta_cache[ta_reg]
        if land or temp:
            result[site["site_name"]] = combine_forecast(land, temp)
        else:
            result[site["site_name"]] = []

    return result

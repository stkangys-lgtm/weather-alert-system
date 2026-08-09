"""기상청 공공데이터포털 API 클라이언트.

사용 API (단기예보 ((구)동네예보) 2.0):
- 초단기실황조회 (getUltraSrtNcst): 현재 시각 기준 실황 (기온, 강수, 풍속 등)
- 단기예보조회 (getVilageFcst): 최대 3일 이내 예보
"""

from datetime import datetime, timedelta

import requests

BASE_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"

PTY_CODE = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈", "5": "빗방울", "6": "빗방울눈날림", "7": "눈날림"}
SKY_CODE = {"1": "맑음", "3": "구름많음", "4": "흐림"}

_VFCST_BASE_HOURS = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]


def _request(endpoint, api_key, params, timeout=10):
    url = f"{BASE_URL}/{endpoint}"
    query = {
        "serviceKey": api_key,
        "dataType": "JSON",
        "numOfRows": "1000",
        "pageNo": "1",
        **params,
    }
    response = requests.get(url, params=query, timeout=timeout)
    response.raise_for_status()
    body = response.json()["response"]

    header = body["header"]
    if header["resultCode"] != "00":
        raise RuntimeError(f"기상청 API 오류: {header['resultCode']} {header['resultMsg']}")

    return body["body"]["items"]["item"]


def _latest_ncst_base_time(now=None):
    # 초단기실황은 매시 40분에 갱신되므로, 그 이전 요청이면 직전 시각 자료를 써야 함
    now = now or datetime.now()
    if now.minute < 40:
        now -= timedelta(hours=1)
    return now.strftime("%Y%m%d"), now.strftime("%H00")


def _latest_vfcst_base_time(now=None):
    # 단기예보는 하루 8회(3시간 간격) 발표되고, 발표 10분 뒤부터 조회 가능
    now = now or datetime.now()
    candidates = [
        now.replace(hour=int(h[:2]), minute=10, second=0, microsecond=0)
        for h in _VFCST_BASE_HOURS
    ]
    passed = [c for c in candidates if c <= now]
    if passed:
        latest = max(passed)
        return latest.strftime("%Y%m%d"), latest.strftime("%H00")

    # 자정~02:10 사이: 전날 23시 발표 자료를 사용
    yesterday = now - timedelta(days=1)
    return yesterday.strftime("%Y%m%d"), "2300"


def get_current_weather(api_key, nx, ny, now=None):
    """초단기실황 조회. {'T1H': 기온, 'RN1': 강수량, 'REH': 습도, 'WSD': 풍속, 'PTY': 강수형태, ...} 반환."""
    base_date, base_time = _latest_ncst_base_time(now)
    items = _request(
        "getUltraSrtNcst",
        api_key,
        {"base_date": base_date, "base_time": base_time, "nx": nx, "ny": ny},
    )

    result = {"base_date": base_date, "base_time": base_time}
    for item in items:
        category = item["category"]
        value = item["obsrValue"]
        if category == "PTY":
            value = PTY_CODE.get(value, value)
        result[category] = value
    return result


def get_forecast(api_key, nx, ny, now=None):
    """단기예보 조회. 시각별 예보 리스트를 시간순으로 반환.

    각 항목: {'fcst_date', 'fcst_time', 'TMP'(기온), 'POP'(강수확률), 'SKY'(하늘상태), 'PTY'(강수형태), ...}
    """
    base_date, base_time = _latest_vfcst_base_time(now)
    items = _request(
        "getVilageFcst",
        api_key,
        {"base_date": base_date, "base_time": base_time, "nx": nx, "ny": ny},
    )

    by_time = {}
    for item in items:
        key = (item["fcstDate"], item["fcstTime"])
        entry = by_time.setdefault(key, {"fcst_date": item["fcstDate"], "fcst_time": item["fcstTime"]})
        category = item["category"]
        value = item["fcstValue"]
        if category == "SKY":
            value = SKY_CODE.get(value, value)
        elif category == "PTY":
            value = PTY_CODE.get(value, value)
        entry[category] = value

    return sorted(by_time.values(), key=lambda e: (e["fcst_date"], e["fcst_time"]))

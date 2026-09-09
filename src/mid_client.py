"""기상청 중기예보 조회 API 클라이언트 (3~10일 예보).

사용 API:
- getMidLandFcst: 광역 육상 예보(하늘상태, 강수확률) - regId 광역코드
- getMidTa: 시군 기온 예보(최저/최고 기온) - regId 시군코드

발표시각(tmFc)은 매일 06:00, 18:00 두 번. 발표 후 약 30분 뒤부터 조회 가능.
"""

import time
from datetime import datetime, timedelta

import requests

BASE_URL = "https://apis.data.go.kr/1360000/MidFcstInfoService"

RETRY_COUNT = 3
RETRY_BACKOFF_SEC = 2


def _latest_tmfc(now=None):
    """중기예보 최신 발표시각(YYYYMMDDHHMM) 반환. 06/18시 발표, 30분 뒤부터 조회 가능."""
    now = now or datetime.now()
    threshold = now - timedelta(minutes=30)
    if threshold.hour >= 18:
        return threshold.strftime("%Y%m%d") + "1800"
    if threshold.hour >= 6:
        return threshold.strftime("%Y%m%d") + "0600"
    yesterday = threshold - timedelta(days=1)
    return yesterday.strftime("%Y%m%d") + "1800"


def _request(endpoint, api_key, params, timeout=10, retries=RETRY_COUNT):
    url = f"{BASE_URL}/{endpoint}"
    query = {
        "serviceKey": api_key,
        "dataType": "JSON",
        "numOfRows": "100",
        "pageNo": "1",
        **params,
    }
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=query, timeout=timeout)
            response.raise_for_status()
            body = response.json()["response"]
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_error = e
            if attempt < retries:
                time.sleep(RETRY_BACKOFF_SEC * attempt)
            continue
    else:
        raise last_error

    header = body["header"]
    if header["resultCode"] != "00":
        raise RuntimeError(f"기상청 중기예보 API 오류: {header['resultCode']} {header['resultMsg']}")

    return body["body"]["items"]["item"]


def get_mid_land_forecast(api_key, land_reg_id, now=None, timeout=10, retries=RETRY_COUNT):
    """광역 육상 중기예보. 3~10일후의 오전/오후 하늘상태와 강수확률 반환.

    반환 dict의 키 예: 'wf3Am'(3일후 오전 하늘상태), 'wf3Pm', 'rnSt3Am'(3일후 오전 강수확률), 'rnSt10' 등.
    """
    tm_fc = _latest_tmfc(now)
    items = _request(
        "getMidLandFcst",
        api_key,
        {"regId": land_reg_id, "tmFc": tm_fc},
        timeout=timeout,
        retries=retries,
    )
    return items[0] if items else {}


def get_mid_temperature(api_key, ta_reg_id, now=None, timeout=10, retries=RETRY_COUNT):
    """시군 기온 중기예보. 3~10일후의 최저/최고 기온 반환.

    반환 dict의 키 예: 'taMin3', 'taMax3', 'taMin10', 'taMax10' 등.
    """
    tm_fc = _latest_tmfc(now)
    items = _request(
        "getMidTa",
        api_key,
        {"regId": ta_reg_id, "tmFc": tm_fc},
        timeout=timeout,
        retries=retries,
    )
    return items[0] if items else {}


def combine_forecast(land_data, temp_data, base_date=None):
    """육상 + 기온 예보를 날짜별 예보 리스트로 결합.

    반환: [{"date": "YYYY-MM-DD", "day_offset": 3~10, "sky_am", "sky_pm", "pop_am", "pop_pm", "ta_min", "ta_max"}, ...]
    base_date: 오늘 날짜 (datetime.date). None이면 today() 사용.
    """
    if base_date is None:
        base_date = datetime.now().date()

    combined = []
    for offset in range(3, 11):
        entry = {
            "day_offset": offset,
            "date": (base_date + timedelta(days=offset)).strftime("%Y-%m-%d"),
        }
        # 3~7일은 오전/오후 분리, 8~10일은 통합 값 하나만 있음
        if offset <= 7:
            entry["sky_am"] = land_data.get(f"wf{offset}Am")
            entry["sky_pm"] = land_data.get(f"wf{offset}Pm")
            entry["pop_am"] = land_data.get(f"rnSt{offset}Am")
            entry["pop_pm"] = land_data.get(f"rnSt{offset}Pm")
        else:
            entry["sky_am"] = entry["sky_pm"] = land_data.get(f"wf{offset}")
            entry["pop_am"] = entry["pop_pm"] = land_data.get(f"rnSt{offset}")

        entry["ta_min"] = temp_data.get(f"taMin{offset}")
        entry["ta_max"] = temp_data.get(f"taMax{offset}")
        combined.append(entry)

    return combined

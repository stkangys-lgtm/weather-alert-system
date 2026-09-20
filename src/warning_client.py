"""기상청 공식 기상특보를 한 번 조회해 현장별로 배분한다.

공식 특보와 자체 수치 기반 선제신호가 섞이지 않도록 별도 자료구조로 유지한다.
현장별 ``warning_regions``/``warning_provinces`` 설정을 우선 사용하며, 현재 운영
현장은 기존 위치에 맞춘 기본 행정구역 매핑을 제공한다.
"""

from __future__ import annotations

import re
import time

import requests


BASE_URL = "https://apis.data.go.kr/1360000/WthrWrnInfoService"
RETRY_COUNT = 3
RETRY_BACKOFF_SEC = 2

PROVINCE_NAMES = {
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원도",
    "강원특별자치도", "충청북도", "충청남도", "전라북도", "전북특별자치도",
    "전라남도", "경상북도", "경상남도", "제주도", "제주특별자치도",
}

# 설정에 warning_regions가 아직 없는 현재 운영 현장의 안전한 기본값이다.
# KMA 특보문에는 시·군 이름이 축약되어 나올 수 있어 정식명과 축약명을 함께 둔다.
KNOWN_SITE_REGIONS = {
    "오리온 진천신공장": (["진천군", "진천"], ["충청북도"]),
    "오리온 진천 기숙사": (["진천군", "진천"], ["충청북도"]),
    "연희·연남동 공공주택": (["서대문구", "서울서북권"], ["서울", "서울특별시"]),
    "청정고원 스포츠센터": (["태백시", "태백"], ["강원도", "강원특별자치도"]),
    "EL충주 버티포트": (["충주시", "충주"], ["충청북도"]),
    "LX 논현 업무시설": (["강남구", "서울동남권"], ["서울", "서울특별시"]),
    "군포복합개발": (["군포시", "군포"], ["경기도"]),
    "오리온수협 목포 김공장": (["목포시", "목포"], ["전라남도"]),
    "렉서스 동탄 네트워크": (["화성시", "화성", "동탄"], ["경기도"]),
    "화천군부대 시설공사": (["화천군", "화천"], ["강원도", "강원특별자치도"]),
    "반얀트리호텔 근생동": (["중구", "서울도심권"], ["서울", "서울특별시"]),
    "포항~안동2 국도건설공사": (
        ["안동시", "안동", "의성군", "의성", "청송군", "청송"], ["경상북도"]
    ),
    "시흥능곡 주변도로": (["시흥시", "시흥"], ["경기도"]),
    "뇌죽천 하천재해예방": (["곡성군", "곡성"], ["전라남도"]),
    "산솔면 하수처리장": (["영월군", "영월"], ["강원도", "강원특별자치도"]),
    "단월정수장 시설공사": (["충주시", "충주"], ["충청북도"]),
    "후포 공공하수처리": (["울진군", "울진"], ["경상북도"]),
    "동해안 바닷가 자동차길": (["강릉시", "강릉"], ["강원도", "강원특별자치도"]),
    "풍각지구 정비사업": (["청도군", "청도"], ["경상북도"]),
    "영주 가흥정수장": (["영주시", "영주"], ["경상북도"]),
    "송산그린시티 용수공급시설": (["화성시", "화성", "송산"], ["경기도"]),
}


def _request(endpoint, api_key, params=None, timeout=10, retries=RETRY_COUNT):
    query = {
        "serviceKey": api_key,
        "dataType": "JSON",
        "numOfRows": "100",
        "pageNo": "1",
        **(params or {}),
    }
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(f"{BASE_URL}/{endpoint}", params=query, timeout=timeout)
            response.raise_for_status()
            payload = response.json()["response"]
            header = payload["header"]
            if header["resultCode"] not in ("00", "03"):
                raise RuntimeError(
                    f"기상청 특보 API 오류: {header['resultCode']} {header['resultMsg']}"
                )
            return payload.get("body") or {}
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(RETRY_BACKOFF_SEC * attempt)
    raise last_error


def _split_areas(value):
    """괄호 안 쉼표는 유지하고 최상위 쉼표만 구역 구분자로 사용한다."""
    areas, current, depth = [], [], 0
    for char in str(value or ""):
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        if char == "," and depth == 0:
            area = "".join(current).strip()
            if area:
                areas.append(area)
            current = []
        else:
            current.append(char)
    area = "".join(current).strip()
    if area:
        areas.append(area)
    return areas


def _phenomenon(title):
    return re.sub(r"(중대경보|경보|주의보)$", "", title).strip()


def parse_warning_status(text, status_kind="기상특보", announced_at=None, effective_at=None):
    """getPwnStatus의 t6/t7 문자열을 표시·비교 가능한 특보 목록으로 변환한다."""
    warnings = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line or line in ("o 없음", "없음"):
            continue
        match = re.match(r"^[o○]\s*([^:：]+)\s*[:：]\s*(.+)$", line)
        if not match:
            continue
        title = match.group(1).strip()
        areas = _split_areas(match.group(2))
        if not areas:
            continue
        if "중대경보" in title:
            level = "중대경보"
        elif "경보" in title:
            level = "경보"
        elif "주의보" in title:
            level = "주의보"
        else:
            level = status_kind
        warnings.append({
            "kind": status_kind,
            "title": title,
            "phenomenon": _phenomenon(title),
            "level": level,
            "areas": areas,
            "announced_at": str(announced_at or ""),
            "effective_at": str(effective_at or ""),
        })
    return warnings


def get_active_warnings(api_key, timeout=10, retries=RETRY_COUNT):
    """전국 최신 특보현황을 한 번 조회한다. 현재 특보와 예비특보를 함께 반환한다."""
    body = _request("getPwnStatus", api_key, timeout=timeout, retries=retries)
    items = (body.get("items") or {}).get("item") or []
    if isinstance(items, dict):
        items = [items]
    if not items:
        return []
    latest = max(items, key=lambda item: (str(item.get("tmFc", "")), str(item.get("tmSeq", ""))))
    common = {
        "announced_at": latest.get("tmFc"),
        "effective_at": latest.get("tmEf"),
    }
    return (
        parse_warning_status(latest.get("t6"), "기상특보", **common)
        + parse_warning_status(latest.get("t7"), "예비특보", **common)
    )


def _as_list(value):
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if item]


def site_warning_regions(site):
    """현장의 세부 행정구역과 광역구역 별칭을 반환한다."""
    configured = _as_list(site.get("warning_regions"))
    configured_provinces = _as_list(site.get("warning_provinces"))
    local = [value for value in configured if value not in PROVINCE_NAMES]
    broad = configured_provinces + [value for value in configured if value in PROVINCE_NAMES]
    if not local and not broad:
        known = KNOWN_SITE_REGIONS.get(site.get("site_name"), ([], []))
        local, broad = list(known[0]), list(known[1])
    return list(dict.fromkeys(local)), list(dict.fromkeys(broad))


def _is_marine_area(area):
    return any(word in area for word in ("바다", "해역", "연안", "해상"))


def _matches_area(area, local, broad):
    compact = re.sub(r"\s+", "", area)
    if any(re.sub(r"\s+", "", alias) in compact for alias in local):
        return True
    # 광역명은 '경기도(일부 시군)' 같은 구역에 무조건 매칭하면 오탐이 생긴다.
    # 세부 괄호가 없는 도·광역시 전체 특보에만 보조적으로 사용한다.
    return "(" not in compact and any(compact == re.sub(r"\s+", "", alias) for alias in broad)


def match_warnings_to_sites(sites, warnings):
    """각 현장에 해당하는 육상 기상특보만 연결한다."""
    result = {}
    for site in sites:
        local, broad = site_warning_regions(site)
        matched = []
        for warning in warnings:
            areas = [
                area for area in warning.get("areas", [])
                if (site.get("include_marine_warnings") or not _is_marine_area(area))
                and _matches_area(area, local, broad)
            ]
            if areas:
                matched.append({**warning, "matched_areas": areas})
        result[site["site_name"]] = matched
    return result


def warning_display_level(warnings):
    levels = {warning.get("level") for warning in warnings or []}
    if levels & {"중대경보", "경보"}:
        return "경보"
    if "주의보" in levels:
        return "주의"
    return None

"""기상청 API 허브의 현재 기상특보를 조회하고 현장에 매칭한다.

단기예보 API(data.go.kr)와 달리 API Hub 전용 인증키가 필요하다. 키가 없으면
호출하지 않으며, 기존 기상 수집 흐름에는 영향을 주지 않는다.
"""

import csv
import io
import re

import requests


# 사용 승인된 「특보현황 조회」 엔드포인트.
WARNING_URL = "https://apihub.kma.go.kr/api/typ01/url/wrn_now_data.php"

WARNING_TYPES = {
    "W": "강풍", "R": "호우", "C": "한파", "D": "건조", "O": "해일",
    "N": "지진해일", "V": "풍랑", "T": "태풍", "S": "대설", "Y": "황사",
    "H": "폭염", "F": "안개", "K": "열대야",
}
WARNING_LEVELS = {"1": "예비", "2": "주의보", "3": "경보"}
WARNING_LEVEL_CODES = {value: key for key, value in WARNING_LEVELS.items()}
COMMAND_CODES = {
    "발표": "1", "대치": "2", "해제": "3", "대치해제": "4",
    "연장": "5", "변경": "6", "변경해제": "7",
}
CANCEL_COMMANDS = {"3", "4", "7"}


def _decode_response(content):
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def parse_warning_csv(text):
    """API Hub CSV 텍스트를 화면 표시용 dict 목록으로 변환한다."""
    warnings = []
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        row = [cell.strip() for cell in row]
        if not row[0] or row[0].startswith("#") or row[0].upper() == "REG_UP":
            continue
        if len(row) < 9:
            continue

        reg_up, reg_up_ko, reg_id, reg_ko, tm_fc, tm_ef, wrn, lvl, cmd = row[:9]
        normalized_cmd = COMMAND_CODES.get(cmd, cmd)
        if normalized_cmd in CANCEL_COMMANDS or cmd.endswith("해제"):
            continue
        warning_type = WARNING_TYPES.get(wrn, wrn or "기상")
        warning_level = WARNING_LEVELS.get(lvl, lvl or "발표")
        normalized_level = WARNING_LEVEL_CODES.get(warning_level, lvl)
        warnings.append({
            "source": "기상청 공식 특보",
            "parent_region_code": reg_up,
            "parent_region_name": reg_up_ko,
            "region_code": reg_id,
            "region_name": reg_ko,
            "issued_at": tm_fc,
            "effective_at": tm_ef,
            "type_code": wrn,
            "warning_type": warning_type,
            "level_code": normalized_level,
            "warning_level": warning_level,
            "command_code": normalized_cmd,
        })
    return warnings


def get_current_warnings(api_key, timeout=10, request_get=requests.get):
    """현재 발효 중인 기상특보를 조회한다. API Hub 키가 없으면 빈 목록을 반환한다."""
    if not api_key:
        return []
    response = request_get(
        WARNING_URL,
        params={"fe": "f", "tm": "", "disp": "0", "help": "0", "authKey": api_key},
        timeout=timeout,
    )
    response.raise_for_status()
    text = _decode_response(response.content)
    if "Authentication" in text or "authKey" in text and not any(ch == "," for ch in text):
        raise RuntimeError("기상청 API Hub 인증에 실패했습니다")
    return parse_warning_csv(text)


def _values(value):
    if value is None:
        return []
    return value if isinstance(value, (list, tuple, set)) else [value]


def _normalized(value):
    return re.sub(r"[^0-9A-Za-z가-힣]", "", str(value or "")).lower()


def _region_name_variants(value):
    normalized = _normalized(value)
    if not normalized:
        return set()
    shortened = re.sub(r"(특별자치시|특별자치도|특별시|광역시|자치시|자치도|시|군|구)$", "", normalized)
    return {name for name in (normalized, shortened) if len(name) >= 2}


def warning_matches_site(warning, site):
    """명시적 구역코드/키워드를 우선하고, 마지막으로 현장명 포함 여부를 본다."""
    codes = _values(site.get("warning_region_codes") or site.get("warning_region_code"))
    if codes:
        return warning.get("region_code") in {str(code) for code in codes}

    region_text = _normalized(
        f"{warning.get('parent_region_name', '')} {warning.get('region_name', '')}"
    )
    keywords = _values(site.get("warning_region_keywords") or site.get("warning_region_keyword"))
    if keywords:
        return any(_normalized(keyword) in region_text for keyword in keywords if _normalized(keyword))

    site_name = _normalized(site.get("site_name"))
    candidates = _region_name_variants(warning.get("region_name"))
    candidates.update(_region_name_variants(warning.get("parent_region_name")))
    return any(candidate and len(candidate) >= 2 and candidate in site_name for candidate in candidates)


def match_warnings_to_sites(warnings, sites):
    """{site_name: [warning, ...]} 형태로 공식 특보를 현장별 매칭한다."""
    return {
        site["site_name"]: [warning for warning in warnings if warning_matches_site(warning, site)]
        for site in sites
    }

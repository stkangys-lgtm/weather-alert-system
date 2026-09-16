"""본사 공지와 현장 확인을 위한 기상 위험 신호 판정 로직.

격자 예보·실황은 현장 계측값이나 법정 작업중지 판단을 대신하지 않는다. 따라서 자체 계산값은
항상 ``시스템 선제알림``으로 표시하고, API Hub에서 받은 ``기상청 공식 특보``와 구분한다.
"""

from src.feels_like import compute_feels_like

WIND_CAUTION = 10.0   # m/s, 강풍 영향을 받는 작업·시설물 선제 점검 신호
WIND_WARNING = 15.0   # m/s, 매우 강한 바람 선제 점검 신호

RAIN_CAUTION = 5.0    # mm/h, 일반 현장용 강수 선제 점검 신호
RAIN_WARNING = 15.0   # mm/h, 강한 비 선제 점검 신호

HEAT_CAUTION = 31.0   # °C 추정 체감온도, 온열질환 예방조치 강화 구간
HEAT_WARNING = 33.0   # °C 추정 체감온도, 매 2시간 이내 20분 이상 휴식 확인 구간

LEVEL_NORMAL, LEVEL_CAUTION, LEVEL_WARNING = "정상", "주의", "경보"
LEVEL_UNKNOWN = "데이터없음"  # 기상청 API 조회 실패 등으로 실황을 못 받아온 경우. "정상"으로 오인되지 않도록 별도 레벨로 취급.

CATEGORY_WIND, CATEGORY_RAIN, CATEGORY_HEAT = "강풍", "호우", "폭염"
CATEGORY_COLD, CATEGORY_SNOW, CATEGORY_TYPHOON = "한파", "대설", "태풍"
CATEGORY_DRY, CATEGORY_DUST, CATEGORY_MARINE = "건조", "황사", "해상기상"
CATEGORY_OTHER = "기타기상"

# 공고문의 【안전관리 유의사항】에 들어갈 항목. 현장에서 실제 쓰던 양식을 참고해 구성.
ACTION_ITEMS = {
    CATEGORY_WIND: [
        "강풍 대비 가설물·자재 등 결속 확인",
        "타워크레인 등 고소작업 장비 점검 및 작업제한 여부 확인",
        "감전·전도 사고 예방 점검",
    ],
    CATEGORY_RAIN: [
        "배수로 및 침사지 주변 이물질 정비",
        "토사 유실 우려 구간 덮개 보양",
        "침수 우려 구역 내 장비 안전지대 이동",
    ],
    CATEGORY_HEAT: [
        "체감온도 33°C 이상 시 매 2시간 이내 20분 이상 휴식 확인",
        "높은 습도로 체감온도가 함께 상승할 수 있어 각별한 주의 요망",
        "폭염안전 5대 기본수칙 준수",
    ],
    CATEGORY_COLD: ["보온시설·한랭질환 예방조치 확인", "결빙 구간과 동파 우려 설비 점검"],
    CATEGORY_SNOW: ["제설자재·장비 확보 및 적설 취약구조물 점검", "통행로 미끄럼·낙상 방지조치 확인"],
    CATEGORY_TYPHOON: ["가설물·양중장비·자재 결속 상태 재점검", "침수·정전·대피계획 및 비상연락망 확인"],
    CATEGORY_DRY: ["용접·용단 등 화기작업과 임시소방시설 점검", "가연물 분리 및 산불 유입 위험 확인"],
    CATEGORY_DUST: ["옥외작업자 호흡기 보호 및 실내 대피공간 확인", "시야 저하에 따른 장비 운행 주의"],
    CATEGORY_MARINE: ["해안·항만 작업 및 선박 운항계획 재확인", "월파·강풍 취약구역 출입 통제 검토"],
    CATEGORY_OTHER: ["기상청 특보 상세내용과 현장 여건을 확인", "취약 작업·시설물에 필요한 예방조치 검토"],
}
CATEGORY_HEADING = {
    CATEGORY_WIND: "강풍 대비", CATEGORY_RAIN: "호우 대비", CATEGORY_HEAT: "온열질환 유의",
    CATEGORY_COLD: "한파 대비", CATEGORY_SNOW: "대설 대비", CATEGORY_TYPHOON: "태풍 대비",
    CATEGORY_DRY: "건조·화재 대비", CATEGORY_DUST: "황사 대비", CATEGORY_MARINE: "해상기상 대비",
    CATEGORY_OTHER: "기상특보 대비",
}
CATEGORY_ORDER = [
    CATEGORY_TYPHOON, CATEGORY_WIND, CATEGORY_RAIN, CATEGORY_HEAT, CATEGORY_COLD,
    CATEGORY_SNOW, CATEGORY_DRY, CATEGORY_DUST, CATEGORY_MARINE, CATEGORY_OTHER,
]

OFFICIAL_CATEGORY = {
    "강풍": CATEGORY_WIND, "호우": CATEGORY_RAIN, "폭염": CATEGORY_HEAT,
    "한파": CATEGORY_COLD, "대설": CATEGORY_SNOW, "태풍": CATEGORY_TYPHOON,
    "건조": CATEGORY_DRY, "황사": CATEGORY_DUST, "풍랑": CATEGORY_MARINE,
    "해일": CATEGORY_MARINE, "지진해일": CATEGORY_MARINE,
}


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def judge(weather):
    """초단기실황 데이터(dict)를 받아 현장의 이상기상 판정 결과를 반환한다.

    반환: {"level": "정상"|"주의"|"경보", "reasons": [str, ...]}
    reasons는 경보/주의를 유발한 항목 설명 리스트 (없으면 빈 리스트).
    """
    wsd = _to_float(weather.get("WSD"))
    rn1 = _to_float(weather.get("RN1"))
    feels = compute_feels_like(weather.get("T1H"), weather.get("REH"), weather.get("WSD"))

    triggered = []  # [(level, category, reason), ...]

    if wsd is not None:
        if wsd >= WIND_WARNING:
            triggered.append((LEVEL_WARNING, CATEGORY_WIND, f"시스템 선제알림: 매우 강한 바람 (풍속 {wsd:.1f}m/s)"))
        elif wsd >= WIND_CAUTION:
            triggered.append((LEVEL_CAUTION, CATEGORY_WIND, f"시스템 선제알림: 강한 바람 (풍속 {wsd:.1f}m/s)"))

    if rn1 is not None:
        if rn1 >= RAIN_WARNING:
            triggered.append((LEVEL_WARNING, CATEGORY_RAIN, f"시스템 선제알림: 강한 비 (시간당 {rn1:.1f}mm)"))
        elif rn1 >= RAIN_CAUTION:
            triggered.append((LEVEL_CAUTION, CATEGORY_RAIN, f"시스템 선제알림: 비 유의 (시간당 {rn1:.1f}mm)"))

    if feels is not None:
        if feels >= HEAT_WARNING:
            triggered.append((LEVEL_WARNING, CATEGORY_HEAT, f"시스템 선제알림: 온열질환 위험 (추정 체감 {feels:.1f}°C)"))
        elif feels >= HEAT_CAUTION:
            triggered.append((LEVEL_CAUTION, CATEGORY_HEAT, f"시스템 선제알림: 고온 유의 (추정 체감 {feels:.1f}°C)"))

    severity = {LEVEL_NORMAL: 0, LEVEL_CAUTION: 1, LEVEL_WARNING: 2}
    level = max((lv for lv, _, _ in triggered), key=lambda lv: severity[lv], default=LEVEL_NORMAL)
    reasons = [reason for _, _, reason in triggered]
    categories = [cat for _, cat, _ in triggered]

    return {"level": level, "reasons": reasons, "categories": categories}


def apply_official_warnings(judgment, warnings):
    """공식 특보를 자체 판정 결과에 합치되 출처를 명확히 표시한다."""
    result = {
        "level": judgment["level"],
        "reasons": list(judgment.get("reasons") or []),
        "categories": list(judgment.get("categories") or []),
        "official_warnings": list(warnings or []),
    }
    severity = {LEVEL_UNKNOWN: -1, LEVEL_NORMAL: 0, LEVEL_CAUTION: 1, LEVEL_WARNING: 2}
    for warning in warnings or []:
        official_level = LEVEL_WARNING if str(warning.get("level_code")) == "3" else LEVEL_CAUTION
        if severity[official_level] > severity.get(result["level"], -1):
            result["level"] = official_level
        warning_type = warning.get("warning_type") or "기상"
        warning_level = warning.get("warning_level") or "특보"
        region = warning.get("region_name") or warning.get("parent_region_name") or "해당 지역"
        reason = f"기상청 공식 특보: {warning_type}{warning_level} ({region})"
        if reason not in result["reasons"]:
            result["reasons"].append(reason)
        category = OFFICIAL_CATEGORY.get(warning_type, CATEGORY_OTHER)
        if category not in result["categories"]:
            result["categories"].append(category)
    return result


def unknown_judgment():
    """실황 데이터를 가져오지 못했을 때 사용하는 판정 결과. "정상"으로 취급하지 않는다."""
    return {"level": LEVEL_UNKNOWN, "reasons": ["기상 데이터 수신 실패"], "categories": []}


def build_announcement(now_str, site_results):
    """단톡방 등에 공유할 수 있는 공고문 텍스트를 생성한다. 이상기상 유무와 관계없이 매번 생성한다.

    site_results: [{"site_name", "level", "reasons", "categories", "events"(선택)}, ...]
    events: [{"date": "9/10(목)", "kind": "폭염"|"호우"|"강풍"|...", "detail": "..."}, ...]
    """
    affected = [r for r in site_results if r["level"] not in (LEVEL_NORMAL, LEVEL_UNKNOWN)]
    unknown = [r for r in site_results if r["level"] == LEVEL_UNKNOWN]
    # 향후 예보에서 위험 이벤트가 있는 현장 (오늘/내일 것은 제외)
    future_events_by_site = {}
    for r in site_results:
        for ev in r.get("events") or []:
            future_events_by_site.setdefault(r["site_name"], []).append(ev)

    # 카테고리별로 해당 현장명을 모은다 (표시 순서는 CATEGORY_ORDER 고정).
    sites_by_category = {cat: [] for cat in CATEGORY_ORDER}
    for r in affected:
        for cat in r["categories"]:
            if r["site_name"] not in sites_by_category[cat]:
                sites_by_category[cat].append(r["site_name"])

    lines = ["■ 공지드립니다.", "", f"{now_str} 기준 현장별 기상현황을 공유드립니다.", ""]

    if not affected:
        lines.append("현재 전 현장 특이 기상상황 없습니다.")
        if unknown:
            names = "、".join(r["site_name"] for r in unknown)
            lines.append(f"(단, {names}은(는) 기상 데이터 수신에 실패해 확인이 필요합니다.)")
        if future_events_by_site:
            lines.append("")
            lines.append("【향후 10일 예보 특이사항】")
            _append_future_events(lines, future_events_by_site)
        lines.append("")
        lines.append("감사합니다.")
        return "\n".join(lines)

    summary_parts = []
    for cat in CATEGORY_ORDER:
        sites = sites_by_category[cat]
        if sites:
            names = "、".join(sites[:3]) + (f" 외 {len(sites) - 3}개 현장" if len(sites) > 3 else "")
            summary_parts.append(f"{names}에 {cat} 관련 기상 위험 신호가 확인되고 있습니다.")
    lines.extend(summary_parts)
    lines.append("")
    lines.append("각 현장에서는 기상상황을 수시로 확인하시어 안전관리에 신경 써 주시기를 당부드립니다.")
    lines.append("")

    lines.append("【안전관리 유의사항】")
    lines.append("")
    section_no = 0
    for cat in CATEGORY_ORDER:
        sites = sites_by_category[cat]
        if not sites:
            continue
        section_no += 1
        lines.append(f"{_circled_number(section_no)} {CATEGORY_HEADING[cat]} (해당: {'、'.join(sites)})")
        for item in ACTION_ITEMS[cat]:
            lines.append(f"ㅇ {item}")
        lines.append("")

    lines.append("【현장별 상세】")
    for r in affected:
        reason_text = ", ".join(r["reasons"])
        lines.append(f"- {r['site_name']} : {reason_text}")
    for r in unknown:
        lines.append(f"- {r['site_name']} : 기상 데이터 수신 실패(확인 필요)")
    normal_count = len(site_results) - len(affected) - len(unknown)
    if normal_count:
        lines.append(f"- 그 외 {normal_count}개 현장 특이사항 없음")
    lines.append("")

    if future_events_by_site:
        lines.append("【향후 10일 예보 특이사항】")
        _append_future_events(lines, future_events_by_site)
        lines.append("")

    lines.append("감사합니다.")
    return "\n".join(lines)


def _append_future_events(lines, future_events_by_site):
    """지역별 향후 예보 이벤트를 공고문에 추가. 같은 (지역, 이벤트) 중복은 하나로 묶어 표시."""
    # 지역코드가 같은 현장은 이벤트도 같으므로, (날짜, 종류, detail)별로 현장들을 그룹핑
    by_event = {}
    for site_name, events in future_events_by_site.items():
        for ev in events:
            key = (ev["date"], ev["kind"], ev["detail"])
            by_event.setdefault(key, []).append(site_name)

    # 날짜순 정렬
    for (date, kind, detail), sites in sorted(by_event.items(), key=lambda x: x[0][0]):
        names = "、".join(sites[:3]) + (f" 외 {len(sites) - 3}개 현장" if len(sites) > 3 else "")
        lines.append(f"- {date} {kind} ({detail}) : {names}")


def _circled_number(n):
    circled = "①②③④⑤⑥⑦⑧⑨"
    return circled[n - 1] if 1 <= n <= len(circled) else f"{n}."

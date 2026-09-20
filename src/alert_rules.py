"""공공 기상자료를 이용한 사내 선제감시 판정 로직.

이 모듈의 주의/경보는 기상청이 발표한 특보나 법정 작업중지 판정이 아니다. 법적 조치는
``src.legal_rules``에서 작업 종류와 현장 실측값을 함께 대조한다.
"""

from src.feels_like import compute_feels_like

WIND_CAUTION = 10.0   # m/s, 사내 선제 확인 기준
WIND_WARNING = 15.0   # m/s, 사내 선제 경계 기준

RAIN_CAUTION = 1.0    # mm/h, 사내 선제 확인 기준(철골작업은 별도 법정 판정)
RAIN_WARNING = 15.0   # mm/h, 사내 선제 경계 기준

HEAT_CAUTION = 33.0   # °C, 인근 격자자료 기반 선제 확인 기준
HEAT_WARNING = 35.0   # °C, 인근 격자자료 기반 선제 경계 기준

LEVEL_NORMAL, LEVEL_CAUTION, LEVEL_WARNING = "정상", "주의", "경보"
LEVEL_UNKNOWN = "데이터없음"  # 기상청 API 조회 실패 등으로 실황을 못 받아온 경우. "정상"으로 오인되지 않도록 별도 레벨로 취급.

CATEGORY_WIND, CATEGORY_RAIN, CATEGORY_HEAT = "강풍", "호우", "폭염"

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
        "작업장소 체감온도 실측 및 법정 휴식기준 해당 여부 확인",
        "높은 습도로 체감온도가 함께 상승할 수 있어 각별한 주의 요망",
        "폭염안전 5대 기본수칙 준수",
    ],
}
CATEGORY_HEADING = {CATEGORY_WIND: "강풍 대비", CATEGORY_RAIN: "호우 대비", CATEGORY_HEAT: "온열질환 유의"}
CATEGORY_ORDER = [CATEGORY_WIND, CATEGORY_RAIN, CATEGORY_HEAT]


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
            triggered.append((LEVEL_WARNING, CATEGORY_WIND, f"시스템 선제알림(경계) · 풍속 {wsd:.1f}m/s"))
        elif wsd >= WIND_CAUTION:
            triggered.append((LEVEL_CAUTION, CATEGORY_WIND, f"시스템 선제알림(주의) · 풍속 {wsd:.1f}m/s"))

    if rn1 is not None:
        if rn1 >= RAIN_WARNING:
            triggered.append((LEVEL_WARNING, CATEGORY_RAIN, f"시스템 선제알림(경계) · 시간당 강우 {rn1:.1f}mm"))
        elif rn1 >= RAIN_CAUTION:
            triggered.append((LEVEL_CAUTION, CATEGORY_RAIN, f"시스템 선제알림(주의) · 시간당 강우 {rn1:.1f}mm"))

    if feels is not None:
        if feels >= HEAT_WARNING:
            triggered.append((LEVEL_WARNING, CATEGORY_HEAT, f"시스템 선제알림(경계) · 인근 격자 체감 {feels:.1f}°C"))
        elif feels >= HEAT_CAUTION:
            triggered.append((LEVEL_CAUTION, CATEGORY_HEAT, f"시스템 선제알림(주의) · 인근 격자 체감 {feels:.1f}°C"))

    severity = {LEVEL_NORMAL: 0, LEVEL_CAUTION: 1, LEVEL_WARNING: 2}
    level = max((lv for lv, _, _ in triggered), key=lambda lv: severity[lv], default=LEVEL_NORMAL)
    reasons = [reason for _, _, reason in triggered]
    categories = [cat for _, cat, _ in triggered]

    return {"level": level, "reasons": reasons, "categories": categories}


def apply_official_warnings(judgment, warnings):
    """이전 API Hub 특보 형식을 사용하는 호출부를 위한 호환 함수.

    신규 관제 화면은 공식 특보를 자체 선제판정과 분리해 표시하지만, 기존 연동부가
    이 함수를 호출해도 출처가 분명한 문구와 상향된 표시단계를 돌려준다.
    """
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
        if warning_type in CATEGORY_ORDER and warning_type not in result["categories"]:
            result["categories"].append(warning_type)
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
    legal_by_site = {}
    legal_gap_count = 0
    for result in site_results:
        actionable = []
        for signal in result.get("legal_signals") or []:
            if signal.get("status") == "데이터 부족":
                legal_gap_count += 1
            else:
                actionable.append(signal)
        if actionable:
            legal_by_site[result["site_name"]] = actionable
    official_by_site = {
        result["site_name"]: result.get("weather_warnings") or []
        for result in site_results
        if result.get("weather_warnings")
    }
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
        if official_by_site:
            lines.append("사내 선제감시 기준 도달 현장은 없으나, 아래 기상청 공식 특보가 발표 중입니다.")
        else:
            lines.append("현재 전 현장 특이 기상상황 없습니다.")
        if unknown:
            names = "、".join(r["site_name"] for r in unknown)
            lines.append(f"(단, {names}은(는) 기상 데이터 수신에 실패해 확인이 필요합니다.)")
        _append_official_warnings(lines, official_by_site)
        if future_events_by_site:
            lines.append("")
            lines.append("【향후 10일 예보 특이사항】")
            _append_future_events(lines, future_events_by_site)
        _append_legal_signals(lines, legal_by_site, legal_gap_count)
        lines.append("")
        lines.append("감사합니다.")
        return "\n".join(lines)

    summary_parts = []
    for cat in CATEGORY_ORDER:
        sites = sites_by_category[cat]
        if sites:
            names = "、".join(sites[:3]) + (f" 외 {len(sites) - 3}개 현장" if len(sites) > 3 else "")
            summary_parts.append(f"{names}에 {cat} 관련 사내 선제감시 기준 도달 상황이 확인되고 있습니다.")
    lines.extend(summary_parts)
    _append_official_warnings(lines, official_by_site)
    lines.append("")
    lines.append("본 안내는 기상청 특보 또는 법정 작업중지 확정이 아닙니다. 현장 작업과 실측값을 확인해 주십시오.")
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

    _append_legal_signals(lines, legal_by_site, legal_gap_count)

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


def _append_official_warnings(lines, warnings_by_site):
    if not warnings_by_site:
        return
    lines.extend(["", "【기상청 공식 특보】"])
    for site_name, warnings in warnings_by_site.items():
        for warning in warnings:
            areas = warning.get("matched_areas") or warning.get("areas") or []
            area_text = ", ".join(areas)
            prefix = "예비특보" if warning.get("kind") == "예비특보" else "기상특보"
            lines.append(f"- {site_name}: [{prefix}] {warning.get('title', '-')} ({area_text})")


def _append_legal_signals(lines, legal_by_site, legal_gap_count):
    if not legal_by_site and not legal_gap_count:
        return
    lines.append("")
    lines.append("【법정 조치·현장 확인】")
    for site_name, signals in legal_by_site.items():
        for signal in signals:
            lines.append(
                f"- {site_name}: [{signal['status']}] {signal['title']} "
                f"({signal['article']})"
            )
            for action in signal.get("actions") or []:
                lines.append(f"  ㅇ {action}")
    if legal_gap_count:
        lines.append(f"- 법적 판정에 필요한 작업정보·현장 실측값 미확보 {legal_gap_count}건")


def _circled_number(n):
    circled = "①②③④⑤⑥⑦⑧⑨"
    return circled[n - 1] if 1 <= n <= len(circled) else f"{n}."

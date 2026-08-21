"""이상기상 판정 로직.

산업안전보건기준에 관한 규칙 제37조(강풍시 작업중지) 및 온열질환 예방 가이드(고용노동부)를
참고한 2단계(주의/경보) 임계값. 다만 법령상 "순간풍속"을 기준으로 하나, 기상청 초단기실황
API는 1시간 평균풍속(WSD)만 제공하므로 이를 근사치로 사용한다. 실제 작업중지 여부는
현장에서 순간풍속계 등으로 별도 확인이 필요하며, 이 판정은 참고용 알림 기준이다.
"""

WIND_CAUTION = 10.0   # m/s, 타워크레인 설치/점검 등 고소작업 제한 권고
WIND_WARNING = 15.0   # m/s, 옥외작업 중지 권고

RAIN_CAUTION = 1.0    # mm/h, 비계 조립·해체 등 우천시 작업 제한 권고
RAIN_WARNING = 15.0   # mm/h, 강한 호우로 작업 중지 권고

HEAT_CAUTION = 33.0   # °C, 매시간 20분 휴식 등 온열질환 예방조치 권고
HEAT_WARNING = 35.0   # °C, 정오~17시 옥외작업 제한 권고

LEVEL_NORMAL, LEVEL_CAUTION, LEVEL_WARNING = "정상", "주의", "경보"

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
        "매시간 20분 휴식 등 온열질환 예방수칙 준수",
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
    t1h = _to_float(weather.get("T1H"))

    triggered = []  # [(level, category, reason), ...]

    if wsd is not None:
        if wsd >= WIND_WARNING:
            triggered.append((LEVEL_WARNING, CATEGORY_WIND, f"강풍 경보 (풍속 {wsd:.1f}m/s)"))
        elif wsd >= WIND_CAUTION:
            triggered.append((LEVEL_CAUTION, CATEGORY_WIND, f"강풍 주의 (풍속 {wsd:.1f}m/s)"))

    if rn1 is not None:
        if rn1 >= RAIN_WARNING:
            triggered.append((LEVEL_WARNING, CATEGORY_RAIN, f"호우 경보 (시간당 {rn1:.1f}mm)"))
        elif rn1 >= RAIN_CAUTION:
            triggered.append((LEVEL_CAUTION, CATEGORY_RAIN, f"호우 주의 (시간당 {rn1:.1f}mm)"))

    if t1h is not None:
        if t1h >= HEAT_WARNING:
            triggered.append((LEVEL_WARNING, CATEGORY_HEAT, f"폭염 경보 (기온 {t1h:.1f}°C)"))
        elif t1h >= HEAT_CAUTION:
            triggered.append((LEVEL_CAUTION, CATEGORY_HEAT, f"폭염 주의 (기온 {t1h:.1f}°C)"))

    severity = {LEVEL_NORMAL: 0, LEVEL_CAUTION: 1, LEVEL_WARNING: 2}
    level = max((lv for lv, _, _ in triggered), key=lambda lv: severity[lv], default=LEVEL_NORMAL)
    reasons = [reason for _, _, reason in triggered]
    categories = [cat for _, cat, _ in triggered]

    return {"level": level, "reasons": reasons, "categories": categories}


def build_announcement(now_str, site_results):
    """단톡방 등에 공유할 수 있는 공고문 텍스트를 생성한다. 이상기상 유무와 관계없이 매번 생성한다.

    site_results: [{"site_name", "manager", "manager_phone", "level", "reasons", "categories"}, ...]
    """
    affected = [r for r in site_results if r["level"] != LEVEL_NORMAL]

    # 카테고리별로 해당 현장명을 모은다 (표시 순서는 CATEGORY_ORDER 고정).
    sites_by_category = {cat: [] for cat in CATEGORY_ORDER}
    for r in affected:
        for cat in r["categories"]:
            if r["site_name"] not in sites_by_category[cat]:
                sites_by_category[cat].append(r["site_name"])

    lines = ["■ 공지드립니다.", "", f"{now_str} 기준 현장별 기상현황을 공유드립니다.", ""]

    if not affected:
        lines.append("현재 전 현장 특이 기상상황 없습니다.")
        lines.append("")
        lines.append("감사합니다.")
        return "\n".join(lines)

    summary_parts = []
    for cat in CATEGORY_ORDER:
        sites = sites_by_category[cat]
        if sites:
            names = "、".join(sites[:3]) + (f" 외 {len(sites) - 3}개 현장" if len(sites) > 3 else "")
            summary_parts.append(f"{names}에 {cat} 관련 기상특보 수준의 상황이 확인되고 있습니다.")
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
    normal_count = len(site_results) - len(affected)
    if normal_count:
        lines.append(f"- 그 외 {normal_count}개 현장 특이사항 없음")
    lines.append("")

    lines.append("감사합니다.")
    return "\n".join(lines)


def _circled_number(n):
    circled = "①②③④⑤⑥⑦⑧⑨"
    return circled[n - 1] if 1 <= n <= len(circled) else f"{n}."

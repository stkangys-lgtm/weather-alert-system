"""현장 작업정보와 측정값을 법정 기상안전 기준에 대조한다.

공공 기상자료만으로 법적 의무의 이행 여부를 확정하지 않는다. 특히 타워크레인은
순간풍속, 폭염작업은 작업장소 실측 체감온도가 필요하다. 필요한 값이나 작업상태가
없으면 ``현장 확인 필요`` 또는 ``데이터 부족``으로 반환한다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


STATUS_STOP = "법정 작업중지"
STATUS_ACTION = "법정 조치 이행 필요"
STATUS_VERIFY = "현장 확인 필요"
STATUS_DATA_GAP = "데이터 부족"

WORK_TOWER_INSTALL = "tower_crane_install"
WORK_TOWER_OPERATION = "tower_crane_operation"
WORK_STEEL = "steel_erection"
WORK_SCAFFOLD = "scaffold"
WORK_EXCAVATION = "excavation"
WORK_OUTDOOR_LIFT = "outdoor_lift"
WORK_OUTDOOR_HEAT = "outdoor_heat"

WORK_LABELS = {
    WORK_TOWER_INSTALL: "타워크레인 설치·수리·점검·해체",
    WORK_TOWER_OPERATION: "타워크레인 운전",
    WORK_STEEL: "철골작업",
    WORK_SCAFFOLD: "비계 조립·해체·변경",
    WORK_EXCAVATION: "굴착작업",
    WORK_OUTDOOR_LIFT: "옥외 승강기",
    WORK_OUTDOOR_HEAT: "옥외 폭염작업",
}


@dataclass(frozen=True)
class LegalSignal:
    status: str
    work_type: str
    title: str
    article: str
    reason: str
    actions: tuple[str, ...]
    source: str = "산업안전보건기준에 관한 규칙"

    def to_dict(self):
        value = asdict(self)
        value["actions"] = list(self.actions)
        return value


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _signal(status, work_type, title, article, reason, *actions):
    return LegalSignal(status, work_type, title, article, reason, tuple(actions)).to_dict()


def _measurements(site, weather):
    measured = site.get("site_measurements") or {}
    return {
        "wind": _number(weather.get("WSD")),
        "rain_1h": _number(weather.get("RN1")),
        "snow_1h": _number(measured.get("snowfall_1h", weather.get("SNO"))),
        "gust": _number(measured.get("gust_wind_speed")),
        "onsite_apparent": _number(measured.get("apparent_temperature")),
    }


def evaluate_legal_signals(site, weather):
    """현장 프로필과 실황을 대조해 법정 조치 신호 목록을 반환한다.

    ``work_types``는 현장에 존재할 수 있는 작업, ``active_work_types``는 현재 실제
    진행 중인 작업이다. 진행 여부가 확인되지 않았으면 법적 의무를 확정하지 않는다.
    """
    weather = weather or {}
    available = set(site.get("work_types") or [])
    active = set(site.get("active_work_types") or [])
    active_state_configured = site.get("active_work_types_configured", bool(active))
    unknown_active_state = not active_state_configured
    values = _measurements(site, weather)
    signals = []

    if not available and not active:
        return [_signal(
            STATUS_DATA_GAP,
            "site_profile",
            "현장 작업 프로필 미등록",
            "판정 전제정보",
            "타워크레인·철골·비계·굴착·옥외작업 여부가 등록되지 않았습니다.",
            "현장별 보유 설비와 작업 종류를 등록",
            "매일 진행 작업을 확인",
        )]

    monitored = active if active_state_configured else (available | active)

    def is_active(work_type):
        return work_type in active

    def activity_unknown(work_type):
        return work_type in available and work_type not in active and unknown_active_state

    # 타워크레인은 법령상 순간풍속 기준이므로 평균풍속 WSD로 대체하지 않는다.
    tower_rules = (
        (WORK_TOWER_INSTALL, 10.0, "타워크레인 설치·수리·점검·해체 작업 중지"),
        (WORK_TOWER_OPERATION, 15.0, "타워크레인 운전작업 중지"),
    )
    for work_type, limit, title in tower_rules:
        if work_type not in monitored:
            continue
        if values["gust"] is None:
            signals.append(_signal(
                STATUS_DATA_GAP,
                work_type,
                f"{WORK_LABELS[work_type]} 순간풍속 확인 필요",
                "제37조제2항",
                f"법정 기준은 순간풍속 {limit:g}m/s 초과이며 현재 자료의 WSD는 대체값으로 확정 판정할 수 없습니다.",
                "현장 풍속계 또는 신뢰 가능한 순간풍속 확인",
                "기준 초과 시 해당 작업 중지",
            ))
        elif values["gust"] > limit:
            status = STATUS_STOP if is_active(work_type) else STATUS_VERIFY
            reason = f"현장 순간풍속 {values['gust']:.1f}m/s로 기준 {limit:g}m/s를 초과했습니다."
            if activity_unknown(work_type):
                reason += " 현재 작업 진행 여부를 확인해야 합니다."
            signals.append(_signal(
                status, work_type, title, "제37조제2항", reason,
                "해당 작업 즉시 중지 또는 미진행 확인",
                "풍속 저하 후 현장 안전상태 확인",
            ))

    if WORK_STEEL in monitored:
        exceeded = []
        if values["wind"] is not None and values["wind"] >= 10:
            exceeded.append(f"풍속 {values['wind']:.1f}m/s")
        if values["rain_1h"] is not None and values["rain_1h"] >= 1:
            exceeded.append(f"시간당 강우 {values['rain_1h']:.1f}mm")
        if values["snow_1h"] is not None and values["snow_1h"] >= 1:
            exceeded.append(f"시간당 적설 {values['snow_1h']:.1f}cm")
        if exceeded:
            status = STATUS_STOP if is_active(WORK_STEEL) else STATUS_VERIFY
            reason = ", ".join(exceeded) + "로 제383조 기준에 해당합니다."
            if activity_unknown(WORK_STEEL):
                reason += " 철골작업 진행 여부를 확인해야 합니다."
            signals.append(_signal(
                status, WORK_STEEL, "철골작업 중지", "제383조", reason,
                "철골작업 즉시 중지 또는 미진행 확인",
                "기상상태와 작업구간 안전 확인 후 재개",
            ))
        elif values["snow_1h"] is None:
            signals.append(_signal(
                STATUS_DATA_GAP, WORK_STEEL, "철골작업 적설량 확인 필요", "제383조",
                "시간당 적설량 자료가 없어 적설 기준을 판정할 수 없습니다.",
                "강설 시 현장 시간당 적설량 확인",
            ))

    # 비계와 굴착은 단일 수치로 확정할 수 없으므로 강수·강설 시 현장확인을 요청한다.
    precipitation = (values["rain_1h"] or 0) > 0 or (values["snow_1h"] or 0) > 0
    if WORK_SCAFFOLD in monitored and precipitation:
        signals.append(_signal(
            STATUS_VERIFY, WORK_SCAFFOLD, "비계 작업 기상상태 확인", "제57조제1항제4호·제58조",
            "강수 또는 강설이 확인되어 날씨 악화 정도와 비계 작업·재개 여부를 확인해야 합니다.",
            "날씨가 몹시 나쁘면 조립·해체·변경 작업 중지",
            "재개 전 비계 상태 점검 및 이상 즉시 보수",
        ))
    if WORK_EXCAVATION in monitored and precipitation:
        signals.append(_signal(
            STATUS_ACTION, WORK_EXCAVATION, "굴착부 강우·강설 점검", "제338조~제340조",
            "강수 또는 강설이 확인되어 지반·배수·붕괴 위험 점검이 필요합니다.",
            "지반 균열·함수·용수·동결 상태 확인",
            "배수로·덮개 및 붕괴 방지조치 확인",
        ))

    if WORK_OUTDOOR_LIFT in monitored:
        if values["gust"] is None:
            signals.append(_signal(
                STATUS_DATA_GAP, WORK_OUTDOOR_LIFT, "옥외 승강기 순간풍속 확인 필요", "제161조",
                "순간풍속 자료가 없어 35m/s 초과 우려를 판정할 수 없습니다.",
                "강풍 예보 시 순간풍속과 붕괴 방지조치 확인",
            ))
        elif values["gust"] > 35:
            signals.append(_signal(
                STATUS_ACTION, WORK_OUTDOOR_LIFT, "옥외 승강기 붕괴 방지조치", "제161조",
                f"현장 순간풍속 {values['gust']:.1f}m/s로 35m/s를 초과했습니다.",
                "받침 수 증가 등 붕괴 방지조치 실시",
                "조치 결과와 확인자 기록",
            ))

    if WORK_OUTDOOR_HEAT in monitored:
        apparent = values["onsite_apparent"]
        if apparent is None:
            signals.append(_signal(
                STATUS_DATA_GAP, WORK_OUTDOOR_HEAT, "작업장소 체감온도 실측 필요", "제559조제4항·제562조제2항",
                "공공 기상자료만으로 폭염작업을 확정할 수 없습니다.",
                "작업장소에 온습도 측정기 상시 비치",
                "체감온도와 조치사항을 일자별 기록",
            ))
        elif apparent >= 33:
            signals.append(_signal(
                STATUS_ACTION, WORK_OUTDOOR_HEAT, "33℃ 이상 폭염작업 조치", "제560조제3항",
                f"작업장소 실측 체감온도 {apparent:.1f}℃입니다.",
                "매 2시간 이내 20분 이상 휴식 부여",
                "조치시간·내용·확인자 기록",
            ))
        elif apparent >= 31:
            signals.append(_signal(
                STATUS_ACTION, WORK_OUTDOOR_HEAT, "폭염작업 예방조치", "제559조제4항·제560조제2항",
                f"작업장소 실측 체감온도 {apparent:.1f}℃로 폭염작업 기준에 해당합니다.",
                "냉방·통풍, 작업시간 조정 또는 적절한 휴식 시행",
                "체감온도와 조치사항 기록",
            ))

    return signals


def highest_legal_status(signals):
    severity = {
        STATUS_DATA_GAP: 1,
        STATUS_VERIFY: 2,
        STATUS_ACTION: 3,
        STATUS_STOP: 4,
    }
    return max(
        (signal["status"] for signal in signals),
        key=lambda status: severity.get(status, 0),
        default=None,
    )

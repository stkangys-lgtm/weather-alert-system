"""현장·전국 요약 문장과 전파 문안을 만든다.

등급어("선제", "기준 도달" 등)를 쓰지 않고 관측값과 예보값을 판단어 없이 나란히 적는다.
세기 표현은 src.intensity의 기상청 예보용어만 쓴다.
"""

from datetime import datetime, timedelta

from src.alert_rules import (
    ACTION_ITEMS,
    CATEGORY_ORDER,
    CATEGORY_RAIN,
    CATEGORY_WIND,
    _situational_closing,
    _situational_title,
)
from src.intensity import DRIZZLE_MAX_MM, fmt_number, rain_term, wind_term

FORBIDDEN_WORDS = ("선제", "기준 도달", "주의 단계", "경계 단계")
FORECAST_HORIZON_HOURS = 12
NO_DATA = "관측 자료를 받지 못했습니다."


def contains_forbidden(text):
    return [word for word in FORBIDDEN_WORDS if word in (text or "")]


def _hour_label(iso, ref_date):
    at = datetime.fromisoformat(iso)
    if at.date() == ref_date:
        prefix = ""
    elif at.date() == ref_date + timedelta(days=1):
        prefix = "내일 "
    else:
        prefix = f"{at.month}/{at.day} "
    return f"{prefix}{at.hour}시"


def _rain_mm(hour):
    return hour.get("rain_mm") or 0


def _first_rain(hourly):
    return next((h for h in hourly if _rain_mm(h) > 0), None)


def _forecast_rain_phrase(hourly, ref_date):
    wet = [h for h in hourly[:FORECAST_HORIZON_HOURS] if _rain_mm(h) > 0]
    if not wet:
        return None
    start, end = _hour_label(wet[0]["at"], ref_date), _hour_label(wet[-1]["at"], ref_date)
    span = start if start == end else f"{start}~{end}"
    if {h["rain_label"] for h in wet} == {"<1"}:
        amount = "1mm 미만"
    else:
        amount = f"최대 {max(wet, key=_rain_mm)['rain_label']}mm"
    return f"{span} {amount}"


def _lead(view):
    if view["state"] == "ok":
        return "지금"
    return f"{datetime.fromisoformat(view['as_of']).hour}시 관측 기준"


def _warning_titles(view):
    return "·".join(w["title"] for w in view["warnings"])


def site_summary(view):
    if view["state"] == "missing" or not view.get("now"):
        return NO_DATA
    now = view["now"]
    ref = datetime.fromisoformat(view["as_of"]).date()
    rain = now.get("rain_mm") or 0
    parts = []
    if view["warnings"]:
        parts.append(f"기상청 {_warning_titles(view)} 발효 중.")
    if rain >= DRIZZLE_MAX_MM:
        parts.append(f"{_lead(view)} 시간당 {fmt_number(rain)}mm(관측)의 {rain_term(rain)}.")
        phrase = _forecast_rain_phrase(view["hourly"], ref)
        parts.append(f"예보는 {phrase}." if phrase else "예보상 12시간 안에 비 예보가 없습니다.")
    else:
        parts.append("지금은 비가 없습니다." if view["state"] == "ok" else f"{_lead(view)} 비가 없습니다.")
        wet = _first_rain(view["hourly"])
        parts.append(f"예보상 {_hour_label(wet['at'], ref)}부터 비(강수확률 {wet['pop']}%)." if wet
                     else "24시간 안에 비 예보가 없습니다.")
    wind = now.get("wind")
    term = wind_term(wind)
    if term:
        parts.append(f"바람 {fmt_number(wind)}m/s({term}).")
    return " ".join(parts)


def _next_hours_phrase(hourly):
    upcoming = hourly[:3]
    if not upcoming:
        return ""
    peak = max(upcoming, key=_rain_mm)
    if _rain_mm(peak) == 0:
        return ", 예보는 비 없음"
    if peak["rain_label"] == "<1":
        return ", 예보는 1mm 미만"
    return f", 예보는 {peak['rain_label']}mm"


def national_summary(sites, warnings_ok):
    live = [s for s in sites if s["state"] != "missing" and s.get("now")]
    if not live:
        return NO_DATA
    rainy = sorted((s for s in live if (s["now"].get("rain_mm") or 0) >= DRIZZLE_MAX_MM),
                   key=lambda s: -s["now"]["rain_mm"])
    parts = []
    if rainy:
        top = rainy[0]
        mm = top["now"]["rain_mm"]
        when = "지금 " if top["state"] == "ok" else f"{datetime.fromisoformat(top['as_of']).hour}시 관측 기준 "
        parts.append(f"{top['short']}에 {when}시간당 {fmt_number(mm)}mm(관측)의 {rain_term(mm)}"
                     f"{_next_hours_phrase(top['hourly'])}.")
        if len(rainy) > 1:
            parts.append(f"그 밖에 {len(rainy) - 1}곳에 비.")
    else:
        parts.append("비 오는 현장은 없습니다.")
    warned = sum(1 for s in sites if s["warnings"])
    if not warnings_ok:
        parts.append("기상청 특보는 확인하지 못했습니다.")
    elif warned:
        parts.append(f"기상청 특보가 {warned}개 현장에 발효 중입니다.")
    else:
        parts.append("기상청 특보는 없습니다.")
    failed = sum(1 for s in sites if s["state"] != "ok")
    if failed:
        parts.append(f"{failed}개 현장은 이번 수집에 실패했습니다.")
    return " ".join(parts)


def _categories(view):
    rain = view["now"].get("rain_mm") or 0
    found = set()
    for warning in view["warnings"]:
        for category in CATEGORY_ORDER:
            if category in (warning.get("title") or ""):
                found.add(category)
    if rain >= DRIZZLE_MAX_MM:
        found.add(CATEGORY_RAIN)
    if wind_term(view["now"].get("wind")) in ("강한 바람", "매우 강한 바람"):
        found.add(CATEGORY_WIND)
    return [category for category in CATEGORY_ORDER if category in found]


def site_notice(view):
    lines = ["■ 공지드립니다.", ""]
    if view["state"] == "missing" or not view.get("now"):
        lines += [f"{view['name']} 현장은 이번에 관측 자료를 받지 못했습니다.",
                  "현장에서 기상 상황을 직접 확인하여 주시기 바랍니다.", "", "감사합니다."]
        return "\n".join(lines)
    at = datetime.fromisoformat(view["as_of"])
    when = at.strftime("%Y-%m-%d %H:%M") + " 관측 기준"
    now = view["now"]
    rain = now.get("rain_mm") or 0
    if view["warnings"]:
        lines.append(f"기상청 {_warning_titles(view)}가 발효 중입니다.")
    if rain >= DRIZZLE_MAX_MM:
        lines.append(f"{when}, {view['name']} 현장에 시간당 {fmt_number(rain)}mm의 {rain_term(rain)}가 관측되고 있습니다.")
        phrase = _forecast_rain_phrase(view["hourly"], at.date())
        lines.append(f"(기상청 예보: {phrase})" if phrase else "(기상청 예보: 12시간 안에 비 예보 없음)")
    else:
        lines.append(f"{when}, {view['name']} 현장에는 비가 관측되지 않았습니다.")
        wet = _first_rain(view["hourly"])
        if wet:
            lines.append(f"다만 예보상 {_hour_label(wet['at'], at.date())}부터 비(강수확률 {wet['pop']}%)가 "
                         "있으니 작업 계획에 참고하여 주시기 바랍니다.")
    term = wind_term(now.get("wind"))
    if term:
        lines.append(f"바람은 {fmt_number(now['wind'])}m/s({term})입니다.")
    categories = _categories(view)
    if categories:
        lines += ["", f"【{_situational_title(categories)}】"]
        for category in categories:
            lines += [f"ㅇ {action}" for action in ACTION_ITEMS[category]]
        lines += ["", _situational_closing(categories)]
    lines += ["", "감사합니다."]
    return "\n".join(lines)

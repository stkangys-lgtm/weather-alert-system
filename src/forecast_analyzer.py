"""단기예보(3일)와 중기예보(3~10일)를 분석해 특이사항을 요약한다.

각 현장의 향후 10일 예보를 스캔해 위험 기상이 예상되는 날을 뽑고,
사람이 읽을 수 있는 문장으로 요약한다. 대시보드/공고문에 표시된다.
공식 특보와 혼동하지 않도록 이벤트 이름에는 ``예상`` 또는 ``가능``을 붙인다.
"""

from datetime import datetime, timedelta

from src.alert_rules import (
    HEAT_CAUTION, HEAT_WARNING,
    RAIN_CAUTION, RAIN_WARNING,
    WIND_CAUTION, WIND_WARNING,
)
from src.feels_like import compute_feels_like


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fcst_date_label(yyyymmdd):
    """'20260910' → '9/10(목)' 형식."""
    try:
        d = datetime.strptime(yyyymmdd, "%Y%m%d")
        weekday = "월화수목금토일"[d.weekday()]
        return f"{d.month}/{d.day}({weekday})"
    except Exception:
        return yyyymmdd


def _mid_date_label(iso_date):
    """'2026-09-13' → '9/13(일)' 형식."""
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d")
        weekday = "월화수목금토일"[d.weekday()]
        return f"{d.month}/{d.day}({weekday})"
    except Exception:
        return iso_date


def analyze_short_term(forecast):
    """단기예보(3일) 리스트를 분석해 위험 이벤트 리스트 반환.

    forecast: [{'fcst_date','fcst_time','TMP','POP','SKY','PTY',...}, ...]
    반환: [{"date": "9/10(목)", "kind": "고온 위험 예상", "detail": "낮 최고 33°C" 등}, ...]
    """
    # 날짜별로 집계
    by_date = {}
    for entry in forecast:
        d = entry.get("fcst_date")
        if not d:
            continue
        bucket = by_date.setdefault(d, {"tmps": [], "feels": [], "pops": [], "ptys": set(), "wsds": []})
        tmp = _to_float(entry.get("TMP"))
        if tmp is not None:
            bucket["tmps"].append(tmp)
            feels = compute_feels_like(tmp, entry.get("REH"), entry.get("WSD"))
            if feels is not None:
                bucket["feels"].append(feels)
        pop = _to_float(entry.get("POP"))
        if pop is not None:
            bucket["pops"].append(pop)
        pty = entry.get("PTY")
        if pty and pty not in ("없음", "-"):
            bucket["ptys"].add(pty)
        wsd = _to_float(entry.get("WSD"))
        if wsd is not None:
            bucket["wsds"].append(wsd)

    events = []
    for d in sorted(by_date.keys()):
        b = by_date[d]
        label = _fcst_date_label(d)
        max_tmp = max(b["tmps"]) if b["tmps"] else None
        max_feels = max(b["feels"]) if b["feels"] else None
        max_pop = max(b["pops"]) if b["pops"] else None
        max_wsd = max(b["wsds"]) if b["wsds"] else None

        if max_feels is not None:
            if max_feels >= HEAT_WARNING:
                events.append({"date": label, "kind": "고온 위험 예상", "detail": f"추정 체감 최고 {max_feels:.1f}°C"})
            elif max_feels >= HEAT_CAUTION:
                events.append({"date": label, "kind": "고온 유의 예상", "detail": f"추정 체감 최고 {max_feels:.1f}°C"})

        if b["ptys"] and max_pop is not None and max_pop >= 60:
            events.append({"date": label, "kind": "강수 예상", "detail": f"{'/'.join(sorted(b['ptys']))} 예보, 강수확률 최고 {max_pop:.0f}%"})

        if max_wsd is not None and max_wsd >= WIND_CAUTION:
            level = "강풍 위험 예상" if max_wsd >= WIND_WARNING else "강풍 유의 예상"
            events.append({"date": label, "kind": level, "detail": f"최대풍속 {max_wsd:.1f}m/s"})

    return events


def analyze_mid_term(mid_forecast):
    """중기예보(3~10일) 리스트를 분석.

    mid_forecast: [{"date","day_offset","sky_am","sky_pm","pop_am","pop_pm","ta_min","ta_max"}, ...]
    """
    events = []
    for entry in mid_forecast:
        label = _mid_date_label(entry["date"])
        ta_max = _to_float(entry.get("ta_max"))
        ta_min = _to_float(entry.get("ta_min"))
        pop_am = _to_float(entry.get("pop_am"))
        pop_pm = _to_float(entry.get("pop_pm"))
        sky_am = entry.get("sky_am") or ""
        sky_pm = entry.get("sky_pm") or ""

        if ta_max is not None:
            if ta_max >= HEAT_WARNING:
                events.append({"date": label, "kind": "고온 위험 예상", "detail": f"낮 최고 {ta_max:.0f}°C (기온 기준)"})
            elif ta_max >= HEAT_CAUTION:
                events.append({"date": label, "kind": "고온 유의 예상", "detail": f"낮 최고 {ta_max:.0f}°C (기온 기준)"})

        if ta_min is not None and ta_min <= -12:
            events.append({"date": label, "kind": "한파 가능", "detail": f"아침 최저 {ta_min:.0f}°C"})

        max_pop = max([p for p in (pop_am, pop_pm) if p is not None], default=None)
        has_rain_word = any("비" in s or "눈" in s or "소나기" in s for s in (sky_am, sky_pm))
        if has_rain_word and max_pop is not None and max_pop >= 60:
            skies = [s for s in (sky_am, sky_pm) if "비" in s or "눈" in s or "소나기" in s]
            events.append({"date": label, "kind": "강수 예상", "detail": f"{'/'.join(sorted(set(skies)))} 예보, 강수확률 최고 {max_pop:.0f}%"})

    return events


def summarize_events(short_events, mid_events, limit=5):
    """단기+중기 이벤트를 합쳐 대시보드에 표시할 짧은 요약 리스트 반환.

    같은 날짜/종류는 중복 제거, 날짜순 정렬, 최대 limit개.
    """
    seen = set()
    combined = []
    for ev in short_events + mid_events:
        key = (ev["date"], ev["kind"])
        if key in seen:
            continue
        seen.add(key)
        combined.append(ev)
    return combined[:limit]

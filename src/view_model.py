"""화면용 공개 데이터(docs/data/latest.json)를 만든다.

담당자·연락처 등 설정의 다른 값은 허용 목록에 없는 한 절대 복사하지 않는다.
시각은 모두 한국시각(+09:00)으로 표기한다.
"""

import re
from datetime import datetime, timedelta, timezone

from src.feels_like import compute_feels_like
from src.intensity import fmt_number

KST = timezone(timedelta(hours=9))
HOURLY_COUNT = 24
DAILY_COUNT = 10
FULL_DAY_HOURS = 12


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    number = _num(value)
    return int(number) if number is not None else None


def parse_pcp(value):
    """단기예보 PCP 문자열 → (색·정렬용 대표값 mm, 표시 문자열)."""
    text = str(value or "").strip()
    if text in ("강수없음", "0", "0.0"):
        return 0.0, "0"
    if "미만" in text:
        return 0.5, "<1"
    numbers = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return None, "-"
    if "~" in text and len(numbers) >= 2:
        return numbers[0], f"{fmt_number(numbers[0])}~{fmt_number(numbers[1])}"
    if "이상" in text:
        return numbers[0], f"{fmt_number(numbers[0])} 이상"
    return numbers[0], fmt_number(numbers[0])


def observed_at(current):
    """초단기실황의 관측 시각(정시)."""
    if not current or not current.get("base_date") or not current.get("base_time"):
        return None
    return datetime.strptime(current["base_date"] + current["base_time"], "%Y%m%d%H%M").replace(tzinfo=KST)


def now_values(current):
    if not current:
        return None
    rain = _num(current.get("RN1"))
    if rain is None:
        rain = parse_pcp(current.get("RN1"))[0] or 0.0
    temp = _num(current.get("T1H"))
    feels = compute_feels_like(current.get("T1H"), current.get("REH"), current.get("WSD"))
    return {"temp": temp, "feels": feels if feels is not None else temp, "rain_mm": rain,
            "wind": _num(current.get("WSD")), "humidity": _int(current.get("REH"))}


def _forecast_time(row):
    return datetime.strptime(row["fcst_date"] + row["fcst_time"], "%Y%m%d%H%M").replace(tzinfo=KST)


def hourly_series(forecast, after):
    rows = []
    for row in forecast or []:
        at = _forecast_time(row)
        if at <= after:
            continue
        rain_mm, rain_label = parse_pcp(row.get("PCP"))
        rows.append({"at": at.isoformat(), "temp": _num(row.get("TMP")), "rain_mm": rain_mm,
                     "rain_label": rain_label, "wind": _num(row.get("WSD")), "pop": _int(row.get("POP")),
                     "sky": row.get("SKY"), "pty": row.get("PTY"), "humidity": _int(row.get("REH"))})
        if len(rows) == HOURLY_COUNT:
            break
    return rows


def _short_day(day, rows):
    temps = [t for t in (_num(r.get("TMP")) for r in rows) if t is not None]
    tmn = next((_num(r.get("TMN")) for r in rows if _num(r.get("TMN")) is not None), None)
    tmx = next((_num(r.get("TMX")) for r in rows if _num(r.get("TMX")) is not None), None)
    ptys = {r.get("PTY") for r in rows} - {None, "", "없음"}
    if ptys:
        sky = "눈" if all("비" not in p and "빗방울" not in p for p in ptys) else "비"
    else:
        skies = [r.get("SKY") for r in rows if r.get("SKY")]
        sky = max(skies, key=skies.count) if skies else None
    pops = [p for p in (_int(r.get("POP")) for r in rows) if p is not None]
    return {"date": day.isoformat(), "sky": sky, "pop": max(pops) if pops else None,
            "tmin": tmn if tmn is not None else (min(temps) if temps else None),
            "tmax": tmx if tmx is not None else (max(temps) if temps else None),
            "source": "short", "missing": False}


def _mid_day(day, entry):
    pops = [p for p in (_int(entry.get("pop_am")), _int(entry.get("pop_pm"))) if p is not None]
    return {"date": day.isoformat(), "sky": entry.get("sky_pm") or entry.get("sky_am"),
            "pop": max(pops) if pops else None, "tmin": _num(entry.get("ta_min")),
            "tmax": _num(entry.get("ta_max")), "source": "mid", "missing": False}


def _missing_day(day):
    return {"date": day.isoformat(), "sky": None, "pop": None, "tmin": None, "tmax": None,
            "source": None, "missing": True}


def daily_series(forecast, mid_entries, today):
    """내일부터 10일. 단기예보가 12시간 이상인 날은 단기, 아니면 중기, 둘 다 없으면 missing."""
    by_date = {}
    for row in forecast or []:
        by_date.setdefault(datetime.strptime(row["fcst_date"], "%Y%m%d").date(), []).append(row)
    mid_by_date = {entry.get("date"): entry for entry in mid_entries or []}
    days = []
    for offset in range(1, DAILY_COUNT + 1):
        day = today + timedelta(days=offset)
        rows = by_date.get(day, [])
        entry = mid_by_date.get(day.isoformat())
        if len(rows) >= FULL_DAY_HOURS:
            days.append(_short_day(day, rows))
        elif entry and (entry.get("ta_min") is not None or entry.get("sky_am") or entry.get("sky_pm")):
            days.append(_mid_day(day, entry))
        else:
            days.append(_missing_day(day))
    return days

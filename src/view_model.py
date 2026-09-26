"""화면용 공개 데이터(docs/data/latest.json)를 만든다.

담당자·연락처 등 설정의 다른 값은 허용 목록에 없는 한 절대 복사하지 않는다.
시각은 모두 한국시각(+09:00)으로 표기한다.
"""

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone

from src import narrative
from src.feels_like import compute_feels_like
from src.intensity import fmt_number, is_snow
from src.kma_client import forecast_base_datetime
from src.legal_rules import STATUS_ACTION, STATUS_STOP, STATUS_VERIFY
from src.mid_client import mid_issue_datetime
from src.schedule import WINDOW_LABEL, next_collection_at
from src.site_profile import region_label, short_name, site_id

KST = timezone(timedelta(hours=9))
HOURLY_COUNT = 24
DAILY_COUNT = 10
FULL_DAY_HOURS = 12
SCHEMA_VERSION = 1
SITE_FIELDS = ("id", "name", "short", "category", "region", "lat", "lon", "state", "as_of", "now",
               "hourly", "daily", "warnings", "legal", "legal_profile", "summary", "notice")
ACTIONABLE_LEGAL = {STATUS_STOP, STATUS_ACTION, STATUS_VERIFY}


MISSING_LIMIT = 900  # 기상청 API: +900 이상, -900 이하 값은 결측(Missing)


def _num(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if -MISSING_LIMIT < number < MISSING_LIMIT else None


def _is_number(value):
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


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
    if rain is None and not _is_number(current.get("RN1")):
        rain = parse_pcp(current.get("RN1"))[0] or 0.0
    temp, wind, humidity = _num(current.get("T1H")), _num(current.get("WSD")), _int(current.get("REH"))
    feels = compute_feels_like(temp, humidity, wind)
    return {"temp": temp, "feels": feels if feels is not None else temp, "rain_mm": rain,
            "wind": wind, "humidity": humidity, "pty": current.get("PTY")}


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
        sky = "눈" if all(is_snow(p) for p in ptys) else "비"
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


def build_site_view(item, mid_entries, previous_site, now):
    """수집 결과 한 건 → 허용 목록 필드만 있는 공개용 현장 항목."""
    site = item["site"]
    current = now_values(item.get("current"))
    obs = observed_at(item.get("current"))
    legal = [{"status": s.get("status"), "title": s.get("title"), "article": s.get("article")}
             for s in item.get("legal_signals") or [] if s.get("work_type") != "site_profile"]
    if current is not None:
        state, as_of = "ok", (obs or now).isoformat()
    elif previous_site and previous_site.get("now"):
        # 법정 신호는 이번 실황 없이 계산되어 "데이터 부족"이 되므로 이어받은 관측값과 함께 직전 판정을 쓴다.
        state, current, as_of = "stale", previous_site["now"], previous_site.get("as_of")
        legal = previous_site.get("legal") or []
    else:
        state, as_of = "missing", None

    hourly = hourly_series(item.get("forecast"), obs or now)
    if not hourly and previous_site:
        hourly = [h for h in previous_site.get("hourly") or []
                  if datetime.fromisoformat(h["at"]) > now][:HOURLY_COUNT]
    daily = daily_series(item.get("forecast"), mid_entries, now.date())
    if all(day["missing"] for day in daily) and previous_site:
        carried = [d for d in previous_site.get("daily") or [] if d["date"] > now.date().isoformat()]
        daily = carried[:DAILY_COUNT] or daily

    view = {
        "id": site_id(site),
        "name": site["site_name"],
        "short": short_name(site),
        "category": site.get("category"),
        "region": region_label(site),
        "lat": site.get("lat"),
        "lon": site.get("lon"),
        "state": state,
        "as_of": as_of,
        "now": current,
        "hourly": hourly,
        "daily": daily,
        "warnings": [{"kind": w.get("kind"), "title": w.get("title"), "level": w.get("level")}
                     for w in item.get("weather_warnings") or []],
        "legal": legal,
        "legal_profile": bool(site.get("work_types") or site.get("active_work_types")),
    }
    view["summary"] = narrative.site_summary(view, now)
    view["notice"] = narrative.site_notice(view, now)
    return {key: view[key] for key in SITE_FIELDS}


def _collection_status(done, total):
    if total and done == total:
        return "ok"
    return "failed" if done == 0 else "partial"


def _top(sites, key, unit_key):
    candidates = [s for s in sites if s["state"] != "missing" and s["now"] and s["now"].get(key) is not None]
    if not candidates:
        return None
    best = max(candidates, key=lambda s: s["now"][key])
    return {unit_key: best["now"][key], "site": best["id"]}


def _kst_iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=KST)
    return value.astimezone(KST).isoformat(timespec="seconds")


def _as_kst(now):
    return now.astimezone(KST) if now.tzinfo else now.replace(tzinfo=KST)


def build_latest(collected, mid_forecasts, previous, now, warnings_ok, forecast_issued_at, mid_issued_at):
    now = _as_kst(now)
    previous_sites = {s.get("id"): s for s in (previous or {}).get("sites") or []}
    sites = [build_site_view(item, mid_forecasts.get(item["site"]["site_name"], []),
                             previous_sites.get(site_id(item["site"])), now)
             for item in collected]
    fresh = [s for s in sites if s["state"] == "ok"]
    live = [s for s in sites if s["state"] != "missing" and s["now"]]
    return {
        "schema": SCHEMA_VERSION,
        "generated_at": _kst_iso(now),
        "observed_at": max((s["as_of"] for s in fresh), default=None),
        "forecast_issued_at": _kst_iso(forecast_issued_at),
        "mid_issued_at": _kst_iso(mid_issued_at),
        "status": {
            "current": _collection_status(len(fresh), len(sites)),
            "forecast": _collection_status(sum(1 for item in collected if item.get("forecast")), len(collected)),
            "warnings": "ok" if warnings_ok else "failed",
            "radar": "off",
        },
        "schedule": {"window": WINDOW_LABEL, "next_run_at": _kst_iso(next_collection_at(now))},
        "national": {
            "warnings": sum(1 for s in sites if any(narrative.is_official_warning(w) for w in s["warnings"])),
            "legal": sum(1 for s in sites if any(l["status"] in ACTIONABLE_LEGAL for l in s["legal"])),
            "rain_sites": sum(1 for s in live if narrative.precipitation(s["now"]) == "rain"),
            "max_rain": _top(sites, "rain_mm", "mm"),
            "max_wind": _top(sites, "wind", "ms"),
            "max_temp": _top(sites, "temp", "c"),
            "summary": narrative.national_summary(sites, warnings_ok, now),
        },
        "radar": None,
        "sites": sites,
    }


def load_latest(path):
    """직전 latest.json. 없거나 깨졌거나 스키마가 다르면 None."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA_VERSION:
        return None
    return data


def write_latest(path, data):
    """임시 파일에 쓴 뒤 교체해 반쯤 쓰인 파일이 게시되지 않게 한다."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".latest-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def publish_latest(path, collected, mid_forecasts, now):
    now = _as_kst(now)

    def build(previous):
        return build_latest(
            collected,
            mid_forecasts,
            previous=previous,
            now=now,
            warnings_ok=all(item.get("weather_warnings_available", True) for item in collected),
            forecast_issued_at=forecast_base_datetime(now),
            mid_issued_at=mid_issue_datetime(now),
        )

    previous = load_latest(path)
    try:
        latest = build(previous)
    except Exception as error:
        if previous is None:
            raise
        # 같은 파일을 매번 다시 읽으므로 여기서 멈추면 이후 갱신이 모두 막힌다.
        print(f"[화면 데이터] 직전 파일 형식이 맞지 않아 무시하고 새로 만듭니다: {type(error).__name__}")
        latest = build(None)
    write_latest(path, latest)
    return latest

"""기상청 API로 현장별 기상 데이터를 수집해 Google Sheets에 기록하고,
이상기상 여부를 판정해 공고문 텍스트와 대시보드(docs/index.html)를 생성한다.

실행 (프로젝트 루트에서, 가상환경 활성화 후):
    python -m src.main
"""

import os
from datetime import datetime

from src import alert_rules
from src import settings as config
from src.collection import CircuitBreaker, collect_mid_forecasts, collect_site_data
from src.dashboard import build_dashboard_html
from src.feels_like import compute_feels_like
from src.forecast_analyzer import analyze_mid_term, analyze_short_term, summarize_events
from src.map_dashboard import build_map_html
from src.notification_queue import process_notifications
from src.state_monitor import (
    build_alert_message,
    build_snapshot,
    carry_change_summary,
    detect_changes,
    load_state,
    save_state,
    state_age_minutes,
)
from src.view_model import publish_latest
from src.warning_client import get_active_warnings, match_warnings_to_sites, warning_display_level

NCST_HEADER = [
    "기록시각", "현장명", "담당자", "기온(°C)", "강수형태", "1시간강수량(mm)",
    # 앞 10개 열 이름은 기존 시트와의 자동 확장 호환성을 위해 유지한다.
    "습도(%)", "풍속(m/s)", "판정", "체감온도(°C)", "법정상태",
    "법정근거", "법정확인·조치", "현장실측체감온도(°C)", "현장순간풍속(m/s)",
]
FCST_HEADER = ["기록시각", "현장명", "담당자", "예보일자", "예보시각", "기온(°C)", "강수확률(%)", "하늘상태", "강수형태"]

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
ANNOUNCEMENT_PATH = os.path.join(DOCS_DIR, "announcement.txt")
DASHBOARD_PATH = os.path.join(DOCS_DIR, "sites.html")
MAP_PATH = os.path.join(DOCS_DIR, "index.html")
LEGACY_MAP_PATH = os.path.join(DOCS_DIR, "map.html")
STATE_PATH = os.path.join(DOCS_DIR, "weather-state.json")
LATEST_ALERT_PATH = os.path.join(DOCS_DIR, "latest-alert.txt")
NOTIFICATION_OUTBOX_PATH = os.path.join(DOCS_DIR, "notification-outbox.json")
LATEST_PATH = os.path.join(DOCS_DIR, "data", "latest.json")

# 공고문은 매시간이 아니라 오전 7시, 오후 1시(KST) 실행 시에만 생성한다 (단톡방 공유용, 하루 2회면 충분).
ANNOUNCEMENT_HOURS = {7, 13}


def attach_weather_warnings(collected, breaker=None):
    """전국 특보를 한 번 조회해 수집된 현장에 연결한다.

    특보 API 장애가 실황·예보 대시보드 전체를 막지 않도록 실패를 격리한다.
    breaker가 전달되면 다른 API 호출과 회로 차단 상태를 공유한다.
    """
    try:
        retries = 1 if breaker is not None and breaker.is_tripped() else 2
        warnings = get_active_warnings(config.KMA_API_KEY, timeout=10, retries=retries, breaker=breaker)
        by_site = match_warnings_to_sites([item["site"] for item in collected], warnings)
        for item in collected:
            item["weather_warnings"] = by_site.get(item["site"]["site_name"], [])
            item["weather_warnings_available"] = True
        affected = sum(1 for item in collected if item["weather_warnings"])
        print(f"[기상특보 수집] 전국 {len(warnings)}건 / 해당 현장 {affected}곳")
        return warnings
    except Exception as e:
        print(f"[기상특보 오류] 특보 확인은 실패했지만 실황·예보 수집은 계속합니다: {e}")
        for item in collected:
            item["weather_warnings"] = []
            item["weather_warnings_available"] = False
        return []


def _display_level(item):
    official = warning_display_level(item.get("weather_warnings") or [])
    internal = item["judgment"]["level"]
    severity = {"정상": 0, "데이터없음": 1, "주의": 2, "경보": 3}
    return max((internal, official or "정상"), key=lambda level: severity[level])


def build_current_weather_rows(collected, now_str):
    rows = []
    for item in collected:
        if item["current"] is None:
            continue
        site, data, judgment = item["site"], item["current"], item["judgment"]
        feels = compute_feels_like(data.get("T1H"), data.get("REH"), data.get("WSD"))
        legal_signals = item.get("legal_signals") or []
        measurements = site.get("site_measurements") or {}
        rows.append([
            now_str,
            site["site_name"],
            site["manager"],
            data.get("T1H", ""),
            data.get("PTY", ""),
            data.get("RN1", ""),
            data.get("REH", ""),
            data.get("WSD", ""),
            judgment["level"],
            feels if feels is not None else "",
            item.get("legal_status") or "해당 없음",
            ", ".join(dict.fromkeys(s.get("article", "") for s in legal_signals if s.get("article"))),
            " / ".join(
                action for signal in legal_signals for action in (signal.get("actions") or [])
            ),
            measurements.get("apparent_temperature", ""),
            measurements.get("gust_wind_speed", ""),
        ])
    return rows


def build_forecast_rows(collected, now_str):
    rows = []
    for item in collected:
        site = item["site"]
        for f in item["forecast"]:
            rows.append([
                now_str,
                site["site_name"],
                site["manager"],
                f.get("fcst_date", ""),
                f.get("fcst_time", ""),
                f.get("TMP", ""),
                f.get("POP", ""),
                f.get("SKY", ""),
                f.get("PTY", ""),
            ])
    return rows


def write_announcement(collected, now_str, mid_forecasts):
    site_results = []
    for item in collected:
        name = item["site"]["site_name"]
        mid = mid_forecasts.get(name, [])
        events = summarize_events(analyze_short_term(item["forecast"]), analyze_mid_term(mid))
        site_results.append({
            "site_name": name,
            "level": item["judgment"]["level"],
            "reasons": item["judgment"]["reasons"],
            "categories": item["judgment"]["categories"],
            "legal_signals": item.get("legal_signals", []),
            "weather_warnings": item.get("weather_warnings", []),
            "weather_warnings_available": item.get("weather_warnings_available", True),
            "events": events,
        })
    text = alert_rules.build_announcement(now_str, site_results)
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(ANNOUNCEMENT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("\n" + text + "\n")
    return text


def write_dashboard(collected, now_str, mid_forecasts, generated_at_iso=None, recent_changes=None, last_change_at=None):
    site_rows = []
    for item in collected:
        name = item["site"]["site_name"]
        mid = mid_forecasts.get(name, [])
        # 단기 + 중기 예보에서 특이사항 이벤트 추출
        events = summarize_events(analyze_short_term(item["forecast"]), analyze_mid_term(mid))
        site_rows.append({
            "site_name": name,
            "category": item["site"]["category"],
            "current": item["current"] or {},
            "forecast": item["forecast"],
            "mid_forecast": mid,
            "events": events,
            "level": item["judgment"]["level"],
            "display_level": _display_level(item),
            "reasons": item["judgment"]["reasons"],
            "legal_signals": item.get("legal_signals", []),
            "legal_status": item.get("legal_status"),
            "weather_warnings": item.get("weather_warnings", []),
            "weather_warnings_available": item.get("weather_warnings_available", True),
        })
    html = build_dashboard_html(
        now_str,
        site_rows,
        generated_at_iso=generated_at_iso,
        recent_changes=recent_changes,
        last_change_at=last_change_at,
        missing_site_count=sum(1 for item in collected if item["current"] is None),
    )
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html)


def write_map(collected, now_str, mid_forecasts):
    site_rows = []
    for item in collected:
        name = item["site"]["site_name"]
        events = summarize_events(
            analyze_short_term(item["forecast"]),
            analyze_mid_term(mid_forecasts.get(name, [])),
        )
        site_rows.append({
            "site_name": item["site"]["site_name"],
            "category": item["site"]["category"],
            "lat": item["site"]["lat"],
            "lon": item["site"]["lon"],
            "current": item["current"] or {},
            "forecast": item["forecast"],
            "events": events,
            "level": item["judgment"]["level"],
            "display_level": _display_level(item),
            "reasons": item["judgment"]["reasons"],
            "legal_signals": item.get("legal_signals", []),
            "legal_status": item.get("legal_status"),
            "weather_warnings": item.get("weather_warnings", []),
            "weather_warnings_available": item.get("weather_warnings_available", True),
        })
    html = build_map_html(now_str, site_rows)
    os.makedirs(DOCS_DIR, exist_ok=True)
    # 지도 화면을 기본 진입점으로 사용하고, 기존 map.html 주소도 호환한다.
    for path in (MAP_PATH, LEGACY_MAP_PATH):
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)


def write_latest_view(collected, mid_forecasts, now):
    """화면용 공개 데이터를 쓴다. 실패해도 기존 대시보드·알림 산출물은 계속 만든다."""
    try:
        latest = publish_latest(LATEST_PATH, collected, mid_forecasts, now.astimezone())
        print(f"[화면 데이터] 현장 {len(latest['sites'])}곳 · 실황 {latest['status']['current']} · "
              f"특보 {latest['status']['warnings']} · 다음 수집 {latest['schedule']['next_run_at'][11:16]}")
    except Exception as e:
        print(f"[화면 데이터 오류] latest.json을 만들지 못했습니다(기존 화면은 계속 생성): {e}")


def update_weather_state(collected, mid_forecasts, generated_at_iso, now_str):
    """이전 실행과 비교하고, 변화가 있을 때만 최신 알림 문안을 갱신한다."""
    previous = load_state(STATE_PATH)
    current = build_snapshot(collected, mid_forecasts, generated_at_iso)
    changes = detect_changes(previous, current)
    current = carry_change_summary(previous, current, changes)
    save_state(STATE_PATH, current)

    alert_text = None
    if changes:
        alert_text = build_alert_message(now_str, changes)
        with open(LATEST_ALERT_PATH, "w", encoding="utf-8") as f:
            f.write(alert_text + "\n")
        print("\n" + alert_text + "\n")
    else:
        print("[기상변화] 알림이 필요한 새로운 변화 없음")
    return current, changes, alert_text


def write_sheets_safely(collected, now_str, write_forecast=True):
    """Sheets 장애가 대시보드와 위험상태 갱신까지 막지 않도록 격리한다."""
    try:
        # 로컬에서 대시보드만 확인할 때 Google 선택 패키지가 없어도 수집·화면 생성을
        # 실행할 수 있도록 실제 Sheets 기록 시점에만 불러온다.
        from src.sheets_client import append_rows, get_worksheet

        ncst_ws = get_worksheet(
            config.GOOGLE_SHEETS_SPREADSHEET_ID,
            "실시간기록",
            credentials_path=config.GOOGLE_SHEETS_CREDENTIALS_PATH,
            credentials_json=config.GOOGLE_SERVICE_ACCOUNT_JSON,
            header=NCST_HEADER,
        )
        append_rows(ncst_ws, build_current_weather_rows(collected, now_str))
        if write_forecast:
            fcst_ws = get_worksheet(
                config.GOOGLE_SHEETS_SPREADSHEET_ID,
                "예보기록",
                credentials_path=config.GOOGLE_SHEETS_CREDENTIALS_PATH,
                credentials_json=config.GOOGLE_SERVICE_ACCOUNT_JSON,
                header=FCST_HEADER,
            )
            append_rows(fcst_ws, build_forecast_rows(collected, now_str))
        else:
            print("[예보기록] 보완 실행에서는 중복 적재를 건너뜁니다")
    except Exception as e:
        print(f"[Google Sheets 오류] 기록은 실패했지만 대시보드 생성은 계속합니다: {e}")


def main():
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M")
    generated_at_iso = now.astimezone().isoformat(timespec="seconds")

    # :17 실행은 :47 주 실행의 지연·누락을 보완하는 용도다. 직전 자료가 신선하면
    # 외부 API와 Sheets를 호출하지 않아 Actions 사용량과 API 호출량을 절약한다.
    if os.environ.get("COLLECTION_MODE") == "backup":
        age = state_age_minutes(load_state(STATE_PATH), now.astimezone())
        if age is not None and age < 45:
            print(f"[보완 실행 건너뜀] 마지막 정상 수집이 {age:.0f}분 전입니다")
            return

    # 실황·예보·중기 호출이 공유하는 회로 차단기. 어느 한쪽에서 전면 장애가 감지되면
    # 다른 쪽 재시도도 즉시 중단해 GitHub Actions 10분 타임아웃 안에서 대시보드가 갱신된다.
    breaker = CircuitBreaker()
    collected = collect_site_data(config.SITES, breaker=breaker)
    attach_weather_warnings(collected, breaker=breaker)
    mid_forecasts = collect_mid_forecasts(config.SITES, breaker=breaker, now=now)
    write_latest_view(collected, mid_forecasts, now)
    state, changes, alert_text = update_weather_state(collected, mid_forecasts, generated_at_iso, now_str)
    delivery = process_notifications(
        NOTIFICATION_OUTBOX_PATH,
        alert_text,
        changes,
        generated_at_iso,
        webhook_url=config.ALERT_WEBHOOK_URL,
        webhook_token=config.ALERT_WEBHOOK_TOKEN,
        mode=config.NOTIFICATION_MODE,
    )
    mode_label = "실발송" if delivery["mode"] == "live" else "모의운영(외부 발송 차단)"
    print(
        f"[알림 전달: {mode_label}] "
        f"발송 {delivery['sent']}건 / 실패 {delivery['failed']}건 / 대기 {delivery['waiting']}건"
    )
    write_forecast_history = os.environ.get("WRITE_FORECAST_HISTORY", "true").lower() == "true"
    write_sheets_safely(collected, now_str, write_forecast=write_forecast_history)

    if now.hour in ANNOUNCEMENT_HOURS:
        write_announcement(collected, now_str, mid_forecasts)
    write_dashboard(
        collected,
        now_str,
        mid_forecasts,
        generated_at_iso=generated_at_iso,
        recent_changes=state.get("last_changes", []),
        last_change_at=state.get("last_change_at"),
    )
    write_map(collected, now_str, mid_forecasts)


if __name__ == "__main__":
    main()

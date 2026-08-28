"""기상청 API로 현장별 기상 데이터를 수집해 Google Sheets에 기록하고,
이상기상 여부를 판정해 공고문 텍스트와 대시보드(docs/index.html)를 생성한다.

실행 (프로젝트 루트에서, 가상환경 활성화 후):
    python -m src.main
"""

import os
from datetime import datetime

from src import alert_rules
from src import settings as config
from src.dashboard import build_dashboard_html
from src.feels_like import compute_feels_like
from src.kma_client import get_current_weather, get_forecast
from src.map_dashboard import build_map_html
from src.sheets_client import append_rows, get_worksheet

NCST_HEADER = ["기록시각", "현장명", "담당자", "기온(°C)", "강수형태", "1시간강수량(mm)", "습도(%)", "풍속(m/s)", "판정", "체감온도(°C)"]
FCST_HEADER = ["기록시각", "현장명", "담당자", "예보일자", "예보시각", "기온(°C)", "강수확률(%)", "하늘상태", "강수형태"]

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
ANNOUNCEMENT_PATH = os.path.join(DOCS_DIR, "announcement.txt")
DASHBOARD_PATH = os.path.join(DOCS_DIR, "index.html")
MAP_PATH = os.path.join(DOCS_DIR, "map.html")

# 공고문은 매시간이 아니라 오전 7시, 오후 1시(KST) 실행 시에만 생성한다 (단톡방 공유용, 하루 2회면 충분).
ANNOUNCEMENT_HOURS = {7, 13}


def collect_site_data(sites):
    """현장별 실황·예보·이상기상 판정을 한 번에 조회한다.

    반환: [{"site": dict, "current": dict|None, "forecast": list, "judgment": dict}, ...]
    실황/예보 조회 실패 시 해당 항목은 None/빈 리스트로 채워지고 오류가 출력된다.
    """
    results = []
    for site in sites:
        try:
            current = get_current_weather(config.KMA_API_KEY, site["nx"], site["ny"])
        except Exception as e:
            print(f"[실황 오류] {site['site_name']}: {e}")
            current = None

        try:
            forecast = get_forecast(config.KMA_API_KEY, site["nx"], site["ny"])
        except Exception as e:
            print(f"[예보 오류] {site['site_name']}: {e}")
            forecast = []

        judgment = alert_rules.judge(current) if current is not None else {"level": alert_rules.LEVEL_NORMAL, "reasons": [], "categories": []}
        results.append({"site": site, "current": current, "forecast": forecast, "judgment": judgment})

        if current is not None:
            print(f"[실황 수집] {site['site_name']}: 기온 {current.get('T1H', '?')}°C ({judgment['level']})")
        print(f"[예보 수집] {site['site_name']}: {len(forecast)}건")

    return results


def build_current_weather_rows(collected, now_str):
    rows = []
    for item in collected:
        if item["current"] is None:
            continue
        site, data, judgment = item["site"], item["current"], item["judgment"]
        feels = compute_feels_like(data.get("T1H"), data.get("REH"), data.get("WSD"))
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


def write_announcement(collected, now_str):
    site_results = [
        {
            "site_name": item["site"]["site_name"],
            "level": item["judgment"]["level"],
            "reasons": item["judgment"]["reasons"],
            "categories": item["judgment"]["categories"],
        }
        for item in collected
    ]
    text = alert_rules.build_announcement(now_str, site_results)
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(ANNOUNCEMENT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("\n" + text + "\n")
    return text


def write_dashboard(collected, now_str):
    site_rows = [
        {
            "site_name": item["site"]["site_name"],
            "category": item["site"]["category"],
            "current": item["current"] or {},
            "forecast": item["forecast"],
            "level": item["judgment"]["level"],
            "reasons": item["judgment"]["reasons"],
        }
        for item in collected
    ]
    html = build_dashboard_html(now_str, site_rows)
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html)


def write_map(collected, now_str):
    site_rows = [
        {
            "site_name": item["site"]["site_name"],
            "category": item["site"]["category"],
            "lat": item["site"]["lat"],
            "lon": item["site"]["lon"],
            "current": item["current"] or {},
            "level": item["judgment"]["level"],
            "reasons": item["judgment"]["reasons"],
        }
        for item in collected
    ]
    html = build_map_html(now_str, site_rows)
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(MAP_PATH, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M")

    collected = collect_site_data(config.SITES)

    ncst_ws = get_worksheet(
        config.GOOGLE_SHEETS_SPREADSHEET_ID,
        "실시간기록",
        credentials_path=config.GOOGLE_SHEETS_CREDENTIALS_PATH,
        credentials_json=config.GOOGLE_SERVICE_ACCOUNT_JSON,
        header=NCST_HEADER,
    )
    fcst_ws = get_worksheet(
        config.GOOGLE_SHEETS_SPREADSHEET_ID,
        "예보기록",
        credentials_path=config.GOOGLE_SHEETS_CREDENTIALS_PATH,
        credentials_json=config.GOOGLE_SERVICE_ACCOUNT_JSON,
        header=FCST_HEADER,
    )

    append_rows(ncst_ws, build_current_weather_rows(collected, now_str))
    append_rows(fcst_ws, build_forecast_rows(collected, now_str))

    if now.hour in ANNOUNCEMENT_HOURS:
        write_announcement(collected, now_str)
    write_dashboard(collected, now_str)
    write_map(collected, now_str)


if __name__ == "__main__":
    main()

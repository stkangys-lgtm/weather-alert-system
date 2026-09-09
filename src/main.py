"""기상청 API로 현장별 기상 데이터를 수집해 Google Sheets에 기록하고,
이상기상 여부를 판정해 공고문 텍스트와 대시보드(docs/index.html)를 생성한다.

실행 (프로젝트 루트에서, 가상환경 활성화 후):
    python -m src.main
"""

import os
from datetime import datetime

import requests

from src import alert_rules
from src import settings as config
from src.dashboard import build_dashboard_html
from src.feels_like import compute_feels_like
from src.forecast_analyzer import analyze_mid_term, analyze_short_term, summarize_events
from src.kma_client import get_current_weather, get_forecast
from src.map_dashboard import build_map_html
from src.mid_client import combine_forecast, get_mid_land_forecast, get_mid_temperature
from src.mid_regions import resolve_region_codes
from src.sheets_client import append_rows, get_worksheet

NCST_HEADER = ["기록시각", "현장명", "담당자", "기온(°C)", "강수형태", "1시간강수량(mm)", "습도(%)", "풍속(m/s)", "판정", "체감온도(°C)"]
FCST_HEADER = ["기록시각", "현장명", "담당자", "예보일자", "예보시각", "기온(°C)", "강수확률(%)", "하늘상태", "강수형태"]

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
ANNOUNCEMENT_PATH = os.path.join(DOCS_DIR, "announcement.txt")
DASHBOARD_PATH = os.path.join(DOCS_DIR, "index.html")
MAP_PATH = os.path.join(DOCS_DIR, "map.html")

# 공고문은 매시간이 아니라 오전 7시, 오후 1시(KST) 실행 시에만 생성한다 (단톡방 공유용, 하루 2회면 충분).
ANNOUNCEMENT_HOURS = {7, 13}


def collect_mid_forecasts(sites, fast_fail_mode=False):
    """중기예보(3~10일)를 지역코드별로 한 번씩만 조회해 캐싱한 뒤 현장별로 매핑.

    반환: {site_name: [combined_forecast_entries]}
    실패 시 해당 현장은 빈 리스트가 채워진다. 지역코드가 같은 현장들은 API 호출 1회로 처리.
    """
    land_cache, ta_cache = {}, {}
    result = {}
    consecutive_conn_failures = 0

    for site in sites:
        land_reg, ta_reg, _, _ = resolve_region_codes(site["lat"], site["lon"])

        if land_reg not in land_cache:
            retries = 1 if (fast_fail_mode or consecutive_conn_failures >= 3) else 3
            try:
                land_cache[land_reg] = get_mid_land_forecast(config.KMA_API_KEY, land_reg, retries=retries)
                consecutive_conn_failures = 0
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"[중기 육상 오류/연결] {land_reg}: {type(e).__name__}")
                land_cache[land_reg] = {}
                consecutive_conn_failures += 1
            except Exception as e:
                print(f"[중기 육상 오류] {land_reg}: {e}")
                land_cache[land_reg] = {}

        if ta_reg not in ta_cache:
            retries = 1 if (fast_fail_mode or consecutive_conn_failures >= 3) else 3
            try:
                ta_cache[ta_reg] = get_mid_temperature(config.KMA_API_KEY, ta_reg, retries=retries)
                consecutive_conn_failures = 0
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"[중기 기온 오류/연결] {ta_reg}: {type(e).__name__}")
                ta_cache[ta_reg] = {}
                consecutive_conn_failures += 1
            except Exception as e:
                print(f"[중기 기온 오류] {ta_reg}: {e}")
                ta_cache[ta_reg] = {}

        land, temp = land_cache[land_reg], ta_cache[ta_reg]
        if land or temp:
            result[site["site_name"]] = combine_forecast(land, temp)
        else:
            result[site["site_name"]] = []

    return result


def collect_site_data(sites):
    """현장별 실황·예보·이상기상 판정을 한 번에 조회한다.

    반환: [{"site": dict, "current": dict|None, "forecast": list, "judgment": dict}, ...]

    기상청 API가 전면 장애일 때 재시도로 시간을 낭비하지 않도록, 앞 3개 현장이 모두 실패하면
    이후 현장부터는 재시도 없이 1회만 시도한다 (연속 실패 → API 자체 문제로 판단해 조기 종료).
    GitHub Actions 10분 타임아웃 안에 끝나야 데이터없음 표시라도 커밋되어 대시보드가 갱신된다.
    """
    results = []
    consecutive_conn_failures = 0
    fast_fail_mode = False

    for site in sites:
        retries = 1 if fast_fail_mode else None
        kwargs = {} if retries is None else {"retries": retries}

        try:
            current = get_current_weather(config.KMA_API_KEY, site["nx"], site["ny"], **kwargs)
            consecutive_conn_failures = 0
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"[실황 오류/연결] {site['site_name']}: {type(e).__name__}")
            current = None
            consecutive_conn_failures += 1
        except Exception as e:
            print(f"[실황 오류] {site['site_name']}: {e}")
            current = None

        try:
            forecast = get_forecast(config.KMA_API_KEY, site["nx"], site["ny"], **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"[예보 오류/연결] {site['site_name']}: {type(e).__name__}")
            forecast = []
        except Exception as e:
            print(f"[예보 오류] {site['site_name']}: {e}")
            forecast = []

        if consecutive_conn_failures >= 3 and not fast_fail_mode:
            print("[전면 장애 감지] 이후 현장은 재시도 없이 1회만 시도합니다 (10분 타임아웃 회피)")
            fast_fail_mode = True

        judgment = alert_rules.judge(current) if current is not None else alert_rules.unknown_judgment()
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
            "events": events,
        })
    text = alert_rules.build_announcement(now_str, site_results)
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(ANNOUNCEMENT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("\n" + text + "\n")
    return text


def write_dashboard(collected, now_str, mid_forecasts):
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
            "reasons": item["judgment"]["reasons"],
        })
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
    mid_forecasts = collect_mid_forecasts(config.SITES)

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
        write_announcement(collected, now_str, mid_forecasts)
    write_dashboard(collected, now_str, mid_forecasts)
    write_map(collected, now_str)


if __name__ == "__main__":
    main()

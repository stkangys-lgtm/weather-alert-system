"""Phase 1: 기상청 API로 현장별 기상 데이터를 수집해 Google Sheets에 기록한다.

실행 (프로젝트 루트에서, 가상환경 활성화 후):
    python -m src.main
"""

from datetime import datetime

from src import settings as config
from src.kma_client import get_current_weather, get_forecast
from src.sheets_client import append_rows, get_worksheet

NCST_HEADER = ["기록시각", "현장명", "담당자", "기온(°C)", "강수형태", "1시간강수량(mm)", "습도(%)", "풍속(m/s)"]
FCST_HEADER = ["기록시각", "현장명", "담당자", "예보일자", "예보시각", "기온(°C)", "강수확률(%)", "하늘상태", "강수형태"]


def build_current_weather_rows(sites, now_str):
    rows = []
    for site in sites:
        try:
            data = get_current_weather(config.KMA_API_KEY, site["nx"], site["ny"])
        except Exception as e:
            print(f"[실황 오류] {site['site_name']}: {e}")
            continue

        rows.append([
            now_str,
            site["site_name"],
            site["manager"],
            data.get("T1H", ""),
            data.get("PTY", ""),
            data.get("RN1", ""),
            data.get("REH", ""),
            data.get("WSD", ""),
        ])
        print(f"[실황 수집] {site['site_name']}: 기온 {data.get('T1H', '?')}°C")
    return rows


def build_forecast_rows(sites, now_str):
    rows = []
    for site in sites:
        try:
            forecasts = get_forecast(config.KMA_API_KEY, site["nx"], site["ny"])
        except Exception as e:
            print(f"[예보 오류] {site['site_name']}: {e}")
            continue

        for f in forecasts:
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
        print(f"[예보 수집] {site['site_name']}: {len(forecasts)}건")
    return rows


def main():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

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

    append_rows(ncst_ws, build_current_weather_rows(config.SITES, now_str))
    append_rows(fcst_ws, build_forecast_rows(config.SITES, now_str))


if __name__ == "__main__":
    main()

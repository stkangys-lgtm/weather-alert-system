"""Google Sheets 기록 클라이언트 (gspread + 서비스 계정 인증)."""

import json

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_worksheet(spreadsheet_id, worksheet_name, credentials_path=None, credentials_json=None, header=None):
    """워크시트(탭)를 열거나 없으면 새로 만들어 반환. header가 있으면 빈 시트일 때 첫 줄에 채워 넣음.

    credentials_path(로컬 파일) 또는 credentials_json(문자열, CI 환경변수용) 중 하나를 넘긴다.
    """
    if credentials_json:
        creds = Credentials.from_service_account_info(json.loads(credentials_json), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(spreadsheet_id)

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)

    if header:
        existing = worksheet.get_all_values()
        if not existing:
            worksheet.append_row(header)
        else:
            _sync_header(worksheet, existing[0], header)

    return worksheet


def _sync_header(worksheet, current_header, target_header):
    """헤더에 새 컬럼이 추가된 경우, 기존 데이터는 그대로 두고 헤더 행 끝에 새 컬럼명만 채워 넣는다.

    스키마 변경(컬럼 추가) 시 이미 쌓인 데이터를 다시 쓰지 않고, 헤더만 안전하게 확장한다.
    기존 헤더가 새 헤더의 앞부분과 정확히 일치할 때만 확장한다 (수기 편집된 시트 보호).
    """
    if len(target_header) <= len(current_header):
        return
    if current_header != target_header[: len(current_header)]:
        print(f"[헤더 동기화 건너뜀] 기존 헤더가 예상과 달라 자동 확장하지 않음: {current_header}")
        return
    worksheet.update(
        range_name=f"A1:{gspread.utils.rowcol_to_a1(1, len(target_header))}",
        values=[target_header],
    )


def append_rows(worksheet, rows):
    """여러 행을 한 번의 API 호출로 기록 (건별 호출 대비 Google API 요청 한도 절약)."""
    if rows:
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")

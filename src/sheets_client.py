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

    if header and not worksheet.get_all_values():
        worksheet.append_row(header)

    return worksheet


def append_rows(worksheet, rows):
    """여러 행을 한 번의 API 호출로 기록 (건별 호출 대비 Google API 요청 한도 절약)."""
    if rows:
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")

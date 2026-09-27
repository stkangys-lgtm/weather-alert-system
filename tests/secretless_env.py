"""config.py·비밀 환경변수가 없는 PC(새 업무용 PC 등)에서도 테스트가 돌도록 가짜 값을 채운다.

src.settings는 config.py가 있으면 그 파일을 먼저 읽으므로, 진짜 설정이 있는 PC와 GitHub Actions에서는
이 값이 쓰이지 않는다(setdefault라 이미 있는 환경변수도 덮어쓰지 않는다). 테스트는 외부 호출을 모두 가짜로 바꾼다.
"""
import os

for key, value in {
    "KMA_API_KEY": "test-key",
    "GOOGLE_SHEETS_SPREADSHEET_ID": "test-sheet",
    "GOOGLE_SERVICE_ACCOUNT_JSON": "{}",
    "SITES_JSON": "[]",
}.items():
    os.environ.setdefault(key, value)

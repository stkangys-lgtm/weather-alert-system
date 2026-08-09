"""설정 로더.

로컬 개발 환경: 프로젝트 루트의 config.py (git에 올라가지 않음)를 그대로 사용.
GitHub Actions 등 CI 환경: config.py가 없으므로 환경변수(Secrets)에서 읽어온다.
    필요한 환경변수: KMA_API_KEY, GOOGLE_SHEETS_SPREADSHEET_ID,
                    GOOGLE_SERVICE_ACCOUNT_JSON, SITES_JSON
"""

import json
import os

try:
    import config as _config

    KMA_API_KEY = _config.KMA_API_KEY
    GOOGLE_SHEETS_SPREADSHEET_ID = _config.GOOGLE_SHEETS_SPREADSHEET_ID
    GOOGLE_SHEETS_CREDENTIALS_PATH = _config.GOOGLE_SHEETS_CREDENTIALS_PATH
    GOOGLE_SERVICE_ACCOUNT_JSON = None
    SITES = _config.SITES

except ImportError:
    KMA_API_KEY = os.environ["KMA_API_KEY"]
    GOOGLE_SHEETS_SPREADSHEET_ID = os.environ["GOOGLE_SHEETS_SPREADSHEET_ID"]
    GOOGLE_SHEETS_CREDENTIALS_PATH = None
    GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    SITES = json.loads(os.environ["SITES_JSON"])

# config.py 예시 파일입니다.
# 이 파일을 복사해서 config.py 로 이름을 바꾸고, 실제 값을 채워 넣어 사용하세요.
#   cp config.example.py config.py
# config.py 는 .gitignore에 등록되어 있어 git에 올라가지 않습니다.

# 기상청 API 인증키 (공공데이터포털에서 발급)
KMA_API_KEY = "YOUR_KMA_API_KEY_HERE"

# Google Sheets 관련 설정
GOOGLE_SHEETS_CREDENTIALS_PATH = "credentials/google-service-account.json"
GOOGLE_SHEETS_SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"

# 감시할 현장 목록 (더미 예시 3~5개)
# nx, ny 는 기상청 API에서 요구하는 격자 좌표입니다.
SITES = [
    {
        "site_name": "서울 A현장",
        "nx": 60,
        "ny": 127,
        "manager": "홍길동",
        "manager_phone": "010-0000-0001",
    },
    {
        "site_name": "부산 B현장",
        "nx": 98,
        "ny": 76,
        "manager": "김철수",
        "manager_phone": "010-0000-0002",
    },
    {
        "site_name": "대전 C현장",
        "nx": 67,
        "ny": 100,
        "manager": "이영희",
        "manager_phone": "010-0000-0003",
    },
    {
        "site_name": "광주 D현장",
        "nx": 58,
        "ny": 74,
        "manager": "박민수",
        "manager_phone": "010-0000-0004",
    },
    {
        "site_name": "인천 E현장",
        "nx": 55,
        "ny": 124,
        "manager": "정수진",
        "manager_phone": "010-0000-0005",
    },
]

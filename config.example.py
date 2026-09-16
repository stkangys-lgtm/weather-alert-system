# config.py 예시 파일입니다.
# 이 파일을 복사해서 config.py 로 이름을 바꾸고, 실제 값을 채워 넣어 사용하세요.
#   cp config.example.py config.py
# config.py 는 .gitignore에 등록되어 있어 git에 올라가지 않습니다.

# 기상청 API 인증키 (공공데이터포털에서 발급)
KMA_API_KEY = "YOUR_KMA_API_KEY_HERE"

# 선택 설정: 기상청 API 허브(apihub.kma.go.kr) 현재 특보 조회용 인증키
# 공공데이터포털 인증키와 별도입니다. 비워 두면 공식 특보 조회만 건너뜁니다.
KMA_API_HUB_KEY = ""

# Google Sheets 관련 설정
GOOGLE_SHEETS_CREDENTIALS_PATH = "credentials/google-service-account.json"
GOOGLE_SHEETS_SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"

# 선택 설정: 알림톡 발송사 또는 사내 메시징 중계 Webhook.
# 비워 두면 외부 발송 없이 알림 문안이 대기열에만 저장됩니다.
ALERT_WEBHOOK_URL = ""
ALERT_WEBHOOK_TOKEN = ""

# 감시할 현장 목록 (더미 예시 3~5개)
# lat/lon은 지도와 중기예보 지역 매핑, nx/ny는 기상청 단기예보 격자에 사용합니다.
SITES = [
    {
        "site_name": "서울 A현장",
        "category": "건축",
        "lat": 37.5665,
        "lon": 126.9780,
        "nx": 60,
        "ny": 127,
        "manager": "홍길동",
        "manager_phone": "010-0000-0001",
        # 공식 특보 구역과 현장을 연결합니다. 구역코드를 알면 warning_region_codes가 가장 정확합니다.
        "warning_region_keywords": ["서울"],
    },
    {
        "site_name": "부산 B현장",
        "category": "토목",
        "lat": 35.1796,
        "lon": 129.0756,
        "nx": 98,
        "ny": 76,
        "manager": "김철수",
        "manager_phone": "010-0000-0002",
    },
    {
        "site_name": "대전 C현장",
        "category": "건축",
        "lat": 36.3504,
        "lon": 127.3845,
        "nx": 67,
        "ny": 100,
        "manager": "이영희",
        "manager_phone": "010-0000-0003",
    },
    {
        "site_name": "광주 D현장",
        "category": "토목",
        "lat": 35.1595,
        "lon": 126.8526,
        "nx": 58,
        "ny": 74,
        "manager": "박민수",
        "manager_phone": "010-0000-0004",
    },
    {
        "site_name": "인천 E현장",
        "category": "건축",
        "lat": 37.4563,
        "lon": 126.7052,
        "nx": 55,
        "ny": 124,
        "manager": "정수진",
        "manager_phone": "010-0000-0005",
    },
]

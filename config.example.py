# config.py 예시 파일입니다.
# 이 파일을 복사해서 config.py 로 이름을 바꾸고, 실제 값을 채워 넣어 사용하세요.
#   cp config.example.py config.py
# config.py 는 .gitignore에 등록되어 있어 git에 올라가지 않습니다.

# 기상청 API 인증키 (공공데이터포털에서 발급)
KMA_API_KEY = "YOUR_KMA_API_KEY_HERE"

# 과거 API Hub 방식과 호환하기 위한 선택값입니다. 현재 공식 특보 수집은
# 공공데이터포털 KMA_API_KEY를 사용하므로 비워 둘 수 있습니다.
KMA_API_HUB_KEY = ""

# Google Sheets 관련 설정
GOOGLE_SHEETS_CREDENTIALS_PATH = "credentials/google-service-account.json"
GOOGLE_SHEETS_SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"

# 선택 설정: 알림톡 발송사 또는 사내 메시징 중계 Webhook.
# shadow: 문안과 대기열만 생성하고 외부 발송은 차단 (기본값)
# live: 승인된 문체와 발송 연동 검증이 끝난 뒤에만 사용
NOTIFICATION_MODE = "shadow"
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
        # 기상청 특보문에 표시되는 시·군·구 별칭. 광역 전체 특보용 도/시 명칭은 별도 지정합니다.
        "warning_regions": ["종로구", "서울도심권"],
        "warning_provinces": ["서울", "서울특별시"],
        "manager": "홍길동",
        "manager_phone": "010-0000-0001",
        # 현장에 존재하는 작업·설비. 가능한 값은 아래 설명을 참고하세요.
        "work_types": ["tower_crane_operation", "steel_erection", "outdoor_heat"],
        # 현재 진행 작업을 확인한 경우 True. 빈 목록 + True는 해당 시점 진행 작업 없음을 뜻합니다.
        "active_work_types_configured": True,
        "active_work_types": ["steel_erection", "outdoor_heat"],
        # 현장 실측값 연계 예시. 자동 연계 전에는 입력·업데이트 방식이 별도로 필요합니다.
        "site_measurements": {
            "gust_wind_speed": 8.2,
            "apparent_temperature": 32.5,
            "snowfall_1h": 0,
        },
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

# work_types / active_work_types 값
# - tower_crane_install: 타워크레인 설치·수리·점검·해체
# - tower_crane_operation: 타워크레인 운전
# - steel_erection: 철골작업
# - scaffold: 비계 조립·해체·변경
# - excavation: 굴착작업
# - outdoor_lift: 옥외 승강기
# - outdoor_heat: 옥외 폭염작업
# warning_regions / warning_provinces
# - 새 현장 추가 시 기상청 특보 구역명과 연결할 행정구역을 입력합니다.
# - 예: 화성시 현장 → warning_regions=["화성시", "화성"], warning_provinces=["경기도"]

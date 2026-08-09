# 전사 기상 자동감시·알림 시스템

기상청 API로 현장별 기상 데이터를 주기적으로 수집하고, Google Sheets에 자동 기록하며,
이상기상 발생 시 관련 담당자에게 알림을 보내는 시스템입니다.

## 프로젝트 목표

- 전사 현장(공사현장 등)의 기상 상황을 자동으로 감시
- 강풍/호우/폭염 등 위험 기상 조건 발생 시 자동 알림
- 안전관리자가 매번 수기로 기상청 사이트를 확인하지 않아도 되도록 자동화

## Phase 구성

- **Phase 1 (현재)**: 개발환경 준비 + 기상청 API → Google Sheets 자동 기록
- Phase 2: 이상기상 판정 로직 + 알림 발송 (예: 카카오톡/이메일/슬랙)
- Phase 3: 배포 및 정기 실행 자동화 (스케줄러)

## 폴더 구조

```
weather-alert-system/
├── .gitignore
├── README.md
├── requirements.txt      # 설치할 파이썬 패키지 목록
├── config.example.py     # 설정 파일 예시 (실제 설정은 config.py로 복사해서 사용)
├── src/                  # 소스 코드
├── credentials/          # 인증정보 보관 (git에 올라가지 않음)
└── tests/                # 테스트 코드
```

## 시작하기

1. 가상환경 생성 및 활성화 (README 안내 참고)
2. `pip install -r requirements.txt`
3. `config.example.py`를 `config.py`로 복사 후 실제 값 입력
4. `credentials/` 폴더에 기상청 API 키, 구글 서비스 계정 JSON 등 배치 (`credentials/README.md` 참고)

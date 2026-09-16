# 전사 기상 자동감시·알림 시스템

기상청 API로 현장별 기상 데이터를 주기적으로 수집하고, Google Sheets에 자동 기록하며,
이상기상 발생 시 관련 담당자에게 알림을 보내는 시스템입니다.

## 프로젝트 목표

- 전사 현장(공사현장 등)의 기상 상황을 자동으로 감시
- 강풍/호우/폭염 등 기상 위험 신호와 기상청 공식 특보 확인
- 안전관리자가 매번 수기로 기상청 사이트를 확인하지 않아도 되도록 자동화

## Phase 구성

- **Phase 1 (완료)**: 개발환경 준비 + 기상청 API(초단기실황/단기예보) → Google Sheets 자동 기록
- **Phase 1.5 (완료)**: GitHub Actions로 현장 운영시간에 자동 실행 — 로컬 컴퓨터를 켜둘 필요 없음
- **Phase 2 (진행중)**: 이상기상 판정, 이전 상태 대비 변화 감지, 모바일 대시보드, 현장 전파용 문안 자동 생성. 알림톡은 승인된 템플릿과 발송 API 정보가 준비되면 연결 예정
- **Phase 2.5 (구현)**: 알림 대기열, 중복 방지, 실패 재시도 및 공급사 독립 Webhook. Webhook 미설정 시 외부 발송은 하지 않음

## 대시보드 (GitHub Pages)

매 실행마다 `docs/index.html`에 지도 중심 통합관제 화면을, `docs/sites.html`에 현장별 카드
대시보드를 생성하고 자동 커밋합니다. 지도에서 현장을 선택하면 실황, 시간대별 예보와 향후
특이기상을 바로 확인할 수 있습니다. **담당자 이름·연락처는 공개 페이지 특성상 포함하지 않습니다** (개인정보 보호).
공개되는 `docs/` 아래 파일에는 담당자 이름·연락처를 저장하지 않습니다. `announcement.txt`와
`latest-alert.txt`도 Pages에서 접근할 수 있으므로 공개 가능한 기상·조치 정보만 포함합니다.

시스템 선제알림 기준(`src/alert_rules.py`에서 조정 가능):

| 항목 | 주의 | 경보 |
|---|---|---|
| 강풍 (풍속) | 10m/s 이상 | 15m/s 이상 |
| 강수 (1시간 강수량) | 5mm 이상 | 15mm 이상 |
| 고온 (추정 체감온도) | 31°C 이상 | 33°C 이상 |

> 위 수치는 본사 공지와 현장 확인을 위한 선제 신호이며 법정 작업중지 기준이나 기상특보를
> 대신하지 않습니다. 화면에서는 API Hub 발효자료를 `기상청 공식 특보`, 격자 실황 계산값을
> `시스템 선제알림`으로 구분합니다. 실제 작업 여부는 현장 계측값, 공종, 작업여건을 함께 확인해야 합니다.

## 폴더 구조

```
weather-alert-system/
├── .github/workflows/collector.yml   # GitHub Actions 자동 실행 워크플로우
├── .gitignore
├── README.md
├── requirements.txt      # 설치할 파이썬 패키지 목록
├── config.example.py     # 설정 파일 예시 (실제 설정은 config.py로 복사해서 사용)
├── src/
│   ├── settings.py       # 설정 로더 (로컬: config.py / CI: 환경변수 자동 분기)
│   ├── kma_client.py      # 기상청 API 호출
│   ├── kma_warning_client.py # 기상청 API Hub 현재 특보 조회·현장 매칭
│   ├── sheets_client.py   # Google Sheets 기록
│   ├── grid_converter.py  # 위경도 -> 기상청 격자좌표 변환
│   ├── alert_rules.py     # 이상기상 판정 + 공고문 텍스트 생성
│   ├── state_monitor.py   # 이전 상태 비교 + 변화 알림 문안 생성
│   ├── dashboard.py       # 현장 목록 대시보드 HTML 생성
│   ├── map_dashboard.py   # 지도 중심 통합관제 HTML 생성
│   └── main.py            # 실행 진입점
├── docs/                 # 지도 관제(index.html), 현장 목록(sites.html), 공고문
├── credentials/          # 인증정보 보관 (git에 올라가지 않음)
└── tests/                # 테스트 코드
```

## 클라우드 자동 실행 (GitHub Actions)

이 저장소는 GitHub Actions로 현장 운영시간 동안 매시 17분과 47분에 자동 실행되도록 설정되어 있습니다.
두 번의 실행으로 예약 지연·누락을 보완하며, 같은 위험상태는 다시 알리지 않습니다.
(야간에는 현장에 인원이 없어 실행하지 않으며, GitHub Actions 무료 사용량 절약에도 도움이 됩니다.)
**로컬 컴퓨터를 켜둘 필요가 없고, 어느 컴퓨터에서 이 저장소를 열든 클라우드 실행에는 영향이 없습니다.**

사용하는 GitHub Secrets (저장소 Settings → Secrets and variables → Actions에서 확인/재설정 가능, 값 조회는 불가):

| Secret | 내용 |
|---|---|
| `KMA_API_KEY` | 기상청 공공데이터포털 인증키 (Decoding 키) |
| `KMA_API_HUB_KEY` | 선택: 기상청 API Hub 현재 특보 조회용 인증키 |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | 기록 대상 스프레드시트 ID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 구글 서비스 계정 키 JSON 전체 내용 |
| `SITES_JSON` | 현장 목록 (JSON) — `config.py`의 `SITES`와 동일 형식 |
| `ALERT_WEBHOOK_URL` | 선택: 알림톡 발송사 또는 사내 메시징 중계 Webhook URL |
| `ALERT_WEBHOOK_TOKEN` | 선택: Webhook Bearer 인증 토큰 |

```bash
gh run list --workflow=collector.yml   # 실행 이력 확인
gh workflow run collector.yml          # 수동 실행
gh run view <run-id> --log             # 특정 실행 로그 확인
```

## 로컬 개발 환경 시작하기 (새 컴퓨터에서 이어서 작업할 때)

`config.py`와 `credentials/`는 보안을 위해 git에서 제외되어 있어서, 저장소를 새로 clone해도 따라오지 않습니다.
아래 순서대로 다시 준비해야 합니다.

1. **개발도구 설치**

   macOS (터미널):
   ```bash
   brew install python@3.12 gh
   ```

   Windows (PowerShell):
   ```powershell
   winget install -e --id Python.Python.3.12
   winget install --id GitHub.cli
   ```
   `winget`이 막혀있다면 [python.org](https://www.python.org/downloads/), [cli.github.com](https://cli.github.com)에서 설치파일을 직접 받는다. Python 설치 시 **"Add python.exe to PATH" 체크 필수**.

2. **GitHub 로그인 & 저장소 클론**
   ```bash
   gh auth login   # GitHub.com -> HTTPS -> Login with a web browser
   ```
   macOS: `gh repo clone stkangys-lgtm/weather-alert-system ~/Projects/weather-alert-system && cd ~/Projects/weather-alert-system`
   Windows (PowerShell): `gh repo clone stkangys-lgtm/weather-alert-system "$HOME\Projects\weather-alert-system"; cd "$HOME\Projects\weather-alert-system"`

3. **가상환경 및 패키지 설치**

   macOS:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   Windows (PowerShell):
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   `Activate.ps1` 실행 시 "이 시스템에서 스크립트를 실행할 수 없으므로..." 오류가 나면 PowerShell 실행 정책 때문이다. 아래를 한 번만 실행하면 해결된다 (관리자 권한 불필요):
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
   ```
   회사 정책(그룹정책)으로 이마저 막혀있다면 IT 부서에 문의가 필요하다.

4. **로컬 설정 파일 재구성**
   ```bash
   cp config.example.py config.py
   ```
   `config.py`를 열어서 아래 값을 채웁니다:
   - `KMA_API_KEY`: [data.go.kr](https://www.data.go.kr) 마이페이지 → 개발계정에서 기존 키 재조회 (Decoding 키 사용)
   - `KMA_API_HUB_KEY`: 선택. [기상청 API 허브](https://apihub.kma.go.kr/)에서 발급 후 입력. 미설정 시 공식 특보 조회만 생략
   - `GOOGLE_SHEETS_SPREADSHEET_ID`: 대상 스프레드시트 URL의 `/d/`와 `/edit` 사이 부분
   - `SITES`: 현장 목록 (GitHub Secrets의 `SITES_JSON`과 동일 — 값을 직접 조회할 수는 없으니, 필요하면 다시 정리)
     - 공식 특보 매칭은 각 현장에 `warning_region_codes` 또는 `warning_region_keywords`를 추가하면 정확해집니다. 둘 다 없으면 현장명에 포함된 지역명으로 자동 매칭합니다.
   - `credentials/google-service-account.json`: Google Cloud Console에서 동일 서비스 계정으로 **새 키를 발급**받아 배치 (`credentials/README.md` 참고). 기존 키 파일을 USB/메신저로 옮기는 것보다, 콘솔에서 새로 발급받는 편이 안전합니다.

5. **동작 확인**
   ```bash
   python -m src.main
   ```

6. **자동 테스트**
   ```bash
   python -m unittest discover -s tests -v
   ```

## 변화 감지 결과

- `docs/weather-state.json`: 다음 실행과 비교할 공개용 최소 상태. 개인정보는 포함하지 않음
- `docs/latest-alert.txt`: 가장 최근에 감지된 기상변화와 현장 확인사항
- `docs/notification-outbox.json`: 알림별 대기·성공·실패 및 재시도 상태
- 대시보드의 `최근 기상변화`: 마지막 변화가 발생한 시각과 대상 현장

위험 수치가 조금 달라진 것만으로는 알리지 않으며, 위험단계·위험종류 변경, 새 예보 위험,
데이터 수집 장애와 정상화가 발생할 때만 새 알림 문안을 생성합니다.

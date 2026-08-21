# 전사 기상 자동감시·알림 시스템

기상청 API로 현장별 기상 데이터를 주기적으로 수집하고, Google Sheets에 자동 기록하며,
이상기상 발생 시 관련 담당자에게 알림을 보내는 시스템입니다.

## 프로젝트 목표

- 전사 현장(공사현장 등)의 기상 상황을 자동으로 감시
- 강풍/호우/폭염 등 위험 기상 조건 발생 시 자동 알림
- 안전관리자가 매번 수기로 기상청 사이트를 확인하지 않아도 되도록 자동화

## Phase 구성

- **Phase 1 (완료)**: 개발환경 준비 + 기상청 API(초단기실황/단기예보) → Google Sheets 자동 기록
- **Phase 1.5 (완료)**: GitHub Actions로 현장 운영시간(KST 04:00~18:00) 매시 45분 자동 실행 — 로컬 컴퓨터를 켜둘 필요 없음
- Phase 2: 이상기상 판정 로직 + 알림 발송 (예: 카카오톡/이메일/슬랙)

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
│   ├── sheets_client.py   # Google Sheets 기록
│   ├── grid_converter.py  # 위경도 -> 기상청 격자좌표 변환
│   └── main.py            # 실행 진입점
├── credentials/          # 인증정보 보관 (git에 올라가지 않음)
└── tests/                # 테스트 코드
```

## 클라우드 자동 실행 (GitHub Actions)

이 저장소는 GitHub Actions로 현장 운영시간(KST 04:00~18:00) 동안 매시 45분에 자동 실행되도록 설정되어 있습니다.
(야간에는 현장에 인원이 없어 실행하지 않으며, GitHub Actions 무료 사용량 절약에도 도움이 됩니다.)
**로컬 컴퓨터를 켜둘 필요가 없고, 어느 컴퓨터에서 이 저장소를 열든 클라우드 실행에는 영향이 없습니다.**

사용하는 GitHub Secrets (저장소 Settings → Secrets and variables → Actions에서 확인/재설정 가능, 값 조회는 불가):

| Secret | 내용 |
|---|---|
| `KMA_API_KEY` | 기상청 공공데이터포털 인증키 (Decoding 키) |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | 기록 대상 스프레드시트 ID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 구글 서비스 계정 키 JSON 전체 내용 |
| `SITES_JSON` | 현장 목록 (JSON) — `config.py`의 `SITES`와 동일 형식 |

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
   - `GOOGLE_SHEETS_SPREADSHEET_ID`: 대상 스프레드시트 URL의 `/d/`와 `/edit` 사이 부분
   - `SITES`: 현장 목록 (GitHub Secrets의 `SITES_JSON`과 동일 — 값을 직접 조회할 수는 없으니, 필요하면 다시 정리)
   - `credentials/google-service-account.json`: Google Cloud Console에서 동일 서비스 계정으로 **새 키를 발급**받아 배치 (`credentials/README.md` 참고). 기존 키 파일을 USB/메신저로 옮기는 것보다, 콘솔에서 새로 발급받는 편이 안전합니다.

5. **동작 확인**
   ```bash
   python -m src.main
   ```

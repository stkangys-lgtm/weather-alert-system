# Claude Code 작업 인수인계

이 파일은 Claude Code가 프로젝트를 열었을 때 가장 먼저 읽어야 하는 현재 작업 지침이다.
사용자와의 대화는 한국어로 하고, 비개발자도 이해할 수 있도록 결과와 영향을 먼저 설명한다.

## 프로젝트 목적

현대아산 본사 안전경영팀이 전국 건설현장의 기상상황을 한눈에 확인하고, 특이기상 발생 시
필요한 안전보건 조치와 현장 전파 문안을 자동으로 준비하는 시스템이다. 현장 안전관리자는
자기 현장 정보만 쉽게 확인하고, 본사는 전 현장 현황과 공문·전파 문안을 관리하는 방향으로
고도화할 예정이다.

현장 센서 설치처럼 비용·허가·접근이 필요한 방식은 최소화하고, 기상청 공개 API와 기존 업무
자료를 우선 활용한다.

## 현재 운영 상태 (2026-09-27)

- GitHub 저장소: `https://github.com/stkangys-lgtm/weather-alert-system`
- 운영 브랜치: `main`
- 공개 관제 화면: `https://stkangys-lgtm.github.io/weather-alert-system/`
- 새 본사 화면: 위 주소(`docs/index.html` ← `web/index.html`). 현장 목록 표는 주소 끝 `#list`
- 현장 화면: `…/site.html?id=현장ID` (ID 없으면 현장 선택 목록). 본사 상세의 "현장 화면" 버튼으로 연결. 휴대폰 홈 화면에 추가하면 그 현장으로 바로 열린다(`docs/manifests/<ID>.webmanifest`, 수집 실행이 생성)
- 이전 화면(2주간 병행, 5단계에서 정리): `…/old/index.html`(지도), `…/old/sites.html`(카드). `map.html`·`sites.html`은 이동 안내 페이지
- 자동 수집: `.github/workflows/collector.yml`
- 전체 테스트: **164개 통과** (2026-09-27 갱신). `config.py`가 없는 PC에서도 가짜 값(`tests/secretless_env.py`)으로 모두 돈다

### 대시보드 리디자인 진행 (2026-09-26~)

- 설계: `design/specs/2026-09-26-dashboard-redesign-design.md`, 계획: `design/plans/`
- 1단계(데이터 층): 매 실행마다 `docs/data/latest.json` 생성. 기존 화면·알림은 그대로.
- 중기예보 날짜를 발표일 기준으로 수정(새벽 실행 하루 밀림 해결).
- 2단계(본사 화면): 화면 원본은 `web/`(HTML·CSS·JS, 빌드 도구 없음). 수집 실행 뒤 `src/publish.py`가 점검(외부 파일 무결성 해시·전화번호·금지어·비공개 값) 후 `docs/`로 복사한다.
  화면을 고칠 때는 `web/`만 수정하고 `docs/`의 게시본은 직접 고치지 않는다.
  로컬 확인: `python3 -m src.publish`(web/ → docs/) → `python3 scripts/preview_fixtures.py`(시험 자료: rain·failed·partial·night·escape·noforecast·onset → `.superpowers/preview/fixtures/`) → 저장소 폴더를 정적 서버로 열고(`python3 -m http.server 8765`) `http://localhost:8765/docs/index.html?data=../.superpowers/preview/fixtures/rain.json` 또는 `docs/site.html?data=…&id=현장ID`. `?map=svg`는 자체 지도 강제. 시험 자료는 만든 뒤 시간이 지나면 "수집 지연"이 뜨는 게 정상.
  로컬 `src.publish`로 바뀐 `docs/`는 커밋하지 않고 `git checkout -- docs && git clean -fd docs`로 되돌린다(공개본은 자동 수집이 올린다).
- 3단계(현장 화면·홈 화면 추가, 2026-09-27 배포): `web/site.html`·`site.css`·`site.js`(본문)·`site-map.js`(지도·시트). 본사 상세와 현장 화면이 함께 쓰는 부품은 `web/assets/parts.js`와 `app.css` 끝 절. 계획서 `design/plans/2026-09-27-phase3-site-ui.md`.
- 승인된 시안: `design/prototypes/`(본사·현장 인터랙티브 시안, README 참고).
- 화면 확인: `node scripts/ui_check.mjs <단계.json>`(헤드리스 Chrome/Edge, 임시 프로필, 브라우저 위치 자동 탐색·`CHROME` 환경변수로 지정 가능) — 앱 미리보기 창이 가려지면 지도가 그려지지 않으므로 이 도구로 본다. 휴대폰 동작은 마우스(`click`·`drag`)만으로는 스크롤 충돌을 못 잡으므로 손가락 단계(`touch`·`swipe`·`tap`)로 확인한다. 시계를 바꿔 보려면 `initScript`. JS 부품 단위 확인은 node `vm`으로 `common.js`·`parts.js`를 읽어 확인(점검 환경에서 `ctx.window = ctx` 필요).

#### 다음 단계
- **4단계(레이더)**: 설계서 5.8절. 공공데이터포털 레이더영상 API(기존 `KMA_API_KEY`로 호출 확인됨)는 배경·범례가 들어간 완성 이미지(LCC 투영)라, 서버에서 강수 색 추출 → 좌표 보정 → 우리 파랑 단계로 다시 칠해 지도에 겹친다. 먼저 좌표 보정 시험(오차 5km 이내)을 하고, 통과 못 하면 "레이더 원본 영상 보기" 카드로 대체. 시안의 비구름 버튼·"주변 비구름" 카드 참고.
- **5단계(정리)**: `docs/old/`·`src/map_dashboard.py`·`src/dashboard.py` 등 이전 화면 삭제(2주 병행 뒤).
- 사용자 결정 대기: 전파 문안 조치 항목이 붙는 조건(현재 비 0.1mm/h·바람 9m/s부터 — 사내 기준 없음).

#### 미룬 작은 개선(필요할 때 처리)
- 3단계: 키보드 초점이 반쯤 내린 시트 밖으로 감(`.sc` scroll-padding, "지도로 보기" 뒤 초점 이동) / iOS 홈 화면 이름이 모두 "기상안전" / 현장 선택 화면에서 홈 화면 추가 시 본사 앱 / `publish._SAFE_ID.match`가 끝 줄바꿈 허용(fullmatch) / 문지를 때 같은 시각도 다시 그림 / "관측 · 맑음"의 하늘은 다음 시각 예보값 / 중기 기온만 빠진 날도 "예보 자료 없음" / 선택 화면으로 열린 뒤 갱신으로 현장이 생기면 지도 미시작 / 자체(SVG) 지도에서 "지도로 보기" 확대 없음·창 크기 변경 시 재중심 / 선택 화면 위 빈 띠·실패 표시·이름 변경 시 홈 화면 다시 추가 안내 / `ui_check` 실패 시 브라우저 정리(try/finally) / `mobile-web-app-capable` 추가 / 갱신 뒤 고른 시각을 칸 위치로 유지. 실기기(아이폰·삼성 인터넷) 설치 확인은 사용자가 한다.
- 2단계: 1280×720 등 중간 폭에서 범례·지도 버튼 겹침 / 전체 수집 실패 시 요약 라벨 / 선택 이름표가 묶음에 가려짐·경보 지도 고리 주황 / '50 이상mm'·'MM/H' 표기 / 동작 줄이기 설정 시 flyTo / aria-live 과다·정렬 aria-pressed / 1.3초 자동 선택이 사용자 선택을 덮음 / publish 검사 예외(작은따옴표·`//` 주소)·`publish_screens` 테스트.
- 1단계: 단기예보 실패 시 일별 날짜별 이어받기 / 이어받은 now·hourly·daily 재필터 / `issued_at` 실제값 / `main.py` import 보호.

#### 디자인 작업 방식(사용자 합의)
- "완성 시안"은 정적 그림이 아니라 실제 크기로 눌러 볼 수 있는 인터랙티브 시안으로 보여 준다(참고 기준: Flighty — 전체 지도 + 떠 있는 유리 패널 + 큰 숫자 하나 + 짧은 상태 글자).
- CI 원색은 쨍하다고 싫어함 → 같은 색상에서 채도를 낮춘 딥 네이비(#2b4775) 계열. 로고만 공식 원색.
- 위험은 사내 "기준/등급"을 만들지 말고 조건·수치 그대로("비 31mm/h"). 빨강·주황은 기상청 특보·법정 조치에만(아이콘 동반), 시스템 상태는 회색.

### 이번 세션(2026-09-20)에서 추가된 것

1. **수집 지연 개선** (`62f9358`) — `src/collection.py` 신설.
   - 동일 (nx, ny) 격자 캐시로 중복 호출 제거.
   - ThreadPoolExecutor(max_workers=6) 병렬 수집.
   - `CircuitBreaker`(임계치 3회 실패)를 실황·예보·중기·특보가 공유해 장애 시 재시도
     대기를 즉시 건너뛴다.
   - `kma_client._request` / `mid_client._request` / `warning_client._request`에
     `breaker` 인자 추가.
   - `tests/test_collection.py`(8건)로 격자 캐시·병렬 순서 보존·회로 차단 공유·부분
     실패 격리·전면 장애 예산(0.6s) 회귀 검증.
2. **문안 톤 상황 반응형** (`56e8ac1`) — `src/alert_rules.py` 헬퍼 추가.
   - `_situational_title(active_categories)`: 폭염만 → `【온열질환 안전관리 사항】`,
     복합 → `【수방 및 온열질환 안전관리 사항】`.
   - `_situational_closing(active_categories)`: 활성 위험 있을 때만
     "각 현장에서는 X가 실제 이행될 수 있도록 관리하여 주시기 바랍니다." 마무리 문단.
   - `state_monitor.build_alert_message`도 같은 톤(■ 공지드립니다 → 【제목】 → ① 변동
     현황 → ② 본사·현장 확인사항 → 마무리 → 감사합니다)으로 정돈.
3. **미확정 사내 기준 표현 삭제** (최신 커밋) —
   - "사내 선제감시 기준 도달" 같은 존재하지 않는 사내 표준을 참조하는 표현을
     상황 서술형(`{현장}에서 {카테고리} 위험이 우려되는 기상 상황이 확인되고 있습니다.`)
     으로 교체. `alert_rules` 모듈 도크스트링도 소프트화.

### 수집 시간 실측 (2026-09-28 확인)

개선(2026-09-20) 이후 실행 61회를 집계한 결과, **61회 모두 성공**했다(실패·취소 0건).
실행 시간은 워크플로 전체 기준으로 중앙값 55초, 최소 12초(:17 보완 실행 생략분), 최대 3분 59초,
상위 90% 3분 47초이고, 3분을 넘긴 실행은 8회다. 개선 전에는 12분 50초가 걸려 10분 제한에
걸리는 일이 잦았다.

## 절대 지켜야 할 안전 제약

1. `NOTIFICATION_MODE`는 반드시 `shadow`로 유지한다.
2. 사용자가 기존 문자·공문 양식을 제공하고, 생성 문안을 검토·승인하고, 실제 발송 전환을
   명시적으로 승인하기 전에는 `live`로 바꾸거나 외부 메시지를 발송하지 않는다.
3. Webhook Secret이 등록돼 있어도 shadow 모드에서는 외부 통신이 차단돼야 한다.
4. `config.py`, `credentials/`, API 키, 서비스 계정 JSON, Webhook 토큰, 담당자 전화번호를
   커밋하거나 공개 `docs/` 파일에 넣지 않는다.
5. 이 저장소와 GitHub Pages는 공개 상태다. `docs/`에는 공개 가능한 기상·조치 정보만 둔다.
6. 법적 판정, 기상청 공식 특보, 자체 상황 신호를 혼동하지 않는다.
   - 기상청 공식 특보: 실제 발표 자료
   - 법정 작업중지·조치: 공종과 법정 실측값을 함께 확인한 결과
   - 자체 상황 신호(내부 명칭 '선제알림'): 공공 격자 기상자료로 관측한 참고용 상황이며,
     확정된 사내 기준이 아니다. 문안에도 '기준 도달'처럼 표준이 있는 것 같은 표현을
     쓰지 않고 상황 서술형으로 표기한다.
7. 법률 근거를 변경할 때는 국가법령정보센터 원문과 시행일을 다시 확인하고 근거 문서도 갱신한다.

## 주요 파일

- `src/main.py`: 실행 진입점과 전체 흐름
- `src/view_model.py`: 화면용 공개 데이터 `docs/data/latest.json` 조립(허용 목록 필드만), 마지막 정상 자료 유지
- `src/narrative.py`: 현장·전국 요약 문장과 전파 문안(금지어 검사 포함)
- `src/intensity.py`: 기상청 예보용어(2025-06-11) 강수·바람 세기 표현
- `src/site_profile.py`: 현장 공개 ID·짧은 이름·지역
- `src/schedule.py`: 다음 수집 시각(워크플로 일정 변경 시 함께 수정)
- `src/collection.py`: 실황·예보 병렬 수집. 격자 캐시·회로 차단(`CircuitBreaker`) 포함.
  실황·예보·중기·특보 호출이 하나의 breaker를 공유한다.
- `src/warning_client.py`: 공공데이터포털 공식 기상특보 수집 및 현장 매칭
- `src/legal_rules.py`: 작업 종류·실측값 기반 법정 조치 판정
- `legal/LEGAL_WEATHER_SAFETY_MATRIX_2026-09-20.md`: 법적 기준과 원문 링크
- `src/state_monitor.py`: 이전 상태 비교와 변화 알림 생성 (문안 톤 alert_rules와 공유)
- `src/alert_rules.py`: 정기 공고문 생성. `_situational_title`·`_situational_closing`
  헬퍼가 카테고리 조합에 따라 【제목】과 마무리 문단을 자동 조립.
- `src/notification_queue.py`: 알림 대기열, 중복 방지, 재시도, shadow/live 제어
- `src/map_dashboard.py`: 지도 중심 본사 관제 화면 — 이전 화면(docs/old/), 5단계에서 삭제 예정
- `src/dashboard.py`: 현장별 카드 화면 — 이전 화면(docs/old/), 5단계에서 삭제 예정
- `src/publish.py`: `web/` → `docs/` 게시와 게시 전 점검, 이전 화면 경로(`docs/old/`)
- `web/`: 새 화면 원본 — `index.html`(본사), `assets/common.js`(공통), `geo.js`(지도·자체 지도 전환), `hq*.js`(본사 모듈), `tokens.css`·`app.css`·`hq.css`, `icons.svg`, `brand/`(공식 로고, 가공 금지)
- `web/site.html`·`assets/site*.js`·`site.css`: 현장 화면, `assets/parts.js`: 현장 카드 공통 부품, `manifest.webmanifest`·`assets/icons/`: 홈 화면 추가
- `scripts/ui_check.mjs`: 헤드리스 Chrome 화면 점검 도구(단계 JSON → 결과·콘솔 오류·캡처)
- `scripts/preview_fixtures.py`: 화면 확인용 시험 자료 생성(공개 폴더 밖)
- `src/weekly_work_importer.py`: 회의자료 XLSX에서 현장명과 금주 공종만 선별 (PDF 미지원)
- `config.example.py`: 현장·공종·특보 구역 설정 예시
- `README.md`: 설치 및 운영 설명

`src/kma_warning_client.py`는 이전 API Hub 특보 방식과의 호환을 위해 남아 있다. 현재 주 실행은
`src/warning_client.py`와 공공데이터포털의 `KMA_API_KEY`를 사용한다.

## 다음 작업 우선순위

### 1. 현장 주소 DB 연계

현장 목록·정확한 주소의 원천은 **업무용 PC에 있는 사업장 현황 엑셀 DB(민감자료)**다. 경로는 저장소에
적지 않는다 — 처음 필요할 때 사용자에게 경로를 물어본다. 이 파일에는 담당자 이름·연락처·이메일 같은
개인정보 열이 있으므로 **공사명·공종·주소(시·군 단위까지)만 읽고, 개인정보 열은 읽어 출력하거나
저장·커밋하지 않는다.** 파일 내용·목록을 저장소에 올리지 않는다.

- 2026-09-26 대조: 관제 대상 21곳 중 20곳 지역 일치, 양산 부산대병원은 경남 양산시로 바로잡음.
  DB에만 있고 관제 대상이 아닌 현장의 추가 여부는 사용자 판단 대기.
- 다음 과제(사용자 요청, 아직 설계 전): 현장을 추가할 때 DB를 활용해 한 번에 갱신하는 방법.
  지금 현장 정보는 GitHub Secret `SITES_JSON`(운영 목록), `src/warning_client.KNOWN_SITE_REGIONS`(특보 구역),
  `src/site_profile.SITE_SHORT_NAMES`(짧은 이름)에 흩어져 있다 → 로컬에서 DB를 읽어 이 셋을 함께
  갱신하는 도구가 후보. 설계안을 먼저 사용자에게 보여 주고 승인받는다.

필요한 최소 필드는 현장명, 주소 또는 위경도, 활성 여부다. 주소에서 위경도를 얻어야 할 경우 무료이면서
이용약관상 허용된 방식을 검토하고, 추측 매칭 결과는 사용자 확인을 받는다.

연계 결과에는 가능하면 다음 값을 채운다.

- `lat`, `lon`
- 기상청 격자 `nx`, `ny`
- `warning_regions`, `warning_provinces`
- `active`
- 사용자가 제공하거나 확인한 경우에만 `work_types`, `active_work_types`

### 2. 기존 문체 학습과 승인

사용자가 기존 문자·공문 양식을 추후 제공할 예정이다. 양식을 받으면 다음 순서로 진행한다.

1. 개인정보와 기밀정보를 분리하고 원문 공개 커밋을 피한다.
2. 인사말, 제목, 위험 설명, 조치 문구, 현장명 표기, 종결어미, 길이 등 문체 규칙을 추출한다.
3. 실제 발송 없이 예시 문안 여러 건을 생성한다.
4. 사용자 검토와 수정을 받아 문체 규칙을 확정한다.
5. 확정된 규칙만 코드나 비민감 템플릿으로 반영한다.
6. shadow 모의운영 결과를 다시 확인한다.
7. 사용자가 별도로 명시 승인하기 전에는 live 발송을 활성화하지 않는다.

**진행 상황 (2026-09-20)**: 폭염 3건 + 우천·폭염 복합 1건 = 총 4건 확보. 톤을
`alert_rules._situational_title` / `_situational_closing`에 반영. 사용자는
"엄격하지 않고 상황에 맞춰 유동적"을 요청. 아직 확보 못한 유형:
- 강풍 **단독** 문안 (지금까지 태풍·우천과 세트로만 등장)
- 호우 **단독** 문안
- 대설·한파 (결빙·미끄럼·동결 어휘)
- 특보 해제 안내문

새 위험 유형 샘플을 받으면 카테고리별 문구를 세분화한다. 실명·연락처는 자리표시자
(`[안전경영팀 담당 매니저]` 등)로만 반영하고 저장소 어디에도 원문을 두지 않는다.
`NOTIFICATION_MODE=live` 전환은 **여전히 금지** 상태.

### 3. 수집 지연 개선 (2026-09-20 완료, 2026-09-28 실측 검증 완료)

코드 개선은 완료됨 (`src/collection.py`).

- 동일 격자 요청 캐시 ✓
- 제한된 동시성 병렬 수집 (max_workers=6) ✓
- 회로 차단(3회 실패 시 재시도 즉시 종료) ✓
- 실황·예보·중기·특보 breaker 공유 ✓
- 최대 대기시간 회귀 테스트(0.6s 예산) ✓

실측 결과: 개선 전 12분 50초 → 개선 후 중앙값 55초, 최대 3분 59초(61회 모두 성공).
자세한 수치는 위 "수집 시간 실측" 절 참고.

### 4. 본사·현장 로그인 분리

향후 목표는 본사 관리자와 현장 사용자의 화면·권한 분리다.

- 본사: 전 현장 지도·목록, 공문/전파문 생성, 상태 확인
- 현장: 배정된 자기 현장 기상·예보·조치만 조회

현재 GitHub Pages는 정적 공개 사이트라 안전한 로그인과 서버 측 권한통제가 없다. 화면만 숨기는
방식은 보안이 아니다. 실제 로그인 구현 전에는 인증·DB·권한통제가 가능한 별도 백엔드 구조를
먼저 제안하고 사용자 승인을 받아야 한다.

## 새 PC에서 이어 하기 (2026-09-27, 4단계부터 업무용 PC)

1. 설치: Git, GitHub CLI(`gh auth login`으로 로그인), Python 3.9 이상(`pip install -r requirements.txt`),
   Node 22 이상(화면 확인 도구), Chrome(없으면 Windows의 Edge를 대신 씀), Claude Code.
2. 저장소 받기: `git clone https://github.com/stkangys-lgtm/weather-alert-system.git`
3. Claude Code 플러그인: 이 저장소의 `.claude/settings.json`에 적어 두어, 저장소 폴더를 신뢰하면 설치를
   안내한다. 안내가 없으면 터미널에서 직접 설치한다.
   ```bash
   claude plugin marketplace add obra/superpowers-marketplace
   claude plugin install superpowers@superpowers-marketplace
   claude plugin marketplace add anthropics/claude-code
   claude plugin install frontend-design@claude-code-plugins
   ```
   superpowers는 계획서 작성 → 단계별 실행 → 최종 검토 방식(1~3단계와 같게 계획서는 `design/plans/`, 최종 검토는 가장 성능 좋은 모델),
   frontend-design은 화면 디자인 보조다.
4. 비밀 설정: `config.py`·`credentials/`는 git에 없다. 테스트는 없어도 통과한다. 실제 기상청 호출이 필요한
   확인(4단계 레이더 시험 등)에는 사용자가 이 두 가지를 USB 등으로 직접 복사한다 — 채팅에 붙여 넣게 하지 않는다.
5. Windows: 이 문서의 `python3`은 `python` 또는 `py -3`으로 바꿔 실행한다.

업무용 Windows PC 준비 완료(2026-09-28): Python 3.12, Node 24 LTS(winget 설치), Chrome, GitHub CLI 로그인,
`config.py`·`credentials/` 배치, 테스트 164개 통과. 새로 연 PowerShell·Git Bash에서 `node`가 안 잡히면
창을 새로 열어 PATH를 다시 읽힌다.

## 작업 시작 절차

```bash
git status -sb
git fetch origin
git pull --ff-only
python3 -m unittest discover -s tests -v
```

`main`에는 GitHub Actions가 `docs/` 자동 갱신 커밋을 자주 추가한다. 작업 전에 반드시 최신 원격을
받고, 사용자의 미커밋 변경이 있으면 보존한다. 충돌 시 자동 생성된 문서만 보고 소스 변경을
덮어쓰지 않는다.

로컬 실제 실행(수집·발송 흐름)에는 git에서 제외된 `config.py`와 인증정보가 필요하다(테스트·화면 확인에는 불필요). 값이 없으면 사용자에게
키 자체를 채팅에 붙여 넣으라고 요구하지 말고, 로컬 파일 또는 GitHub Secrets에 안전하게
설정하도록 안내한다.

## 검증과 배포

변경 후 최소 검증:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

GitHub Actions를 수동 실행할 때는 먼저 워크플로우의 `NOTIFICATION_MODE: shadow`를 확인한다.
실행 후 로그에서 아래 항목을 확인한다.

- 공식 특보 수집 성공 또는 명확한 실패 표시
- 데이터 미수신을 정상으로 판정하지 않았는지
- `[알림 전달: 모의운영(외부 발송 차단)]`
- 발송 `0건`
- 공개 대시보드에 개인정보가 포함되지 않았는지

배포 결과를 사용자에게 보고할 때는 테스트 개수, Actions 성공/실패, 실제 발송 0건 여부,
데이터 수집 장애 여부, 공개 화면 링크를 간단히 설명한다.

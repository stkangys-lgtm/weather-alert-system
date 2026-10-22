# 외부 예약 서비스로 수집 실행하기 (cron-job.org)

작성 2026-10-22. 이 문서에는 토큰 값을 적지 않는다(공개 저장소).

## 왜 필요한가

수집 워크플로(`.github/workflows/collector.yml`)는 한국시각 04~17시 :17·:47마다 돌도록 예약돼 있지만,
GitHub 예약 실행은 많이 빠지고 늦는다. 2026-10-08~21 실측: 하루 6~8회만 실행, 업무시간 공백 3~7시간.
그래서 외부 예약 서비스가 정해진 시각에 GitHub에 "수집 실행"을 요청하게 한다.
GitHub 자체 예약은 그대로 두어 외부 서비스가 멈췄을 때의 예비로 쓴다.

같은 시각에 두 요청이 겹쳐도 한 번만 수집한다(`src/schedule.py`).

| 실행 | 수집 조건 |
| --- | --- |
| :47 주 실행(외부 `auto` 또는 GitHub 예약) | 직전 정상 수집이 20분 넘게 지났을 때 |
| :17 보완 실행(외부 `auto` 또는 GitHub 예약) | 직전 정상 수집이 45분 넘게 지났을 때(주 실행이 빠졌을 때만) |
| Actions 화면에서 직접 실행(`manual`) | 항상 |

## 1. GitHub 실행 권한 키(토큰) 만들기 — 사용자가 직접

1. https://github.com/settings/personal-access-tokens/new 접속(Fine-grained token).
2. Token name: `weather-collector-trigger`
3. Expiration: 1년 뒤 날짜(만료일을 달력에 적어 둔다).
4. Repository access: **Only select repositories** → `weather-alert-system`만 선택.
5. Permissions → Repository permissions → **Actions: Read and write** 하나만 켠다(Metadata: Read-only는 자동).
6. Generate token → 화면에 한 번만 보이는 값을 복사해 바로 2단계 칸에 붙여 넣는다.
   채팅·메모장·파일에 붙여 넣지 않는다.

이 키로 할 수 있는 일은 이 저장소의 Actions 실행·취소뿐이다. 코드 변경이나 비밀값 열람은 할 수 없다.

## 2. cron-job.org에 예약 만들기 — 사용자가 직접

1. https://console.cron-job.org/signup 에서 가입(무료)·메일 인증 후 로그인 → Dashboard → **Create cronjob**.
2. 기본(Common)
   - Title: `기상안전 수집`
   - URL: `https://api.github.com/repos/stkangys-lgtm/weather-alert-system/actions/workflows/collector.yml/dispatches`
   - Execution schedule: 사용자 지정(Custom) — 분 `17, 47`, 시 `4`~`17`, 매일.
     crontab 식을 넣는 칸이면 `17,47 4-17 * * *`
   - 실패 알림(실행 실패·자동 중지 알림)을 켠다 — 키가 만료되면 메일로 알 수 있다.
     cron-job.org는 25번 연속 실패한 예약을 자동으로 끈다.
3. 고급(Advanced)
   - Time zone: `Asia/Seoul`(화면에 따라 Common 탭의 일정 아래에 있을 수 있음)
   - Request method: `POST`
   - Headers(3개):
     - `Accept` : `application/vnd.github+json`
     - `Authorization` : `Bearer ` 뒤에 1단계에서 복사한 키(띄어쓰기 한 칸 포함)
     - `Content-Type` : `application/json`
   - Request body: `{"ref":"main","inputs":{"mode":"auto"}}`
4. 아래쪽 **Test run**을 눌러 응답이 `200` 또는 `204`인지 확인한 뒤 저장(Create/Save)한다.
   시험 실행도 실제 실행 요청이라 Actions에 실행이 하나 생긴다(직전 수집이 최근이면 건너뛰고 끝난다).

## 3. 확인

- GitHub 저장소 → Actions → Weather Collector에 `workflow_dispatch`로 시작된 실행이 생긴다.
- 실행 기록(`python -m src.main` 단계)에 수집 결과 또는 `[중복 실행 건너뜀]`·`[보완 실행 건너뜀]`이 찍힌다.
- 하루 지나 실행 횟수를 다시 센다(목표: 04~17시 매시 :47 수집, 업무시간 공백 1시간 이내).

## 문제가 생기면

| 증상 | 원인·조치 |
| --- | --- |
| 응답 401 | 키가 틀렸거나 만료 → 1단계로 새 키를 만들어 Authorization 값만 바꾼다(자동 중지됐으면 예약을 다시 켠다) |
| 응답 403 | 키에 Actions 쓰기 권한이 없음 → 1단계 5번 확인 |
| 응답 404 | URL 오타 또는 키에 이 저장소 권한이 없음 |
| 응답 422 "Unexpected inputs" | 워크플로에 `mode` 입력이 없는 옛 버전 → 최신 `main`인지 확인 |
| 외부 서비스가 멈춤 | GitHub 자체 예약이 예비로 계속 돈다(하루 6~8회 수준) |

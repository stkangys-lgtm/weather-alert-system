"""다음 실제 수집 시각을 계산한다(.github/workflows/collector.yml 일정 기준).

- 매시 :47이 주 실행이고, :17 보완 실행은 직전 수집이 45분 넘게 지났을 때만 수집한다.
- 운영시간은 한국시각 04:17~17:47(UTC 19~23시, 0~8시). 하루 첫 실행 04:17은 전날
  자료가 오래되어 실제로 수집한다.
- 워크플로 일정이 바뀌면 tests/test_schedule.py가 실패하므로 이 파일도 함께 고친다.
"""

from datetime import datetime, time, timedelta

FIRST_RUN = time(4, 17)
PRIMARY_MINUTE = 47
FIRST_HOUR, LAST_HOUR = 4, 17
WINDOW_LABEL = "04:17-17:47"


PRIMARY_DEDUPE_MINUTES = 20
BACKUP_FRESH_MINUTES = 45


def resolve_run_mode(mode, now):
    """실행 종류를 정한다: primary(주), backup(보완), manual(사람이 직접 실행 — 항상 수집).

    외부 예약 서비스는 :17과 :47에 같은 요청(auto)을 보내므로 한국시각 분으로 나눈다.
    """
    if mode == "auto":
        return "primary" if now.minute >= 40 else "backup"
    if mode in ("primary", "backup"):
        return mode
    return "manual"


def skip_reason(mode, age_minutes):
    """수집을 건너뛸 이유(로그 문장)를 돌려준다. 수집해야 하면 None.

    외부 예약과 GitHub 예약이 같은 시각에 함께 오거나 GitHub 예약이 늦게 도착해도
    한 번만 수집하도록, 직전 정상 수집이 충분히 최근이면 건너뛴다.
    """
    if age_minutes is None:
        return None
    if mode == "backup" and age_minutes < BACKUP_FRESH_MINUTES:
        return f"[보완 실행 건너뜀] 마지막 정상 수집이 {age_minutes:.0f}분 전입니다"
    if mode == "primary" and age_minutes < PRIMARY_DEDUPE_MINUTES:
        return f"[중복 실행 건너뜀] 마지막 정상 수집이 {age_minutes:.0f}분 전입니다"
    return None


def next_collection_at(now):
    day, tz = now.date(), now.tzinfo
    candidates = [datetime.combine(day, FIRST_RUN, tz)] + [
        datetime.combine(day, time(hour, PRIMARY_MINUTE), tz) for hour in range(FIRST_HOUR, LAST_HOUR + 1)
    ]
    for candidate in candidates:
        if candidate > now:
            return candidate
    return datetime.combine(day + timedelta(days=1), FIRST_RUN, tz)

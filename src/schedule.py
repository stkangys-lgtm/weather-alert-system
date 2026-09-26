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


def next_collection_at(now):
    day, tz = now.date(), now.tzinfo
    candidates = [datetime.combine(day, FIRST_RUN, tz)] + [
        datetime.combine(day, time(hour, PRIMARY_MINUTE), tz) for hour in range(FIRST_HOUR, LAST_HOUR + 1)
    ]
    for candidate in candidates:
        if candidate > now:
            return candidate
    return datetime.combine(day + timedelta(days=1), FIRST_RUN, tz)

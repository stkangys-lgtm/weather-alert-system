# 1단계 데이터 층(latest.json) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매 수집 실행마다 화면용 공개 데이터 `docs/data/latest.json`을 만들고, 수집 실패 시 마지막 정상 자료를 시각과 함께 유지한다. 기존 화면·알림은 그대로 둔다.

**Architecture:** 수집(`collection.py`)이 만든 `collected`·`mid_forecasts`를 순수 함수 모듈로 가공한다. 표현은 `intensity.py`, 현장 표시 정보는 `site_profile.py`, 수집 일정은 `schedule.py`, 문장은 `narrative.py`가 맡고, `view_model.py`가 이들을 조립해 허용 목록 필드만 JSON으로 쓴다. `main.py`는 한 줄로 연결하고 실패를 격리한다.

**Tech Stack:** Python 3.12(Actions)·3.9(로컬) 호환 표준 라이브러리만 사용, unittest.

**Spec:** `design/specs/2026-09-26-dashboard-redesign-design.md` (5.2~5.6, 7, 8, 9의 1단계, 10)

**범위:** 설계 문서 9장의 배포 1단계만 다룬다. 2단계(공통 디자인+본사 화면)~5단계(정리)는 이 계획이 반영된 뒤 각각 별도 계획서로 작성한다.

## Global Constraints

- `NOTIFICATION_MODE`는 `shadow`를 유지한다. 알림·공고문·`weather-state.json` 동작을 바꾸지 않는다.
- `docs/`에는 공개 가능한 기상·조치 정보만 둔다. `latest.json`은 허용 목록 필드만 쓴다: 현장 항목 `id, name, short, category, region, lat, lon, state, as_of, now, hourly, daily, warnings, legal, legal_profile, summary, notice`.
- 담당자 이름·연락처(`manager`, `manager_phone` 등)는 어떤 형태로도 `latest.json`에 들어가면 안 된다.
- 금지어: "선제", "기준 도달", "주의 단계", "경계 단계". 문장에 나오면 안 된다.
- 세기 표현은 기상청 예보용어(2025-06-11)만 쓴다. 비: 빗방울 0.1mm 미만 · 약한 비 3mm/h 미만 · 비 3~15 · 강한 비 15~30 · 매우 강한 비 30 이상. 바람: 4m/s 이상에서만 약간 강한 바람(4~9) · 강한 바람(9~14) · 매우 강한 바람(14 이상).
- 실측과 예보는 판단어("훨씬", "크게") 없이 나란히 적는다.
- `hourly`는 관측 시각 이후 최대 24개. `daily`는 내일부터 10일, 단기예보가 하루 12시간 미만이고 중기예보 값도 없으면 `missing: true`.
- `rain_label`/`rain_mm`: 강수없음→"0"/0, 1mm 미만→"<1"/0.5, 범위→"30~50"/하한, 이상→"50 이상"/값, 해석 불가→"-"/null.
- 시각은 모두 한국시각 `+09:00` ISO 문자열.
- 다음 수집: 낮에는 다음 :47, 17:47 이후와 자정~04:16에는 04:17.
- Python 3.9에서도 돌아야 한다(`match`, `X | Y` 타입 표기, `datetime.UTC` 금지). 새 외부 패키지를 추가하지 않는다.
- 테스트는 기존 방식(`unittest`, `python3 -m unittest discover -s tests`)을 따르고 기존 59개를 깨지 않는다.

## Review Focus

1. **첫 실행에서 전 현장 수집 실패 + 이전 파일 없음**: 모든 현장 `missing`, JSON은 정상 생성, 전국 요약 "관측 자료를 받지 못했습니다." → Task 7 테스트.
2. **이전 `latest.json`이 손상되었거나 스키마가 다름**: 무시하고 새로 만든다(예외 없음) → Task 7 테스트.
3. **예상 밖 PCP 문자열**("-", 빈 값, 범위, "이상", 모르는 글자): 오류 없이 "-" 등으로 표시 → Task 5 테스트.
4. **운영시간 경계**(04:17 정각, 17:47 정각, 자정 이후)와 **워크플로 일정 변경**: 다음 수집 시각이 맞고, `collector.yml` 일정이 바뀌면 테스트가 실패해 알려준다 → Task 4 테스트.
5. **새벽 실행(전날 18시 중기예보)**: 10일 예보 날짜가 하루 밀리지 않는다 → Task 1 테스트.

---

## 파일 구성

| 파일 | 역할 |
|---|---|
| `src/kma_client.py` (수정) | `forecast_base_datetime(now)` 공개 헬퍼 추가 |
| `src/mid_client.py` (수정) | `mid_issue_datetime(now)` 공개 헬퍼 추가 |
| `src/collection.py` (수정) | 중기예보 날짜를 발표일 기준으로 계산, `now` 전달 |
| `src/intensity.py` (신규) | 기상청 세기 표현, 숫자 표기 |
| `src/site_profile.py` (신규) | 현장 ID·짧은 이름·지역 |
| `src/schedule.py` (신규) | 다음 실제 수집 시각 |
| `src/narrative.py` (신규) | 현장·전국 요약 문장, 전파 문안, 금지어 검사 |
| `src/view_model.py` (신규) | 예보 값 변환, 현장·전체 데이터 조립, 읽기·쓰기 |
| `src/main.py` (수정) | `latest.json` 생성 연결 |
| `tests/test_intensity.py`, `test_site_profile.py`, `test_schedule.py`, `test_view_model.py`, `test_narrative.py` (신규), `tests/test_collection.py` (수정) | 테스트 |
| `CLAUDE.md` (수정) | 새 파일과 1단계 상태 기록 |

---

### Task 1: 중기예보 날짜를 발표일 기준으로 계산

**Files:**
- Modify: `src/kma_client.py` (`_latest_vfcst_base_time` 아래에 함수 추가)
- Modify: `src/mid_client.py` (`_latest_tmfc` 아래에 함수 추가)
- Modify: `src/collection.py` (`collect_mid_forecasts`)
- Test: `tests/test_collection.py`

**Interfaces:**
- Produces: `kma_client.forecast_base_datetime(now=None) -> datetime`(naive), `mid_client.mid_issue_datetime(now=None) -> datetime`(naive), `collection.collect_mid_forecasts(sites, api_key=None, breaker=None, land_fetcher=None, ta_fetcher=None, now=None) -> dict[str, list[dict]]`. fetcher는 `now=` 키워드를 받는다.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_collection.py` 맨 위 import에 추가:

```python
from datetime import datetime

from src.kma_client import forecast_base_datetime
from src.mid_client import mid_issue_datetime
```

같은 파일의 기존 `test_shared_between_site_and_mid_collection` 안 두 가짜 함수를 아래로 바꾸고(지금은 `now`를 못 받아 예외가 삼켜진 채 통과할 수 있음), 끝에 개수 검사를 추가:

```python
        def fake_land(api_key, reg, now=None, timeout=None, retries=None, breaker=None):
            received_retries.append(retries)
            return {"wf4Am": "맑음"}

        def fake_ta(api_key, reg, now=None, timeout=None, retries=None, breaker=None):
            received_retries.append(retries)
            return {"taMin4": "10"}
```

```python
        self.assertEqual(2, len(received_retries))
        self.assertTrue(all(r == 1 for r in received_retries))
```

(기존 `self.assertTrue(all(r == 1 for r in received_retries))` 줄은 위 두 줄로 교체.) 파일 끝(`if __name__` 위)에 새 클래스 추가:

```python
class MidForecastDateTests(unittest.TestCase):
    SITE = make_site("A", 103, 109, lat=36.68, lon=129.45)

    def _collect(self, now):
        def land(api_key, reg, **kwargs):
            return {"wf5Am": "맑음", "wf5Pm": "구름많음", "rnSt5Am": 10, "rnSt5Pm": 20}

        def ta(api_key, reg, **kwargs):
            return {"taMin5": 17, "taMax5": 23}

        entries = collect_mid_forecasts([self.SITE], api_key="TEST", land_fetcher=land, ta_fetcher=ta, now=now)["A"]
        return {entry["date"]: entry for entry in entries}

    def test_issue_time_helpers(self):
        self.assertEqual(datetime(2026, 9, 25, 18, 0), mid_issue_datetime(datetime(2026, 9, 26, 5, 0)))
        self.assertEqual(datetime(2026, 9, 26, 6, 0), mid_issue_datetime(datetime(2026, 9, 26, 10, 0)))
        self.assertEqual(datetime(2026, 9, 26, 14, 0), forecast_base_datetime(datetime(2026, 9, 26, 15, 0)))

    def test_morning_run_uses_previous_evening_issue_date(self):
        # 06:30 전에는 전날 18시 발표를 쓰므로 "5일 뒤"는 9/25 + 5 = 9/30 이다.
        by_date = self._collect(datetime(2026, 9, 26, 5, 0))
        self.assertEqual("맑음", by_date["2026-09-30"]["sky_am"])
        self.assertEqual(17, by_date["2026-09-30"]["ta_min"])

    def test_daytime_run_uses_same_day_issue_date(self):
        by_date = self._collect(datetime(2026, 9, 26, 10, 0))
        self.assertEqual("맑음", by_date["2026-10-01"]["sky_am"])

    def test_fetchers_receive_now(self):
        seen = []

        def land(api_key, reg, **kwargs):
            seen.append(kwargs.get("now"))
            return {}

        def ta(api_key, reg, **kwargs):
            return {}

        now = datetime(2026, 9, 26, 5, 0)
        collect_mid_forecasts([self.SITE], api_key="TEST", land_fetcher=land, ta_fetcher=ta, now=now)
        self.assertEqual([now], seen)
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m unittest tests.test_collection -v`
Expected: FAIL — `ImportError: cannot import name 'forecast_base_datetime'`

- [ ] **Step 3: 구현** — `src/kma_client.py`의 `_latest_vfcst_base_time` 함수 바로 아래에 추가:

```python
def forecast_base_datetime(now=None):
    """지금 조회되는 최신 단기예보의 발표시각(한국시각, 시간대 정보 없음)."""
    base_date, base_time = _latest_vfcst_base_time(now)
    return datetime.strptime(base_date + base_time, "%Y%m%d%H%M")
```

`src/mid_client.py`의 `_latest_tmfc` 함수 바로 아래에 추가:

```python
def mid_issue_datetime(now=None):
    """지금 조회되는 최신 중기예보의 발표시각(06:00 또는 18:00, 한국시각, 시간대 정보 없음)."""
    return datetime.strptime(_latest_tmfc(now), "%Y%m%d%H%M")
```

`src/collection.py`의 import 줄을 바꾼다:

```python
from src.mid_client import combine_forecast, get_mid_land_forecast, get_mid_temperature, mid_issue_datetime
```

`collect_mid_forecasts` 시그니처에 `now=None`을 추가하고, 기본값 처리 블록 바로 뒤에 발표일을 구한다:

```python
def collect_mid_forecasts(
    sites,
    api_key=None,
    breaker=None,
    land_fetcher=None,
    ta_fetcher=None,
    now=None,
):
```

```python
    # 중기예보의 "N일 뒤"는 발표일 기준이다. 실행한 날 기준으로 계산하면 전날 18시 발표를
    # 쓰는 새벽 실행(04:17~06:17)에서 날짜가 하루씩 밀린다.
    issue_date = mid_issue_datetime(now).date()
```

두 fetcher 호출에 `now=now,`를 추가한다:

```python
                land_cache[land_reg] = land_fetcher(
                    api_key, land_reg, now=now, timeout=mid_timeout, retries=mid_retries, breaker=breaker,
                )
```

```python
                ta_cache[ta_reg] = ta_fetcher(
                    api_key, ta_reg, now=now, timeout=mid_timeout, retries=mid_retries, breaker=breaker,
                )
```

결합 줄을 바꾼다:

```python
            result[site["site_name"]] = combine_forecast(land, temp, base_date=issue_date)
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m unittest tests.test_collection -v`
Expected: 새 테스트 4개 포함 모두 PASS

- [ ] **Step 5: 전체 테스트 후 커밋**

Run: `python3 -m unittest discover -s tests` → Expected: OK
```bash
git add src/kma_client.py src/mid_client.py src/collection.py tests/test_collection.py
git commit -m "중기예보 날짜를 발표일 기준으로 계산해 새벽 실행의 하루 밀림 수정"
```

---

### Task 2: 기상청 세기 표현과 숫자 표기

**Files:**
- Create: `src/intensity.py`
- Test: `tests/test_intensity.py`

**Interfaces:**
- Produces: `DRIZZLE_MAX_MM = 0.1`, `rain_term(mm) -> str | None`, `wind_term(ms) -> str | None`, `fmt_number(value) -> str`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_intensity.py`:

```python
import unittest

from src.intensity import fmt_number, rain_term, wind_term


class IntensityTests(unittest.TestCase):
    def test_rain_terms_follow_kma_boundaries(self):
        cases = [(None, None), (0.05, None), (0.1, "약한 비"), (2.9, "약한 비"), (3, "비"), (14.9, "비"),
                 (15, "강한 비"), (29.9, "강한 비"), (30, "매우 강한 비"), (31, "매우 강한 비")]
        for mm, expected in cases:
            with self.subTest(mm=mm):
                self.assertEqual(expected, rain_term(mm))

    def test_wind_terms_only_from_four_meters(self):
        cases = [(None, None), (3.9, None), (4, "약간 강한 바람"), (8.9, "약간 강한 바람"), (9, "강한 바람"),
                 (13.9, "강한 바람"), (14, "매우 강한 바람")]
        for ms, expected in cases:
            with self.subTest(ms=ms):
                self.assertEqual(expected, wind_term(ms))

    def test_fmt_number(self):
        self.assertEqual("31", fmt_number(31.0))
        self.assertEqual("2.5", fmt_number(2.5))
        self.assertEqual("0.5", fmt_number(0.46))
        self.assertEqual("-", fmt_number(None))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m unittest tests.test_intensity -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.intensity'`

- [ ] **Step 3: 구현** — `src/intensity.py`:

```python
"""기상청 예보용어의 강수·바람 세기 표현.

출처: 기상청 예보용어(2025-06-11, 예보업무규정 제5조에 따른 세부지침)
https://www.weather.go.kr/w/resources/pdf/forecast_terms_list_20250611.pdf
- 강수(시간당): 빗방울 0.1mm 미만, 약한 비 3mm 미만, (보통) 비 3~15mm 미만,
  강한 비 15~30mm 미만, 매우 강한 비 30mm 이상
- 바람: 약한 바람 4m/s 미만, 약간 강한 바람 4~9m/s 미만, 강한 바람 9~14m/s 미만,
  매우 강한 바람 14m/s 이상(강풍주의보 수준)
- 원문 규칙상 바람은 수치를 기본으로 쓰고 주의가 필요한 단계부터 표현을 붙인다.
사내 위험 기준이 아니며 문장에서 세기를 부를 때만 쓴다.
"""

DRIZZLE_MAX_MM = 0.1
_RAIN_STEPS = ((3, "약한 비"), (15, "비"), (30, "강한 비"))
_WIND_NOTICE_MIN = 4
_WIND_STEPS = ((9, "약간 강한 바람"), (14, "강한 바람"))


def rain_term(mm):
    if mm is None or mm < DRIZZLE_MAX_MM:
        return None
    for upper, term in _RAIN_STEPS:
        if mm < upper:
            return term
    return "매우 강한 비"


def wind_term(ms):
    if ms is None or ms < _WIND_NOTICE_MIN:
        return None
    for upper, term in _WIND_STEPS:
        if ms < upper:
            return term
    return "매우 강한 바람"


def fmt_number(value):
    """31.0 → "31", 2.5 → "2.5", None → "-"."""
    if value is None:
        return "-"
    value = round(float(value), 1)
    return str(int(value)) if value.is_integer() else f"{value:.1f}"
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m unittest tests.test_intensity -v`
Expected: 3 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/intensity.py tests/test_intensity.py
git commit -m "기상청 예보용어 기준 강수·바람 세기 표현 추가"
```

---

### Task 3: 현장 ID·짧은 이름·지역

**Files:**
- Create: `src/site_profile.py`
- Test: `tests/test_site_profile.py`

**Interfaces:**
- Consumes: `src.warning_client.site_warning_regions(site) -> (local: list[str], broad: list[str])`
- Produces: `site_id(site) -> str`, `short_name(site) -> str`, `region_label(site) -> str | None`, `SITE_SHORT_NAMES: dict[str, str]`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_site_profile.py`:

```python
import unittest

from src.site_profile import SITE_SHORT_NAMES, region_label, short_name, site_id


class SiteProfileTests(unittest.TestCase):
    def test_configured_id_wins(self):
        self.assertEqual("hupo", site_id({"site_name": "후포 공공하수처리", "id": "hupo"}))

    def test_default_id_is_stable_hash(self):
        self.assertEqual("5355accc", site_id({"site_name": "후포 공공하수처리"}))

    def test_short_name_precedence(self):
        self.assertEqual("후포", short_name({"site_name": "후포 공공하수처리"}))
        self.assertEqual("후포현장", short_name({"site_name": "후포 공공하수처리", "short_name": "후포현장"}))
        self.assertEqual("새 현장", short_name({"site_name": "새 현장"}))

    def test_short_names_are_unique(self):
        names = list(SITE_SHORT_NAMES.values())
        self.assertEqual(len(names), len(set(names)))

    def test_region_from_known_mapping(self):
        self.assertEqual("경상북도 울진군", region_label({"site_name": "후포 공공하수처리"}))
        self.assertEqual("서울특별시 서대문구", region_label({"site_name": "연희·연남동 공공주택"}))

    def test_region_from_config_and_override(self):
        site = {"site_name": "새 현장", "warning_regions": ["화성시", "화성"], "warning_provinces": ["경기도"]}
        self.assertEqual("경기도 화성시", region_label(site))
        self.assertEqual("직접 입력", region_label({"site_name": "새 현장", "region": "직접 입력"}))
        self.assertIsNone(region_label({"site_name": "새 현장"}))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m unittest tests.test_site_profile -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.site_profile'`

- [ ] **Step 3: 구현** — `src/site_profile.py` (짧은 이름 목록은 계획 검토 때 사용자가 확인한 값으로 넣는다):

```python
"""현장의 공개용 식별자·짧은 이름·지역을 정한다. 담당자 정보는 다루지 않는다."""

import hashlib

from src.warning_client import site_warning_regions

# 2026-09 운영 현장의 짧은 이름(사용자 확인). 설정의 short_name이 있으면 그것을 우선한다.
SITE_SHORT_NAMES = {
    "오리온 진천신공장": "진천 신공장",
    "오리온 진천 기숙사": "진천 기숙사",
    "연희·연남동 공공주택": "연희·연남",
    "청정고원 스포츠센터": "청정고원",
    "LX 논현 업무시설": "LX 논현",
    "양산 부산대병원": "양산 부산대병원",
    "군포복합개발": "군포복합개발",
    "오리온수협 목포 김공장": "목포 김공장",
    "렉서스 동탄 네트워크": "렉서스 동탄",
    "화천군부대 시설공사": "화천 군부대",
    "반얀트리호텔 근생동": "반얀트리",
    "포항~안동2 국도건설공사": "포항~안동 국도",
    "시흥능곡 주변도로": "시흥능곡",
    "뇌죽천 하천재해예방": "뇌죽천",
    "산솔면 하수처리장": "산솔면",
    "단월정수장 시설공사": "단월정수장",
    "후포 공공하수처리": "후포",
    "동해안 바닷가 자동차길": "동해안 자동차길",
    "풍각지구 정비사업": "풍각지구",
    "영주 가흥정수장": "가흥정수장",
    "송산그린시티 용수공급시설": "송산그린시티",
}


def site_id(site):
    """설정의 id, 없으면 현장명 SHA-1 앞 8자리. 이름을 바꾸면 id도 바뀐다."""
    configured = str(site.get("id") or "").strip()
    if configured:
        return configured
    return hashlib.sha1(site["site_name"].encode("utf-8")).hexdigest()[:8]


def short_name(site):
    configured = str(site.get("short_name") or "").strip()
    return configured or SITE_SHORT_NAMES.get(site["site_name"]) or site["site_name"]


def region_label(site):
    """설정의 region, 없으면 특보 구역의 광역 정식명 + 첫 세부 구역."""
    configured = str(site.get("region") or "").strip()
    if configured:
        return configured
    local, broad = site_warning_regions(site)
    province = max(broad, key=len) if broad else ""
    parts = [part for part in (province, local[0] if local else "") if part]
    return " ".join(parts) or None
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m unittest tests.test_site_profile -v`
Expected: 6 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/site_profile.py tests/test_site_profile.py
git commit -m "현장 공개 ID·짧은 이름·지역 표기 추가"
```

---

### Task 4: 다음 실제 수집 시각

**Files:**
- Create: `src/schedule.py`
- Test: `tests/test_schedule.py`

**Interfaces:**
- Produces: `WINDOW_LABEL = "04:17-17:47"`, `next_collection_at(now: datetime) -> datetime` (입력과 같은 tzinfo)

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_schedule.py`:

```python
import os
import unittest
from datetime import datetime, timedelta, timezone

from src.schedule import WINDOW_LABEL, next_collection_at

KST = timezone(timedelta(hours=9))


def at(hour, minute, day=25):
    return datetime(2026, 9, day, hour, minute, tzinfo=KST)


class ScheduleTests(unittest.TestCase):
    def test_next_collection(self):
        cases = [
            (at(0, 30), at(4, 17)),
            (at(4, 17), at(4, 47)),
            (at(4, 30), at(4, 47)),
            (at(16, 50), at(17, 47)),
            (at(17, 47), at(4, 17, day=26)),
            (at(23, 0), at(4, 17, day=26)),
        ]
        for now, expected in cases:
            with self.subTest(now=now):
                self.assertEqual(expected, next_collection_at(now))

    def test_window_label(self):
        self.assertEqual("04:17-17:47", WINDOW_LABEL)

    def test_workflow_schedule_matches(self):
        # 워크플로 일정이 바뀌면 이 테스트가 실패한다. 그때는 src/schedule.py도 함께 고친다.
        path = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "collector.yml")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn('cron: "17 0-8,19-23 * * *"', text)
        self.assertIn('cron: "47 0-8,19-23 * * *"', text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m unittest tests.test_schedule -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.schedule'`

- [ ] **Step 3: 구현** — `src/schedule.py`:

```python
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
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m unittest tests.test_schedule -v`
Expected: 3 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/schedule.py tests/test_schedule.py
git commit -m "워크플로 일정 기준 다음 수집 시각 계산 추가"
```

---

### Task 5: 예보 값 변환(실황·시간별·일별)

**Files:**
- Create: `src/view_model.py`
- Test: `tests/test_view_model.py`

**Interfaces:**
- Consumes: `src.feels_like.compute_feels_like(t1h, reh, wsd)`, `src.intensity.fmt_number`
- Produces: `KST`, `HOURLY_COUNT = 24`, `DAILY_COUNT = 10`, `parse_pcp(value) -> (float | None, str)`, `observed_at(current) -> datetime | None`, `now_values(current) -> dict | None`(`temp, feels, rain_mm, wind, humidity`), `hourly_series(forecast, after) -> list[dict]`(`at, temp, rain_mm, rain_label, wind, pop, sky, pty, humidity`), `daily_series(forecast, mid_entries, today) -> list[dict]`(`date, sky, pop, tmin, tmax, source, missing`)

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_view_model.py`:

```python
import unittest
from datetime import date, datetime, timedelta

from src.view_model import KST, daily_series, hourly_series, now_values, observed_at, parse_pcp


def fc_rows(start, hours, pcp_for=lambda at: "강수없음", **defaults):
    rows = []
    for k in range(hours):
        at = start + timedelta(hours=k)
        row = {"fcst_date": at.strftime("%Y%m%d"), "fcst_time": at.strftime("%H%M"), "TMP": "20",
               "PCP": pcp_for(at), "POP": "30", "WSD": "1.0", "SKY": "흐림", "PTY": "없음", "REH": "85"}
        row.update(defaults)
        rows.append(row)
    return rows


class ParsePcpTests(unittest.TestCase):
    def test_labels(self):
        cases = [("강수없음", (0.0, "0")), ("1mm 미만", (0.5, "<1")), ("2.0mm", (2.0, "2")),
                 ("6.5mm", (6.5, "6.5")), ("30.0~50.0mm", (30.0, "30~50")), ("50.0mm 이상", (50.0, "50 이상")),
                 ("", (None, "-")), (None, (None, "-")), ("-", (None, "-")), ("알수없음", (None, "-"))]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(expected, parse_pcp(value))


class NowValuesTests(unittest.TestCase):
    CURRENT = {"base_date": "20260925", "base_time": "1700", "T1H": "18.6", "RN1": "31", "WSD": "4.1", "REH": "95"}

    def test_now_values(self):
        self.assertEqual({"temp": 18.6, "feels": 18.6, "rain_mm": 31.0, "wind": 4.1, "humidity": 95},
                         now_values(self.CURRENT))

    def test_missing_current(self):
        self.assertIsNone(now_values(None))
        self.assertIsNone(observed_at(None))

    def test_observed_at_is_hourly_observation_time(self):
        self.assertEqual(datetime(2026, 9, 25, 17, 0, tzinfo=KST), observed_at(self.CURRENT))


class SeriesTests(unittest.TestCase):
    def test_hourly_starts_after_observation_and_caps_at_24(self):
        wet = lambda at: "1mm 미만" if at.hour >= 20 or at.hour <= 1 else "강수없음"
        rows = fc_rows(datetime(2026, 9, 25, 15, 0), 40, pcp_for=wet)
        series = hourly_series(rows, datetime(2026, 9, 25, 17, 0, tzinfo=KST))
        self.assertEqual(24, len(series))
        self.assertEqual("2026-09-25T18:00:00+09:00", series[0]["at"])
        self.assertEqual((0.0, "0"), (series[0]["rain_mm"], series[0]["rain_label"]))
        self.assertEqual((0.5, "<1"), (series[2]["rain_mm"], series[2]["rain_label"]))
        self.assertEqual({"at", "temp", "rain_mm", "rain_label", "wind", "pop", "sky", "pty", "humidity"},
                         set(series[0]))

    def test_daily_uses_short_then_mid_and_marks_gaps(self):
        day1 = fc_rows(datetime(2026, 9, 26, 0, 0), 24)
        day1[6]["TMN"] = "17.0"
        day1[15]["TMX"] = "24.0"
        day1[10]["PTY"] = "비"
        day1[10]["POP"] = "60"
        day2 = fc_rows(datetime(2026, 9, 27, 0, 0), 24, SKY="맑음")
        for k, row in enumerate(day2):
            row["TMP"] = str(15 + k % 10)
        partial = fc_rows(datetime(2026, 9, 28, 0, 0), 3)
        mid = [
            {"date": "2026-09-29", "sky_am": "맑음", "sky_pm": "구름많음", "pop_am": 10, "pop_pm": 20, "ta_min": 17, "ta_max": 23},
            {"date": "2026-09-30", "sky_am": None, "sky_pm": None, "pop_am": None, "pop_pm": None, "ta_min": None, "ta_max": None},
        ]
        days = daily_series(day1 + day2 + partial, mid, date(2026, 9, 25))
        self.assertEqual(10, len(days))
        self.assertEqual(("2026-09-26", "2026-10-05"), (days[0]["date"], days[-1]["date"]))
        self.assertEqual({"date": "2026-09-26", "sky": "비", "pop": 60, "tmin": 17.0, "tmax": 24.0,
                          "source": "short", "missing": False}, days[0])
        self.assertEqual(("맑음", 15.0, 24.0, "short"), (days[1]["sky"], days[1]["tmin"], days[1]["tmax"], days[1]["source"]))
        self.assertTrue(days[2]["missing"])
        self.assertEqual(("구름많음", 20, 17.0, 23.0, "mid"),
                         (days[3]["sky"], days[3]["pop"], days[3]["tmin"], days[3]["tmax"], days[3]["source"]))
        self.assertTrue(days[4]["missing"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m unittest tests.test_view_model -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.view_model'`

- [ ] **Step 3: 구현** — `src/view_model.py`:

```python
"""화면용 공개 데이터(docs/data/latest.json)를 만든다.

담당자·연락처 등 설정의 다른 값은 허용 목록에 없는 한 절대 복사하지 않는다.
시각은 모두 한국시각(+09:00)으로 표기한다.
"""

import re
from datetime import datetime, timedelta, timezone

from src.feels_like import compute_feels_like
from src.intensity import fmt_number

KST = timezone(timedelta(hours=9))
HOURLY_COUNT = 24
DAILY_COUNT = 10
FULL_DAY_HOURS = 12


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    number = _num(value)
    return int(number) if number is not None else None


def parse_pcp(value):
    """단기예보 PCP 문자열 → (색·정렬용 대표값 mm, 표시 문자열)."""
    text = str(value or "").strip()
    if text in ("강수없음", "0", "0.0"):
        return 0.0, "0"
    if "미만" in text:
        return 0.5, "<1"
    numbers = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return None, "-"
    if "~" in text and len(numbers) >= 2:
        return numbers[0], f"{fmt_number(numbers[0])}~{fmt_number(numbers[1])}"
    if "이상" in text:
        return numbers[0], f"{fmt_number(numbers[0])} 이상"
    return numbers[0], fmt_number(numbers[0])


def observed_at(current):
    """초단기실황의 관측 시각(정시)."""
    if not current or not current.get("base_date") or not current.get("base_time"):
        return None
    return datetime.strptime(current["base_date"] + current["base_time"], "%Y%m%d%H%M").replace(tzinfo=KST)


def now_values(current):
    if not current:
        return None
    rain = _num(current.get("RN1"))
    if rain is None:
        rain = parse_pcp(current.get("RN1"))[0] or 0.0
    temp = _num(current.get("T1H"))
    feels = compute_feels_like(current.get("T1H"), current.get("REH"), current.get("WSD"))
    return {"temp": temp, "feels": feels if feels is not None else temp, "rain_mm": rain,
            "wind": _num(current.get("WSD")), "humidity": _int(current.get("REH"))}


def _forecast_time(row):
    return datetime.strptime(row["fcst_date"] + row["fcst_time"], "%Y%m%d%H%M").replace(tzinfo=KST)


def hourly_series(forecast, after):
    rows = []
    for row in forecast or []:
        at = _forecast_time(row)
        if at <= after:
            continue
        rain_mm, rain_label = parse_pcp(row.get("PCP"))
        rows.append({"at": at.isoformat(), "temp": _num(row.get("TMP")), "rain_mm": rain_mm,
                     "rain_label": rain_label, "wind": _num(row.get("WSD")), "pop": _int(row.get("POP")),
                     "sky": row.get("SKY"), "pty": row.get("PTY"), "humidity": _int(row.get("REH"))})
        if len(rows) == HOURLY_COUNT:
            break
    return rows


def _short_day(day, rows):
    temps = [t for t in (_num(r.get("TMP")) for r in rows) if t is not None]
    tmn = next((_num(r.get("TMN")) for r in rows if _num(r.get("TMN")) is not None), None)
    tmx = next((_num(r.get("TMX")) for r in rows if _num(r.get("TMX")) is not None), None)
    ptys = {r.get("PTY") for r in rows} - {None, "", "없음"}
    if ptys:
        sky = "눈" if all("비" not in p and "빗방울" not in p for p in ptys) else "비"
    else:
        skies = [r.get("SKY") for r in rows if r.get("SKY")]
        sky = max(skies, key=skies.count) if skies else None
    pops = [p for p in (_int(r.get("POP")) for r in rows) if p is not None]
    return {"date": day.isoformat(), "sky": sky, "pop": max(pops) if pops else None,
            "tmin": tmn if tmn is not None else (min(temps) if temps else None),
            "tmax": tmx if tmx is not None else (max(temps) if temps else None),
            "source": "short", "missing": False}


def _mid_day(day, entry):
    pops = [p for p in (_int(entry.get("pop_am")), _int(entry.get("pop_pm"))) if p is not None]
    return {"date": day.isoformat(), "sky": entry.get("sky_pm") or entry.get("sky_am"),
            "pop": max(pops) if pops else None, "tmin": _num(entry.get("ta_min")),
            "tmax": _num(entry.get("ta_max")), "source": "mid", "missing": False}


def _missing_day(day):
    return {"date": day.isoformat(), "sky": None, "pop": None, "tmin": None, "tmax": None,
            "source": None, "missing": True}


def daily_series(forecast, mid_entries, today):
    """내일부터 10일. 단기예보가 12시간 이상인 날은 단기, 아니면 중기, 둘 다 없으면 missing."""
    by_date = {}
    for row in forecast or []:
        by_date.setdefault(datetime.strptime(row["fcst_date"], "%Y%m%d").date(), []).append(row)
    mid_by_date = {entry.get("date"): entry for entry in mid_entries or []}
    days = []
    for offset in range(1, DAILY_COUNT + 1):
        day = today + timedelta(days=offset)
        rows = by_date.get(day, [])
        entry = mid_by_date.get(day.isoformat())
        if len(rows) >= FULL_DAY_HOURS:
            days.append(_short_day(day, rows))
        elif entry and (entry.get("ta_min") is not None or entry.get("sky_am") or entry.get("sky_pm")):
            days.append(_mid_day(day, entry))
        else:
            days.append(_missing_day(day))
    return days
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m unittest tests.test_view_model -v`
Expected: 6 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/view_model.py tests/test_view_model.py
git commit -m "화면 데이터용 실황·시간별·일별 예보 변환 추가"
```

---

### Task 6: 요약 문장·전파 문안

**Files:**
- Create: `src/narrative.py`
- Test: `tests/test_narrative.py`

**Interfaces:**
- Consumes: `src.intensity.{DRIZZLE_MAX_MM, fmt_number, rain_term, wind_term}`, `src.alert_rules.{ACTION_ITEMS, CATEGORY_ORDER, CATEGORY_RAIN, CATEGORY_WIND, _situational_title, _situational_closing}`. 입력 `view`는 Task 7의 현장 항목과 같은 키(`name, short, state, as_of, now, hourly, warnings`)를 쓴다.
- Produces: `FORBIDDEN_WORDS`, `contains_forbidden(text) -> list[str]`, `site_summary(view) -> str`, `national_summary(sites, warnings_ok) -> str`, `site_notice(view) -> str`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_narrative.py`:

```python
import unittest

from src.narrative import contains_forbidden, national_summary, site_notice, site_summary


def hour(at, mm=0.0, label="0", pop=30):
    return {"at": at, "temp": 20, "rain_mm": mm, "rain_label": label, "wind": 1.0, "pop": pop,
            "sky": "흐림", "pty": "없음", "humidity": 85}


HUPO_HOURLY = ([hour("2026-09-25T18:00:00+09:00"), hour("2026-09-25T19:00:00+09:00")]
               + [hour(f"2026-09-25T{h}:00:00+09:00", 0.5, "<1", 60) for h in (20, 21, 22, 23)]
               + [hour(f"2026-09-26T0{h}:00:00+09:00", 0.5, "<1", 60) for h in (0, 1)]
               + [hour("2026-09-26T02:00:00+09:00")])
LATER_RAIN = [hour("2026-09-25T18:00:00+09:00"), hour("2026-09-25T19:00:00+09:00"),
              hour("2026-09-25T20:00:00+09:00"), hour("2026-09-25T21:00:00+09:00", 2.0, "2", 60)]


def make_view(rain=0.0, wind=1.0, state="ok", as_of="2026-09-25T17:00:00+09:00", hourly=None,
              warnings=None, name="후포 공공하수처리", short="후포"):
    now = None if state == "missing" else {"temp": 18.6, "feels": 18.6, "rain_mm": rain, "wind": wind, "humidity": 95}
    return {"id": "5355accc", "name": name, "short": short, "state": state,
            "as_of": None if state == "missing" else as_of, "now": now,
            "hourly": hourly or [], "daily": [], "warnings": warnings or [], "legal": [], "legal_profile": False}


class SiteSummaryTests(unittest.TestCase):
    def test_observed_rain_with_forecast_side_by_side(self):
        self.assertEqual("지금 시간당 31mm(관측)의 매우 강한 비. 예보는 20시~내일 1시 1mm 미만.",
                         site_summary(make_view(rain=31, hourly=HUPO_HOURLY)))

    def test_no_rain_but_rain_later(self):
        self.assertEqual("지금은 비가 없습니다. 예보상 21시부터 비(강수확률 60%).",
                         site_summary(make_view(hourly=LATER_RAIN)))

    def test_no_rain_no_forecast(self):
        self.assertEqual("지금은 비가 없습니다. 24시간 안에 비 예보가 없습니다.", site_summary(make_view()))

    def test_stale_uses_observation_hour(self):
        text = site_summary(make_view(rain=5.6, state="stale", as_of="2026-09-25T15:00:00+09:00"))
        self.assertTrue(text.startswith("15시 관측 기준 시간당 5.6mm(관측)의 비."))

    def test_missing(self):
        self.assertEqual("관측 자료를 받지 못했습니다.", site_summary(make_view(state="missing")))

    def test_wind_term_only_from_four_meters(self):
        self.assertIn("바람 9.5m/s(강한 바람).", site_summary(make_view(wind=9.5)))
        self.assertNotIn("바람", site_summary(make_view(wind=3.9)))

    def test_official_warning_first(self):
        warning = [{"kind": "기상특보", "title": "호우주의보", "level": "주의보"}]
        self.assertTrue(site_summary(make_view(rain=31, warnings=warning)).startswith("기상청 호우주의보 발효 중."))


class NationalSummaryTests(unittest.TestCase):
    def sites(self):
        return [make_view(rain=31, hourly=HUPO_HOURLY),
                make_view(rain=10, name="연희·연남동 공공주택", short="연희·연남"),
                make_view(rain=0, name="오리온수협 목포 김공장", short="목포 김공장")]

    def test_top_site_and_count(self):
        self.assertEqual("후포에 지금 시간당 31mm(관측)의 매우 강한 비, 예보는 1mm 미만. 그 밖에 1곳에 비. 기상청 특보는 없습니다.",
                         national_summary(self.sites(), True))

    def test_warning_failure_and_stale_are_reported(self):
        sites = self.sites()
        sites[2]["state"] = "stale"
        text = national_summary(sites, False)
        self.assertIn("기상청 특보는 확인하지 못했습니다.", text)
        self.assertIn("1개 현장은 이번 수집에 실패했습니다.", text)

    def test_all_missing(self):
        self.assertEqual("관측 자료를 받지 못했습니다.", national_summary([make_view(state="missing")], True))


class NoticeTests(unittest.TestCase):
    def test_rain_notice_in_house_style(self):
        text = site_notice(make_view(rain=31, hourly=HUPO_HOURLY))
        self.assertTrue(text.startswith("■ 공지드립니다."))
        self.assertIn("2026-09-25 17:00 관측 기준, 후포 공공하수처리 현장에 시간당 31mm의 매우 강한 비가 관측되고 있습니다.", text)
        self.assertIn("(기상청 예보: 20시~내일 1시 1mm 미만)", text)
        self.assertIn("【수방 안전관리 사항】", text)
        self.assertIn("ㅇ 배수로 및 침사지 주변 이물질 정비", text)
        self.assertIn("각 현장에서는 수방 조치가 실제 이행될 수 있도록 관리하여 주시기 바랍니다.", text)
        self.assertTrue(text.endswith("감사합니다."))

    def test_dry_notice_mentions_later_rain_without_actions(self):
        text = site_notice(make_view(hourly=LATER_RAIN))
        self.assertIn("현장에는 비가 관측되지 않았습니다.", text)
        self.assertIn("다만 예보상 21시부터 비(강수확률 60%)가 있으니 작업 계획에 참고하여 주시기 바랍니다.", text)
        self.assertNotIn("【", text)

    def test_wind_warning_adds_wind_actions(self):
        warning = [{"kind": "기상특보", "title": "강풍주의보", "level": "주의보"}]
        text = site_notice(make_view(wind=12, warnings=warning))
        self.assertIn("기상청 강풍주의보가 발효 중입니다.", text)
        self.assertIn("【강풍 대비 안전관리 사항】", text)

    def test_missing_notice(self):
        self.assertIn("관측 자료를 받지 못했습니다", site_notice(make_view(state="missing")))


class ForbiddenWordTests(unittest.TestCase):
    def test_detects_forbidden(self):
        self.assertEqual(["선제", "기준 도달"], contains_forbidden("사내 선제감시 기준 도달"))

    def test_all_outputs_are_clean(self):
        views = [make_view(rain=31, hourly=HUPO_HOURLY), make_view(hourly=LATER_RAIN), make_view(wind=15),
                 make_view(state="stale", rain=2, as_of="2026-09-25T15:00:00+09:00"), make_view(state="missing")]
        for view in views:
            for text in (site_summary(view), site_notice(view)):
                self.assertEqual([], contains_forbidden(text), text)
        self.assertEqual([], contains_forbidden(national_summary(views, True)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m unittest tests.test_narrative -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.narrative'`

- [ ] **Step 3: 구현** — `src/narrative.py`:

```python
"""현장·전국 요약 문장과 전파 문안을 만든다.

등급어("선제", "기준 도달" 등)를 쓰지 않고 관측값과 예보값을 판단어 없이 나란히 적는다.
세기 표현은 src.intensity의 기상청 예보용어만 쓴다.
"""

from datetime import datetime, timedelta

from src.alert_rules import (
    ACTION_ITEMS,
    CATEGORY_ORDER,
    CATEGORY_RAIN,
    CATEGORY_WIND,
    _situational_closing,
    _situational_title,
)
from src.intensity import DRIZZLE_MAX_MM, fmt_number, rain_term, wind_term

FORBIDDEN_WORDS = ("선제", "기준 도달", "주의 단계", "경계 단계")
FORECAST_HORIZON_HOURS = 12
NO_DATA = "관측 자료를 받지 못했습니다."


def contains_forbidden(text):
    return [word for word in FORBIDDEN_WORDS if word in (text or "")]


def _hour_label(iso, ref_date):
    at = datetime.fromisoformat(iso)
    if at.date() == ref_date:
        prefix = ""
    elif at.date() == ref_date + timedelta(days=1):
        prefix = "내일 "
    else:
        prefix = f"{at.month}/{at.day} "
    return f"{prefix}{at.hour}시"


def _rain_mm(hour):
    return hour.get("rain_mm") or 0


def _first_rain(hourly):
    return next((h for h in hourly if _rain_mm(h) > 0), None)


def _forecast_rain_phrase(hourly, ref_date):
    wet = [h for h in hourly[:FORECAST_HORIZON_HOURS] if _rain_mm(h) > 0]
    if not wet:
        return None
    start, end = _hour_label(wet[0]["at"], ref_date), _hour_label(wet[-1]["at"], ref_date)
    span = start if start == end else f"{start}~{end}"
    if {h["rain_label"] for h in wet} == {"<1"}:
        amount = "1mm 미만"
    else:
        amount = f"최대 {max(wet, key=_rain_mm)['rain_label']}mm"
    return f"{span} {amount}"


def _lead(view):
    if view["state"] == "ok":
        return "지금"
    return f"{datetime.fromisoformat(view['as_of']).hour}시 관측 기준"


def _warning_titles(view):
    return "·".join(w["title"] for w in view["warnings"])


def site_summary(view):
    if view["state"] == "missing" or not view.get("now"):
        return NO_DATA
    now = view["now"]
    ref = datetime.fromisoformat(view["as_of"]).date()
    rain = now.get("rain_mm") or 0
    parts = []
    if view["warnings"]:
        parts.append(f"기상청 {_warning_titles(view)} 발효 중.")
    if rain >= DRIZZLE_MAX_MM:
        parts.append(f"{_lead(view)} 시간당 {fmt_number(rain)}mm(관측)의 {rain_term(rain)}.")
        phrase = _forecast_rain_phrase(view["hourly"], ref)
        parts.append(f"예보는 {phrase}." if phrase else "예보상 12시간 안에 비 예보가 없습니다.")
    else:
        parts.append("지금은 비가 없습니다." if view["state"] == "ok" else f"{_lead(view)} 비가 없습니다.")
        wet = _first_rain(view["hourly"])
        parts.append(f"예보상 {_hour_label(wet['at'], ref)}부터 비(강수확률 {wet['pop']}%)." if wet
                     else "24시간 안에 비 예보가 없습니다.")
    wind = now.get("wind")
    term = wind_term(wind)
    if term:
        parts.append(f"바람 {fmt_number(wind)}m/s({term}).")
    return " ".join(parts)


def _next_hours_phrase(hourly):
    upcoming = hourly[:3]
    if not upcoming:
        return ""
    peak = max(upcoming, key=_rain_mm)
    if _rain_mm(peak) == 0:
        return ", 예보는 비 없음"
    if peak["rain_label"] == "<1":
        return ", 예보는 1mm 미만"
    return f", 예보는 {peak['rain_label']}mm"


def national_summary(sites, warnings_ok):
    live = [s for s in sites if s["state"] != "missing" and s.get("now")]
    if not live:
        return NO_DATA
    rainy = sorted((s for s in live if (s["now"].get("rain_mm") or 0) >= DRIZZLE_MAX_MM),
                   key=lambda s: -s["now"]["rain_mm"])
    parts = []
    if rainy:
        top = rainy[0]
        mm = top["now"]["rain_mm"]
        when = "지금 " if top["state"] == "ok" else f"{datetime.fromisoformat(top['as_of']).hour}시 관측 기준 "
        parts.append(f"{top['short']}에 {when}시간당 {fmt_number(mm)}mm(관측)의 {rain_term(mm)}"
                     f"{_next_hours_phrase(top['hourly'])}.")
        if len(rainy) > 1:
            parts.append(f"그 밖에 {len(rainy) - 1}곳에 비.")
    else:
        parts.append("비 오는 현장은 없습니다.")
    warned = sum(1 for s in sites if s["warnings"])
    if not warnings_ok:
        parts.append("기상청 특보는 확인하지 못했습니다.")
    elif warned:
        parts.append(f"기상청 특보가 {warned}개 현장에 발효 중입니다.")
    else:
        parts.append("기상청 특보는 없습니다.")
    failed = sum(1 for s in sites if s["state"] != "ok")
    if failed:
        parts.append(f"{failed}개 현장은 이번 수집에 실패했습니다.")
    return " ".join(parts)


def _categories(view):
    rain = view["now"].get("rain_mm") or 0
    found = set()
    for warning in view["warnings"]:
        for category in CATEGORY_ORDER:
            if category in (warning.get("title") or ""):
                found.add(category)
    if rain >= DRIZZLE_MAX_MM:
        found.add(CATEGORY_RAIN)
    if wind_term(view["now"].get("wind")) in ("강한 바람", "매우 강한 바람"):
        found.add(CATEGORY_WIND)
    return [category for category in CATEGORY_ORDER if category in found]


def site_notice(view):
    lines = ["■ 공지드립니다.", ""]
    if view["state"] == "missing" or not view.get("now"):
        lines += [f"{view['name']} 현장은 이번에 관측 자료를 받지 못했습니다.",
                  "현장에서 기상 상황을 직접 확인하여 주시기 바랍니다.", "", "감사합니다."]
        return "\n".join(lines)
    at = datetime.fromisoformat(view["as_of"])
    when = at.strftime("%Y-%m-%d %H:%M") + " 관측 기준"
    now = view["now"]
    rain = now.get("rain_mm") or 0
    if view["warnings"]:
        lines.append(f"기상청 {_warning_titles(view)}가 발효 중입니다.")
    if rain >= DRIZZLE_MAX_MM:
        lines.append(f"{when}, {view['name']} 현장에 시간당 {fmt_number(rain)}mm의 {rain_term(rain)}가 관측되고 있습니다.")
        phrase = _forecast_rain_phrase(view["hourly"], at.date())
        lines.append(f"(기상청 예보: {phrase})" if phrase else "(기상청 예보: 12시간 안에 비 예보 없음)")
    else:
        lines.append(f"{when}, {view['name']} 현장에는 비가 관측되지 않았습니다.")
        wet = _first_rain(view["hourly"])
        if wet:
            lines.append(f"다만 예보상 {_hour_label(wet['at'], at.date())}부터 비(강수확률 {wet['pop']}%)가 "
                         "있으니 작업 계획에 참고하여 주시기 바랍니다.")
    term = wind_term(now.get("wind"))
    if term:
        lines.append(f"바람은 {fmt_number(now['wind'])}m/s({term})입니다.")
    categories = _categories(view)
    if categories:
        lines += ["", f"【{_situational_title(categories)}】"]
        for category in categories:
            lines += [f"ㅇ {action}" for action in ACTION_ITEMS[category]]
        lines += ["", _situational_closing(categories)]
    lines += ["", "감사합니다."]
    return "\n".join(lines)
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m unittest tests.test_narrative -v`
Expected: 16 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/narrative.py tests/test_narrative.py
git commit -m "관측·예보 병기 요약 문장과 사내 문체 전파 문안 추가"
```

---

### Task 7: 현장·전체 데이터 조립, 마지막 정상 자료 유지, 읽기·쓰기

**Files:**
- Modify: `src/view_model.py` (import 블록 교체 + 함수 추가)
- Test: `tests/test_view_model.py` (클래스 추가)

**Interfaces:**
- Consumes: Task 2~6의 함수 전부, `src.kma_client.forecast_base_datetime`, `src.mid_client.mid_issue_datetime`, `src.legal_rules.{STATUS_STOP, STATUS_ACTION, STATUS_VERIFY}`. `collected` 항목 형식은 `collection.collect_site_data` + `main.attach_weather_warnings` 결과(`site, current, forecast, legal_signals, weather_warnings, weather_warnings_available`).
- Produces: `SCHEMA_VERSION = 1`, `SITE_FIELDS`, `build_site_view(item, mid_entries, previous_site, now) -> dict`, `build_latest(collected, mid_forecasts, previous, now, warnings_ok, forecast_issued_at, mid_issued_at) -> dict`, `load_latest(path) -> dict | None`, `write_latest(path, data) -> None`, `publish_latest(path, collected, mid_forecasts, now) -> dict`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_view_model.py` 맨 위 import를 아래로 바꾼다:

```python
import json
import os
import re
import tempfile
import unittest
from datetime import date, datetime, timedelta

from src.narrative import contains_forbidden
from src.view_model import (
    KST,
    SITE_FIELDS,
    build_latest,
    daily_series,
    hourly_series,
    load_latest,
    now_values,
    observed_at,
    parse_pcp,
    publish_latest,
    write_latest,
)
```

파일 끝(`if __name__` 위)에 추가:

```python
NOW = datetime(2026, 9, 25, 17, 47, tzinfo=KST)
_UNSET = object()
PROFILE_GAP = {"status": "데이터 부족", "work_type": "site_profile", "title": "현장 작업 프로필 미등록",
               "article": "판정 전제정보", "reason": "미등록", "actions": []}


def site_cfg(name="후포 공공하수처리", **extra):
    site = {"site_name": name, "category": "토목", "lat": 36.68, "lon": 129.45, "nx": 103, "ny": 109,
            "manager": "홍길동", "manager_phone": "010-1234-5678"}
    site.update(extra)
    return site


def obs(rn1="31", t1h="18.6"):
    return {"base_date": "20260925", "base_time": "1700", "T1H": t1h, "RN1": rn1, "WSD": "4.1", "REH": "95"}


def forecast_rows():
    rows = []
    start = datetime(2026, 9, 25, 18, 0)
    for k in range(78):
        at = start + timedelta(hours=k)
        wet = (at.day == 25 and at.hour >= 20) or (at.day == 26 and at.hour <= 1)
        rows.append({"fcst_date": at.strftime("%Y%m%d"), "fcst_time": at.strftime("%H%M"), "TMP": "20",
                     "PCP": "1mm 미만" if wet else "강수없음", "POP": "60" if wet else "30", "WSD": "1.0",
                     "SKY": "흐림", "PTY": "비" if wet else "없음", "REH": "85"})
    return rows


def make_item(site=None, current=_UNSET, forecast=None, warnings=None, available=True, legal=None):
    return {"site": site or site_cfg(), "current": obs() if current is _UNSET else current,
            "forecast": forecast_rows() if forecast is None else forecast,
            "judgment": {"level": "정상", "reasons": [], "categories": []},
            "legal_signals": [PROFILE_GAP] if legal is None else legal, "legal_status": None,
            "weather_warnings": warnings or [], "weather_warnings_available": available}


def build(items, previous=None, warnings_ok=True, now=NOW):
    return build_latest(items, {}, previous=previous, now=now, warnings_ok=warnings_ok,
                        forecast_issued_at=datetime(2026, 9, 25, 14, 0), mid_issued_at=datetime(2026, 9, 25, 6, 0))


class BuildLatestTests(unittest.TestCase):
    def test_top_level_fields(self):
        latest = build([make_item()])
        self.assertEqual(1, latest["schema"])
        self.assertEqual("2026-09-25T17:47:00+09:00", latest["generated_at"])
        self.assertEqual("2026-09-25T17:00:00+09:00", latest["observed_at"])
        self.assertEqual("2026-09-25T14:00:00+09:00", latest["forecast_issued_at"])
        self.assertEqual("2026-09-25T06:00:00+09:00", latest["mid_issued_at"])
        self.assertEqual({"current": "ok", "forecast": "ok", "warnings": "ok", "radar": "off"}, latest["status"])
        self.assertEqual({"window": "04:17-17:47", "next_run_at": "2026-09-26T04:17:00+09:00"}, latest["schedule"])
        self.assertIsNone(latest["radar"])

    def test_site_fields_are_allowlisted(self):
        site = build([make_item()])["sites"][0]
        self.assertEqual(set(SITE_FIELDS), set(site))
        self.assertEqual(("5355accc", "후포", "경상북도 울진군", "ok"),
                         (site["id"], site["short"], site["region"], site["state"]))

    def test_no_personal_data_or_forbidden_words(self):
        text = json.dumps(build([make_item()]), ensure_ascii=False)
        self.assertNotIn("홍길동", text)
        self.assertNotIn("010-1234-5678", text)
        self.assertNotIn("manager", text)
        self.assertIsNone(re.search(r"01[016789]-?\d{3,4}-?\d{4}", text))
        self.assertEqual([], contains_forbidden(text))

    def test_national_aggregates(self):
        national = build([make_item()])["national"]
        self.assertEqual((0, 0, 1), (national["warnings"], national["legal"], national["rain_sites"]))
        self.assertEqual({"mm": 31.0, "site": "5355accc"}, national["max_rain"])
        self.assertTrue(national["summary"].startswith("후포에 지금 시간당 31mm(관측)의 매우 강한 비, 예보는 1mm 미만."))

    def test_profile_gap_is_not_a_legal_signal(self):
        site = build([make_item()])["sites"][0]
        self.assertEqual(([], False), (site["legal"], site["legal_profile"]))

    def test_legal_signal_subset_and_count(self):
        stop = {"status": "법정 작업중지", "work_type": "steel_erection", "title": "철골작업 중지",
                "article": "제383조", "reason": "강우 1mm 이상", "actions": ["철골작업 즉시 중지"]}
        item = make_item(site=site_cfg(work_types=["steel_erection"], active_work_types=["steel_erection"]), legal=[stop])
        latest = build([item])
        self.assertEqual([{"status": "법정 작업중지", "title": "철골작업 중지", "article": "제383조"}],
                         latest["sites"][0]["legal"])
        self.assertTrue(latest["sites"][0]["legal_profile"])
        self.assertEqual(1, latest["national"]["legal"])

    def test_warning_subset(self):
        warning = {"kind": "기상특보", "title": "호우주의보", "level": "주의보", "areas": ["경상북도(울진)"],
                   "matched_areas": ["경상북도(울진)"], "announced_at": "202609251600"}
        latest = build([make_item(warnings=[warning])])
        self.assertEqual([{"kind": "기상특보", "title": "호우주의보", "level": "주의보"}], latest["sites"][0]["warnings"])
        self.assertEqual(1, latest["national"]["warnings"])
        self.assertTrue(latest["sites"][0]["summary"].startswith("기상청 호우주의보 발효 중."))

    def test_warning_failure_status(self):
        self.assertEqual("failed", build([make_item(available=False)], warnings_ok=False)["status"]["warnings"])

    def test_stale_carries_last_good_values(self):
        previous = build([make_item()])
        latest = build([make_item(current=None)], previous=previous, now=NOW + timedelta(minutes=30))
        site = latest["sites"][0]
        self.assertEqual("stale", site["state"])
        self.assertEqual(previous["sites"][0]["now"], site["now"])
        self.assertEqual("2026-09-25T17:00:00+09:00", site["as_of"])
        self.assertTrue(site["summary"].startswith("17시 관측 기준 시간당 31mm(관측)"))
        self.assertEqual("failed", latest["status"]["current"])

    def test_hourly_falls_back_to_previous_forecast(self):
        previous = build([make_item()])
        later = NOW + timedelta(hours=2)
        site = build([make_item(forecast=[])], previous=previous, now=later)["sites"][0]
        self.assertTrue(site["hourly"])
        self.assertTrue(all(datetime.fromisoformat(h["at"]) > later for h in site["hourly"]))

    def test_first_run_total_failure(self):
        latest = build([make_item(current=None, forecast=[]), make_item(site=site_cfg("연희·연남동 공공주택"), current=None, forecast=[])])
        self.assertEqual(["missing", "missing"], [s["state"] for s in latest["sites"]])
        self.assertEqual("관측 자료를 받지 못했습니다.", latest["national"]["summary"])
        self.assertEqual("failed", latest["status"]["current"])
        json.dumps(latest, ensure_ascii=False)

    def test_partial_status(self):
        latest = build([make_item(), make_item(site=site_cfg("연희·연남동 공공주택"), current=None)])
        self.assertEqual("partial", latest["status"]["current"])


class LatestFileTests(unittest.TestCase):
    def test_write_then_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "data", "latest.json")
            data = build([make_item()])
            write_latest(path, data)
            self.assertEqual(data, load_latest(path))
            self.assertEqual([], [n for n in os.listdir(os.path.dirname(path)) if n.startswith(".latest-")])

    def test_load_rejects_missing_corrupt_or_old_schema(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(load_latest(os.path.join(d, "none.json")))
            broken = os.path.join(d, "broken.json")
            with open(broken, "w", encoding="utf-8") as f:
                f.write("{not json")
            self.assertIsNone(load_latest(broken))
            old = os.path.join(d, "old.json")
            with open(old, "w", encoding="utf-8") as f:
                json.dump({"schema": 0, "sites": []}, f)
            self.assertIsNone(load_latest(old))

    def test_publish_twice_carries_last_good_values(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "data", "latest.json")
            first = publish_latest(path, [make_item()], {}, NOW)
            second = publish_latest(path, [make_item(current=None)], {}, NOW + timedelta(minutes=30))
            self.assertEqual("stale", second["sites"][0]["state"])
            self.assertEqual(first["sites"][0]["now"], second["sites"][0]["now"])
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m unittest tests.test_view_model -v`
Expected: FAIL — `ImportError: cannot import name 'SITE_FIELDS'`

- [ ] **Step 3: 구현** — `src/view_model.py` 맨 위 import 블록(`import re`부터 `from src.intensity import fmt_number`까지)을 아래로 교체:

```python
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone

from src import narrative
from src.feels_like import compute_feels_like
from src.intensity import DRIZZLE_MAX_MM, fmt_number
from src.kma_client import forecast_base_datetime
from src.legal_rules import STATUS_ACTION, STATUS_STOP, STATUS_VERIFY
from src.mid_client import mid_issue_datetime
from src.schedule import WINDOW_LABEL, next_collection_at
from src.site_profile import region_label, short_name, site_id
```

`FULL_DAY_HOURS = 12` 아래에 상수 추가:

```python
SCHEMA_VERSION = 1
SITE_FIELDS = ("id", "name", "short", "category", "region", "lat", "lon", "state", "as_of", "now",
               "hourly", "daily", "warnings", "legal", "legal_profile", "summary", "notice")
ACTIONABLE_LEGAL = {STATUS_STOP, STATUS_ACTION, STATUS_VERIFY}
```

파일 끝에 추가:

```python
def build_site_view(item, mid_entries, previous_site, now):
    """수집 결과 한 건 → 허용 목록 필드만 있는 공개용 현장 항목."""
    site = item["site"]
    current = now_values(item.get("current"))
    obs = observed_at(item.get("current"))
    if current is not None:
        state, as_of = "ok", (obs or now).isoformat()
    elif previous_site and previous_site.get("now"):
        state, current, as_of = "stale", previous_site["now"], previous_site.get("as_of")
    else:
        state, as_of = "missing", None

    hourly = hourly_series(item.get("forecast"), obs or now)
    if not hourly and previous_site:
        hourly = [h for h in previous_site.get("hourly") or []
                  if datetime.fromisoformat(h["at"]) > now][:HOURLY_COUNT]
    daily = daily_series(item.get("forecast"), mid_entries, now.date())
    if all(day["missing"] for day in daily) and previous_site:
        carried = [d for d in previous_site.get("daily") or [] if d["date"] > now.date().isoformat()]
        daily = carried[:DAILY_COUNT] or daily

    view = {
        "id": site_id(site),
        "name": site["site_name"],
        "short": short_name(site),
        "category": site.get("category"),
        "region": region_label(site),
        "lat": site.get("lat"),
        "lon": site.get("lon"),
        "state": state,
        "as_of": as_of,
        "now": current,
        "hourly": hourly,
        "daily": daily,
        "warnings": [{"kind": w.get("kind"), "title": w.get("title"), "level": w.get("level")}
                     for w in item.get("weather_warnings") or []],
        "legal": [{"status": s.get("status"), "title": s.get("title"), "article": s.get("article")}
                  for s in item.get("legal_signals") or [] if s.get("work_type") != "site_profile"],
        "legal_profile": bool(site.get("work_types") or site.get("active_work_types")),
    }
    view["summary"] = narrative.site_summary(view)
    view["notice"] = narrative.site_notice(view)
    return {key: view[key] for key in SITE_FIELDS}


def _collection_status(done, total):
    if total and done == total:
        return "ok"
    return "failed" if done == 0 else "partial"


def _top(sites, key, unit_key):
    candidates = [s for s in sites if s["state"] != "missing" and s["now"] and s["now"].get(key) is not None]
    if not candidates:
        return None
    best = max(candidates, key=lambda s: s["now"][key])
    return {unit_key: best["now"][key], "site": best["id"]}


def _kst_iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=KST)
    return value.astimezone(KST).isoformat(timespec="seconds")


def _as_kst(now):
    return now.astimezone(KST) if now.tzinfo else now.replace(tzinfo=KST)


def build_latest(collected, mid_forecasts, previous, now, warnings_ok, forecast_issued_at, mid_issued_at):
    now = _as_kst(now)
    previous_sites = {s.get("id"): s for s in (previous or {}).get("sites") or []}
    sites = [build_site_view(item, mid_forecasts.get(item["site"]["site_name"], []),
                             previous_sites.get(site_id(item["site"])), now)
             for item in collected]
    fresh = [s for s in sites if s["state"] == "ok"]
    live = [s for s in sites if s["state"] != "missing" and s["now"]]
    return {
        "schema": SCHEMA_VERSION,
        "generated_at": _kst_iso(now),
        "observed_at": max((s["as_of"] for s in fresh), default=None),
        "forecast_issued_at": _kst_iso(forecast_issued_at),
        "mid_issued_at": _kst_iso(mid_issued_at),
        "status": {
            "current": _collection_status(len(fresh), len(sites)),
            "forecast": _collection_status(sum(1 for item in collected if item.get("forecast")), len(collected)),
            "warnings": "ok" if warnings_ok else "failed",
            "radar": "off",
        },
        "schedule": {"window": WINDOW_LABEL, "next_run_at": _kst_iso(next_collection_at(now))},
        "national": {
            "warnings": sum(1 for s in sites if s["warnings"]),
            "legal": sum(1 for s in sites if any(l["status"] in ACTIONABLE_LEGAL for l in s["legal"])),
            "rain_sites": sum(1 for s in live if (s["now"].get("rain_mm") or 0) >= DRIZZLE_MAX_MM),
            "max_rain": _top(sites, "rain_mm", "mm"),
            "max_wind": _top(sites, "wind", "ms"),
            "max_temp": _top(sites, "temp", "c"),
            "summary": narrative.national_summary(sites, warnings_ok),
        },
        "radar": None,
        "sites": sites,
    }


def load_latest(path):
    """직전 latest.json. 없거나 깨졌거나 스키마가 다르면 None."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA_VERSION:
        return None
    return data


def write_latest(path, data):
    """임시 파일에 쓴 뒤 교체해 반쯤 쓰인 파일이 게시되지 않게 한다."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".latest-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def publish_latest(path, collected, mid_forecasts, now):
    now = _as_kst(now)
    latest = build_latest(
        collected,
        mid_forecasts,
        previous=load_latest(path),
        now=now,
        warnings_ok=all(item.get("weather_warnings_available", True) for item in collected),
        forecast_issued_at=forecast_base_datetime(now),
        mid_issued_at=mid_issue_datetime(now),
    )
    write_latest(path, latest)
    return latest
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m unittest tests.test_view_model -v`
Expected: 21 PASS (Task 5의 6개 + 새 15개)

- [ ] **Step 5: 전체 테스트 후 커밋**

Run: `python3 -m unittest discover -s tests` → Expected: OK
```bash
git add src/view_model.py tests/test_view_model.py
git commit -m "latest.json 조립·마지막 정상 자료 유지·안전한 쓰기 추가"
```

---

### Task 8: 수집 실행에 연결하고 문서 갱신

**Files:**
- Modify: `src/main.py`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: `view_model.publish_latest(path, collected, mid_forecasts, now) -> dict`, `collection.collect_mid_forecasts(..., now=)`

- [ ] **Step 1: `src/main.py` 수정** — import에 추가:

```python
from src.view_model import publish_latest
```

경로 상수들(`NOTIFICATION_OUTBOX_PATH` 아래)에 추가:

```python
LATEST_PATH = os.path.join(DOCS_DIR, "data", "latest.json")
```

`update_weather_state` 함수 위에 추가:

```python
def write_latest_view(collected, mid_forecasts, now):
    """화면용 공개 데이터를 쓴다. 실패해도 기존 대시보드·알림 산출물은 계속 만든다."""
    try:
        latest = publish_latest(LATEST_PATH, collected, mid_forecasts, now.astimezone())
        print(f"[화면 데이터] 현장 {len(latest['sites'])}곳 · 실황 {latest['status']['current']} · "
              f"특보 {latest['status']['warnings']} · 다음 수집 {latest['schedule']['next_run_at'][11:16]}")
    except Exception as e:
        print(f"[화면 데이터 오류] latest.json을 만들지 못했습니다(기존 화면은 계속 생성): {e}")
```

`main()`의 수집 부분을 바꾼다:

```python
    breaker = CircuitBreaker()
    collected = collect_site_data(config.SITES, breaker=breaker)
    attach_weather_warnings(collected, breaker=breaker)
    mid_forecasts = collect_mid_forecasts(config.SITES, breaker=breaker, now=now)
    write_latest_view(collected, mid_forecasts, now)
```

- [ ] **Step 2: 컴파일·전체 테스트**

Run: `python3 -m compileall -q src tests && python3 -m unittest discover -s tests`
Expected: OK (기존 59 + 신규)

- [ ] **Step 3: `CLAUDE.md` 갱신** — "## 주요 파일" 목록의 `src/main.py` 줄 아래에 추가:

```markdown
- `src/view_model.py`: 화면용 공개 데이터 `docs/data/latest.json` 조립(허용 목록 필드만), 마지막 정상 자료 유지
- `src/narrative.py`: 현장·전국 요약 문장과 전파 문안(금지어 검사 포함)
- `src/intensity.py`: 기상청 예보용어(2025-06-11) 강수·바람 세기 표현
- `src/site_profile.py`: 현장 공개 ID·짧은 이름·지역
- `src/schedule.py`: 다음 수집 시각(워크플로 일정 변경 시 함께 수정)
```

"### 이번 세션(2026-09-20)에서 추가된 것" 섹션 위에 추가:

```markdown
### 대시보드 리디자인 진행 (2026-09-26~)

- 설계: `design/specs/2026-09-26-dashboard-redesign-design.md`, 계획: `design/plans/`
- 1단계(데이터 층): 매 실행마다 `docs/data/latest.json` 생성. 기존 화면·알림은 그대로.
- 중기예보 날짜를 발표일 기준으로 수정(새벽 실행 하루 밀림 해결).
```

- [ ] **Step 4: 커밋**

```bash
git add src/main.py CLAUDE.md
git commit -m "수집 실행에서 latest.json 생성 연결"
```

---

### Task 9: 실제 실행으로 확인 (사용자 확인 후 진행)

**Files:** 없음(검증만)

- [ ] **Step 1: 원격 반영** — 사용자에게 푸시해도 되는지 확인한 뒤:

```bash
git pull --ff-only
python3 -m unittest discover -s tests
git push origin main
```

- [ ] **Step 2: 수동 실행** — `.github/workflows/collector.yml`에 `NOTIFICATION_MODE: shadow`가 그대로인지 먼저 확인:

```bash
grep -n "NOTIFICATION_MODE: shadow" .github/workflows/collector.yml
gh workflow run collector.yml
sleep 10
RUN_ID=$(gh run list --workflow=collector.yml --limit 1 --json databaseId -q '.[0].databaseId')
echo "$RUN_ID"
gh run watch "$RUN_ID" --exit-status
```

- [ ] **Step 3: 로그 확인** — 아래 두 줄이 있어야 한다: `[화면 데이터] 현장 21곳 · 실황 ok …`, `[알림 전달: 모의운영(외부 발송 차단)] 발송 0건 …`

```bash
gh run view "$RUN_ID" --log | grep -E "화면 데이터|알림 전달"
```

- [ ] **Step 4: 게시된 파일 검사**

```bash
git pull --ff-only
python3 - <<'EOF'
import json, re
from src.narrative import contains_forbidden
from src.view_model import SITE_FIELDS
text = open("docs/data/latest.json", encoding="utf-8").read()
data = json.loads(text)
assert data["schema"] == 1, data["schema"]
assert all(set(s) == set(SITE_FIELDS) for s in data["sites"])
assert re.search(r"01[016789]-?\d{3,4}-?\d{4}", text) is None, "전화번호 형식 발견"
assert "manager" not in text
assert contains_forbidden(text) == [], contains_forbidden(text)
print("현장", len(data["sites"]), "| 상태", data["status"], "| 다음 수집", data["schedule"]["next_run_at"])
print("짧은 이름이 설정되지 않은 현장:", [s["name"] for s in data["sites"] if s["short"] == s["name"]])
print("요약:", data["national"]["summary"])
EOF
```

Expected: 오류 없이 출력되고, "짧은 이름이 설정되지 않은 현장"이 빈 목록(`[]`)이다. 빈 목록이 아니면 해당 이름을 `SITE_SHORT_NAMES`에 추가하는 작업을 사용자에게 보고한다.

- [ ] **Step 5: 공개 주소 확인** (Pages 반영까지 1~2분)

```bash
curl -s https://stkangys-lgtm.github.io/weather-alert-system/data/latest.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['generated_at'], len(d['sites']))"
```

- [ ] **Step 6: 사용자 보고** — 테스트 개수, Actions 성공 여부, 실제 발송 0건, 수집 장애 여부, `latest.json` 공개 주소, 요약 문장 예시를 짧게 보고한다.

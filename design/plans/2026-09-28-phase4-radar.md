# 4단계 레이더(비구름 레이어) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기상청 레이더 합성영상에서 비구름만 뽑아 우리 비 단계 색으로 다시 칠하고, 본사·현장 지도 위에 겹쳐 보여 준다.

**Architecture:** 수집 실행(`src/main.py`)이 `src/radar.py`로 가장 최근 레이더 영상(`RDR_CMP_WRC_*.png`)을 받아, 범례 24색 → mm/h → 우리 비 5단계로 바꾸고, 보정한 기상청 LCC 변환식으로 웹 지도(메르카토르) 격자에 다시 그려 `docs/data/radar.png`로 쓴다. 영상 시각·파일 이름·네 모서리를 `latest.json`의 `radar`에 적고, 화면은 MapLibre 이미지 레이어로 겹친다. 실패하면 직전 영상을 그대로 두고 상태만 `failed`로 적으며, 화면은 영상이 90분보다 오래되면 숨긴다.

**Tech Stack:** Python 3.12(Actions)·3.9 이상(로컬) + unittest + Pillow + numpy / 순수 HTML·CSS·JS / MapLibre GL JS 4.7.1 image source

**Spec:** `design/specs/2026-09-26-dashboard-redesign-design.md` 5.8절(레이더)·3.2·3.3·6절. 2·3단계 계획(`design/plans/2026-09-26-phase2-hq-ui.md`, `2026-09-27-phase3-site-ui.md`)의 결정을 이어받는다.

## Global Constraints

- 레이더 API: `https://apis.data.go.kr/1360000/RadarImgInfoService/getCmpImg`, `data=CMP_WRC`, `time=YYYYMMDD`(한국 날짜), 기존 `KMA_API_KEY`. 응답 `items.item[0]["rdr-img-file"]`은 목록 또는 `"[주소, 주소, …]"` 문자열이며 마지막이 최신이다. 영상 주소는 `http://`로 오지만 `https://`로 바꿔 받는다(2026-09-28 확인).
- 영상 틀(2026-09-28 시험으로 확정, 00:00·04:45·09:30 영상에서 격자선이 픽셀 단위로 동일): 635×620 RGB, 지도 영역 `x < 596`, `y >= 20`. 투영은 `src/grid_converter.py`와 같은 기상청 LCC(RE 6371.00877, 표준위도 30·60, 기준 126°E·38°N)를 km 단위 연속값으로 쓰고, 픽셀 중심 `(i+0.5, j+0.5)` → km는
  `X = 1.70090916·px + 0.000800691565·py − 437.740555`, `Y = 0.000205876798·px − 1.71024429·py + 290.302204`.
- 수용 기준(설계서 5.8): 기준점 오차 5km 이내. 시험 결과 격자선 3,223픽셀 평균 0.57km·최대 1.6km, 섬 기준점 1픽셀 안팎.
- 범례(위→아래 24칸, 칸 k는 `y = 21+24k … 44+24k`, 확인 위치 `x=603, y=33+24k`)와 칸의 하한 mm/h:
  `(51,51,51)`150 · `(0,3,144)`110 · `(76,78,177)`90 · `(179,180,222)`70 · `(147,0,228)`60 · `(179,41,255)`50 · `(201,105,255)`40 · `(224,169,255)`30 · `(180,0,0)`25 · `(210,0,0)`20 · `(255,50,0)`15 · `(255,102,0)`10 · `(204,170,0)`9 · `(224,185,0)`8 · `(249,205,0)`7 · `(255,220,31)`6 · `(255,255,0)`5 · `(0,90,0)`4 · `(0,140,0)`3 · `(0,190,0)`2 · `(0,255,0)`1 · `(0,74,245)`0.5 · `(0,155,245)`0.1 · `(0,200,255)`0.0
- 우리 비 단계: 눈금 `0.1·1·3·15·30` mm/h, 색 `#cde2fb #9ec5f4 #5598e7 #256abf #0d366b`(`web/assets/common.js`의 `WX.RAIN_BINS`·`WX.RAIN_COLORS`와 같은 값). 단계 = 하한 이하인 눈금 수 − 1, 하한 0.0 칸(0.1 미만)은 그리지 않는다.
- 출력 영상: 경도 122.5~132.0°, 위도 31.0~40.0°의 웹 메르카토르 격자, 가로 760px(세로는 메르카토르 비율로 계산), 투명 바탕 팔레트 PNG. `latest.json` `radar.corners`는 MapLibre 순서(왼쪽 위·오른쪽 위·오른쪽 아래·왼쪽 아래) `[[122.5,40.0],[132.0,40.0],[132.0,31.0],[122.5,31.0]]`.
- 출처 표기 "자료: 기상청"(공공누리 1유형)과 영상 시각을 화면에 보인다. 90분보다 오래된 영상은 숨기고 "레이더 자료 없음".
- 빨강·주황은 특보·법정에만. 레이더 상태 안내는 회색. 이모지 금지(Lucide 아이콘). `prefers-reduced-motion`이면 애니메이션 없음.
- `docs/`는 공개 폴더. `NOTIFICATION_MODE=shadow` 그대로. 화면은 `web/`만 고치고 로컬 `docs/` 게시본은 커밋하지 않는다(`git checkout -- docs && git clean -fd docs`). 푸시·병합은 사용자 확인 후.
- Windows 작업 PC: 명령의 `python3`은 `python`으로 실행한다.

### 계획 단계에서 정한 사항 (사용자 검토 대상)

- **Ruling: 범례는 고정 표 + 매번 확인** — 설계서의 "범례에서 자동으로 읽기" 대신, 위 24색 표를 코드에 두고 매 실행마다 범례 칸 색과 격자선 픽셀 수(3,223±50)를 확인한다. 다르면 영상을 만들지 않고 `radar` 상태를 `failed`로 둔다(기상청이 틀·색을 바꾸면 잘못된 비구름 대신 "레이더 자료 없음"). — 틀리면: 확인 함수만 바꾸면 됨.
- **Ruling: 0.1mm/h 미만 칸은 그리지 않음** — 우리 범례의 첫 눈금(0.1)과 맞추고, 약한 잡음 에코를 줄인다.
- **Ruling: 선 아래 비 채우기** — 해안선·경계선·격자선(검정·회색 선) 픽셀은 주변 8칸 중 2칸 이상이 비이면 그 중 가장 높은 단계로 채운다(선 모양 구멍 방지).
- **Ruling: 영상 경로는 latest.json 기준 상대 경로** — `radar.image`는 `"radar.png?v=YYYYMMDDHHMM"`(설계서 예시 `data/radar.png` 대신). `?data=` 시험 자료 옆에 둔 영상도 같은 방식으로 불러오고, `?v=`로 브라우저 캐시를 피한다.
- **Ruling: 비구름은 "지금"에서만** — 레이더는 관측이므로 본사 스크러버가 예보 시각(1~24)이면 레이어를 숨기고 범례에 "비구름은 지금(관측)만 표시"를 적는다. 현장 화면 지도는 늘 지금 자료(표식과 같음).
- **Ruling: 자체(SVG) 지도에서는 비구름 없음** — 자체 지도 투영이 달라 겹치지 않는다. 비구름 버튼을 숨기고, 현장 카드에는 시각만 적는다.
- **Ruling: 켜기·끄기 기억** — 비구름 버튼 상태는 이 브라우저에만 기억한다(`localStorage` `wx.radar`, 읽기·쓰기 모두 try/catch, 기본 켜짐).
- **Ruling: 지난 1시간 애니메이션은 넣지 않음** — 설계서 50행의 "지난 1시간 레이더 애니메이션"은 이번 단계에서 제외(파일 1장만 덮어쓴다는 5.8의 저장소 용량 원칙 유지).

## Review Focus

1. **오래된 영상·수집 실패**: 수집이 실패해 직전 영상이 남아 있거나(상태 `failed`) 영상 시각이 90분을 넘으면, 오래된 비구름을 지금처럼 보이지 않고 레이어를 숨기며 "레이더 자료 없음"(회색)을 보인다. 90분 이내의 직전 영상은 시각과 함께 계속 보인다. → Task 3 테스트, Task 4 Step 1 node 점검.
2. **기상청 영상 틀·범례 변경**: 영상 크기·범례 색·격자선이 달라지면 잘못 칠한 비구름을 만들지 않고 실패로 처리한다. → Task 1 테스트.
3. **예보 시각에서 관측 비구름**: 본사 스크러버를 예보 시각으로 옮기면 비구름이 사라지고 설명이 바뀐다. 다시 "지금"으로 오면 켜기 설정대로 돌아온다. → Task 4 Step 6.
4. **자체(SVG) 지도로 전환**(`?map=svg` 또는 지도 서비스 장애): 비구름 버튼이 숨고 콘솔 오류가 없다. → Task 4 Step 6, Task 5 Step 4.
5. **화면을 열어 둔 채 자동 갱신**: 5분마다 새 `latest.json`을 받으면 레이어가 새 영상(`?v=` 바뀜)으로 바뀌고 켜기·끄기 선택이 유지된다. → Task 4 Step 6.

---

## 파일 구조

| 파일 | 역할 |
|---|---|
| `src/radar.py` (신규) | 영상 확인·비 단계 추출·투영 변환·웹 지도 영상 만들기(`render_overlay`), API 조회·다운로드·저장(`update_radar`), 수동 확인용 `python -m src.radar <출력 폴더>` |
| `tests/fixtures/radar/RDR_CMP_WRC_202609280930.png` (신규) | 표본 영상(기상청, 공공누리 1유형, 2026-09-28 09:30) |
| `tests/test_radar.py` (신규) | 레이더 처리·조회 테스트 |
| `requirements.txt` (수정) | `Pillow>=10`, `numpy>=1.24` |
| `src/view_model.py` (수정) | `build_latest`/`publish_latest`에 `radar` 인자, 상태 `ok/failed/off`, 실패 시 직전 `radar` 유지 |
| `src/main.py` (수정) | 특보 뒤·화면 데이터 앞에 레이더 갱신 |
| `scripts/preview_fixtures.py` (수정) | 시험 자료에 레이더(표본 영상으로 만든 `radar.png`), `radarold`·`noradar` 추가 |
| `web/assets/common.js` (수정) | `WX.radarInfo`, `WX.radarPref` |
| `web/assets/geo.js` (수정) | 지도 어댑터 `canRadar`·`setRadar` |
| `web/index.html`, `hq-map.js`, `hq.css` (수정) | 비구름 버튼·범례 문구 |
| `web/site.html`, `site-map.js`, `site.js`, `site.css` (수정) | 비구름 버튼·"주변 비구름" 카드 |
| `CLAUDE.md`, 설계서 5.8 (수정) | 운영 설명·결정 반영 |

## 작업 환경 (실행 전 1회)

- 작업 폴더: `.worktrees/phase4-radar`(브랜치 `phase4-radar`, `origin/main`에서 분기). Windows는 심볼릭 링크 대신 `config.py`를 복사한다(git 제외 파일, 커밋 금지).
- 기준 테스트: `python -m unittest discover -s tests -b` → `OK` (164개).
- 화면 점검: `python -m src.publish` → `python scripts/preview_fixtures.py` → 저장소 폴더에서 `python -m http.server 8765` → `node scripts/ui_check.mjs <단계.json>`(단계 파일은 작업 기록 폴더, 지도 준비 대기 `after` 10000 이상).

---

### Task 1: 레이더 영상 처리 핵심(확인·비 단계·투영·웹 지도 영상)

**Files:**
- Create: `src/radar.py`, `tests/test_radar.py`, `tests/fixtures/radar/RDR_CMP_WRC_202609280930.png`(작업 기록 폴더의 시험 영상을 복사하거나 `https://www.kma.go.kr/repositary/image/rdr/img/RDR_CMP_WRC_202609280930.png`에서 받는다)
- Modify: `requirements.txt`

**Interfaces:**
- Produces (`src/radar.py`):
  - 상수 `LEGEND: tuple[tuple[tuple[int,int,int], float], ...]`(위 24칸, 위→아래), `RAIN_BINS = (0.1, 1, 3, 15, 30)`, `RAIN_COLORS`(RGB 5개), `PIXEL_TO_KM`(6개 계수), `BOUNDS = (122.5, 31.0, 132.0, 40.0)`, `OUT_WIDTH = 760`, `CORNERS`(Global Constraints의 목록), `GRATICULE = (80, 80, 80)`, `GRATICULE_COUNT = 3223`.
  - `class RadarFormatError(Exception)`
  - `check_frame(rgb: np.ndarray) -> None` — 크기(620, 635, 3)·범례 24칸·격자선 픽셀 수(지도 영역, ±50)가 다르면 `RadarFormatError`.
  - `rain_steps(rgb: np.ndarray) -> np.ndarray` — (620, 635) int8, 비 단계 0~4, 없음 −1. 지도 영역 밖은 −1. 선 채우기 Ruling 적용.
  - `lcc_km(lat, lon) -> (x, y)`, `pixel_to_latlon(px, py) -> (lat, lon)`, `latlon_to_pixel(lat, lon) -> (px, py)` — numpy 배열 지원, 픽셀은 가장자리 기준 연속 좌표(픽셀 i의 중심 = i+0.5).
  - `render_overlay(rgb: np.ndarray) -> PIL.Image.Image` — `check_frame` 후 팔레트("P") 영상, 색 번호 0 = 투명, 1~5 = 비 단계.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_radar.py`에 표본 영상을 읽는 도우미 `sample()`(RGB numpy 배열)와 아래 테스트.

```python
class FrameTests(unittest.TestCase):
    def test_sample_frame_passes(self):
        radar.check_frame(sample())

    def test_changed_legend_is_rejected(self):
        rgb = sample().copy(); rgb[33 + 24 * 10, 600:606] = (1, 2, 3)
        with self.assertRaises(radar.RadarFormatError):
            radar.check_frame(rgb)

    def test_moved_graticule_is_rejected(self):
        rgb = sample().copy(); rgb[(rgb == radar.GRATICULE).all(-1)] = (250, 250, 250)
        with self.assertRaises(radar.RadarFormatError):
            radar.check_frame(rgb)

    def test_wrong_size_is_rejected(self):
        with self.assertRaises(radar.RadarFormatError):
            radar.check_frame(sample()[:600])


class StepTests(unittest.TestCase):
    def test_legend_colours_map_to_our_bins(self):
        # (0,155,245)=0.1~0.5 → 0, (0,255,0)=1~2 → 1, (0,140,0)=3~4 → 2, (255,50,0)=15~20 → 3, (224,169,255)=30~40 → 4
        steps = radar.rain_steps(sample())
        self.assertEqual(0, steps[490, 302]); self.assertEqual(2, steps[527, 199])
        self.assertEqual(3, steps[548, 274]); self.assertEqual(4, steps[546, 212])

    def test_below_point_one_background_and_outside_are_empty(self):
        steps = radar.rain_steps(sample())
        self.assertEqual(-1, steps[490, 231])    # (0,200,255) = 0.0~0.1
        self.assertEqual(-1, steps[196, 306])    # 서울 부근, 비 없음
        self.assertEqual(-1, steps[300, 610])    # 범례
        self.assertEqual(-1, steps[5, 100])      # 제목 줄

    def test_line_pixels_inside_rain_are_filled(self):
        rgb = np.full((620, 635, 3), 250, np.uint8); rgb[100:110, 100:110] = (255, 50, 0); rgb[105, 100:110] = (0, 0, 0)
        self.assertEqual(3, radar.rain_steps(rgb)[105, 105])
```

`test_line_pixels_inside_rain_are_filled`는 틀 확인을 하지 않는 `rain_steps`만 부른다. 표본 좌표는 2026-09-28 시험에서 뽑은 값이다(행, 열 = y, x).

```python
class ProjectionTests(unittest.TestCase):
    def test_round_trip(self):
        px, py = radar.latlon_to_pixel(36.35, 127.385)
        lat, lon = radar.pixel_to_latlon(px, py)
        self.assertAlmostEqual(36.35, float(lat), places=4); self.assertAlmostEqual(127.385, float(lon), places=4)

    def test_graticule_error_within_acceptance(self):
        # 설계서 5.8 수용 기준 5km. 시험 결과 평균 0.57km·최대 1.6km.
        ys, xs = np.nonzero((sample() == radar.GRATICULE).all(-1))
        keep = (xs < 596) & (ys >= 20)
        lat, lon = radar.pixel_to_latlon(xs[keep] + 0.5, ys[keep] + 0.5)
        d_lon = (lon - np.round(lon)) * 111.32 * np.cos(np.radians(lat)); d_lat = (lat - np.round(lat)) * 111.0
        err = np.minimum(abs(d_lon), abs(d_lat))
        self.assertLess(float(np.sqrt((err ** 2).mean())), 1.0); self.assertLess(float(err.max()), 2.0)

    def test_islands_land_on_coastline(self):
        black = np.argwhere((sample() == (0, 0, 0)).all(-1)) + 0.5
        for lat, lon in ((37.242, 131.867), (34.684, 125.435)):   # 독도, 흑산도
            px, py = radar.latlon_to_pixel(lat, lon)
            self.assertLess(np.hypot(black[:, 1] - px, black[:, 0] - py).min(), 2.0)


class OverlayTests(unittest.TestCase):
    def test_overlay_shape_palette_and_colours(self):
        img = radar.render_overlay(sample())
        self.assertEqual(("P", 760), (img.mode, img.width))
        self.assertTrue(880 < img.height < 900)

    def test_overlay_places_rain_where_it_was_observed(self):
        img = radar.render_overlay(sample())
        self.assertIn(4 + 1, window(img, 32.096, 125.188))    # 30mm/h 이상
        self.assertIn(3 + 1, window(img, 32.068, 126.317))    # 15~30
        self.assertEqual({0}, window(img, 37.5665, 126.978))  # 서울, 비 없음
```

`window(img, lat, lon)`은 테스트 안의 도우미로, `BOUNDS`와 메르카토르 식(`y = ln(tan(π/4 + φ/2))`)으로 출력 픽셀 위치를 계산해(구현 코드를 쓰지 않고 독립적으로) 그 둘레 5×5칸 값의 집합을 돌려준다. 재투영은 가장 가까운 원본 픽셀을 쓰므로 한 픽셀 단위로는 흔들릴 수 있다.

- [ ] **Step 2: 실패 확인** — `python -m unittest tests.test_radar -v` → `ModuleNotFoundError: No module named 'src.radar'`.

- [ ] **Step 3: `src/radar.py` 구현(Interfaces의 상수·함수).**
  - `lcc_km`와 역변환은 `grid_converter`의 상수(RE·SLAT1·SLAT2·OLON·OLAT)를 가져와 격자 반올림 없이 km로 계산한다(numpy 벡터).
  - `render_overlay`: 출력 행 j의 위도는 메르카토르 y를 위(40°)→아래(31°)로 균등 분할, 열 i의 경도는 균등 분할(픽셀 중심). 각 출력 픽셀 → `latlon_to_pixel` → `floor` → 지도 영역 안이면 `rain_steps` 값, 밖이면 투명. 세로 = `round(760 × (merc(40)−merc(31)) / radians(9.5))`. 팔레트는 0번 투명(`transparency=0`) + `RAIN_COLORS`.
  - `requirements.txt`에 `Pillow>=10`, `numpy>=1.24` 추가.

- [ ] **Step 4: 통과 확인** — `python -m unittest tests.test_radar -v` → 모두 PASS, 전체 `python -m unittest discover -s tests -b` → OK.

- [ ] **Step 5: 커밋**

```bash
git add src/radar.py tests/test_radar.py tests/fixtures/radar requirements.txt
git commit -m "레이더 영상 처리: 범례·틀 확인, 비 단계 추출, 기상청 LCC 보정 변환, 웹 지도 영상"
```

---

### Task 2: 레이더 조회·저장(`update_radar`)과 실패 격리

**Files:**
- Modify: `src/radar.py`, `tests/test_radar.py`

**Interfaces:**
- Consumes: Task 1의 `render_overlay`, `CORNERS`, `RadarFormatError`; `src.collection.CircuitBreaker`(`is_tripped`, `record_success`, `record_failure`).
- Produces:
  - `image_urls(item: dict) -> list[str]` — `rdr-img-file`이 목록·`"[a, b]"` 문자열 어느 쪽이든 주소 목록(`http://` → `https://`).
  - `observed_at(url: str) -> datetime` — 파일 이름 `RDR_CMP_WRC_YYYYMMDDHHMM.png`의 한국시각(+09:00). 형식이 다르면 `ValueError`.
  - `update_radar(api_key, out_path, now, breaker=None, timeout=10) -> dict | None` — 성공하면 `out_path`에 PNG를 임시 파일 → 교체로 쓰고 `{"image": "radar.png?v=YYYYMMDDHHMM", "observed_at": "…+09:00", "corners": CORNERS}`를 돌려준다(`image`의 파일 이름은 `os.path.basename(out_path)`). 어떤 실패든(네트워크·빈 목록·형식 변경·회로 차단 중) 기존 파일을 건드리지 않고 이유를 한 줄 출력한 뒤 `None`. 회로 차단이 이미 발동돼 있으면 요청하지 않는다. 출력에 API 키를 넣지 않는다.
  - `python -m src.radar [출력 폴더]` — `config.KMA_API_KEY`로 실제 영상을 받아 `<폴더>/radar.png`를 만들고 결과 dict를 출력(수동 확인용, 기본 폴더 `tmp/radar`).

- [ ] **Step 1: 실패하는 테스트 작성** — `requests.get`을 `unittest.mock.patch("src.radar.requests.get")`로 바꾼다. 목록 응답은 `{"response": {"header": {"resultCode": "00"}, "body": {"items": {"item": [{"rdr-img-file": …}]}}}}`, 영상 응답은 표본 PNG 바이트.

```python
class UpdateTests(unittest.TestCase):
    def test_image_urls_accepts_list_and_string(self):
        a = "http://www.kma.go.kr/repositary/image/rdr/img/RDR_CMP_WRC_202609280925.png"
        b = a.replace("0925", "0930")
        expected = [a.replace("http://", "https://"), b.replace("http://", "https://")]
        self.assertEqual(expected, radar.image_urls({"rdr-img-file": [a, b]}))
        self.assertEqual(expected, radar.image_urls({"rdr-img-file": f"[{a}, {b}]"}))

    def test_observed_at_from_file_name(self):
        self.assertEqual("2026-09-28T09:30:00+09:00", radar.observed_at("https://x/RDR_CMP_WRC_202609280930.png").isoformat())
        with self.assertRaises(ValueError):
            radar.observed_at("https://x/other.png")

    def test_success_writes_png_and_returns_view(self):
        # 목록의 마지막(최신) 주소를 받고, 결과 파일은 760폭 PNG
        view = radar.update_radar("KEY", out, NOW)
        self.assertEqual({"image": "radar.png?v=202609280930", "observed_at": "2026-09-28T09:30:00+09:00",
                          "corners": radar.CORNERS}, view)
        self.assertEqual(760, Image.open(out).width)
        self.assertTrue(get.call_args_list[-1].args[0].endswith("RDR_CMP_WRC_202609280930.png"))

    def test_network_error_keeps_old_file(self):
        # 기존 파일 내용 b"old"가 그대로이고 None
    def test_empty_list_returns_none(self):
    def test_changed_frame_returns_none_and_keeps_old_file(self):
        # 영상 응답을 범례 한 칸 색을 바꾼 PNG로
    def test_tripped_breaker_skips_request(self):
        # breaker.is_tripped() True → requests.get 호출 0회, None
    def test_key_is_not_printed(self):
        # 네트워크 오류 메시지에 키가 들어 있어도 출력(contextlib.redirect_stdout)에 "SECRETKEY"가 없다
```

빈 본문으로 적은 테스트는 주석에 적힌 조건을 그대로 단언한다.

- [ ] **Step 2: 실패 확인** — `python -m unittest tests.test_radar -v` → 새 테스트 FAIL(`AttributeError: … 'image_urls'` 등).
- [ ] **Step 3: 구현** — 목록 조회 파라미터 `serviceKey, dataType=JSON, pageNo=1, numOfRows=10, data=CMP_WRC, time=<now의 한국 날짜>`. 오류 출력은 예외 종류와 단계("목록 조회"/"영상 받기"/"영상 형식")만 적는다. 저장은 같은 폴더의 임시 파일 → `os.replace`.
- [ ] **Step 4: 통과 확인** — `python -m unittest tests.test_radar -v` PASS, 전체 OK. 실제 확인: `python -m src.radar tmp/radar` → dict 출력, `tmp/radar/radar.png`를 열어 남해·제주 부근 비구름 확인.
- [ ] **Step 5: 커밋** — `git add src/radar.py tests/test_radar.py && git commit -m "레이더 조회·저장: 최신 영상 선택, 원자적 저장, 실패 시 기존 영상 유지"`

---

### Task 3: `latest.json` 연결·수집 흐름·시험 자료

**Files:**
- Modify: `src/view_model.py`, `src/main.py`, `scripts/preview_fixtures.py`, `tests/test_view_model.py`, `tests/test_preview_fixtures.py`

**Interfaces:**
- Consumes: Task 2의 `update_radar`, 반환 dict 형태.
- Produces:
  - `build_latest(..., radar=None, radar_ok=None)`: `radar_ok is None` → 상태 `"off"`·`radar` 그대로(None); `True` → `"ok"`·`radar` 값; `False` → `"failed"`·직전 `latest["radar"]`(없으면 None).
  - `publish_latest(path, collected, mid_forecasts, now, radar=None, radar_ok=None)` — 그대로 넘긴다.
  - `main.update_radar_safely(breaker) -> tuple[dict | None, bool]` — 예외도 삼켜 `(None, False)`. 레이더 파일 `docs/data/radar.png`(`RADAR_PATH`).
  - 시험 자료: 모든 자료에 `radar = {"image": "radar.png?v=fixture", "observed_at": generated_at − 10분, "corners": CORNERS}`·상태 `ok`, 추가 `radarold`(관측 generated_at − 120분, 상태 `failed`)·`noradar`(`radar: None`, 상태 `failed`). 출력 폴더에 표본 영상으로 만든 `radar.png`를 쓴다.

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_view_model.py`)

```python
    def test_radar_ok(self):
        view = {"image": "radar.png?v=202609251740", "observed_at": "2026-09-25T17:40:00+09:00", "corners": CORNERS}
        latest = build([make_item()], radar=view, radar_ok=True)
        self.assertEqual(("ok", view), (latest["status"]["radar"], latest["radar"]))

    def test_radar_failure_keeps_previous_image(self):
        previous = build([make_item()], radar=VIEW, radar_ok=True)
        latest = build([make_item()], previous=previous, radar=None, radar_ok=False)
        self.assertEqual(("failed", VIEW), (latest["status"]["radar"], latest["radar"]))

    def test_radar_failure_without_previous(self):
        latest = build([make_item()], radar=None, radar_ok=False)
        self.assertEqual(("failed", None), (latest["status"]["radar"], latest["radar"]))
```

`build` 도우미에 `radar`, `radar_ok` 인자를 더한다. 기존 `test_top_level_fields`(`"off"`, `None`)는 그대로 통과해야 한다. `tests/test_preview_fixtures.py`에는 `radarold`·`noradar`가 있고, 모든 자료의 `radar.image`가 `radar.png?v=`로 시작하거나 None인지, 출력 폴더에 `radar.png`가 생기는지 단언한다.

- [ ] **Step 2: 실패 확인** — `python -m unittest tests.test_view_model tests.test_preview_fixtures -v` → FAIL(`unexpected keyword argument 'radar'`).
- [ ] **Step 3: 구현** — `main()`에서 `attach_weather_warnings` 다음, `write_latest_view` 앞에 `radar_view, radar_ok = update_radar_safely(breaker)`를 두고 `write_latest_view(..., radar_view, radar_ok)`로 넘긴다. 로그 한 줄: `[레이더] 09:30 영상` 또는 `[레이더] 이번 수집 실패(직전 영상 유지)`. 모듈 도크스트링의 산출물 목록에 `docs/data/radar.png`를 더한다.
- [ ] **Step 4: 통과 확인** — 전체 `python -m unittest discover -s tests -b` → OK, `python -m compileall -q src tests`.
- [ ] **Step 5: 커밋** — `git commit -m "latest.json에 레이더 영상 정보·상태 연결, 실패 시 직전 영상 유지, 시험 자료 추가"`

---

### Task 4: 공통 레이더 표시와 본사 화면 비구름 레이어

**Files:**
- Modify: `web/assets/common.js`, `web/assets/geo.js`, `web/index.html`, `web/assets/hq-map.js`, `web/assets/hq.css`

**Interfaces:**
- Consumes: `latest.radar`(Task 3), `WX.dataUrl`.
- Produces:
  - `WX.RADAR_MAX_MIN = 90`
  - `WX.radarInfo(latest, now = Date.now()) -> {url, corners, time, fresh} | null` — `latest.radar`가 없거나 `image`가 `/^[\w.-]+\.png(\?v=\w+)?$/`가 아니거나 `corners`가 숫자 4쌍이 아니면 null. `url`은 `new URL(image, new URL(WX.dataUrl("data/latest.json"), location.href)).href`, `time`은 "HH:MM"(한국시각), `fresh`는 관측 후 0~90분.
  - `WX.radarPref.get() -> boolean`(기본 true), `WX.radarPref.set(on)` — `localStorage` `wx.radar`, 예외 시 기본값·무시.
  - 지도 어댑터: `canRadar`(maplibre true, svg false), `setRadar(info | null, visible: boolean)` — maplibre는 처음에 image source `radar` + raster layer `radar`(`raster-opacity` 0.72, `raster-fade-duration` 0)를 첫 symbol 레이어 아래에 추가하고, 이후 `url`이 바뀌면 `updateImage`, 숨길 때는 `visibility: none`. svg는 아무것도 안 함.
  - 본사: `#layerBtn`(아이콘 `i-rain`, `aria-pressed`, `aria-label="비구름 레이어"`)을 `.mapctl` 맨 앞에, 범례 `.src`에 `id="radarSrc"`.

- [ ] **Step 1: node 점검(실패 확인)** — 작업 기록 폴더에 `radar_check.js`: `vm`으로 `common.js`를 읽고(`ctx.window = ctx`, `location = {search: "", href: "https://x/weather-alert-system/index.html"}`, `localStorage`는 던지는 가짜) 아래를 확인. 지금은 `WX.radarInfo is not a function`으로 실패해야 한다.
  - 관측 10분 전 → `fresh: true`, `time: "09:30"`, `url`이 `https://x/weather-alert-system/data/radar.png?v=202609280930`
  - 관측 91분 전 → `fresh: false`
  - `radar: null`, `image: "https://evil/x.png"`, `image: "../x.png"`, `corners` 3쌍 → 모두 null
  - `localStorage`가 던져도 `WX.radarPref.get() === true`, `set(false)`가 예외 없음
- [ ] **Step 2: `common.js` 구현 후 Step 1 점검 통과.**
- [ ] **Step 3: `geo.js`에 `canRadar`·`setRadar` 구현.**
- [ ] **Step 4: 본사 화면 연결** — `hq-map.js`에 `syncRadar()`: `info = WX.radarInfo(state.latest)`; 보임 = `adapter.canRadar && info && info.fresh && state.h === 0 && WX.radarPref.get()`. `attach`·`render`(시각 변경)·`reload`(자동 갱신) 끝에서 부른다. `#layerBtn`은 `canRadar`가 false면 숨기고, 누르면 `radarPref` 반전 + `aria-pressed`·`.on` 갱신 + `syncRadar()`. `#radarSrc` 문구:
  - 신선·지금: `비구름 {time} 레이더 · 자료: 기상청`
  - 예보 시각: `비구름은 지금(관측)만 표시 · 자료: 기상청`
  - 없음·90분 초과: `레이더 자료 없음 · 자료: 기상청`
  - 자체 지도: `자료: 기상청`(지금과 같음)
  `hq.css`는 `.mapctl button.on`을 선택 틴트(`--sel-tint` 계열, 기존 토큰)로 표시한다.
- [ ] **Step 5: 게시·시험 자료** — `python -m src.publish && python scripts/preview_fixtures.py`, `python -m http.server 8765`.
- [ ] **Step 6: 화면 점검(`ui_check`)** — `docs/index.html?data=../.superpowers/preview/fixtures/rain.json`, 1440×900:
  - 캡처에서 남해·제주 남쪽에 파랑 비구름이 보이고 현장 표식·지명 글자가 비구름 위에 보인다. 범례 "비구름 HH:MM 레이더".
  - `#layerBtn` 클릭 → 비구름 사라짐, 새로고침 뒤에도 꺼짐 유지, 다시 클릭 → 켜짐.
  - 스크러버 키보드 → 1칸: 비구름 사라짐·"지금(관측)만" 문구, ← 로 복귀: 다시 보임.
  - `radarold.json`·`noradar.json`: 비구름 없음, "레이더 자료 없음", 콘솔 오류 0.
  - `?map=svg`: `#layerBtn` 숨김, 콘솔 오류 0.
  - 자동 갱신: `initScript`로 `fetch`를 가로채 두 번째 응답의 `radar.image`를 `radar.png?v=fixture2`로 바꾸고 `REFRESH` 간격이 지난 뒤(또는 `visibilitychange` 발생) 레이어 source URL이 `fixture2`로 바뀌고 버튼 상태가 유지되는지 확인.
  - 390×844: 버튼·범례가 겹치지 않는다.
- [ ] **Step 7: 전체 테스트·게시본 되돌리기·커밋** — `python -m unittest discover -s tests -b` OK, `git checkout -- docs && git clean -fd docs`, `git commit -m "본사 화면 비구름 레이어: 레이더 영상 겹치기, 켜기·끄기, 지금 시각에서만 표시, 90분 초과 숨김"`

---

### Task 5: 현장 화면 비구름(지도 버튼·"주변 비구름" 카드)

**Files:**
- Modify: `web/site.html`, `web/assets/site-map.js`, `web/assets/site.js`, `web/assets/site.css`

**Interfaces:**
- Consumes: Task 4의 `WX.radarInfo`, `WX.radarPref`, 어댑터 `canRadar`·`setRadar`.
- Produces: `#layerBtn`(지도 오른쪽 위, 상단 막대 아래, 유리 버튼), 6번 카드 제목 "주변 비구름"·부제 `#radarSub`. `SITE.map.render()`가 레이어를 맞춘다(보임 = `canRadar && info && info.fresh && radarPref`; 현장 화면은 시각과 무관).

- [ ] **Step 1: 카드 문구 구현** — `#radarSub`:
  - 신선: `레이더 {time} · 자료: 기상청`
  - 없음·90분 초과: `레이더 자료 없음`
  - 자체 지도(`canRadar` false): `간단한 지도에서는 비구름을 표시하지 않습니다`
  버튼 "지도로 보기"는 그대로(3단계 동작 유지).
- [ ] **Step 2: 지도 버튼·레이어 구현** — 본사와 같은 켜기·끄기 규칙(`radarPref` 공유). 자동 갱신(`site.js`의 새 자료 적용) 뒤 `SITE.map.render()`에서 새 영상으로 바뀐다. 시트가 "펼침" 위치일 때 버튼이 시트에 가리면 되고, "반"·"지도" 위치에서 누를 수 있어야 한다.
- [ ] **Step 3: 게시·시험 자료** — Task 4 Step 5와 같음.
- [ ] **Step 4: 화면 점검(`ui_check`)** — `docs/site.html?data=../.superpowers/preview/fixtures/rain.json&id=<제주·남해안에 가까운 현장 ID>`, 390×844:
  - "지도로 보기"(손가락 `tap`) → 시트가 내려가고 현장 주변 비구름이 보인다. 카드 부제 "레이더 HH:MM · 자료: 기상청".
  - `#layerBtn` `tap` → 비구름 꺼짐, 다시 → 켜짐. 본사에서 끈 설정이 현장 화면에도 적용.
  - `radarold`·`noradar`·`?map=svg`: 비구름 없음, 카드 문구가 위 규칙대로, 콘솔 오류 0.
  - 1440×900(PC 2단): 버튼이 지도 열 안에 있고 내용 열에 가리지 않는다.
- [ ] **Step 5: 전체 테스트·게시본 되돌리기·커밋** — `git commit -m "현장 화면 비구름: 지도 버튼, 주변 비구름 카드(레이더 시각·자료 없음 안내)"`

---

### Task 6: 문서 정리와 최종 확인

**Files:**
- Modify: `CLAUDE.md`, `design/specs/2026-09-26-dashboard-redesign-design.md`(5.8절), `README.md`(설치 패키지가 적혀 있으면)

- [ ] **Step 1: 설계서 5.8 갱신** — 결정 사항(고정 범례 표 + 확인, 0.1 미만 제외, 상대 경로 `radar.png?v=`, 지금 시각에서만, 자체 지도 제외, 애니메이션 제외)과 시험 결과(평균 0.57km·최대 1.6km, 2026-09-28)를 적는다.
- [ ] **Step 2: `CLAUDE.md` 갱신** — 4단계 완료 표시(배포는 병합 뒤), 테스트 수, `src/radar.py`·`python -m src.radar` 설명, 새 미룬 개선.
- [ ] **Step 3: 최종 확인** — `python -m unittest discover -s tests -v`(개수 기록), `python -m compileall -q src tests`, `python -m src.radar tmp/radar`로 실제 영상 1회, `git status`에 `docs/`·`config.py`·`tmp/`가 없는지.
- [ ] **Step 4: 커밋** — `git commit -m "4단계 레이더 문서 정리: 설계서 5.8 결정 반영, 인수인계 갱신"`
- [ ] **Step 5: 사용자 확인 뒤** 병합·푸시하고, Actions 수동 실행 1회 로그에서 `[레이더]` 줄·발송 0건·`NOTIFICATION_MODE: shadow`를 확인한 뒤 공개 화면에서 비구름을 확인한다.

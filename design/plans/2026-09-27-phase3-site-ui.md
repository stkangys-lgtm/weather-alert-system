# 3단계 현장 화면 + 홈 화면 추가 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 현장 안전관리자가 휴대폰으로 자기 현장 하나를 보는 현장 화면(`site.html?id=현장ID`)을 만들고, 본사·현장 화면을 휴대폰 홈 화면에 추가할 수 있게 한다.

**Architecture:** 2단계의 `web/` → `src/publish.py` → `docs/` 구조를 그대로 쓴다. 본사 상세와 현장 화면이 함께 쓰는 부품(칩·수치·타임라인·법정 안내)을 `web/assets/parts.js`와 `app.css`로 옮기고, 현장 화면은 `site.html`·`site.css`·`site.js`(본문)·`site-map.js`(지도·끌어올리는 시트)로 만든다. 홈 화면 추가는 본사용 고정 매니페스트와, 수집 실행이 현장마다 만드는 매니페스트(`docs/manifests/<ID>.webmanifest`, 시작 주소 = 그 현장 화면)로 한다.

**Tech Stack:** Python 3.12(Actions)·3.9(로컬) + unittest / 순수 HTML·CSS·JS(빌드 도구 없음) / MapLibre GL JS 4.7.1 + OpenFreeMap positron / Pretendard v1.3.9 / Lucide 아이콘 / 웹 앱 매니페스트

**Spec:** `design/specs/2026-09-26-dashboard-redesign-design.md` (2026-09-26 승인). 이 계획은 9절의 3단계와 3.3·4·5.9·5.10·6·7절을 구현한다. 2단계 계획(`design/plans/2026-09-26-phase2-hq-ui.md`)의 결정을 이어받는다.

## Global Constraints

- 빌드 도구 없음(순수 HTML·CSS·JS). 계산 규칙(문장·자료 상태·정렬 기준 값)은 Python에서 만들고 JS는 표시·상호작용만 한다(5.1).
- 외부 파일은 2단계와 같은 버전·무결성 해시를 쓴다:
  - `https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.js` → `sha384-SYKAG6cglRMN0RVvhNeBY0r3FYKNOJtznwA0v7B5Vp9tr31xAHsZC0DqkQ/pZDmj`
  - `https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.css` → `sha384-MinO0mNliZ3vwppuPOUnGa+iq619pfMhLVUXfC4LHwSCvF9H+6P/KO4Q7qBOYV5V`
  - `https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard-dynamic-subset.min.css` → `sha384-V1aeodcjJTo8c7lEQKPTnsMG6Yk8y6O/1kzqU/BCXw78Yw1W8XYFJGgjYa3oInYZ`
- 색·글꼴·움직임은 `tokens.css`만 쓴다. 빨강·주황은 기상청 특보·법정 조치에만(아이콘 필수). 수집 실패·지연·예보 없음은 회색. 작은 글자 대비 4.5 이상(`--muted-ink`).
- CI: 로고 PNG는 가공 없이 높이만(모바일 22px), 불투명 흰 바탕. 앱 아이콘은 규정집 심볼 SVG를 흰 바탕 정사각형에 여백을 두고 크기만 바꿔 만든다(5.9). 히어로에 심볼·워터마크 금지.
- 금지어("선제", "기준 도달", "주의 단계", "경계 단계")·판단어("훨씬", "크게") 금지. 예비특보는 "발표".
- `prefers-reduced-motion: reduce`이면 애니메이션을 끈다. 이모지 금지(Lucide 아이콘).
- 서비스 워커(오프라인 캐시)는 넣지 않는다(5.9).
- `docs/`는 공개 폴더다. 개인정보를 넣지 않는다. 계획·설계는 `design/`. `NOTIFICATION_MODE=shadow` 그대로. 푸시·병합은 사용자 확인 후.
- 지원: 최근 2년 Chrome·Safari·Edge·삼성 인터넷. 화면 문구 한국어.

### 계획 단계에서 정한 사항 (사용자 검토 대상)

- **Ruling: 현장별 홈 화면 추가** — 설계서 5.9 "현장 화면에서 추가하면 그 현장 주소로 시작한다"를 지키려고, 수집 실행이 현장마다 매니페스트(`docs/manifests/<ID>.webmanifest`, 시작 주소 `site.html?id=<ID>`)를 만들고, 현장 화면이 주소의 ID로 자기 매니페스트를 연결한다. 본사 화면은 고정 매니페스트(`manifest.webmanifest`, 시작 주소 `./`). — 틀리면: 매니페스트 방식만 바꾸면 됨.
- **Ruling: 주변 비구름 카드** — 레이더는 4단계이므로 3단계의 6번 카드는 "현장 주변 지도"(누르면 시트가 내려가 지도가 보임)로 두고, 4단계에서 비구름을 더한다.
- **Ruling: 주소에 현장 ID가 없거나 모르는 ID일 때** — 빈 화면 대신 "현장 선택" 목록을 보여 준다(현장 이름이 바뀌면 ID도 바뀌므로 안내 문구 포함). 로그인 분리는 이후 과제.
- **Ruling: 공통 부품 정리** — 본사 상세(`hq-detail.js`)의 칩·수치·타임라인·법정 안내 코드와 CSS를 `parts.js`·`app.css`로 옮겨 현장 화면과 함께 쓴다(본사 화면 동작·모양은 그대로).
- **Ruling: 화면 확인 도구 커밋** — 2단계에서 만든 헤드리스 Chrome 점검 도구를 `scripts/ui_check.mjs`로 저장소에 넣는다(시험 도구, 자동 테스트 체계 아님). 앱 미리보기 창이 가려지면 지도가 그려지지 않기 때문.
- **Ruling: 현장 화면 지도** — 자기 현장 표식(맥박 효과)만 보인다. 다른 현장은 본사 화면에서 본다.

## Review Focus

1. **주소의 현장 ID가 없거나, 모르거나, 이상한 값**(`?id=`, `?id=<script>`, 이름이 바뀐 옛 ID): 빈 화면·오류 없이 "현장 선택" 목록이 나오고, 이상한 값으로 매니페스트 주소를 만들지 않는다. → Task 3 Step 6, Task 1 테스트.
2. **작은 휴대폰 첫 화면**(390×844, 360×640): 현장명·기온·요약 문장·특보/법정 칩이 스크롤 없이 보이고, 긴 현장명("포항~안동2 국도건설공사")은 줄바꿈되어 넘치지 않는다. → Task 3 Step 5, Task 4 Step 4.
3. **끌기·스크롤 충돌**: 타임라인을 좌우로 문지를 때 시트가 끌려가지 않고, 시트 손잡이로만 시트가 움직이며, 시트 안 스크롤이 지도를 움직이지 않는다. → Task 4 Step 4.
4. **10일 예보의 빈 날·같은 기온**: 자료 없는 날은 "예보 자료 없음", 모든 날의 기온이 같거나 하루만 있어도 막대가 깨지지 않는다. → Task 3 Step 5(node 점검).
5. **수집 실패·지연·예보 없음·자동 갱신**: 현장 화면에서도 회색 안내로 보이고 "정상"으로 보이지 않으며, 홈 화면 앱으로 열어 둔 채 5분마다 새 자료로 바뀐다(선택 시각 유지). → Task 3 Step 6.

---

## 파일 구조

| 파일 | 역할 |
|---|---|
| `src/publish.py` (수정) | 현장별 매니페스트 생성 `write_site_manifests()` |
| `src/main.py` (수정) | 게시 뒤 현장별 매니페스트 생성 |
| `web/manifest.webmanifest` (신규) | 본사 화면 홈 화면 추가 |
| `web/assets/icons/app-192.png`, `app-512.png`, `apple-touch-icon.png` (신규) | 앱 아이콘(심볼 SVG를 흰 바탕에 배치) |
| `web/assets/parts.js` (신규) | 현장 카드 공통 부품: 히어로 하늘 판정·칩·수치·법정 안내·예보 문장·타임라인 |
| `web/assets/common.js` (수정) | `isRain`·`hourText`·`skyIcon`·`weekday`·`shortDate` |
| `web/assets/geo.js` (수정) | 처음 보기 위치(`view`) 선택 |
| `web/assets/app.css` (수정) | 지도 알림·자체 지도·로고·상태·히어로·수치·타임라인·불러오기 실패를 공통으로 |
| `web/assets/hq.css`, `hq.js`, `hq-detail.js`, `web/index.html` (수정) | 공통 부품 사용, 매니페스트 연결, "현장 화면" 버튼 |
| `web/assets/icons.svg` (수정) | 해·구름·구름해·눈 아이콘 |
| `web/site.html`, `web/assets/site.css`, `site.js`, `site-map.js` (신규) | 현장 화면 |
| `scripts/ui_check.mjs` (신규) | 헤드리스 Chrome 화면 점검 도구 |
| `tests/test_web_app.py` (신규), `tests/test_publish.py` (수정) | Python 테스트 |

## 작업 환경 (실행 전 1회)

- 작업 폴더: `~/Projects/weather-alert-system/.worktrees/phase3-site-ui` (브랜치 `phase3-site-ui`, `origin/main`에서 분기), `config.py`는 `ln -s ../../config.py config.py`.
- 기준 테스트: `python3 -m unittest discover -s tests -b` → `OK` (155개).
- 미리보기: `python3 -m src.publish && python3 scripts/preview_fixtures.py && ln -sfn ../../docs .superpowers/preview/site`, `/Users/youngsookang/Claude/.claude/launch.json`의 `hq-preview` 경로를 `…/.worktrees/phase3-site-ui/.superpowers/preview`로 바꾼다. `docs/` 게시본은 커밋하지 않는다.
- 화면 점검: Task 2부터 `node scripts/ui_check.mjs <steps.json>` (단계 파일은 작업 기록 폴더에 둔다). 지도는 준비에 6~10초 걸리므로 `after`를 10000 이상으로.

---

### Task 1: 앱 아이콘과 홈 화면 추가 설정(본사 고정 + 현장별 생성)

**Files:**
- Create: `web/assets/icons/app-192.png`, `app-512.png`, `apple-touch-icon.png`, `web/manifest.webmanifest`
- Modify: `src/publish.py`, `src/main.py` (`publish_screens`), `web/index.html` (`<head>`)
- Test: `tests/test_web_app.py` (신규), `tests/test_publish.py`

**Interfaces:**
- Consumes: `docs/data/latest.json`의 `sites[].id/short/name`
- Produces: `publish.write_site_manifests(latest_path, docs_dir=DOCS_DIR) -> list[str]`, `publish.site_manifest(site) -> dict`, 상수 `MANIFEST_DIR="manifests"`, `APP_ICONS`. 게시물 `docs/manifests/<ID>.webmanifest`(ID는 `[A-Za-z0-9_-]{1,64}`만).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_web_app.py`:

```python
import json
import os
import struct
import unittest

from src.publish import WEB_DIR


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def read(name):
    with open(os.path.join(WEB_DIR, name), encoding="utf-8") as f:
        return f.read()


class AppManifestTests(unittest.TestCase):
    def test_hq_manifest(self):
        data = json.loads(read("manifest.webmanifest"))
        self.assertEqual(("현대아산 기상안전", "./", "#2b4775", "standalone"),
                         (data["name"], data["start_url"], data["theme_color"], data["display"]))
        sizes = {icon["sizes"]: icon["src"] for icon in data["icons"]}
        self.assertEqual({"192x192", "512x512"}, set(sizes))
        for size, src in sizes.items():
            width = int(size.split("x")[0])
            self.assertEqual((width, width), png_size(os.path.join(WEB_DIR, src)))

    def test_apple_touch_icon(self):
        self.assertEqual((180, 180), png_size(os.path.join(WEB_DIR, "assets", "icons", "apple-touch-icon.png")))

    def test_hq_page_links_manifest_and_icon(self):
        html = read("index.html")
        self.assertIn('<link rel="manifest" href="manifest.webmanifest">', html)
        self.assertIn('<link rel="apple-touch-icon" href="assets/icons/apple-touch-icon.png">', html)


if __name__ == "__main__":
    unittest.main()
```

`tests/test_publish.py`의 import에 `write_site_manifests`를 추가하고, `RealWebTests` 앞에 추가:

```python
class SiteManifestTests(unittest.TestCase):
    def test_site_manifests_start_at_their_site_and_drop_old_ones(self):
        with tempfile.TemporaryDirectory() as d:
            latest = os.path.join(d, "data", "latest.json")
            write(latest, json.dumps({"sites": [
                {"id": "5355accc", "short": "후포", "name": "후포 공공하수처리"},
                {"id": "a/b\"<x>", "short": "이상", "name": "잘못된 ID"},
            ]}, ensure_ascii=False))
            write(os.path.join(d, "manifests", "oldsite.webmanifest"), "{}")
            self.assertEqual(["5355accc.webmanifest"], write_site_manifests(latest, d))
            self.assertEqual(["5355accc.webmanifest"], sorted(os.listdir(os.path.join(d, "manifests"))))
            with open(os.path.join(d, "manifests", "5355accc.webmanifest"), encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(("현대아산 기상안전 · 후포", "후포", "../site.html?id=5355accc", "../", "#2b4775"),
                             (data["name"], data["short_name"], data["start_url"], data["scope"], data["theme_color"]))
            self.assertEqual(["../assets/icons/app-192.png", "../assets/icons/app-512.png"],
                             [icon["src"] for icon in data["icons"]])

    def test_unreadable_latest_keeps_existing_manifests(self):
        with tempfile.TemporaryDirectory() as d:
            write(os.path.join(d, "manifests", "5355accc.webmanifest"), "{}")
            self.assertEqual([], write_site_manifests(os.path.join(d, "none.json"), d))
            self.assertEqual(["5355accc.webmanifest"], os.listdir(os.path.join(d, "manifests")))
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m unittest tests.test_web_app tests.test_publish 2>&1 | grep -E "^(FAIL|ERROR)|Error|FAILED" | head`
Expected: `FileNotFoundError …manifest.webmanifest`/`apple-touch-icon.png`, `ImportError: cannot import name 'write_site_manifests'`, `FAILED`

- [ ] **Step 3: 앱 아이콘 만들기 (헤드리스 Chrome으로 심볼 SVG를 흰 바탕에 배치)**

```bash
mkdir -p web/assets/icons
TMP=$(mktemp -d)
cat > "$TMP/icon.html" <<EOF
<!DOCTYPE html><html><body style="margin:0;background:#fff">
<div style="width:100vw;height:100vh;display:grid;place-items:center;background:#fff">
<img src="file://$PWD/web/assets/brand/hdasan-symbol.svg" style="width:68%;height:auto" alt=""></div></body></html>
EOF
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
for spec in "192 app-192.png" "512 app-512.png" "180 apple-touch-icon.png"; do
  set -- $spec
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --default-background-color=ffffffff \
    --force-device-scale-factor=1 --window-size=$1,$1 --screenshot="$PWD/web/assets/icons/$2" "file://$TMP/icon.html" 2>/dev/null
done
python3 -c "import struct;[print(n, struct.unpack('>II', open('web/assets/icons/'+n,'rb').read()[16:24])) for n in ('app-192.png','app-512.png','apple-touch-icon.png')]"
```

Expected: `app-192.png (192, 192)`, `app-512.png (512, 512)`, `apple-touch-icon.png (180, 180)`. 512 파일을 이미지로 열어 흰 바탕 가운데 노랑·초록 심볼이 잘리지 않고 여백이 있는지 본다(심볼 모양·색을 바꾸지 않는다).

- [ ] **Step 4: 본사 매니페스트·연결·현장별 매니페스트 구현**

`web/manifest.webmanifest`:

```json
{
  "name": "현대아산 기상안전",
  "short_name": "기상안전",
  "description": "현대아산 건설현장 기상안전 관제",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "background_color": "#eef2f5",
  "theme_color": "#2b4775",
  "lang": "ko",
  "icons": [
    {"src": "assets/icons/app-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
    {"src": "assets/icons/app-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"}
  ]
}
```

`web/index.html`의 `<link rel="icon" …>` 줄 다음에 추가:

```html
<link rel="apple-touch-icon" href="assets/icons/apple-touch-icon.png">
<link rel="manifest" href="manifest.webmanifest">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="기상안전">
```

`src/publish.py`: `import json` 추가, 상수 목록(`OLD_SITES_PATH` 다음)에 추가:

```python
MANIFEST_DIR = "manifests"
APP_ICONS = (("assets/icons/app-192.png", "192x192"), ("assets/icons/app-512.png", "512x512"))
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
```

`publish()` 함수 앞에 추가:

```python
def site_manifest(site):
    """현장 화면을 휴대폰 홈 화면에 추가했을 때 그 현장 주소로 열리게 하는 매니페스트(설계서 5.9)."""
    return {
        "name": f"현대아산 기상안전 · {site['short']}",
        "short_name": site["short"][:12],
        "description": f"{site['name']} 현장 기상 정보",
        "start_url": f"../site.html?id={site['id']}",
        "scope": "../",
        "display": "standalone",
        "background_color": "#eef2f5",
        "theme_color": "#2b4775",
        "lang": "ko",
        "icons": [{"src": f"../{src}", "sizes": size, "type": "image/png", "purpose": "any"} for src, size in APP_ICONS],
    }


def write_site_manifests(latest_path, docs_dir=DOCS_DIR):
    """docs/manifests/<현장ID>.webmanifest를 만들고, 목록에서 빠진 현장의 파일은 지운다. 만든 파일 이름 목록.

    latest.json을 읽지 못하면 아무것도 바꾸지 않는다. ID는 영문·숫자·_·-만 받는다(주소에 그대로 쓰이므로).
    """
    try:
        with open(latest_path, encoding="utf-8") as f:
            sites = json.load(f).get("sites") or []
    except (OSError, ValueError, AttributeError):
        return []
    out = os.path.join(docs_dir, MANIFEST_DIR)
    os.makedirs(out, exist_ok=True)
    written = []
    for site in sites:
        if not isinstance(site, dict) or not _SAFE_ID.match(str(site.get("id", ""))) or not site.get("short"):
            continue
        name = f"{site['id']}.webmanifest"
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            json.dump(site_manifest(site), f, ensure_ascii=False, indent=1)
        written.append(name)
    for name in os.listdir(out):
        if name.endswith(".webmanifest") and name not in written:
            os.remove(os.path.join(out, name))
    return sorted(written)
```

`src/main.py`: import를 `from src.publish import OLD_MAP_PATH, OLD_SITES_PATH, check_latest, private_values, publish, write_site_manifests`로 바꾸고, `publish_screens()`의

```python
        files = publish(blocked=blocked)
        print(f"[화면 게시] {len(files)}개 파일")
```

를 다음으로 바꾼다:

```python
        files = publish(blocked=blocked)
        manifests = write_site_manifests(LATEST_PATH)
        print(f"[화면 게시] {len(files)}개 파일 · 현장 홈 화면 설정 {len(manifests)}곳")
```

`src/publish.py` 맨 아래 로컬 게시 명령도 현장별 매니페스트를 만들게 바꾼다(미리보기에서 현장 화면이 자기 매니페스트를 찾도록):

```python
if __name__ == "__main__":
    files = publish()
    manifests = write_site_manifests(os.path.join(DOCS_DIR, "data", "latest.json"))
    print(f"[화면 게시] {len(files)}개 파일 · 현장 홈 화면 설정 {len(manifests)}곳 → docs/")
```

- [ ] **Step 5: 통과 확인**

Run: `python3 -m unittest tests.test_web_app tests.test_publish -v 2>&1 | tail -3` → Expected: `OK`
Run: `python3 -m src.publish` → Expected: `[화면 게시] …개 파일 · 현장 홈 화면 설정 21곳 → docs/` (게시본은 커밋하지 않음)
Run: `python3 -m unittest discover -s tests -b 2>&1 | tail -3` → Expected: `OK` (160개)

- [ ] **Step 6: 커밋**

```bash
git add web/assets/icons web/manifest.webmanifest web/index.html src/publish.py src/main.py tests/test_web_app.py tests/test_publish.py
git commit -m "앱 아이콘과 홈 화면 추가 설정(본사 고정·현장별 생성)"
```

---

### Task 2: 공통 부품 정리 — 본사 상세 부품을 현장 화면과 함께 쓰게 옮기기(본사 동작 그대로)

**Files:**
- Create: `web/assets/parts.js`, `scripts/ui_check.mjs`
- Modify: `web/assets/common.js`, `web/assets/geo.js`, `web/assets/icons.svg`, `web/assets/app.css`, `web/assets/hq.css`, `web/assets/hq.js`, `web/assets/hq-detail.js`, `web/index.html`

**Interfaces:**
- Consumes: `WX.valueAt`, `WX.warningChip`, `WX.legalChip`, `WX.rainColor`, `WX.windColor`, `WX.mmText`, `WX.kst`, `WX.icon`, `WX.esc`, `WX.fmt`
- Produces:
  - `WX.isRain(v) -> bool` (관측은 `precip`, 예보는 강수량), `WX.hourText(times, h) -> "지금"|"21시"|"내일 3시"`, `WX.skyIcon(sky) -> "i-sun"|"i-csun"|"i-cloud"|"i-rain"|"i-snow"`, `WX.weekday("2026-09-27") -> "일"`, `WX.shortDate("2026-10-04") -> "10/4"`
  - `WX.parts`: `heroSky(site, times, h) -> "heavy"|"rain"|"snow"|"clear"|"cloudy"`, `heroClass(sky) -> string`, `chips(site, warningsOk) -> html`, `tiles(v, observed) -> html`, `legal(site) -> html`, `forecastSentence(v, when) -> html`, `timeline(els, site, times, issuedAt, label)`, `cursor(els, h, text)`, `scrub(els, count, onHour, onStart?)` — `els = { tl, rain, wind, spark, hours, note, cursor }`
  - `WX.createMap({ …, view: { center:[lon,lat], zoom } })` — `view`가 있으면 전국 대신 그 위치로 시작
  - `node scripts/ui_check.mjs <steps.json>` — 단계: `{nav, after}`, `{wait}`, `{eval, label}`, `{click, label, after}`, `{drag, dx, dy, after}`, `{key, after}`, `{size:[w,h,mobile]}`, `{shot}`; 결과 JSON(`results`, `console`)

- [ ] **Step 1: 공통 함수 점검(실패 확인)**

작업 기록 폴더(`.superpowers/sdd/2026-09-27-phase3-site-ui/`)에 `parts-check.js`를 만든다:

```js
const fs = require("fs"), vm = require("vm");
const ctx = { window: { matchMedia: () => ({ matches: false }) }, location: { search: "" }, URLSearchParams, Intl, document: {}, console };
vm.createContext(ctx);
["web/assets/common.js", "web/assets/parts.js"].forEach(f => vm.runInContext(fs.readFileSync(f, "utf8"), ctx));
const WX = ctx.window.WX, P = WX.parts;
const obs = "2026-09-27T16:00:00+09:00";
const site = { state: "ok", as_of: obs, warnings: [{ kind: "기상특보", title: "호우경보", level: "경보" }], legal: [], legal_profile: false,
  now: { temp: 18.6, feels: 18.6, rain_mm: 31, wind: 4.1, humidity: 95, pty: "비", precip: "rain" },
  hourly: [{ at: "2026-09-27T17:00:00+09:00", temp: 18, rain_mm: 0, rain_label: "0", wind: 2, humidity: 88, sky: "맑음", pty: "없음", pop: 10 }] };
const times = [new Date(obs).getTime(), new Date("2026-09-27T17:00:00+09:00").getTime()];
const checks = {
  isRain: WX.isRain({ observed: true, precip: "rain", rain: 0 }) && !WX.isRain({ observed: true, precip: null, rain: 2 })
    && WX.isRain({ observed: false, rain: 0.5 }) && !WX.isRain(null),
  hourText: WX.hourText(times, 0) === "지금" && WX.hourText(times, 1) === "17시",
  sky: ["맑음", "구름많음", "흐림", "비", "흐리고 비", "소나기", "눈", "흐리고 눈", "비/눈", null].map(WX.skyIcon).join()
    === "i-sun,i-csun,i-cloud,i-rain,i-rain,i-rain,i-snow,i-snow,i-rain,i-cloud",
  weekday: WX.weekday("2026-09-27") === "일" && WX.weekday("2026-09-28") === "월",
  shortDate: WX.shortDate("2026-10-04") === "10/4",
  heroSky: P.heroSky(site, times, 0) === "heavy" && P.heroSky(site, times, 1) === "clear"
    && P.heroClass("heavy") === "rain heavy" && P.heroClass("snow") === "cloudy",
  chips: P.chips(site, true).includes("호우경보 발효 중") && P.chips(site, true).includes('class="chip crit"')
    && P.chips(site, false).includes("특보 확인 실패"),
  tiles: P.tiles(WX.valueAt(site, times, 0), true).includes("체감") && P.tiles(WX.valueAt(site, times, 0), true).includes(">31<")
    && P.tiles(null, false).includes(">-<"),
  legal: P.legal(site).includes("작업 정보가 등록되지 않아"),
  sentence: P.forecastSentence(WX.valueAt(site, times, 1), "17시") === "<b>17시 예보: 비 없음.</b> 기온 18°, 바람 2m/s, 강수확률 10%."
    && P.forecastSentence(null, "18시") === "<b>18시 예보 자료가 없습니다.</b>",
};
const bad = Object.keys(checks).filter(k => !checks[k]);
console.log(bad.length ? "FAIL " + bad.join(", ") : "ALL OK (" + Object.keys(checks).length + ")");
```

Run: `node .superpowers/sdd/2026-09-27-phase3-site-ui/parts-check.js`
Expected: `ENOENT … web/assets/parts.js` (파일 없음)

- [ ] **Step 2: `common.js`에 함수 추가, `parts.js` 작성**

`web/assets/common.js`의 `WX.valueAt = …` 함수 블록 바로 뒤에 추가:

```js
  // 관측(지금)은 Python 판단(now.precip)을 따르고, 예보 시각은 예보 강수량으로 본다.
  WX.isRain = v => !!v && (v.observed && v.precip !== undefined ? v.precip === "rain" : (v.rain || 0) >= WX.RAIN_BINS[0]);
  WX.hourText = (times, h) => (h === 0 ? "지금" : WX.hourLabel(times[h], times[0]));
  // 하늘 상태 글자(단기·중기 예보) → 아이콘 이름
  WX.skyIcon = sky => {
    const s = sky || "";
    if (/비|소나기/.test(s)) return "i-rain";
    if (/눈/.test(s)) return "i-snow";
    if (/구름/.test(s)) return "i-csun";
    if (/맑/.test(s)) return "i-sun";
    return "i-cloud";
  };
  WX.weekday = date => "일월화수목금토"[new Date(`${date}T12:00:00+09:00`).getUTCDay()];
  WX.shortDate = date => `${Number(date.slice(5, 7))}/${Number(date.slice(8, 10))}`;
```

`web/assets/parts.js`:

```js
/* 현장 한 곳을 보여 주는 공통 부품 — 본사 상세(hq-detail.js)와 현장 화면(site.js)이 함께 쓴다.
   히어로 하늘 판정·특보/법정 칩·수치 4개·법정 안내·예보 시각 문장·앞으로 24시간 타임라인. */
(function () {
  "use strict";
  const { esc, fmt } = WX;
  const P = (WX.parts = {});

  // 히어로 하늘: 비(강한 비 15mm 이상은 heavy)·눈·맑음·흐림. 지금은 다음 시각 예보의 하늘을 빌린다.
  P.heroSky = (site, times, h) => {
    const v = WX.valueAt(site, times, h);
    if (WX.isRain(v)) return (v.rain || 0) >= 15 ? "heavy" : "rain";
    const snow = v && (v.observed ? v.precip === "snow" : /눈/.test(v.pty || "") && !/비/.test(v.pty || ""));
    if (snow) return "snow";
    const sky = h === 0 ? (WX.valueAt(site, times, 1) || {}).sky : v && v.sky;
    return sky === "맑음" ? "clear" : "cloudy";
  };
  P.heroClass = sky => ({ heavy: "rain heavy", rain: "rain", snow: "cloudy", clear: "clear", cloudy: "cloudy" })[sky] || "cloudy";

  P.chips = (site, warningsOk) => {
    const out = [];
    if (site.state === "stale") out.push(`<span class="chip mute">${WX.icon("i-clock")}${WX.kst(site.as_of).hm} 관측 자료 · 이번 수집 실패</span>`);
    if (site.state === "missing") out.push(`<span class="chip mute">${WX.icon("i-clock")}자료 없음 · 이번 수집 실패</span>`);
    if (!warningsOk) out.push(`<span class="chip mute">${WX.icon("i-alert")}특보 확인 실패</span>`);
    else if (!site.warnings.length) out.push('<span class="chip">기상특보 없음</span>');
    site.warnings.forEach(w => { const c = WX.warningChip(w); out.push(`<span class="chip ${c.cls}">${WX.icon("i-alert")}${esc(c.text)}</span>`); });
    site.legal.forEach(l => { const c = WX.legalChip(l); out.push(`<span class="chip ${c.cls || "mute"}">${WX.icon("i-shield")}${esc(c.text)}</span>`); });
    if (site.legal_profile && !site.legal.length) out.push('<span class="chip">법정조치 해당 없음</span>');
    return out.join("");
  };

  P.tiles = (v, observed) => {
    v = v || {};
    const items = [
      ["i-drop", "비", v.rainText == null ? "-" : v.rainText, "mm/h"],
      ["i-wind", "바람", fmt(v.wind, 1), "m/s"],
      ["i-temp", observed ? "체감" : "기온", fmt(observed ? v.feels : v.temp, 1), "°"],
      ["i-hum", "습도", v.humidity == null ? "-" : v.humidity, "%"],
    ];
    return items.map(([ic, name, value, unit]) =>
      `<div class="tile"><div class="l">${WX.icon(ic)}${name}<small>${unit}</small></div><div class="v num">${esc(value)}</div></div>`).join("");
  };

  P.legal = site => {
    if (!site.legal_profile) {
      return `${WX.icon("i-info")}<div>작업 정보가 등록되지 않아 <b>법정 기준(타워크레인·철골·폭염 작업 등)</b>은 확인하지 않았습니다.</div>`;
    }
    if (!site.legal.length) return `${WX.icon("i-info")}<div>등록된 작업 기준으로 확인한 법정 조치 대상이 없습니다.</div>`;
    return `${WX.icon("i-shield")}<div>${site.legal.map(l =>
      `<b>${esc(l.status)}</b> · ${esc(l.title)} <span class="art">${esc(l.article || "")}</span>`).join("<br>")}</div>`;
  };

  P.forecastSentence = (v, when) => {
    if (!v) return `<b>${esc(when)} 예보 자료가 없습니다.</b>`;
    const rain = WX.isRain(v) ? `비 ${esc(WX.mmText(v.rainText))}` : "비 없음";
    return `<b>${esc(when)} 예보: ${rain}.</b> 기온 ${fmt(v.temp, 1)}°, 바람 ${fmt(v.wind, 1)}m/s, 강수확률 ${v.pop == null ? "-" : v.pop}%.`;
  };

  // 앞으로 24시간: 비·바람 칸 + 기온 선. label(k)는 칸 설명("16:00 관측", "21시 예보").
  P.timeline = (els, site, times, issuedAt, label) => {
    const n = times.length, slots = times.map((_, k) => WX.valueAt(site, times, k));
    els.tl.classList.remove("shown");
    els.tl.style.setProperty("--n", n);
    els.tl.setAttribute("aria-valuemax", String(n - 1));
    els.rain.innerHTML = slots.map((v, k) => `<i class="${k === 0 ? "now" : ""}" style="background:${v ? WX.rainColor(v.rain, WX.CELL) : WX.CELL};transition-delay:${k * 18}ms" title="${esc(label(k))} · 비 ${v ? esc(WX.mmText(v.rainText)) : "-"}"></i>`).join("");
    els.wind.innerHTML = slots.map((v, k) => `<i class="${k === 0 ? "now" : ""}" style="background:${v ? WX.windColor(v.wind) : WX.CELL};transition-delay:${k * 18 + 120}ms" title="${esc(label(k))} · 바람 ${v ? fmt(v.wind, 1) : "-"}m/s"></i>`).join("");
    const temps = slots.map(v => (v && v.temp != null ? v.temp : null)), known = temps.filter(t => t != null);
    if (known.length > 1) {
      const lo = Math.min(...known), hi = Math.max(...known), pts = [];
      temps.forEach((t, k) => { if (t != null) pts.push([((k + 0.5) / n) * 100, 36 - ((t - lo) / Math.max(1, hi - lo)) * 30]); });
      const d = pts.map((p, k) => `${k ? "L" : "M"}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(" ");
      els.spark.innerHTML = '<svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="tgrad" x1="0" x2="0" y1="0" y2="1">'
        + '<stop offset="0" stop-color="#5598e7" stop-opacity=".22"/><stop offset="1" stop-color="#5598e7" stop-opacity="0"/></linearGradient></defs>'
        + `<path class="area" d="${d} L${pts[pts.length - 1][0]} 40 L${pts[0][0]} 40 Z"/><path class="line" d="${d}" vector-effect="non-scaling-stroke" pathLength="600"/></svg>`
        + `<span class="hi num">${fmt(hi, 1)}°</span><span class="lo num">${fmt(lo, 1)}°</span>`;
    } else {
      els.spark.innerHTML = '<span class="empty">기온 자료 없음</span>';
    }
    els.hours.innerHTML = times.map((t, k) => `<b class="${k === 0 ? "k" : ""}">${k === 0 ? "지금" : k % 3 === 0 ? WX.kst(t).h : ""}</b>`).join("");
    const obs = site.as_of ? `${WX.kst(site.as_of).hm} 관측` : "관측 자료 없음";
    const issued = issuedAt ? `${WX.kst(issuedAt).hm} 발표` : "발표 시각 없음";
    els.note.textContent = (site.hourly || []).length ? `지금 칸은 ${obs}, 나머지는 기상청 단기예보(${issued})입니다.`
      : `지금 칸은 ${obs}입니다. 이 현장은 이번 수집에서 기상청 예보 자료를 받지 못했습니다.`;
    requestAnimationFrame(() => requestAnimationFrame(() => els.tl.classList.add("shown")));
  };

  P.cursor = (els, h, text) => {
    const cells = els.rain.children;
    if (!cells.length) return;
    const cell = cells[Math.min(h, cells.length - 1)], box = els.tl.getBoundingClientRect(), r = cell.getBoundingClientRect();
    els.cursor.style.left = `${r.left - box.left + r.width / 2 - 1}px`;
    els.cursor.dataset.label = text;
    els.tl.setAttribute("aria-valuenow", String(h));
    els.tl.setAttribute("aria-valuetext", text);
  };

  // 칸을 누르거나 좌우로 문지르면 그 시각으로. 초점이 있으면 ←→ 키(화면 전체 키 처리와 겹치지 않게 전달을 막는다).
  P.scrub = (els, count, onHour, onStart) => {
    let dragging = false;
    const at = e => { const r = els.rain.getBoundingClientRect(); return Math.floor(((e.clientX - r.left) / r.width) * count()); };
    els.tl.addEventListener("pointerdown", e => { dragging = true; els.tl.setPointerCapture(e.pointerId); if (onStart) onStart(); onHour(at(e)); });
    els.tl.addEventListener("pointermove", e => { if (dragging) onHour(at(e)); });
    const end = () => { dragging = false; };
    els.tl.addEventListener("pointerup", end);
    els.tl.addEventListener("pointercancel", end);
    els.tl.addEventListener("keydown", e => {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (!step) return;
      e.preventDefault();
      e.stopPropagation();
      if (onStart) onStart();
      onHour(Number(els.tl.getAttribute("aria-valuenow") || 0) + step);
    });
  };
})();
```

Run: `node .superpowers/sdd/2026-09-27-phase3-site-ui/parts-check.js` → Expected: `ALL OK (10)`

- [ ] **Step 3: 본사 코드가 공통 부품을 쓰게 바꾸기**

`web/assets/hq.js`:

```js
  HQ.isRain = v => !!v && (v.observed && v.precip !== undefined ? v.precip === "rain" : (v.rain || 0) >= WX.RAIN_BINS[0]);
  HQ.hourText = h => (h === 0 ? "지금" : WX.hourLabel(state.times[h], state.times[0]));
```

을 다음으로 바꾼다(앞의 설명 주석 한 줄도 함께 지운다):

```js
  HQ.isRain = WX.isRain;
  HQ.hourText = h => WX.hourText(state.times, h);
```

`web/assets/hq-detail.js` 전체를 다음으로 바꾼다:

```js
/* 선택 현장 상세: 히어로(하늘 반응형)·특보/법정 칩·수치 4개·앞으로 24시간·법정 안내(설계서 3.2).
   칩·수치·타임라인 부품은 현장 화면과 함께 쓰는 parts.js에 있다. */
(function () {
  "use strict";
  const { $ } = WX;
  const P = WX.parts;
  const HQ = window.HQ, state = HQ.state;
  const els = () => ({ tl: $("#tl"), rain: $("#cR"), wind: $("#cW"), spark: $("#spark"), hours: $("#hours"), note: $("#tlNote"), cursor: $("#cursor") });

  function moveCursor() { P.cursor(els(), state.h, HQ.hourText(state.h)); }
  function render(first) {
    const site = state.sel;
    if (!site) return;
    const h = state.h, v = HQ.value(site, h);
    $("#dCat").textContent = [site.category, site.region].filter(Boolean).join(" · ");
    $("#dName").textContent = site.name;
    $("#hero").className = `hero ${P.heroClass(P.heroSky(site, state.times, h))}${h === 0 && site.state !== "ok" ? " dim" : ""}`;
    $("#hWhen").textContent = h > 0 ? `${HQ.hourText(h)} 예보`
      : site.as_of ? `${WX.kst(site.as_of).hm} 관측${site.state === "stale" ? " · 이번 수집 실패" : ""}` : "관측 자료 없음";
    WX.tween($("#hTemp"), v ? v.temp : null, 1, 600);
    $("#hSent").innerHTML = h === 0 ? WX.leadBold(site.summary) : P.forecastSentence(v, HQ.hourText(h));
    $("#dChips").innerHTML = P.chips(site, state.latest.status.warnings === "ok");
    $("#dTiles").innerHTML = P.tiles(v, h === 0);
    $("#dLegal").innerHTML = P.legal(site);
    if (first) P.timeline(els(), site, state.times, state.latest.forecast_issued_at, HQ.whenText);
    moveCursor();
  }

  HQ.detail = {
    init() {
      P.scrub(els(), () => state.times.length, h => HQ.setHour(h), () => { if (HQ.time) HQ.time.stop(); });
      $("#dClose").addEventListener("click", () => HQ.close());
      $("#bNotice").addEventListener("click", () => { if (HQ.notice && state.sel) HQ.notice.open(state.sel); });
    },
    open(site, first) {
      $("#detail").classList.add("open");
      $("#detail").inert = false;
      render(first);
    },
    close() {
      $("#detail").classList.remove("open", "expanded");
      $("#detail").inert = true;
    },
    render() { render(false); },
    moveCursor,
  };
})();
```

`web/index.html`:
- `<script src="assets/common.js" defer></script>` 다음 줄에 `<script src="assets/parts.js" defer></script>`를 넣는다.
- `<div class="tl" id="tl">`를 `<div class="tl" id="tl" role="slider" tabindex="0" aria-label="예보 시각" aria-valuemin="0" aria-valuemax="24" aria-valuenow="0">`로 바꾼다.

`web/assets/icons.svg`의 `</svg>` 앞에 추가:

```svg
<symbol id="i-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></symbol>
<symbol id="i-cloud" viewBox="0 0 24 24"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></symbol>
<symbol id="i-csun" viewBox="0 0 24 24"><path d="M12 2v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="M20 12h2"/><path d="m19.07 4.93-1.41 1.41"/><path d="M15.947 12.65a4 4 0 0 0-5.925-4.128"/><path d="M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6Z"/></symbol>
<symbol id="i-snow" viewBox="0 0 24 24"><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="M8 15h.01"/><path d="M8 19h.01"/><path d="M12 17h.01"/><path d="M12 21h.01"/><path d="M16 15h.01"/><path d="M16 19h.01"/></symbol>
```

`web/assets/geo.js`:
- `WX.createMap = ({ container, padding, onReady, onNotice }) => {`를 `WX.createMap = ({ container, padding, onReady, onNotice, view }) => {`로 바꾼다.
- `startReal()` 안의

```js
        map = new maplibregl.Map({ container, style: STYLE, bounds: WX.KOREA, fitBoundsOptions: { padding: padding() },
          attributionControl: { compact: true }, dragRotate: false, pitchWithRotate: false, touchPitch: false });
```

를 다음으로 바꾼다:

```js
        // view가 있으면(현장 화면) 그 위치에서, 없으면(본사) 전국이 보이게 시작한다.
        const start = view ? { center: view.center, zoom: view.zoom } : { bounds: WX.KOREA, fitBoundsOptions: { padding: padding() } };
        map = new maplibregl.Map(Object.assign({ container, style: STYLE, attributionControl: { compact: true },
          dragRotate: false, pitchWithRotate: false, touchPitch: false }, start));
```

- [ ] **Step 4: 공통 CSS 옮기기(모양 그대로)**

지도 알림·자체 지도·로고·수집 상태·히어로·수치·타임라인·법정 안내·불러오기 실패 규칙을 `hq.css`에서 `app.css` 끝으로 옮긴다(규칙 내용은 바꾸지 않는다). `.top`, `.top .seg`, `.banner`, `.hero .t1/.t2/.t3`, 좁은 화면 규칙은 `hq.css`에 남긴다.

```bash
python3 - <<'EOF'
hq = open("web/assets/hq.css", encoding="utf-8").read()
def cut(start, end):
    global hq
    i = hq.index(start)
    j = hq.index(end, i) + len(end)
    block, hq = hq[i:j], hq[:i] + hq[j:]
    return block
moved = [
    cut(".map { position: fixed;", ".svgmark { position: absolute; }\n"),
    cut(".brand { display: flex;", ".brand small { color: var(--muted-ink); font-size: 12px; }\n"),
    cut(".live { display: flex;", "100% { box-shadow: 0 0 0 0 rgba(89, 127, 96, 0); } }\n"),
    cut(".hero { position: relative;", "@keyframes rain { from { transform: translate(0, 0); } to { transform: translate(-6px, 26px); } }\n"),
    cut(".tiles { display: grid;", ".info .art { color: var(--muted-ink); font-size: 11.5px; }\n"),
    cut(".loadfail { position: fixed;", ".loadfail .btn .ic { width: 16px; height: 16px; color: #fff; }\n"),
]
open("web/assets/hq.css", "w", encoding="utf-8").write(hq)
with open("web/assets/app.css", "a", encoding="utf-8") as f:
    f.write("\n/* 화면 공통 틀·현장 카드 부품 — 본사 상세와 현장 화면이 함께 쓴다 */\n" + "\n".join(b.rstrip("\n") for b in moved) + "\n")
print("moved", len(moved))
EOF
grep -c "^\.hero {" web/assets/app.css web/assets/hq.css
```

Expected: `moved 6`, `app.css:1`, `hq.css:0`.

- [ ] **Step 5: 화면 점검 도구 `scripts/ui_check.mjs` 작성**

```js
// 화면 확인 도구(자동 테스트 체계 아님): 사용자 Chrome과 분리된 임시 프로필의 헤드리스 Chrome을 띄워
// 페이지를 열고, 단계별 JS 식 결과·콘솔 오류·캡처를 JSON으로 남긴다. 앱 미리보기 창이 가려지면 지도가 그려지지 않을 때 쓴다.
// 사용: node scripts/ui_check.mjs steps.json
//   steps.json = {"width":1440,"height":900,"mobile":false,"steps":[{"nav":url,"after":ms}|{"wait":ms}|{"eval":js,"label":s}
//                |{"click":jsElementExpr,"label":s,"after":ms}|{"drag":jsElementExpr,"dx":px,"dy":px,"after":ms}
//                |{"key":"ArrowRight","after":ms}|{"size":[w,h,mobile]}|{"shot":path}]}
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const spec = JSON.parse(readFileSync(process.argv[2], "utf8"));
const port = 9333 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), "ui-check-"));
const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--no-first-run",
  "--no-default-browser-check", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--hide-scrollbars",
  `--window-size=${spec.width || 1440},${spec.height || 900}`, "about:blank",
], { stdio: "ignore" });
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function pageSocket() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find(t => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch (e) { /* 아직 준비 안 됨 */ }
    await sleep(200);
  }
  throw new Error("Chrome 연결 실패");
}

const ws = new WebSocket(await pageSocket());
await new Promise(r => ws.addEventListener("open", r, { once: true }));
let seq = 0;
const waiting = new Map(), logs = [];
ws.addEventListener("message", ev => {
  const msg = JSON.parse(ev.data);
  if (msg.id && waiting.has(msg.id)) { waiting.get(msg.id)(msg); waiting.delete(msg.id); }
  if (msg.method === "Runtime.consoleAPICalled" && ["error", "warning"].includes(msg.params.type)) {
    logs.push(`[${msg.params.type}] ${msg.params.args.map(a => a.value ?? a.description ?? "").join(" ")}`);
  }
  if (msg.method === "Runtime.exceptionThrown") logs.push(`[exception] ${msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text}`);
  if (msg.method === "Log.entryAdded" && msg.params.entry.level === "error") logs.push(`[log] ${msg.params.entry.text} ${msg.params.entry.url || ""}`);
});
const send = (method, params = {}) => new Promise(r => { const n = ++seq; waiting.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
const size = (w, h, mobile) => send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: !!mobile });

await send("Runtime.enable");
await send("Log.enable");
await send("Page.enable");
await size(spec.width || 1440, spec.height || 900, spec.mobile);
const out = [];
for (const step of spec.steps) {
  if (step.nav) { await send("Page.navigate", { url: step.nav }); await sleep(step.after ?? 3000); }
  if (step.size) { await size(step.size[0], step.size[1], step.size[2]); await sleep(500); }
  if (step.wait) await sleep(step.wait);
  if (step.eval) {
    const res = await send("Runtime.evaluate", { expression: step.eval, returnByValue: true, awaitPromise: true });
    const r = res.result;
    out.push({ eval: step.label || step.eval.slice(0, 60), value: r.exceptionDetails ? `EXCEPTION ${r.exceptionDetails.exception?.description}` : r.result.value });
  }
  if (step.click) {
    const res = await send("Runtime.evaluate", { expression: `(() => { const el = ${step.click}; if (!el) return false; el.scrollIntoView({block:"center"}); const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()`, returnByValue: true });
    const xy = res.result.result.value;
    if (xy) for (const type of ["mousePressed", "mouseReleased"]) await send("Input.dispatchMouseEvent", { type, x: xy[0], y: xy[1], button: "left", clickCount: 1 });
    out.push({ click: step.label || step.click.slice(0, 60), ok: !!xy });
    await sleep(step.after ?? 800);
  }
  if (step.drag) {
    const res = await send("Runtime.evaluate", { expression: `(() => { const el = ${step.drag}; if (!el) return false; const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()`, returnByValue: true });
    const xy = res.result.result.value;
    if (xy) {
      const [x, y] = xy, dx = step.dx || 0, dy = step.dy || 0;
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      for (let k = 1; k <= 10; k++) {
        await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: x + (dx * k) / 10, y: y + (dy * k) / 10, button: "left", buttons: 1 });
        await sleep(16);
      }
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: x + dx, y: y + dy, button: "left", clickCount: 1 });
    }
    out.push({ drag: step.label || step.drag.slice(0, 60), ok: !!xy });
    await sleep(step.after ?? 800);
  }
  if (step.key) {
    for (const type of ["keyDown", "keyUp"]) await send("Input.dispatchKeyEvent", { type, key: step.key, code: step.key, windowsVirtualKeyCode: { ArrowRight: 39, ArrowLeft: 37, Escape: 27, Enter: 13, Tab: 9 }[step.key] || 0 });
    await sleep(step.after ?? 400);
  }
  if (step.shot) {
    const res = await send("Page.captureScreenshot", { format: "png" });
    writeFileSync(step.shot, Buffer.from(res.result.data, "base64"));
    out.push({ shot: step.shot });
  }
}
console.log(JSON.stringify({ results: out, console: logs }, null, 1));
ws.close();
chrome.kill();
await sleep(300);
try { rmSync(profile, { recursive: true, force: true }); } catch (e) { /* 임시 폴더 */ }
```

- [ ] **Step 6: 본사 화면이 그대로인지 점검**

Run: `python3 -m src.publish && python3 -m unittest tests.test_publish 2>&1 | tail -1` → Expected: `OK`

작업 기록 폴더에 `hq-regress.json`을 만들어 실행한다(`node scripts/ui_check.mjs …/hq-regress.json`):

```json
{"width": 1440, "height": 900, "steps": [
 {"nav": "http://localhost:8765/site/index.html?data=../fixtures/rain.json", "after": 10000},
 {"label": "detail", "eval": "({open: document.querySelector('#detail').classList.contains('open'), hero: document.querySelector('#hero').className, chip: document.querySelector('#dChips').textContent.includes('호우경보 발효 중'), tiles: document.querySelectorAll('#dTiles .tile').length, cells: document.querySelectorAll('#cR i').length === HQ.state.times.length, note: document.querySelector('#tlNote').textContent.startsWith('지금 칸은'), noScroll: document.documentElement.scrollHeight <= innerHeight, marks: document.querySelectorAll('.mk').length})"},
 {"label": "hour3", "eval": "HQ.setHour(3); new Promise(r => setTimeout(() => r({when: document.querySelector('#when').textContent.endsWith('예보'), cursor: document.querySelector('#cursor').dataset.label === HQ.hourText(3), sent: document.querySelector('#hSent').textContent.includes('예보')}), 800))"},
 {"label": "focus tl", "eval": "HQ.setHour(0); document.querySelector('#tl').focus(); document.activeElement.id"},
 {"key": "ArrowRight"},
 {"label": "one step", "eval": "HQ.state.h"},
 {"shot": "hq-regress.png"}
]}
```

Expected: `detail` 모두 참(`hero`는 `hero rain heavy`, `tiles` 4, `marks` 21), `hour3` 모두 참, `focus tl` = `"tl"`, `one step` = `1`(두 칸 넘어가지 않음), 콘솔 오류 0건. 캡처가 2단계 화면과 같은 모양인지 본다.

- [ ] **Step 7: 커밋**

```bash
git add web/assets/parts.js web/assets/common.js web/assets/geo.js web/assets/icons.svg web/assets/app.css web/assets/hq.css web/assets/hq.js web/assets/hq-detail.js web/index.html scripts/ui_check.mjs
git commit -m "현장 카드 공통 부품 분리(parts.js·app.css)와 화면 점검 도구"
```

---

### Task 3: 현장 화면 본문 — 현장명·히어로·칩·수치·24시간·10일 예보·법정 안내·전파 문안·현장 선택

**Files:**
- Create: `web/site.html`, `web/assets/site.css`, `web/assets/site.js`
- Modify: `web/assets/parts.js` (`daily` 추가)
- Test: `tests/test_web_app.py`

**Interfaces:**
- Consumes: `WX.*`, `WX.parts.*`(Task 2), `latest.json`(`sites[].daily`, `notice`, `summary`, `pinned`, `now.precip`)
- Produces:
  - `WX.parts.daily(days) -> html`
  - 전역 `window.SITE`: `state = { latest, site, times, h }`, `value(h?)`, `hourText(h)`, `setHour(h)`; 선택 연결 지점 `SITE.map = { init(), render() }`(Task 4)
  - 주소: `site.html?id=<현장ID>`(+ 확인용 `data=`), ID가 없거나 모르면 `#picker` 목록
  - 현장별 매니페스트 연결: `<link rel="manifest" id="manifest">`를 `manifests/<ID>.webmanifest`로 바꾸는 머리 스크립트

- [ ] **Step 1: 실패하는 테스트·점검 작성**

`tests/test_web_app.py`의 `AppManifestTests`에 추가:

```python
    def test_site_page_uses_its_own_manifest(self):
        html = read("site.html")
        self.assertIn('<link rel="manifest" id="manifest" href="manifest.webmanifest">', html)
        self.assertIn("/^[A-Za-z0-9_-]{1,64}$/.test(id)", html)
        self.assertIn('"manifests/" + id + ".webmanifest"', html)
        self.assertIn('<link rel="apple-touch-icon" href="assets/icons/apple-touch-icon.png">', html)
```

작업 기록 폴더에 `daily-check.js`:

```js
const fs = require("fs"), vm = require("vm");
const ctx = { window: { matchMedia: () => ({ matches: false }) }, location: { search: "" }, URLSearchParams, Intl, document: {}, console };
vm.createContext(ctx);
["web/assets/common.js", "web/assets/parts.js"].forEach(f => vm.runInContext(fs.readFileSync(f, "utf8"), ctx));
const P = ctx.window.WX.parts;
const day = (date, o) => Object.assign({ date, sky: "맑음", pop: 10, tmin: 15, tmax: 24, source: "short", missing: false }, o);
const mixed = P.daily([day("2026-09-28"), day("2026-09-29", { pop: 60, sky: "흐리고 비" }), day("2026-09-30", { missing: true, tmin: null, tmax: null })]);
const same = P.daily([day("2026-09-28", { tmin: 20, tmax: 20 }), day("2026-09-29", { tmin: 20, tmax: 20 })]);
const single = P.daily([day("2026-09-28"), day("2026-09-29", { missing: true, tmin: null, tmax: null })]);
const checks = {
  tomorrow: mixed.startsWith('<div class="d10"><span class="dw tomorrow">내일</span><span class="dt num">9/28</span>'),
  weekday: mixed.includes('<span class="dw">화</span><span class="dt num">9/29</span>'),
  popOnlyFrom30: mixed.includes('<span class="pop num">60%</span>') && !mixed.includes(">10%<"),
  rainIcon: mixed.includes("#i-rain"),
  missing: mixed.includes('<div class="d10 gap"><span class="dw">수</span><span class="dt num">9/30</span><span class="gt">예보 자료 없음</span></div>'),
  sameTemps: !same.includes("NaN") && !same.includes("Infinity") && same.includes("left:0.0%;right:0.0%"),
  single: !single.includes("NaN") && single.includes("예보 자료 없음"),
  empty: P.daily([]) === "" && P.daily(null) === "",
};
const bad = Object.keys(checks).filter(k => !checks[k]);
console.log(bad.length ? "FAIL " + bad.join(", ") : "ALL OK (" + Object.keys(checks).length + ")");
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m unittest tests.test_web_app 2>&1 | tail -3` → Expected: `FileNotFoundError … site.html`, `FAILED`
Run: `node .superpowers/sdd/2026-09-27-phase3-site-ui/daily-check.js` → Expected: `TypeError: P.daily is not a function`

- [ ] **Step 3: `parts.js`에 10일 예보 추가**

`web/assets/parts.js`의 `P.scrub = …` 블록 뒤, 마지막 `})();` 앞에 추가:

```js
  // 10일 예보 줄(설계서 3.3-7): 기온 범위 막대, 강수확률 30% 이상만, 자료 없는 날은 "예보 자료 없음".
  P.daily = days => {
    const list = days || [], known = list.filter(d => !d.missing && d.tmin != null && d.tmax != null);
    const lo = known.length ? Math.min(...known.map(d => d.tmin)) : 0;
    const hi = known.length ? Math.max(...known.map(d => d.tmax)) : 0;
    const span = Math.max(1, hi - lo);
    return list.map((d, k) => {
      const head = `<span class="dw${k === 0 ? " tomorrow" : ""}">${k === 0 ? "내일" : WX.weekday(d.date)}</span><span class="dt num">${WX.shortDate(d.date)}</span>`;
      if (d.missing || d.tmin == null || d.tmax == null) return `<div class="d10 gap">${head}<span class="gt">예보 자료 없음</span></div>`;
      const left = ((d.tmin - lo) / span) * 100, right = ((hi - d.tmax) / span) * 100;
      const pop = d.pop != null && d.pop >= 30 ? `${d.pop}%` : "";
      return `<div class="d10">${head}${WX.icon(WX.skyIcon(d.sky))}<span class="sr">${esc(d.sky || "")}</span><span class="pop num">${pop}</span>`
        + `<span class="mn num">${fmt(d.tmin, 0)}°</span><span class="rb"><i style="left:${left.toFixed(1)}%;right:${right.toFixed(1)}%"></i></span>`
        + `<span class="mx num">${fmt(d.tmax, 0)}°</span></div>`;
    }).join("");
  };
```

Run: `node .superpowers/sdd/2026-09-27-phase3-site-ui/daily-check.js` → Expected: `ALL OK (8)`

- [ ] **Step 4: `web/site.html`, `site.css`, `site.js` 작성**

`web/site.html`:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#2b4775">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="기상안전">
<title>현대아산 기상안전 · 현장</title>
<link rel="icon" type="image/svg+xml" href="assets/brand/hdasan-symbol.svg">
<link rel="apple-touch-icon" href="assets/icons/apple-touch-icon.png">
<link rel="manifest" id="manifest" href="manifest.webmanifest">
<script>
  // 홈 화면에 추가하면 이 현장 주소로 열리도록, 수집 실행이 만든 현장별 매니페스트(manifests/<ID>)를 연결한다.
  (function () {
    var id = new URLSearchParams(location.search).get("id");
    if (id && /^[A-Za-z0-9_-]{1,64}$/.test(id)) document.getElementById("manifest").href = "manifests/" + id + ".webmanifest";
  })();
</script>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard-dynamic-subset.min.css" integrity="sha384-V1aeodcjJTo8c7lEQKPTnsMG6Yk8y6O/1kzqU/BCXw78Yw1W8XYFJGgjYa3oInYZ" crossorigin="anonymous">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.css" integrity="sha384-MinO0mNliZ3vwppuPOUnGa+iq619pfMhLVUXfC4LHwSCvF9H+6P/KO4Q7qBOYV5V" crossorigin="anonymous">
<link rel="stylesheet" href="assets/tokens.css">
<link rel="stylesheet" href="assets/app.css">
<link rel="stylesheet" href="assets/site.css">
<script id="maplibre-js" src="https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.js" integrity="sha384-SYKAG6cglRMN0RVvhNeBY0r3FYKNOJtznwA0v7B5Vp9tr31xAHsZC0DqkQ/pZDmj" crossorigin="anonymous" async onload="window.__maplibreLoaded=true" onerror="window.__maplibreFailed=true"></script>
<script src="assets/common.js" defer></script>
<script src="assets/parts.js" defer></script>
<script src="assets/site.js" defer></script>
</head>
<body>
<div id="map" class="map" role="region" aria-label="현장 주변 지도"></div>
<div class="mapmsg" id="mapMsg" role="status"></div>

<header class="top">
  <div class="brand"><img class="logo-img" src="assets/brand/hdasan-signature-ko.png" alt="현대아산"><b>기상안전</b></div>
  <div class="live glass" id="live" role="status"></div>
</header>

<section class="sheet" id="sheet" data-snap="half" aria-label="현장 날씨">
  <button type="button" class="grab" id="grab" aria-label="시트 펼치기·접기" aria-expanded="false"><i></i></button>
  <div class="sc" id="sc">
    <div class="ttl"><div class="names"><h1 id="name"></h1><div class="sub" id="sub"></div></div><button type="button" class="nowchip" id="nowchip" disabled>지금</button></div>
    <p class="banner" id="banner" role="status" hidden></p>
    <div class="hero" id="hero">
      <div class="k"><svg class="ic" aria-hidden="true"><use id="hIcon" href="assets/icons.svg#i-cloud"/></svg><span id="hK"></span></div>
      <div class="t num" id="hT" data-suffix="°">-</div>
      <div class="m" id="hM"></div>
      <p class="s" id="hS"></p>
    </div>
    <div class="stack">
      <div class="chips" id="chips"></div>
      <div class="tiles" id="tiles"></div>
      <div class="card"><h3>앞으로 24시간 <span>좌우로 문지르면 그 시각 예보</span></h3>
        <div class="tl" id="tl" role="slider" tabindex="0" aria-label="예보 시각" aria-valuemin="0" aria-valuemax="24" aria-valuenow="0">
          <div class="cursor" id="cursor" data-label="지금"></div>
          <div class="tl-row"><span><svg class="ic" aria-hidden="true"><use href="assets/icons.svg#i-drop"/></svg>비</span><div class="cells" id="cR"></div></div>
          <div class="tl-row"><span><svg class="ic" aria-hidden="true"><use href="assets/icons.svg#i-wind"/></svg>바람</span><div class="cells" id="cW"></div></div>
          <div class="tl-row"><span><svg class="ic" aria-hidden="true"><use href="assets/icons.svg#i-temp"/></svg>기온</span><div class="spark" id="spark"></div></div>
          <div class="hours" id="hours"></div>
        </div>
        <p class="note" id="tlNote"></p>
        <div class="readout" id="readout" aria-live="polite"></div>
      </div>
      <div class="card mapcard"><div class="mapcta"><div><b>현장 주변 지도</b><span>시트를 내려 지도를 크게 봅니다</span></div><button type="button" class="go" id="goMap">지도로 보기<svg class="ic" aria-hidden="true"><use href="assets/icons.svg#i-chev"/></svg></button></div></div>
      <div class="card"><h3>10일 예보 <span>단기 3일 + 중기</span></h3><div id="d10"></div></div>
      <div class="card"><div class="info" id="legal"></div></div>
      <div class="card"><h3>전파 문안 <span>사내 문체</span></h3><div class="nt" id="nt"></div><button type="button" class="more" id="ntMore">전체 보기</button><button type="button" class="btn pri wide" id="copy"><svg class="ic" aria-hidden="true"><use href="assets/icons.svg#i-copy"/></svg>문안 복사</button></div>
      <p class="foot">자료: 기상청 · 지도: OpenStreetMap · 현대아산 안전경영팀</p>
    </div>
  </div>
</section>

<section class="picker" id="picker" aria-labelledby="pickTitle" hidden>
  <div class="pickbox"><h1 id="pickTitle">현장 선택</h1><p id="pickMsg"></p><div class="picklist" id="pickList"></div>
    <p class="foot">현장 화면을 휴대폰 홈 화면에 추가하면 다음부터 바로 열립니다.</p></div>
</section>

<div class="toast" id="toast" role="status"><svg class="ic" aria-hidden="true"><use href="assets/icons.svg#i-check"/></svg><span></span></div>
<div class="loadfail" id="loadfail" role="alert" hidden><div><svg class="ic" aria-hidden="true"><use href="assets/icons.svg#i-alert"/></svg><b>화면 자료를 불러오지 못했습니다</b><p>잠시 뒤 다시 시도해 주세요. 계속되면 관리자에게 알려 주세요.</p><button type="button" class="btn pri" id="retry"><svg class="ic" aria-hidden="true"><use href="assets/icons.svg#i-refresh"/></svg>다시 시도</button></div></div>
</body>
</html>
```

`web/assets/site.css`:

```css
/* 현장 화면 배치 — 설계서 3.3. 휴대폰 우선(아래에서 끌어올리는 시트), 1024px 이상은 왼쪽 지도 + 오른쪽 내용 열. */
html, body { height: 100%; overflow: hidden; }
.top { position: fixed; top: calc(10px + env(safe-area-inset-top)); left: 12px; right: 12px; z-index: 5;
  display: flex; align-items: center; gap: 8px; pointer-events: none; }
.top > * { pointer-events: auto; }
.brand { height: 42px; padding: 0 12px 0 10px; gap: 8px; border-radius: 14px; }
.logo-img { height: 22px; }
.brand b { font-size: 14px; }
.live { margin-left: auto; height: 42px; padding: 0 12px; border-radius: 14px; font-size: 12.5px; gap: 8px; }
.live .full { display: none; }
.live .short { display: inline; }
.mapmsg { top: calc(64px + env(safe-area-inset-top)); }

/* 끌어올리는 시트: --yn(0 = 다 펼침)만큼 아래로 내려가 있다. 손잡이로만 끈다(타임라인 문지르기와 겹치지 않게). */
.sheet { position: fixed; left: 0; right: 0; bottom: 0; height: calc(100% - 60px - env(safe-area-inset-top)); z-index: 4;
  display: flex; flex-direction: column; background: var(--page); border-radius: 28px 28px 0 0;
  box-shadow: 0 -10px 40px rgba(16, 24, 32, .16); --yn: 20;
  transform: translateY(calc(var(--yn) * 1%)); transition: transform .55s cubic-bezier(.22, 1.2, .36, 1); }
.sheet.drag { transition: none; }
.grab { flex: none; width: 100%; height: 30px; display: grid; place-items: center; cursor: grab; touch-action: none; }
.grab i { width: 40px; height: 5px; border-radius: 3px; background: rgba(16, 24, 32, .2); }
.sc { flex: 1; overflow-y: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch;
  padding: 0 16px calc(var(--yn) * (100dvh - 60px) / 100 + 28px + env(safe-area-inset-bottom)); }
.sheet[data-snap="map"] .sc { overflow: hidden; }
.ttl { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; padding: 0 4px 12px; }
.ttl h1 { margin: 0; font-size: 22px; letter-spacing: -.5px; line-height: 1.25; word-break: keep-all; overflow-wrap: anywhere; }
.ttl .sub { font-size: 12.5px; color: var(--muted-ink); font-weight: 600; margin-top: 3px; }
.nowchip { flex: none; font-size: 12px; font-weight: 800; color: var(--primary); background: var(--tint); border-radius: 999px; padding: 6px 11px; white-space: nowrap; }
.nowchip.back { background: var(--primary); color: #fff; }
.nowchip:disabled { cursor: default; }
.banner { display: flex; align-items: center; gap: 8px; margin: 0 0 12px; padding: 10px 12px; border-radius: 14px; background: var(--surface);
  border: 1px solid var(--line); color: var(--ink2); font-size: 13px; font-weight: 600; }
.banner .ic { color: var(--muted); }

/* 히어로(공통 .hero 위에 크기만 바꾼다) */
.hero { padding: 20px 20px 18px; border-radius: 24px; min-height: 0; }
.hero .k { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; position: relative; }
.hero .t { font-size: 76px; font-weight: 800; letter-spacing: -.06em; line-height: .95; margin: 10px 0 4px; position: relative; }
.hero .m { font-size: 13px; position: relative; }
.hero .s { font-size: 16px; line-height: 1.45; margin: 12px 0 0; position: relative; max-width: 94%; letter-spacing: -.2px; }

.stack { display: flex; flex-direction: column; gap: 12px; margin-top: 12px; }
.stack .chip { min-height: 30px; font-size: 13px; }
.tile { border-radius: 16px; }
.card { border-radius: 20px; padding: 16px; }
.card h3 { font-size: 14px; }
.cells i { height: 20px; border-radius: 4px; }
.readout { margin-top: 12px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 10px 12px; border-radius: 14px;
  background: var(--tint); font-size: 13px; font-weight: 600; min-height: 42px; }
.readout b { color: var(--primary); font-weight: 800; }
.readout .hint { color: var(--muted-ink); font-weight: 500; }
.mapcta { display: flex; align-items: center; gap: 12px; }
.mapcta b { display: block; font-size: 15px; }
.mapcta span { font-size: 12.5px; color: var(--muted-ink); }
.mapcta .go { margin-left: auto; color: var(--primary); font-weight: 800; font-size: 13px; display: flex; align-items: center; gap: 2px; white-space: nowrap; }

/* 10일 예보 */
.d10 { display: grid; grid-template-columns: 34px 40px 20px 34px 30px 1fr 30px; gap: 8px; align-items: center; padding: 9px 0;
  border-top: 1px solid var(--line); font-size: 14px; }
.d10:first-child { border-top: 0; padding-top: 0; }
.d10 .dw { font-weight: 700; }
.d10 .dw.tomorrow { color: var(--primary); }
.d10 .dt { font-size: 12px; color: var(--muted-ink); }
.d10 .ic { width: 18px; height: 18px; color: var(--ink2); }
.d10 .pop { font-size: 12px; font-weight: 800; color: var(--r3); }
.d10 .mn { text-align: right; color: var(--muted-ink); }
.d10 .mx { text-align: right; font-weight: 700; }
.rb { height: 6px; border-radius: 3px; background: var(--cell); position: relative; overflow: hidden; }
.rb i { position: absolute; top: 0; bottom: 0; border-radius: 3px; background: linear-gradient(90deg, #8fb1d6, #e0b27a); }
.d10.gap .gt { grid-column: 3 / 8; color: var(--muted-ink); font-size: 13px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

.info { font-size: 13.5px; }
.nt { background: var(--page); border-radius: 14px; padding: 12px 14px; font-size: 13px; line-height: 1.65; white-space: pre-wrap; max-height: 150px;
  overflow: hidden; position: relative; color: var(--ink2); transition: max-height .5s var(--ease); user-select: text; }
.nt.open { max-height: 1600px; }
.nt:not(.open)::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 40px; background: linear-gradient(transparent, var(--page)); }
.more { display: block; margin: 8px auto 0; padding: 6px 10px; font-size: 12.5px; font-weight: 700; color: var(--primary); }
.btn.wide { width: 100%; height: 52px; margin-top: 10px; border-radius: 16px; font-size: 15.5px; }
.foot { text-align: center; font-size: 11.5px; color: var(--muted-ink); margin: 6px 0 4px; }
.toast { bottom: calc(24px + env(safe-area-inset-bottom)); }

/* 등장 */
.rv { opacity: 0; transform: translateY(14px); transition: opacity .5s var(--ease), transform .6s var(--ease); }
.rv.in { opacity: 1; transform: none; }

/* 지도의 현장 표식(주색은 데이터 영역에 쓰지 않으므로 잉크색 점) — 위치는 지도 라이브러리가 바깥 요소로 정한다 */
.me { position: relative; width: 22px; height: 22px; border-radius: 50%; background: var(--ink); border: 4px solid #fff; box-shadow: 0 2px 10px rgba(16, 24, 32, .35); }
.me::after { content: ""; position: absolute; inset: -14px; border-radius: 50%; border: 2px solid rgba(16, 24, 32, .35); animation: ring 2.2s infinite var(--ease); }
@keyframes ring { from { transform: scale(.4); opacity: 1; } to { transform: scale(1.4); opacity: 0; } }
.mlab { position: absolute; left: 24px; top: -2px; white-space: nowrap; background: rgba(253, 253, 253, .95); padding: 4px 9px; border-radius: 9px;
  font-size: 12px; font-weight: 800; color: var(--ink); box-shadow: 0 2px 8px rgba(16, 24, 32, .18); }

/* 현장 선택 */
.picker { position: fixed; inset: 0; z-index: 8; overflow-y: auto; background: var(--page); padding: calc(70px + env(safe-area-inset-top)) 16px 32px; }
.pickbox { max-width: 560px; margin: 0 auto; }
.pickbox h1 { font-size: 22px; margin: 0 0 6px; }
.pickbox > p { color: var(--ink2); margin: 0 0 14px; line-height: 1.5; }
.picklist { display: flex; flex-direction: column; gap: 8px; }
.pick { display: grid; grid-template-columns: 1fr auto; gap: 2px 10px; padding: 12px 14px; border-radius: 16px; background: var(--surface);
  border: 1px solid var(--line); text-decoration: none; color: var(--ink); }
.pick b { font-size: 15px; }
.pick small { grid-column: 1; color: var(--muted-ink); font-size: 12px; }
.pick .num { grid-row: 1 / 3; grid-column: 2; align-self: center; font-weight: 700; color: var(--ink2); }

/* PC(1024px 이상): 왼쪽 지도(고정) + 오른쪽 내용 열(최대 560px) */
@media (min-width: 1024px) {
  .top { top: 16px; left: 16px; right: calc(min(560px, 46vw) + 16px); }
  .live .full { display: inline; }
  .live .short { display: none; }
  .sheet { top: 0; left: auto; width: min(560px, 46vw); height: 100%; border-radius: 0; transform: none; transition: none;
    box-shadow: -10px 0 40px rgba(16, 24, 32, .12); }
  .sc { padding: 24px 24px 32px; }
  .grab, .mapcard { display: none; }
}
```

`web/assets/site.js`:

```js
/* 현장 화면(설계서 3.3): 한 현장의 지금·앞으로 24시간·10일 예보·법정 안내·전파 문안.
   문장·판단은 Python이 만든 값을 그대로 쓰고, 여기서는 표시와 상호작용만 한다. 지도·시트 끌기는 site-map.js. */
(function () {
  "use strict";
  const { $, $$, esc, fmt } = WX;
  const P = WX.parts;
  const SITE = (window.SITE = window.SITE || {});
  const state = (SITE.state = { latest: null, site: null, times: [], h: 0 });
  const REFRESH_MS = 5 * 60 * 1000, STATUS_MS = 60 * 1000;
  const SKY_WORD = { heavy: "비", rain: "비", snow: "눈" };
  const SKY_ICON = { heavy: "i-rain", rain: "i-rain", snow: "i-snow", clear: "i-sun" };
  const els = () => ({ tl: $("#tl"), rain: $("#cR"), wind: $("#cW"), spark: $("#spark"), hours: $("#hours"), note: $("#tlNote"), cursor: $("#cursor") });
  let bound = false, timers = false;

  SITE.value = (h = state.h) => WX.valueAt(state.site, state.times, h);
  SITE.hourText = h => WX.hourText(state.times, h);
  const label = k => (k === 0 ? (state.site.as_of ? `${WX.kst(state.site.as_of).hm} 관측` : "관측 자료 없음") : `${SITE.hourText(k)} 예보`);

  const askedId = () => new URLSearchParams(location.search).get("id");
  function siteHref(id) {
    const query = new URLSearchParams(location.search);   // 확인용 시험 자료(?data=)는 그대로 둔다
    query.set("id", id);
    return `site.html?${query.toString()}`;
  }

  function renderStatus() {
    const st = WX.collectionStatus(state.latest);
    $("#live").innerHTML = `<span class="dot ${st.level}"></span><span class="full">${st.html}</span><span class="short">${st.short}</span>`;
    const banner = $("#banner");
    banner.hidden = !st.banner;
    banner.innerHTML = st.banner ? `${WX.icon("i-clock")}<span>${esc(st.banner)}</span>` : "";
  }

  function renderHero() {
    const site = state.site, h = state.h, v = SITE.value(h), sky = P.heroSky(site, state.times, h);
    $("#hero").className = `hero ${P.heroClass(sky)}${h === 0 && site.state !== "ok" ? " dim" : ""}`;
    const skyText = SKY_WORD[sky] || (h === 0 ? (SITE.value(1) || {}).sky : v && v.sky) || "";
    $("#hIcon").setAttribute("href", `${WX.ICONS}#${SKY_ICON[sky] || WX.skyIcon(skyText)}`);
    const when = h > 0 ? `${SITE.hourText(h)} 예보`
      : site.as_of ? `${WX.kst(site.as_of).hm} 관측${site.state === "stale" ? " · 이번 수집 실패" : ""}` : "관측 자료 없음";
    $("#hK").textContent = skyText ? `${when} · ${skyText}` : when;
    WX.tween($("#hT"), v ? v.temp : null, 1, h === 0 ? 750 : 350);
    const tomorrow = (site.daily || [])[0];
    $("#hM").textContent = h === 0
      ? [v && v.feels != null ? `체감 ${fmt(v.feels, 1)}°` : "",
         tomorrow && !tomorrow.missing && tomorrow.tmin != null ? `내일 최저 ${fmt(tomorrow.tmin, 0)}° 최고 ${fmt(tomorrow.tmax, 0)}°` : ""].filter(Boolean).join(" · ")
      : v ? `강수확률 ${v.pop == null ? "-" : v.pop}% · 습도 ${v.humidity == null ? "-" : v.humidity}%` : "";
    $("#hS").innerHTML = h === 0 ? WX.leadBold(site.summary) : P.forecastSentence(v, SITE.hourText(h));
  }

  SITE.setHour = h => {
    h = Math.max(0, Math.min(state.times.length - 1, Math.round(h)));
    state.h = h;
    renderHero();
    const v = SITE.value(h);
    $("#tiles").innerHTML = P.tiles(v, h === 0);
    P.cursor(els(), h, SITE.hourText(h));
    $("#readout").innerHTML = h === 0 ? '<span class="hint">타임라인을 좌우로 문지르면 그 시각 예보가 보입니다</span>'
      : v ? `<b>${esc(SITE.hourText(h))}</b> ${fmt(v.temp, 1)}° · 비 ${esc(WX.mmText(v.rainText))} · 바람 ${fmt(v.wind, 1)}m/s · 강수확률 ${v.pop == null ? "-" : v.pop}%`
      : `<b>${esc(SITE.hourText(h))}</b> 예보 자료가 없습니다`;
    const chip = $("#nowchip");
    chip.textContent = h === 0 ? "지금" : "지금으로";
    chip.disabled = h === 0;
    chip.classList.toggle("back", h !== 0);
  };

  function reveal() {
    $$(".stack > *").forEach((el, k) => {
      el.classList.add("rv");
      el.classList.remove("in");
      setTimeout(() => el.classList.add("in"), WX.REDUCED ? 0 : 150 + k * 60);
    });
  }
  function renderSite(first) {
    const site = state.site;
    document.title = `${site.short} · 현대아산 기상안전`;
    $("#name").textContent = site.name;
    $("#sub").textContent = [site.category, site.region].filter(Boolean).join(" · ");
    $("#chips").innerHTML = P.chips(site, state.latest.status.warnings === "ok");
    $("#legal").innerHTML = P.legal(site);
    $("#d10").innerHTML = P.daily(site.daily);
    $("#nt").textContent = site.notice;
    if (first) {
      $("#nt").classList.remove("open");
      $("#ntMore").textContent = "전체 보기";
      reveal();
    }
    P.timeline(els(), site, state.times, state.latest.forecast_issued_at, label);
    SITE.setHour(first ? 0 : state.h);
  }

  function showPicker(message) {
    state.site = null;
    $("#sheet").hidden = true;
    $("#picker").hidden = false;
    $("#pickMsg").textContent = message;
    const sites = state.latest.sites.slice().sort((a, b) => a.short.localeCompare(b.short, "ko"));
    $("#pickList").innerHTML = sites.map(s => {
      const v = WX.valueAt(s, state.times, 0);
      const now = !v ? "자료 없음" : WX.isRain(v) ? `비 ${v.rainText}mm/h` : `${fmt(v.temp, 1)}°`;
      return `<a class="pick" href="${esc(siteHref(s.id))}"><b>${esc(s.short)}</b><small>${esc([s.region, s.name].filter(Boolean).join(" · "))}</small><span class="num">${esc(now)}</span></a>`;
    }).join("");
  }

  // 자료를 화면에 반영한다. 현장을 찾으면 true.
  function apply(latest, first) {
    state.latest = latest;
    state.times = WX.timeline(latest);
    renderStatus();
    const id = askedId();
    const site = id ? latest.sites.find(s => s.id === id) : null;
    if (!site) {
      showPicker(id ? "주소의 현장을 찾지 못했습니다(현장 이름이 바뀌면 주소도 바뀝니다). 현장을 다시 골라 주세요."
        : "현장을 골라 주세요.");
      return false;
    }
    $("#picker").hidden = true;
    $("#sheet").hidden = false;
    state.site = site;
    state.h = Math.min(state.h, state.times.length - 1);
    renderSite(first);
    return true;
  }

  async function copy() {
    if (await WX.copy($("#nt").textContent)) { WX.toast("전파 문안을 복사했습니다"); return; }
    $("#nt").classList.add("open");
    const range = document.createRange();
    range.selectNodeContents($("#nt"));
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    WX.toast("자동 복사가 막혀 있습니다. 선택된 문안을 직접 복사해 주세요");
  }
  function bind() {
    if (bound) return;
    bound = true;
    P.scrub(els(), () => state.times.length, h => SITE.setHour(h));
    $("#nowchip").addEventListener("click", () => SITE.setHour(0));
    $("#ntMore").addEventListener("click", () => {
      const open = $("#nt").classList.toggle("open");
      $("#ntMore").textContent = open ? "접기" : "전체 보기";
    });
    $("#copy").addEventListener("click", copy);
    window.addEventListener("resize", () => { if (state.site) P.cursor(els(), state.h, SITE.hourText(state.h)); });
  }
  // 새 자료로 바꾼다(고른 시각·펼친 문안은 그대로). 5분 갱신과 확인에 쓴다.
  SITE.applyLatest = latest => {
    const shown = apply(latest, false);
    if (shown && SITE.map) SITE.map.render();
    return shown;
  };
  async function refresh() {
    try {
      const latest = await WX.load(WX.dataUrl("data/latest.json"));
      if (latest.generated_at === state.latest.generated_at) { renderStatus(); return; }
      SITE.applyLatest(latest);
    } catch (error) {
      renderStatus();   // 다시 불러오기에 실패하면 이전 화면을 두고 수집 상태만 다시 판단한다
    }
  }
  function startTimers() {
    if (timers) return;
    timers = true;
    setInterval(() => { if (state.latest) renderStatus(); }, STATUS_MS);
    setInterval(refresh, REFRESH_MS);
  }

  async function boot() {
    $("#loadfail").hidden = true;
    let latest;
    try {
      latest = await WX.load(WX.dataUrl("data/latest.json"));
    } catch (error) {
      console.warn("[화면 자료]", error);
      $("#loadfail").hidden = false;
      return;
    }
    bind();
    const shown = apply(latest, true);
    startTimers();
    if (shown && SITE.map) SITE.map.init();
  }
  document.addEventListener("DOMContentLoaded", () => {
    $("#retry").addEventListener("click", boot);
    boot();
  });
})();
```

- [ ] **Step 5: 현장 화면 확인 (휴대폰 첫 화면·상태)**

Run: `python3 -m unittest tests.test_web_app 2>&1 | tail -1` → Expected: `OK`
Run: `python3 -m src.publish && python3 scripts/preview_fixtures.py` (게시·시험 자료 갱신)

작업 기록 폴더에 `site-mobile.json`을 만들어 `node scripts/ui_check.mjs`로 실행한다. `ID`는 `python3 -c "import json;print(json.load(open('.superpowers/preview/fixtures/rain.json'))['sites'][0]['id'])"`로 구한 rain 시험 자료 첫 현장(호우경보 현장) ID로 바꾼다.

```json
{"width": 390, "height": 844, "mobile": true, "steps": [
 {"nav": "http://localhost:8765/site/site.html?data=../fixtures/rain.json&id=ID", "after": 4000},
 {"label": "first screen", "eval": "(() => { const b = s => document.querySelector(s).getBoundingClientRect().bottom; return {name: b('#name') <= innerHeight, temp: b('#hT') <= innerHeight, summary: b('#hS') <= innerHeight, chips: b('#chips') <= innerHeight, chipText: document.querySelector('#chips').textContent, title: document.title, hScroll: document.documentElement.scrollWidth <= innerWidth}; })()"},
 {"shot": "site-mobile.png"},
 {"label": "daily", "eval": "document.querySelectorAll('#d10 .d10').length"},
 {"label": "scrub", "eval": "document.querySelector('#tl').focus(); 1"},
 {"key": "ArrowRight"}, {"key": "ArrowRight"},
 {"label": "hour2", "eval": "({h: SITE.state.h, chip: document.querySelector('#nowchip').textContent, k: document.querySelector('#hK').textContent, readout: document.querySelector('#readout').textContent})"},
 {"click": "document.querySelector('#nowchip')", "label": "back", "after": 500},
 {"label": "back0", "eval": "({h: SITE.state.h, readout: document.querySelector('#readout').textContent})"},
 {"click": "document.querySelector('#ntMore')", "label": "more", "after": 600},
 {"label": "notice", "eval": "({open: document.querySelector('#nt').classList.contains('open'), same: document.querySelector('#nt').textContent === SITE.state.site.notice})"},
 {"click": "document.querySelector('#copy')", "label": "copy", "after": 700},
 {"label": "toast", "eval": "document.querySelector('#toast span').textContent"}
]}
```

Expected:
- `first screen`: `name`·`temp`·`summary`·`chips` 모두 `true`, `chipText`에 `호우경보 발효 중`, `title`이 `진천 신공장 · 현대아산 기상안전` 형태, `hScroll` `true`
- `daily` = 10, `hour2`: `h` 2, `chip` `지금으로`, `k`가 `예보`를 포함, `readout`이 시각으로 시작
- `back0`: `h` 0, `readout`에 `문지르면`
- `notice`: 모두 `true`, `toast`: `전파 문안을 복사했습니다` 또는 `자동 복사가 막혀 있습니다…`
- 콘솔 오류 0건. 캡처를 열어 시안과 같은 모양(흰 로고 막대, 시트 안 히어로·칩)인지 본다.

같은 단계를 `{"width": 360, "height": 640, "mobile": true}`로 한 번 더 실행해 `first screen`이 모두 `true`인지 본다(Review Focus 2). 긴 현장명: rain 자료에서 `포항~안동2 국도건설공사`의 ID로 열어 `document.querySelector('#name').scrollWidth <= document.querySelector('#name').clientWidth`가 `true`.

- [ ] **Step 6: 상태·선택 화면 확인 (Review Focus 1·5)**

같은 방식으로 확인한다(390×844):

| 주소 | 식 | 기대값 |
|---|---|---|
| `site.html?data=../fixtures/rain.json` (ID 없음) | `({picker: !document.querySelector('#picker').hidden, n: document.querySelectorAll('#pickList .pick').length === SITE.state.latest.sites.length, msg: document.querySelector('#pickMsg').textContent})` | `picker` true, `n` true, `msg` `현장을 골라 주세요.` |
| `…&id=nosuchid` | 같은 식 | `picker` true, `msg`에 `찾지 못했습니다` |
| `…&id=%3Cscript%3E` | `({picker: !document.querySelector('#picker').hidden, manifest: document.querySelector('#manifest').getAttribute('href')})` | `picker` true, `manifest` `manifest.webmanifest` |
| `rain.json&id=ID` | `document.querySelector('#manifest').getAttribute('href')` | `manifests/ID.webmanifest` |
| 선택 목록의 첫 링크 클릭 | `SITE.state.site && location.search.includes('data=')` | `true` (시험 자료 유지) |
| `failed.json&id=ID` | `({chips: document.querySelector('#chips').textContent, dim: document.querySelector('#hero').classList.contains('dim'), live: document.querySelector('#live .short').textContent, banner: !document.querySelector('#banner').hidden})` | `chips`에 `이번 수집 실패`, `dim` true, `live`에 `수집 실패` 또는 `수집 지연`, `banner` true |
| `noforecast.json&id=<sites[2] ID>` | `document.querySelector('#tlNote').textContent` | `…예보 자료를 받지 못했습니다.` |
| `escape.json&id=<sites[0] ID>` | `document.querySelector('#name').textContent.includes('<b>진천</b>') && !document.querySelector('#name b')` | `true` |
| `none.json&id=ID` | `!document.querySelector('#loadfail').hidden` | `true` |
| `rain.json&id=ID` | `(() => { SITE.setHour(3); const L = JSON.parse(JSON.stringify(SITE.state.latest, (k, v) => k === '_byTime' ? undefined : v)); L.generated_at = '2026-09-27T21:08:00+09:00'; SITE.applyLatest(L); return {h: SITE.state.h, name: document.querySelector('#name').textContent === SITE.state.site.name, chip: document.querySelector('#nowchip').textContent}; })()` | `h` 3, `name` true, `chip` `지금으로` (새 자료로 바뀌어도 고른 시각 유지) |

콘솔 오류는 `none.json` 경우의 404 기록 외 0건. 금지어 점검: `['선제','기준 도달','주의 단계','경계 단계','훨씬','크게'].filter(w => document.body.innerText.includes(w))` → `[]`.

- [ ] **Step 7: 커밋**

```bash
git add web/site.html web/assets/site.css web/assets/site.js web/assets/parts.js tests/test_web_app.py
git commit -m "현장 화면 본문: 히어로·칩·수치·24시간·10일 예보·법정 안내·전파 문안·현장 선택"
```

---

### Task 4: 현장 화면 지도와 끌어올리는 시트, PC 2단 배치

**Files:**
- Create: `web/assets/site-map.js`
- Modify: `web/site.html` (스크립트 두 줄)

**Interfaces:**
- Consumes: `SITE.state`, `WX.createMap({ …, view })`(Task 2), `WX.valueAt`, `WX.isRain`
- Produces: `SITE.map = { init(), render() }`, `SITE.padding() -> {left,right,top,bottom}`. 시트 위치 `data-snap`: `full`(다 펼침) · `half`(지도 띠가 화면 26%, 최소 150px) · `map`(지도 크게). 손잡이: 끌기·누르기(펼침↔반)·키보드(Enter/Space). 제목 누르기 → 펼침, "지도로 보기" → 지도.

- [ ] **Step 1: 점검 단계 작성(실패 확인)**

작업 기록 폴더에 `site-map.json`(`ID`는 Task 3 Step 5와 같은 값):

```json
{"width": 390, "height": 844, "mobile": true, "steps": [
 {"nav": "http://localhost:8765/site/site.html?data=../fixtures/rain.json&id=ID", "after": 11000},
 {"label": "map", "eval": "({canvas: document.querySelectorAll('.maplibregl-canvas').length, me: document.querySelectorAll('.mewrap').length, label: (document.querySelector('.mlab') || {}).textContent || '', snap: document.querySelector('#sheet').dataset.snap, sheetTop: Math.round(document.querySelector('#sheet').getBoundingClientRect().top)})"},
 {"shot": "site-map-half.png"},
 {"click": "document.querySelector('#goMap')", "label": "goMap", "after": 900},
 {"label": "mapSnap", "eval": "({snap: document.querySelector('#sheet').dataset.snap, low: document.querySelector('#sheet').getBoundingClientRect().top > innerHeight * 0.7, meVisible: (() => { const r = document.querySelector('.mewrap').getBoundingClientRect(); return r.top > 0 && r.bottom < document.querySelector('#sheet').getBoundingClientRect().top; })()})"},
 {"shot": "site-map-map.png"},
 {"click": "document.querySelector('#grab')", "label": "tap grab", "after": 900},
 {"label": "fullSnap", "eval": "({snap: document.querySelector('#sheet').dataset.snap, expanded: document.querySelector('#grab').getAttribute('aria-expanded')})"},
 {"click": "document.querySelector('#grab')", "label": "tap grab 2", "after": 900},
 {"label": "halfAgain", "eval": "document.querySelector('#sheet').dataset.snap"},
 {"drag": "document.querySelector('#grab')", "dy": 300, "label": "drag down", "after": 900},
 {"label": "dragged", "eval": "document.querySelector('#sheet').dataset.snap"},
 {"click": "document.querySelector('#grab')", "label": "tap grab 3", "after": 900},
 {"label": "scrubStart", "eval": "({snap: document.querySelector('#sheet').dataset.snap, h: SITE.state.h})"},
 {"drag": "document.querySelector('#cR')", "dx": 120, "label": "scrub timeline", "after": 700},
 {"label": "scrubbed", "eval": "({snap: document.querySelector('#sheet').dataset.snap, h: SITE.state.h})"}
]}
```

Run: `node scripts/ui_check.mjs .superpowers/sdd/2026-09-27-phase3-site-ui/site-map.json`
Expected: `map`의 `canvas` 0·`me` 0(지도 모듈 없음), `goMap` 뒤 `snap`이 `half` 그대로 — 실패

- [ ] **Step 2: `web/assets/site-map.js` 작성**

```js
/* 현장 화면의 지도와 끌어올리는 시트(설계서 3.3).
   휴대폰: 시트 세 위치(펼침·반·지도)를 손잡이로만 옮긴다(타임라인 문지르기와 겹치지 않게).
   PC(1024px 이상): 왼쪽 지도 + 오른쪽 내용 열(시트 이동 없음). */
(function () {
  "use strict";
  const { $, fmt } = WX;
  const SITE = window.SITE, state = SITE.state;
  const TOP_GAP = 60;                     // 다 펼쳤을 때 위 여백(상단 막대 자리)
  const ORDER = ["full", "half", "map"];
  let snap = "half", adapter = null, marker = null, started = false;
  const desktop = () => window.innerWidth >= 1024;

  // 시트가 내려간 정도(시트 높이의 %). 반 위치는 지도 띠가 화면 높이의 26%(최소 150px) 보이게 화면에 맞춰 정한다
  // → 작은 휴대폰에서도 첫 화면에 현장명·기온·요약·특보 칩이 보인다(설계서 1.3-2).
  function snapValue(name) {
    if (name === "full") return 0;
    if (name === "map") return 78;
    const sheetH = window.innerHeight - TOP_GAP, mapPx = Math.max(150, window.innerHeight * 0.26);
    return Math.max(0, Math.min(60, ((mapPx - TOP_GAP) / sheetH) * 100));
  }
  function currentValue() {
    const value = Number($("#sheet").style.getPropertyValue("--yn"));
    return isFinite(value) && $("#sheet").style.getPropertyValue("--yn") !== "" ? value : snapValue(snap);
  }
  SITE.padding = () => {
    if (desktop()) return { left: 40, right: Math.min(560, window.innerWidth * 0.46) + 40, top: 90, bottom: 40 };
    const visible = (window.innerHeight - TOP_GAP) * (1 - currentValue() / 100);
    return { left: 30, right: 30, top: 70, bottom: Math.round(visible) + 16 };
  };

  function center() {
    if (!adapter || !state.site || typeof state.site.lat !== "number") return;
    adapter.flyTo({ center: [state.site.lon, state.site.lat], zoom: Math.max(adapter.getZoom(), 9), padding: SITE.padding(),
      speed: WX.REDUCED ? 10 : 1.2 });
  }
  function setSnap(name, animate = true) {
    snap = name;
    const sheet = $("#sheet");
    sheet.classList.toggle("drag", !animate);
    sheet.style.setProperty("--yn", snapValue(name).toFixed(2));
    sheet.dataset.snap = name;
    $("#grab").setAttribute("aria-expanded", String(name === "full"));
    if (!animate) requestAnimationFrame(() => sheet.classList.remove("drag"));
    setTimeout(center, animate && !WX.REDUCED ? 560 : 0);
  }

  function bindSheet() {
    const sheet = $("#sheet"), grab = $("#grab");
    let drag = null;
    grab.addEventListener("pointerdown", e => {
      if (desktop()) return;
      drag = { y: e.clientY, from: currentValue(), t: performance.now(), moved: false };
      grab.setPointerCapture(e.pointerId);
      sheet.classList.add("drag");
    });
    grab.addEventListener("pointermove", e => {
      if (!drag) return;
      const dy = e.clientY - drag.y;
      if (Math.abs(dy) > 4) drag.moved = true;
      const value = Math.max(0, Math.min(85, drag.from + (dy / (window.innerHeight - TOP_GAP)) * 100));
      sheet.style.setProperty("--yn", value.toFixed(2));
    });
    const end = e => {
      if (!drag) return;
      sheet.classList.remove("drag");
      const moved = drag.moved, speed = (e.clientY - drag.y) / Math.max(1, performance.now() - drag.t), now = currentValue();
      drag = null;
      if (!moved) { setSnap(snap === "full" ? "half" : "full"); return; }
      let target = ORDER.reduce((a, b) => (Math.abs(snapValue(b) - now) < Math.abs(snapValue(a) - now) ? b : a));
      if (Math.abs(speed) > 0.5) target = ORDER[Math.max(0, Math.min(2, ORDER.indexOf(snap) + (speed > 0 ? 1 : -1)))];
      setSnap(target);
    };
    grab.addEventListener("pointerup", end);
    grab.addEventListener("pointercancel", end);
    grab.addEventListener("click", e => { if (e.detail === 0) setSnap(snap === "full" ? "half" : "full"); });   // 키보드(Enter·Space)
    $("#goMap").addEventListener("click", () => { $("#sc").scrollTo({ top: 0 }); setSnap("map"); });
    $(".ttl .names").addEventListener("click", () => { if (!desktop() && snap !== "full") setSnap("full"); });
    window.addEventListener("resize", () => { setSnap(snap, false); if (adapter) adapter.resize(); });
  }

  function markerText() {
    const v = WX.valueAt(state.site, state.times, 0);
    if (!v) return `${state.site.short} · -`;
    return WX.isRain(v) ? `${state.site.short} · 비 ${v.rainText}` : `${state.site.short} · ${fmt(v.temp, 1)}°`;
  }
  function render() {
    if (!marker || !state.site) return;
    marker.setLngLat(state.site.lon, state.site.lat);
    const text = markerText();
    marker.el.querySelector(".mlab").textContent = text;
    marker.el.setAttribute("aria-label", `${state.site.name} ${text}`);
  }
  function attach(next) {
    if (marker) marker.remove();
    adapter = next;
    const el = document.createElement("div");
    el.className = "mewrap";
    el.setAttribute("role", "img");
    el.innerHTML = '<div class="me"></div><div class="mlab"></div>';
    marker = adapter.addMarker(el, state.site.lon, state.site.lat, "center");
    render();
    center();
  }
  function notice(mode) {
    const msg = $("#mapMsg");
    msg.textContent = mode === "svg" ? "지도 서비스를 불러오지 못해 간단한 지도로 표시합니다."
      : mode === "none" ? "지도를 불러오지 못했습니다. 현장 정보는 그대로 볼 수 있습니다." : "";
    msg.classList.toggle("show", !!mode);
    clearTimeout(msg._timer);
    if (mode) msg._timer = setTimeout(() => msg.classList.remove("show"), 8000);
  }

  SITE.map = {
    init() {
      if (started || !state.site) return;
      started = true;
      bindSheet();
      setSnap(desktop() ? "full" : "half", false);
      if (typeof state.site.lat !== "number" || typeof state.site.lon !== "number") return;   // 위치 없는 현장은 지도 없이
      WX.createMap({ container: $("#map"), padding: SITE.padding, view: { center: [state.site.lon, state.site.lat], zoom: 9 },
        onReady: attach, onNotice: notice });
    },
    render,
  };
})();
```

`web/site.html`의 스크립트를 다음 순서로 만든다:

```html
<script src="assets/common.js" defer></script>
<script src="assets/geo.js" defer></script>
<script src="assets/parts.js" defer></script>
<script src="assets/site.js" defer></script>
<script src="assets/site-map.js" defer></script>
```

- [ ] **Step 3: 통과 확인**

Run: `python3 -m src.publish && node scripts/ui_check.mjs .superpowers/sdd/2026-09-27-phase3-site-ui/site-map.json`

Expected:
- `map`: `canvas` 1, `me` 1, `label`이 현장 짧은 이름으로 시작, `snap` `half`, `sheetTop` 약 219(390×844에서 화면의 26%)
- `mapSnap`: `snap` `map`, `low` true, `meVisible` true
- `fullSnap`: `snap` `full`, `expanded` `"true"`; `halfAgain` `half`; `dragged` `map`(아래로 300px 끌기)
- `scrubStart` → `scrubbed`: `snap`이 그대로(`half`)이고 `h`가 0에서 늘어남(Review Focus 3)
- 콘솔 오류 0건. 캡처 두 장(반·지도)을 열어 표식·이름표가 시트에 가리지 않는지 본다.

- [ ] **Step 4: 작은 휴대폰·PC·자체 지도 확인**

1. 360×640(`mobile: true`)으로 Task 3 Step 5의 `first screen` 식을 다시 실행 → 모두 `true`(반 위치가 화면에 맞춰짐).
2. 1440×900으로 `…site.html?data=../fixtures/rain.json&id=ID`, 11초 대기:

```js
(() => { const s = document.querySelector('#sheet').getBoundingClientRect(), me = document.querySelector('.mewrap').getBoundingClientRect();
  return { transform: getComputedStyle(document.querySelector('#sheet')).transform, width: Math.round(s.width), right: Math.round(s.right),
    grab: getComputedStyle(document.querySelector('#grab')).display, mapcard: getComputedStyle(document.querySelector('.mapcard')).display,
    meLeftOfColumn: me.right < s.left, noScroll: document.documentElement.scrollHeight <= innerHeight, live: document.querySelector('#live .full').offsetWidth > 0 }; })()
```

Expected: `transform` `none`, `width` 560, `right` 1440, `grab`·`mapcard` `none`, `meLeftOfColumn` true, `noScroll` true, `live` true. 캡처를 남긴다.

3. `…&id=ID&map=svg`(390×844): `document.querySelector('.svgmap') !== null && document.querySelectorAll('.mewrap').length === 1` → `true`, 안내 문구 표시, 콘솔 오류 0건.

- [ ] **Step 5: 커밋**

```bash
git add web/assets/site-map.js web/site.html
git commit -m "현장 화면 지도·끌어올리는 시트·PC 2단 배치"
```

---

### Task 5: 본사 화면에서 현장 화면 열기, 문서 갱신, 두 화면 최종 점검

**Files:**
- Modify: `web/assets/hq-detail.js` (`open`), `CLAUDE.md`, `README.md`

**Interfaces:**
- Consumes: 현장 화면 주소 `site.html?id=<ID>`
- Produces: 본사 상세의 "현장 화면" 버튼(새 탭이 아닌 같은 창에서 이동)

- [ ] **Step 1: 점검 단계 작성(실패 확인)**

작업 기록 폴더에 `hq-link.json`:

```json
{"width": 1440, "height": 900, "steps": [
 {"nav": "http://localhost:8765/site/index.html?data=../fixtures/rain.json", "after": 10000},
 {"label": "button", "eval": "({hidden: document.querySelector('#bSite').hidden, href: document.querySelector('#bSite').getAttribute('href'), selId: HQ.state.sel && HQ.state.sel.id})"}
]}
```

Run → Expected: `hidden` true, `href` null — 실패

- [ ] **Step 2: 구현**

`web/assets/hq-detail.js`의 `open(site, first) {` 블록을 다음으로 바꾼다:

```js
    open(site, first) {
      $("#detail").classList.add("open");
      $("#detail").inert = false;
      const link = $("#bSite");
      link.setAttribute("href", `site.html?id=${encodeURIComponent(site.id)}`);
      link.hidden = false;
      render(first);
    },
```

Run: `python3 -m src.publish` 후 `hq-link.json` 다시 실행 → Expected: `hidden` false, `href`가 `site.html?id=` + `selId`. 버튼을 누르면(`{"click": "document.querySelector('#bSite')", "after": 4000}` 뒤 `location.pathname.endsWith('site.html') && SITE.state.site.id === <selId>`) `true`.

- [ ] **Step 3: 문서 갱신**

`CLAUDE.md`:
- "현재 운영 상태" 목록의 새 본사 화면 줄 다음에 추가:

```markdown
- 현장 화면: `…/site.html?id=현장ID` (ID 없으면 현장 선택 목록). 본사 상세의 "현장 화면" 버튼으로 연결. 휴대폰 홈 화면에 추가하면 그 현장으로 바로 열린다(`docs/manifests/<ID>.webmanifest`, 수집 실행이 생성)
```

- "대시보드 리디자인 진행" 목록에 추가:

```markdown
- 3단계(현장 화면·홈 화면 추가): `web/site.html`·`site.css`·`site.js`(본문)·`site-map.js`(지도·시트). 본사 상세와 현장 화면이 함께 쓰는 부품은 `web/assets/parts.js`와 `app.css` 끝 절. 화면 확인은 `node scripts/ui_check.mjs <단계.json>`(헤드리스 Chrome, 임시 프로필) — 앱 미리보기 창이 가려지면 지도가 그려지지 않으므로 이 도구로 본다.
```

- "주요 파일"의 `web/:` 줄 다음에 추가:

```markdown
- `web/site.html`·`assets/site*.js`·`site.css`: 현장 화면, `assets/parts.js`: 현장 카드 공통 부품, `manifest.webmanifest`·`assets/icons/`: 홈 화면 추가
- `scripts/ui_check.mjs`: 헤드리스 Chrome 화면 점검 도구(단계 JSON → 결과·콘솔 오류·캡처)
```

- 전체 테스트 수를 실제 통과 수(161)로 고친다.

`README.md`의 "대시보드 (GitHub Pages)" 첫 문단 끝(개인정보 문장 앞)에 한 문장 추가:

```markdown
현장 안전관리자는 `site.html?id=현장ID`로 자기 현장 화면을 보고, 휴대폰 "홈 화면에 추가"로 앱처럼 쓸 수 있습니다.
```

Run: `python3 -m unittest discover -s tests -b 2>&1 | tail -3` → Expected: `OK` (161개)

- [ ] **Step 4: 두 화면 최종 점검과 캡처**

1. 2단계 점검(`hq-regress.json`, Task 2 Step 6)을 다시 실행 → 같은 기대값.
2. 현장 화면 점검(`site-mobile.json`·`site-map.json`)을 다시 실행 → 같은 기대값.
3. 시간 표시가 지금 시각 기준으로 정상인 캡처를 위해, `rain.json`의 시각을 지금으로 옮긴 임시 자료(`fixtures/demo.json`, 커밋하지 않음)를 만들고 390×844 현장 화면(반·펼침), 1440×900 현장 화면, 1440×900 본사 화면을 캡처한다:

```bash
python3 - <<'EOF'
import json, re
from datetime import datetime, timedelta, timezone
src = json.load(open(".superpowers/preview/fixtures/rain.json", encoding="utf-8"))
now = datetime.now(timezone(timedelta(hours=9)))
shift = timedelta(hours=int((now - datetime.fromisoformat(src["generated_at"])).total_seconds() // 3600))
iso = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?\+09:00$")
def walk(v):
    if isinstance(v, dict): return {k: walk(x) for k, x in v.items()}
    if isinstance(v, list): return [walk(x) for x in v]
    if isinstance(v, str) and iso.match(v): return (datetime.fromisoformat(v) + shift).isoformat()
    return v
demo = walk(src)
demo["schedule"]["next_run_at"] = (now + timedelta(minutes=30)).replace(second=0, microsecond=0).isoformat()
json.dump(demo, open(".superpowers/preview/fixtures/demo.json", "w", encoding="utf-8"), ensure_ascii=False)
print("shift", shift)
EOF
```

캡처 파일은 작업 기록 폴더 `shots/`에 두고, 사용자 보고 때 보낸다.

- [ ] **Step 5: 커밋**

```bash
git add web/assets/hq-detail.js CLAUDE.md README.md
git commit -m "본사 상세에서 현장 화면 열기, 3단계 문서 갱신"
```

---

### Task 6: 배포와 운영 확인

**Files:** 없음

- [ ] **Step 1: 최종 검토 뒤 사용자 확인** — 최종 리뷰(Review Focus 포함)·수정이 끝나면 캡처(휴대폰 현장 화면·PC 현장 화면·본사)를 보여 주고 **main 병합과 GitHub 푸시 여부를 묻는다.**

- [ ] **Step 2: 병합·푸시(승인 후)**

```bash
cd ~/Projects/weather-alert-system
git fetch -q origin && git checkout -q main && git merge -q --no-edit origin/main
git merge --no-ff phase3-site-ui -m "3단계 현장 화면 합치기"
python3 -m unittest discover -s tests -b 2>&1 | tail -3
git push origin main
```

- [ ] **Step 3: 수집 실행과 게시 확인**

```bash
gh workflow run collector.yml && sleep 6
RUN_ID=$(gh run list --workflow=collector.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --exit-status --interval 10 > /dev/null; echo "exit=$?"
gh run view "$RUN_ID" --log | grep -E "화면 데이터|화면 게시|알림 전달"
```

Expected: `exit=0`, `[화면 게시] N개 파일 · 현장 홈 화면 설정 21곳`, `[알림 전달: 모의운영(외부 발송 차단)] 발송 0건`.

- [ ] **Step 4: 공개 주소 확인**

```bash
git pull -q --rebase origin main
BASE=https://stkangys-lgtm.github.io/weather-alert-system
ID=$(python3 -c "import json;print(json.load(open('docs/data/latest.json'))['sites'][0]['id'])")
for p in "" "site.html" "site.html?id=$ID" "manifest.webmanifest" "manifests/$ID.webmanifest" "assets/parts.js" "assets/site.js" "assets/site-map.js" "assets/icons/app-512.png"; do
  printf "%-44s %s\n" "/$p" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/$p")"; done
curl -s "$BASE/manifests/$ID.webmanifest" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['start_url'], d['short_name'])"
```

Expected: 모두 `200`, 매니페스트 `start_url`이 `../site.html?id=<ID>`. `ui_check`로 공개 현장 화면(390×844)을 열어 첫 화면 식이 모두 `true`이고 콘솔 오류 0건인지 확인하고 사용자에게 보고한다.

- [ ] **Step 5: 정리** — 미리보기 게시본을 되돌린 뒤(`git checkout -- docs && git clean -fq -- docs/assets docs/data/kr-map.json docs/manifests docs/site.html docs/manifest.webmanifest`) 작업 폴더·브랜치 삭제.

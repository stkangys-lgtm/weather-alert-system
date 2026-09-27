"""화면 원본(web/)을 공개 폴더(docs/)로 게시하고, 게시 전 기본 안전 점검을 한다.

- web/ 아래 파일만 덮어쓴다. docs/의 다른 파일(수집 결과·알림 대기열·이전 화면)은 건드리지 않는다.
- 자체 지도 원본(src/kr_map_data.json)을 docs/data/kr-map.json으로 함께 게시한다(지도 장애 시 대체 지도).
- 외부 스크립트·스타일시트에는 무결성 해시(integrity="sha384-…")와 crossorigin이 있어야 한다.
- 공개 파일에 전화번호 형식·금지어·설정의 비공개 값(담당자 등)이 있으면 게시하지 않는다.
  Actions 로그도 공개되므로 문제 값 자체는 출력하지 않는다.

로컬 확인: python -m src.publish
"""

import json
import os
import re
import shutil

from src.narrative import contains_forbidden

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(ROOT, "web")
DOCS_DIR = os.path.join(ROOT, "docs")
MAP_SOURCE = os.path.join(ROOT, "src", "kr_map_data.json")
MAP_TARGET = os.path.join("data", "kr-map.json")
OLD_DIR = os.path.join(DOCS_DIR, "old")
OLD_MAP_PATH = os.path.join(OLD_DIR, "index.html")
OLD_SITES_PATH = os.path.join(OLD_DIR, "sites.html")
MANIFEST_DIR = "manifests"
APP_ICONS = (("assets/icons/app-192.png", "192x192"), ("assets/icons/app-512.png", "512x512"))
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

TEXT_EXTENSIONS = (".html", ".css", ".js", ".json", ".svg", ".webmanifest", ".txt")
PHONE_PATTERN = re.compile(r"01[016789]-?\d{3,4}-?\d{4}")
PRIVATE_KEY_PATTERN = re.compile(r"manager|phone|contact|email|token|담당|연락", re.I)
_TAG = re.compile(r"<(script|link)\b([^>]*)>", re.I)
_URL = re.compile(r"\b(?:src|href)=\"(https?://[^\"]+)\"")


class PublishError(Exception):
    """게시 전 점검에서 공개하면 안 되는 내용을 찾았다."""


def private_values(sites):
    """설정 현장 목록에서 공개하면 안 되는 값(담당자 이름·연락처 등)."""
    values = set()
    for site in sites or []:
        for key, value in site.items():
            if PRIVATE_KEY_PATTERN.search(str(key)) and isinstance(value, str) and len(value.strip()) >= 2:
                values.add(value.strip())
    return values


def external_tag_problems(html):
    """integrity·crossorigin 없이 외부에서 불러오는 script·stylesheet 주소 목록."""
    problems = []
    for kind, attrs in _TAG.findall(html):
        url = _URL.search(attrs)
        if not url:
            continue
        if kind.lower() == "link" and 'rel="stylesheet"' not in attrs:
            continue
        if 'integrity="sha384-' not in attrs or "crossorigin" not in attrs:
            problems.append(url.group(1))
    return problems


def text_problems(text, blocked=()):
    """공개 파일에 있으면 안 되는 내용의 종류(값 자체는 돌려주지 않는다)."""
    problems = []
    if PHONE_PATTERN.search(text):
        problems.append("전화번호 형식")
    problems += [f"금지어 '{word}'" for word in contains_forbidden(text)]
    if any(value in text for value in blocked):
        problems.append("설정의 비공개 값")
    return problems


def web_files(web_dir=WEB_DIR):
    """web/ 아래 게시할 파일의 상대 경로(숨김 파일·폴더 제외)."""
    found = []
    for base, dirs, files in os.walk(web_dir):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        found += [os.path.relpath(os.path.join(base, name), web_dir)
                  for name in sorted(files) if not name.startswith(".")]
    return found


def check_web(web_dir=WEB_DIR, blocked=()):
    """게시 전 점검. 문제 목록('상대 경로: 내용')을 돌려준다."""
    problems = []
    for rel in web_files(web_dir):
        if not rel.endswith(TEXT_EXTENSIONS):
            continue
        with open(os.path.join(web_dir, rel), encoding="utf-8") as f:
            text = f.read()
        found = text_problems(text, blocked)
        if rel.endswith(".html"):
            found += [f"무결성 해시 없는 외부 파일 {url}" for url in external_tag_problems(text)]
        problems += [f"{rel}: {item}" for item in found]
    return problems


def check_latest(path, blocked=()):
    """docs/data/latest.json 점검. 파일이 없으면 빈 목록."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return text_problems(f.read(), blocked)


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


def publish(web_dir=WEB_DIR, docs_dir=DOCS_DIR, map_source=MAP_SOURCE, blocked=()):
    """점검을 통과하면 web/ 파일과 자체 지도 자료를 docs/로 복사하고, 게시한 상대 경로 목록을 돌려준다."""
    problems = check_web(web_dir, blocked)
    if problems:
        raise PublishError("; ".join(problems))
    published = []
    for rel in web_files(web_dir):
        target = os.path.join(docs_dir, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(os.path.join(web_dir, rel), target)
        published.append(rel)
    target = os.path.join(docs_dir, MAP_TARGET)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(map_source, target)
    published.append(MAP_TARGET)
    return published


if __name__ == "__main__":
    files = publish()
    manifests = write_site_manifests(os.path.join(DOCS_DIR, "data", "latest.json"))
    print(f"[화면 게시] {len(files)}개 파일 · 현장 홈 화면 설정 {len(manifests)}곳 → docs/")

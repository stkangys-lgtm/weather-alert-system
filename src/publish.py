"""화면 원본(web/)을 공개 폴더(docs/)로 게시하고, 게시 전 기본 안전 점검을 한다.

- web/ 아래 파일만 덮어쓴다. docs/의 다른 파일(수집 결과·알림 대기열·이전 화면)은 건드리지 않는다.
- 자체 지도 원본(src/kr_map_data.json)을 docs/data/kr-map.json으로 함께 게시한다(지도 장애 시 대체 지도).
- 외부 스크립트·스타일시트에는 무결성 해시(integrity="sha384-…")와 crossorigin이 있어야 한다.
- 공개 파일에 전화번호 형식·금지어·설정의 비공개 값(담당자 등)이 있으면 게시하지 않는다.
  Actions 로그도 공개되므로 문제 값 자체는 출력하지 않는다.

로컬 확인: python -m src.publish
"""

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
    print(f"[화면 게시] {len(files)}개 파일 → docs/")

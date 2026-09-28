"""화면 확인용 시험 자료를 만든다(공개 폴더 밖에 저장).

사용: python3 scripts/preview_fixtures.py [출력 폴더]   (기본: .superpowers/preview/fixtures)
docs/data/latest.json의 현장 목록·위치를 바탕으로 상황별 자료를 만들고, 문장은 src/narrative.py로 다시 만든다.
- rain: 여러 현장 비 + 호우경보 1곳·예비특보 1곳·법정 작업중지 1곳
- failed: 이번 수집 전체 실패(모든 현장 이전 자료)
- partial: 일부 현장 이전 자료 + 1곳 자료 없음
- night: 운영시간 뒤(다음 수집 내일 04:17) + 특보 확인 실패
- escape: 현장명·문장에 <, &, " 가 들어간 경우(글자로만 보여야 함)
- noforecast: 1곳 예보 없음(단기예보 일부 실패)
- onset: 비가 막 시작된 현장(강수량 0, 강수형태 빗방울) 1곳 + 비 1곳
- radarold: 레이더 영상이 90분보다 오래됨(관측 생성시각 − 120분) + 상태 failed
- noradar: 레이더 영상 없음(radar: None) + 상태 failed

모든 자료(radarold·noradar 제외)에는 표본 레이더 영상으로 만든 "radar.png"를 가리키는
radar 값(상태 ok)을 함께 넣는다. 실제 영상 파일은 main()이 출력 폴더에 한 번만 쓴다.
"""

import copy
import json
import os
import sys
from datetime import datetime, timedelta

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.radar import CORNERS, render_overlay  # noqa: E402
from src.view_model import finish_site, national_view, parse_pcp  # noqa: E402

SOURCE = os.path.join(ROOT, "docs", "data", "latest.json")
DEFAULT_OUT = os.path.join(ROOT, ".superpowers", "preview", "fixtures")
RADAR_SAMPLE = os.path.join(ROOT, "tests", "fixtures", "radar", "RDR_CMP_WRC_202609280930.png")
RADAR_IMAGE = "radar.png?v=fixture"
RAIN_NOW = (31.0, 12.4, 4.2, 0.6)
HEAVY = {"kind": "기상특보", "title": "호우경보", "level": "경보"}
PRE = {"kind": "예비특보", "title": "강풍 예비특보", "level": "예비특보"}
STOP = {"status": "법정 작업중지", "title": "철골작업 중지", "article": "산업안전보건기준에 관한 규칙 제383조"}


def _radar_view(generated_at, minutes_ago):
    observed = datetime.fromisoformat(generated_at) - timedelta(minutes=minutes_ago)
    return {"image": RADAR_IMAGE, "observed_at": observed.isoformat(), "corners": CORNERS}


def _pcp_text(mm):
    """예보 강수량(mm) → 기상청 단기예보 PCP 문자열."""
    if mm < 1:
        return "1mm 미만"
    if mm < 30:
        return f"{round(mm)}.0mm"
    return "30.0~50.0mm" if mm < 50 else "50.0mm 이상"


def _finish(latest):
    now = datetime.fromisoformat(latest["generated_at"])
    latest["sites"] = [finish_site(site, now) for site in latest["sites"]]
    latest["national"] = national_view(latest["sites"], latest["status"]["warnings"] == "ok", now)
    return latest


def _calm(latest):
    """그날 실제 날씨와 무관하게 같은 결과가 나오도록 비·특보·법정을 비운 사본."""
    latest = copy.deepcopy(latest)
    for site in latest["sites"]:
        site.update(warnings=[], legal=[])
        if site["now"]:
            site["now"].update(rain_mm=0.0, pty="없음")
        for hour in site["hourly"]:
            hour.update(rain_mm=0.0, rain_label="0", pty="없음")
    return latest


def build_fixtures(base):
    """상황별 시험 자료(이름 → latest.json 형태 dict)."""
    fixtures = {}

    rain = _calm(base)
    located = [s for s in rain["sites"] if s["now"]]
    for site, mm in zip(located, RAIN_NOW):
        site["now"].update(rain_mm=mm, pty="비")
        for k, hour in enumerate(site["hourly"][:8]):
            hour["rain_mm"], hour["rain_label"] = parse_pcp(_pcp_text(mm / (k + 2)))
            hour.update(pty="비", pop=80)
    located[0]["warnings"] = [dict(HEAVY)]
    located[4]["warnings"] = [dict(PRE)]
    located[5].update(legal=[dict(STOP)], legal_profile=True)
    fixtures["rain"] = _finish(rain)

    failed = copy.deepcopy(base)
    failed["status"]["current"] = "failed"
    failed["observed_at"] = None
    failed["generated_at"] = (datetime.fromisoformat(base["generated_at"]) + timedelta(hours=1)).isoformat()
    for site in failed["sites"]:
        if site["now"]:
            site["state"] = "stale"
    fixtures["failed"] = _finish(failed)

    partial = copy.deepcopy(base)
    partial["status"]["current"] = "partial"
    for site in partial["sites"][1:4]:
        site["state"] = "stale"
    partial["sites"][4].update(state="missing", as_of=None, now=None)
    fixtures["partial"] = _finish(partial)

    night = copy.deepcopy(base)
    day = datetime.fromisoformat(base["generated_at"]).date()
    night["generated_at"] = f"{day.isoformat()}T17:47:30+09:00"
    night["schedule"]["next_run_at"] = f"{(day + timedelta(days=1)).isoformat()}T04:17:00+09:00"
    night["status"]["warnings"] = "failed"
    fixtures["night"] = _finish(night)

    escape = copy.deepcopy(base)
    escape["sites"][0].update(name='오리온 <b>진천</b> & "시험" 현장', short='<i>진천</i> & "시험"')
    fixtures["escape"] = _finish(escape)

    noforecast = copy.deepcopy(base)
    noforecast["status"]["forecast"] = "partial"
    noforecast["sites"][2]["hourly"] = []
    fixtures["noforecast"] = _finish(noforecast)

    onset = _calm(base)
    wet = [s for s in onset["sites"] if s["now"]]
    wet[0]["now"].update(rain_mm=0.0, pty="빗방울")
    wet[1]["now"].update(rain_mm=2.0, pty="비")
    fixtures["onset"] = _finish(onset)

    for latest in fixtures.values():
        latest["radar"] = _radar_view(latest["generated_at"], 10)
        latest["status"]["radar"] = "ok"

    radarold = copy.deepcopy(fixtures["rain"])
    radarold["radar"] = _radar_view(radarold["generated_at"], 120)
    radarold["status"]["radar"] = "failed"
    fixtures["radarold"] = radarold

    noradar = copy.deepcopy(fixtures["rain"])
    noradar["radar"] = None
    noradar["status"]["radar"] = "failed"
    fixtures["noradar"] = noradar

    return fixtures


def _write_radar_png(out_dir):
    """표본 레이더 영상으로 만든 radar.png를 출력 폴더에 쓴다."""
    with Image.open(RADAR_SAMPLE) as img:
        rgb = np.array(img.convert("RGB"))
    overlay = render_overlay(rgb)
    overlay.save(os.path.join(out_dir, "radar.png"), format="PNG")


def main(out_dir=DEFAULT_OUT):
    with open(SOURCE, encoding="utf-8") as f:
        base = json.load(f)
    fixtures = build_fixtures(base)
    os.makedirs(out_dir, exist_ok=True)
    for name, latest in fixtures.items():
        with open(os.path.join(out_dir, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(latest, f, ensure_ascii=False)
    _write_radar_png(out_dir)
    print(f"[시험 자료] {out_dir} ← {', '.join(sorted(fixtures))}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT)

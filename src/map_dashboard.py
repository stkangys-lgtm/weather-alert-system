"""남한 지도(단순화된 SVG 실루엣) 위에 현장을 표시하는 대시보드(정적 HTML) 생성.

지도 경계 데이터 출처: southkorea-maps (KOSTAT 2018 시도 경계, MIT) — src/kr_map_data.json.
Douglas-Peucker로 단순화하고 각 시도의 최대 폴리곤만 남겨(부속 도서 생략) 일러스트풍으로 가공했다.
담당자 이름·연락처 등 개인정보는 포함하지 않는다 (GitHub Pages로 공개 게시되므로).
"""

import json
import math
import os
from html import escape

from src.feels_like import compute_feels_like

LEVEL_COLOR = {"정상": "#2fbf71", "주의": "#f5b400", "경보": "#e63946"}
CATEGORY_ICON = {"건축": "🏗️", "토목": "🚧"}

_DATA_PATH = os.path.join(os.path.dirname(__file__), "kr_map_data.json")
with open(_DATA_PATH, encoding="utf-8") as _f:
    _MAP = json.load(_f)


def _project(lat, lon):
    x = (lon - _MAP["lon_min"]) * _MAP["cos"] * _MAP["scale"] + _MAP["pad"]
    y = (_MAP["lat_max"] - lat) * _MAP["scale"] + _MAP["pad"]
    return round(x, 1), round(y, 1)


def _province_paths_svg():
    parts = []
    for code, info in _MAP["paths"].items():
        parts.append(f'<path class="province" d="{info["d"]}" />')
    return "".join(parts)


_PAGE_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>전사 기상 자동감시 지도</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>%F0%9F%97%BA</text></svg>">
<style>
  :root {{ --bg:#eef3fa; --ink:#1b1f27; --sub:#6b7280; --line: rgba(15,23,42,0.07); }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: -apple-system, "Segoe UI", "Malgun Gothic", sans-serif;
  }}
  .hero {{
    background: linear-gradient(135deg, #16223f 0%, #1f3a68 55%, #2f5a9e 100%);
    color: #fff; padding: 28px 24px 40px;
  }}
  .hero-inner {{ max-width: 1180px; margin: 0 auto; }}
  .hero-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }}
  .hero h1 {{ font-size: 1.5rem; margin: 0 0 6px; letter-spacing: -0.02em; }}
  .hero .updated {{ color: rgba(255,255,255,0.72); font-size: 0.85rem; }}
  .hero a.navlink {{ color: #fff; background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.3);
    padding: 8px 14px; border-radius: 10px; text-decoration: none; font-size: 0.85rem; white-space: nowrap; }}
  .hero a.navlink:hover {{ background: rgba(255,255,255,0.26); }}
  .stats {{ display: flex; gap: 12px; margin-top: 18px; flex-wrap: wrap; }}
  .stat {{
    flex: 1; min-width: 120px; background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.18); border-radius: 14px; padding: 12px 16px;
  }}
  .stat .num {{ font-size: 1.4rem; font-weight: 700; line-height: 1.1; }}
  .stat .lbl {{ font-size: 0.8rem; color: rgba(255,255,255,0.75); margin-top: 2px; }}
  .stat.hi-경보 .num {{ color: #ff8a8a; }}
  .stat.hi-주의 .num {{ color: #ffd670; }}
  .stat.hi-정상 .num {{ color: #8fe3b5; }}

  .content {{ max-width: 1180px; margin: -22px auto 40px; padding: 0 24px; }}
  .panel {{
    background: #fff; border-radius: 18px; box-shadow: 0 6px 24px rgba(15,23,42,0.08);
    border: 1px solid var(--line); overflow: hidden;
  }}
  .toolbar {{
    display: flex; gap: 10px; align-items: center; padding: 14px 18px; flex-wrap: wrap;
    border-bottom: 1px solid var(--line);
  }}
  .chip {{
    padding: 7px 14px; border-radius: 999px; border: 1px solid var(--line); cursor: pointer;
    font-size: 0.85rem; font-weight: 600; background: #f7f8fb; color: var(--sub); user-select: none;
  }}
  .chip.active {{ background: #1f3a68; color: #fff; border-color: #1f3a68; }}
  .legend {{ margin-left: auto; display: flex; gap: 14px; font-size: 0.8rem; color: var(--sub); }}
  .legend .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }}

  .map-wrap {{ position: relative; display: flex; justify-content: center; padding: 18px; background: #f4f8fd; }}
  svg.kr-map {{ width: 100%; max-width: 460px; height: auto; display: block; }}
  .province {{ fill: #dbe6f5; stroke: #ffffff; stroke-width: 1.6; }}
  .site {{ cursor: pointer; stroke: #fff; stroke-width: 2; transition: r 0.12s ease; }}
  .site:hover {{ stroke-width: 3; }}
  .site.selected {{ r: 12; stroke: #16223f; }}

  .detail {{
    position: absolute; bottom: 18px; left: 18px; right: 18px; max-width: 340px;
    background: #fff; border-radius: 14px; box-shadow: 0 10px 30px rgba(15,23,42,0.18);
    border: 1px solid var(--line); padding: 16px 18px; display: none;
  }}
  .detail.show {{ display: block; }}
  .detail .close {{ float: right; cursor: pointer; color: var(--sub); font-size: 1.1rem; line-height: 1; }}
  .detail h3 {{ margin: 0 0 4px; font-size: 1.05rem; }}
  .detail .badge {{
    display: inline-flex; padding: 2px 10px; border-radius: 999px; font-size: 0.76rem; font-weight: 700;
    margin-bottom: 8px;
  }}
  .detail .metrics {{ display: flex; gap: 14px; font-size: 0.85rem; color: var(--sub); margin-bottom: 6px; }}
  .detail .metrics span.v {{ color: var(--ink); font-weight: 600; }}
  .detail .reasons {{ font-size: 0.82rem; font-weight: 600; }}

  footer {{ max-width: 1180px; margin: 0 auto 30px; padding: 0 24px; color: #98a2b3; font-size: 0.78rem; }}

  @media (max-width: 480px) {{
    .hero {{ padding: 24px 16px 36px; }}
    .content {{ padding: 0 14px; }}
    .detail {{ left: 12px; right: 12px; max-width: none; }}
  }}
</style>
</head>
<body>
  <div class="hero">
    <div class="hero-inner">
      <div class="hero-top">
        <div>
          <h1>🗺️ 현장 기상 지도</h1>
          <div class="updated">최종 갱신 {updated}</div>
        </div>
        <a class="navlink" href="index.html">📋 목록으로 보기</a>
      </div>
      <div class="stats">
        <div class="stat hi-경보"><div class="num">{count_경보}</div><div class="lbl">🚨 경보</div></div>
        <div class="stat hi-주의"><div class="num">{count_주의}</div><div class="lbl">⚠️ 주의</div></div>
        <div class="stat hi-정상"><div class="num">{count_정상}</div><div class="lbl">✅ 정상</div></div>
      </div>
    </div>
  </div>

  <div class="content">
    <div class="panel">
      <div class="toolbar">
        <div class="chip active" data-cat="all" onclick="setCategory('all', this)">전체 {total}</div>
        <div class="chip" data-cat="건축" onclick="setCategory('건축', this)">🏗️ 건축 {count_건축}</div>
        <div class="chip" data-cat="토목" onclick="setCategory('토목', this)">🚧 토목 {count_토목}</div>
        <div class="legend">
          <span><span class="dot" style="background:#2fbf71"></span>정상</span>
          <span><span class="dot" style="background:#f5b400"></span>주의</span>
          <span><span class="dot" style="background:#e63946"></span>경보</span>
        </div>
      </div>
      <div class="map-wrap">
        <svg class="kr-map" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
          {province_paths}
          {markers}
        </svg>
        <div class="detail" id="detail"></div>
      </div>
    </div>
  </div>
  <footer>기상청 공공데이터포털(단기예보 2.0) 기반 · 지도 경계: KOSTAT/southkorea-maps · 담당자 정보는 비공개 처리됨</footer>

  <script>
    const SITES = {sites_json};
    const LEVEL_COLOR = {{"정상": "#2fbf71", "주의": "#f5b400", "경보": "#e63946"}};
    let activeCategory = 'all';
    let selectedIdx = null;

    function setCategory(cat, el) {{
      activeCategory = cat;
      document.querySelectorAll('.toolbar .chip').forEach(c => c.classList.remove('active'));
      el.classList.add('active');
      document.querySelectorAll('.site').forEach(m => {{
        const show = cat === 'all' || m.dataset.category === cat;
        m.style.display = show ? '' : 'none';
      }});
      closeDetail();
    }}

    function showDetail(idx) {{
      const s = SITES[idx];
      document.querySelectorAll('.site').forEach(m => m.classList.remove('selected'));
      document.querySelector('.site[data-idx="' + idx + '"]').classList.add('selected');
      const color = LEVEL_COLOR[s.level];
      const reasonHtml = s.reasons.length ? '<div class="reasons" style="color:' + color + '">' + s.reasons.join(', ') + '</div>' : '';
      document.getElementById('detail').innerHTML =
        '<span class="close" onclick="closeDetail()">✕</span>' +
        '<span class="badge" style="background:' + color + '22;color:' + color + '">' + s.level + ' · ' + s.category + '</span>' +
        '<h3>' + s.site_name + '</h3>' +
        '<div class="metrics">' +
          '<div>🌡 <span class="v">' + s.temp + '°C</span></div>' +
          (s.feels !== null ? '<div>🤔 체감 <span class="v">' + s.feels + '°C</span></div>' : '') +
          '<div>💨 <span class="v">' + s.wsd + 'm/s</span></div>' +
          '<div>💧 <span class="v">' + s.rn1 + 'mm</span></div>' +
        '</div>' + reasonHtml;
      document.getElementById('detail').classList.add('show');
    }}

    function closeDetail() {{
      document.getElementById('detail').classList.remove('show');
      document.querySelectorAll('.site').forEach(m => m.classList.remove('selected'));
      selectedIdx = null;
    }}
  </script>
</body>
</html>
"""


def build_map_html(updated_str, site_rows):
    """site_rows: [{"site_name", "category", "lat", "lon", "current", "level", "reasons"}, ...]"""
    counts = {"건축": 0, "토목": 0}
    sites_payload = []
    marker_svgs = []
    for i, row in enumerate(site_rows):
        counts[row["category"]] = counts.get(row["category"], 0) + 1
        current = row["current"] or {}
        x, y = _project(row["lat"], row["lon"])
        color = LEVEL_COLOR[row["level"]]
        marker_svgs.append(
            f'<circle class="site" data-idx="{i}" data-category="{escape(row["category"])}" '
            f'cx="{x}" cy="{y}" r="8" fill="{color}" onclick="showDetail({i})">'
            f'<title>{escape(row["site_name"])} ({escape(row["level"])})</title></circle>'
        )
        sites_payload.append({
            "site_name": row["site_name"],
            "category": row["category"],
            "level": row["level"],
            "reasons": row["reasons"],
            "temp": current.get("T1H", "-"),
            "feels": compute_feels_like(current.get("T1H"), current.get("REH"), current.get("WSD")),
            "wsd": current.get("WSD", "-"),
            "rn1": current.get("RN1", "-"),
        })

    return _PAGE_TEMPLATE.format(
        updated=escape(updated_str),
        total=len(site_rows),
        count_건축=counts.get("건축", 0),
        count_토목=counts.get("토목", 0),
        count_경보=sum(1 for r in site_rows if r["level"] == "경보"),
        count_주의=sum(1 for r in site_rows if r["level"] == "주의"),
        count_정상=sum(1 for r in site_rows if r["level"] == "정상"),
        width=_MAP["width"],
        height=_MAP["height"],
        province_paths=_province_paths_svg(),
        markers="".join(marker_svgs),
        sites_json=json.dumps(sites_payload, ensure_ascii=False),
    )

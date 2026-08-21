"""현장 기상현황 대시보드(정적 HTML) 생성.

담당자 이름·연락처 등 개인정보는 포함하지 않는다 (GitHub Pages로 공개 게시되므로).
"""

from html import escape

LEVEL_STYLE = {
    "정상": {"bg": "#eafaf1", "fg": "#1a7d4e", "bar": "#2fbf71", "icon": "✅"},
    "주의": {"bg": "#fff6e0", "fg": "#9a6b00", "bar": "#f5b400", "icon": "⚠️"},
    "경보": {"bg": "#fdeaea", "fg": "#c62828", "bar": "#e63946", "icon": "🚨"},
}

SKY_ICON = {"맑음": "☀️", "구름많음": "⛅", "흐림": "☁️"}
PTY_ICON = {"비": "🌧️", "비/눈": "🌨️", "눈": "❄️", "빗방울": "🌦️", "빗방울눈날림": "🌨️", "눈날림": "🌨️"}


def _weather_icon(sky, pty):
    if pty and pty not in ("없음", "", "-"):
        return PTY_ICON.get(pty, "🌧️")
    return SKY_ICON.get(sky, "🌤️")


_PAGE_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>전사 기상 자동감시 대시보드</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>%E2%9B%85</text></svg>">
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="stylesheet" as="style" crossorigin
  href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>
  :root {{
    --bg: #f2f4f8; --card: #ffffff; --ink: #1b1f27; --sub: #6b7280;
    --line: rgba(15,23,42,0.07);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: "Pretendard", -apple-system, "Segoe UI", "Malgun Gothic", sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .hero {{
    background: linear-gradient(135deg, #16223f 0%, #1f3a68 55%, #2f5a9e 100%);
    color: #fff; padding: 36px 24px 48px;
  }}
  .hero-inner {{ max-width: 1180px; margin: 0 auto; }}
  .hero-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }}
  .hero h1 {{ font-size: 1.7rem; margin: 0 0 6px; letter-spacing: -0.02em; }}
  .hero .updated {{ color: rgba(255,255,255,0.72); font-size: 0.88rem; }}
  .hero a.navlink {{ color: #fff; background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.3);
    padding: 8px 14px; border-radius: 10px; text-decoration: none; font-size: 0.85rem; white-space: nowrap; }}
  .hero a.navlink:hover {{ background: rgba(255,255,255,0.26); }}
  .stats {{ display: flex; gap: 12px; margin-top: 22px; flex-wrap: wrap; }}
  .stat {{
    flex: 1; min-width: 140px; background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.18); border-radius: 14px; padding: 14px 18px;
    backdrop-filter: blur(6px);
  }}
  .stat .num {{ font-size: 1.6rem; font-weight: 700; line-height: 1.1; }}
  .stat .lbl {{ font-size: 0.82rem; color: rgba(255,255,255,0.75); margin-top: 2px; }}
  .stat.hi-경보 .num {{ color: #ff8a8a; }}
  .stat.hi-주의 .num {{ color: #ffd670; }}
  .stat.hi-정상 .num {{ color: #8fe3b5; }}

  .content {{ max-width: 1180px; margin: -26px auto 40px; padding: 0 24px; }}
  .toolbar {{
    background: var(--card); border-radius: 14px; box-shadow: 0 6px 24px rgba(15,23,42,0.08);
    padding: 12px 16px; margin-bottom: 18px; display: flex; gap: 10px; align-items: center;
  }}
  .toolbar input {{
    flex: 1; border: 1px solid var(--line); border-radius: 10px; padding: 9px 12px;
    font-size: 0.92rem; font-family: inherit; outline: none;
  }}
  .toolbar input:focus {{ border-color: #2f5a9e; }}
  .toolbar .count {{ color: var(--sub); font-size: 0.82rem; white-space: nowrap; }}
  .toolbar .chip {{
    padding: 8px 14px; border-radius: 999px; border: 1px solid var(--line); cursor: pointer;
    font-size: 0.85rem; font-weight: 600; background: #f7f8fb; color: var(--sub); white-space: nowrap;
  }}
  .toolbar .chip.active {{ background: #1f3a68; color: #fff; border-color: #1f3a68; }}

  .grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 16px;
  }}
  .card {{
    background: var(--card); border-radius: 16px; overflow: hidden;
    box-shadow: 0 4px 16px rgba(15,23,42,0.07); border: 1px solid var(--line);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }}
  .card:hover {{ transform: translateY(-3px); box-shadow: 0 10px 28px rgba(15,23,42,0.12); }}
  .card .bar {{ height: 5px; }}
  .card .body {{ padding: 18px 18px 16px; }}
  .card-top {{ display: flex; justify-content: space-between; align-items: flex-start; }}
  .card h2 {{ font-size: 1.08rem; margin: 2px 0 0; line-height: 1.35; }}
  .cat-tag {{ font-size: 0.72rem; font-weight: 700; color: var(--sub); }}
  .badge {{
    display: inline-flex; align-items: center; gap: 4px; padding: 3px 11px; border-radius: 999px;
    font-size: 0.76rem; font-weight: 700; white-space: nowrap; margin-left: 8px;
  }}
  .now {{ display: flex; align-items: center; gap: 12px; margin: 14px 0 10px; }}
  .now .icon {{ font-size: 2.4rem; line-height: 1; }}
  .now .temp {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; }}
  .metrics {{ display: flex; gap: 16px; color: var(--sub); font-size: 0.82rem; margin-bottom: 4px; }}
  .metrics span.v {{ color: var(--ink); font-weight: 600; }}
  .reasons {{
    margin-top: 10px; font-size: 0.82rem; font-weight: 600; padding: 8px 10px; border-radius: 8px;
  }}
  .forecast {{ display: flex; gap: 8px; overflow-x: auto; margin-top: 14px; padding-bottom: 2px; }}
  .fc {{
    flex: 0 0 auto; text-align: center; background: #f7f8fb; border-radius: 10px;
    padding: 8px 10px; min-width: 52px; font-size: 0.75rem; color: var(--sub);
  }}
  .fc .fc-icon {{ font-size: 1.15rem; margin: 3px 0; }}
  .fc .fc-temp {{ color: var(--ink); font-weight: 700; font-size: 0.82rem; }}
  footer {{ max-width: 1180px; margin: 0 auto 30px; padding: 0 24px; color: #98a2b3; font-size: 0.78rem; }}

  @media (max-width: 480px) {{
    .hero {{ padding: 28px 16px 42px; }}
    .content {{ padding: 0 14px; }}
  }}
</style>
</head>
<body>
  <div class="hero">
    <div class="hero-inner">
      <div class="hero-top">
        <div>
          <h1>⛅ 전사 기상 자동감시 대시보드</h1>
          <div class="updated">최종 갱신 {updated} · 기상청 단기예보 2.0 기반</div>
        </div>
        <a class="navlink" href="map.html">🗺️ 지도로 보기</a>
      </div>
      <div class="stats">
        <div class="stat hi-경보"><div class="num">{count_경보}</div><div class="lbl">🚨 경보</div></div>
        <div class="stat hi-주의"><div class="num">{count_주의}</div><div class="lbl">⚠️ 주의</div></div>
        <div class="stat hi-정상"><div class="num">{count_정상}</div><div class="lbl">✅ 정상</div></div>
      </div>
    </div>
  </div>
  <div class="content">
    <div class="toolbar">
      <div class="chip active" data-cat="all" onclick="setCategory('all', this)">전체</div>
      <div class="chip" data-cat="건축" onclick="setCategory('건축', this)">🏗️ 건축</div>
      <div class="chip" data-cat="토목" onclick="setCategory('토목', this)">🚧 토목</div>
      <input id="filter" type="text" placeholder="현장명 검색..." oninput="filterCards()">
      <div class="count" id="filterCount"></div>
    </div>
    <div class="grid" id="grid">
      {cards}
    </div>
  </div>
  <footer>기상청 공공데이터포털(단기예보 2.0) 기반 · 담당자 정보는 비공개 처리됨</footer>
  <script>
    let activeCategory = 'all';

    function setCategory(cat, el) {{
      activeCategory = cat;
      document.querySelectorAll('.toolbar .chip').forEach(c => c.classList.remove('active'));
      el.classList.add('active');
      filterCards();
    }}

    function filterCards() {{
      const q = document.getElementById('filter').value.trim().toLowerCase();
      const cards = document.querySelectorAll('#grid .card');
      let shown = 0;
      cards.forEach(c => {{
        const matchText = c.dataset.name.includes(q);
        const matchCat = activeCategory === 'all' || c.dataset.category === activeCategory;
        const show = matchText && matchCat;
        c.style.display = show ? '' : 'none';
        if (show) shown++;
      }});
      document.getElementById('filterCount').textContent = shown + '개 현장';
    }}
    filterCards();
  </script>
</body>
</html>
"""


def _forecast_chips(forecast, limit=6):
    chips = []
    for f in forecast[:limit]:
        time_label = f.get("fcst_time", "")[:2] + "시"
        icon = _weather_icon(f.get("SKY"), f.get("PTY"))
        chips.append(
            f'<div class="fc"><div>{escape(time_label)}</div>'
            f'<div class="fc-icon">{icon}</div>'
            f'<div class="fc-temp">{escape(str(f.get("TMP", "-")))}°</div>'
            f'<div>💧{escape(str(f.get("POP", "-")))}%</div></div>'
        )
    return "".join(chips)


CATEGORY_ICON = {"건축": "🏗️", "토목": "🚧"}


def _card(site_name, category, current, forecast, level, reasons):
    style = LEVEL_STYLE[level]
    icon = _weather_icon(None, current.get("PTY"))
    reasons_html = ""
    if reasons:
        reasons_html = (
            f'<div class="reasons" style="background:{style["bg"]};color:{style["fg"]}">'
            f'{escape(", ".join(reasons))}</div>'
        )
    forecast_html = ""
    if forecast:
        forecast_html = f'<div class="forecast">{_forecast_chips(forecast)}</div>'

    temp = current.get("T1H", "-")
    wsd = current.get("WSD", "-")
    rn1 = current.get("RN1", "-")
    reh = current.get("REH", "-")

    cat_icon = CATEGORY_ICON.get(category, "")

    return f"""
    <div class="card" data-name="{escape(site_name.lower())}" data-category="{escape(category)}">
      <div class="bar" style="background:{style['bar']}"></div>
      <div class="body">
        <div class="card-top">
          <div><span class="cat-tag">{cat_icon} {escape(category)}</span><h2>{escape(site_name)}</h2></div>
          <span class="badge" style="background:{style['bg']};color:{style['fg']}">{style['icon']} {escape(level)}</span>
        </div>
        <div class="now">
          <div class="icon">{icon}</div>
          <div class="temp">{escape(str(temp))}°C</div>
        </div>
        <div class="metrics">
          <div>💨 <span class="v">{escape(str(wsd))}m/s</span></div>
          <div>💧 <span class="v">{escape(str(rn1))}mm</span></div>
          <div>💦 <span class="v">{escape(str(reh))}%</span></div>
        </div>
        {reasons_html}
        {forecast_html}
      </div>
    </div>"""


def build_dashboard_html(updated_str, site_rows):
    """site_rows: [{"site_name", "current": dict, "forecast": list, "level": str, "reasons": list}, ...]"""
    severity = {"경보": 2, "주의": 1, "정상": 0}
    ordered = sorted(site_rows, key=lambda r: severity[r["level"]], reverse=True)

    counts = {"경보": 0, "주의": 0, "정상": 0}
    for row in site_rows:
        counts[row["level"]] += 1

    cards = "".join(
        _card(row["site_name"], row["category"], row["current"], row["forecast"], row["level"], row["reasons"])
        for row in ordered
    )

    return _PAGE_TEMPLATE.format(
        updated=escape(updated_str),
        count_경보=counts["경보"],
        count_주의=counts["주의"],
        count_정상=counts["정상"],
        cards=cards,
    )

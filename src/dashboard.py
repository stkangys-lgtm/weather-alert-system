"""현장 기상현황 대시보드(정적 HTML) 생성.

담당자 이름·연락처 등 개인정보는 포함하지 않는다 (GitHub Pages로 공개 게시되므로).
"""

from html import escape

from src.feels_like import compute_feels_like

LEVEL_STYLE = {
    "정상": {"bg": "#eafaf1", "fg": "#1a7d4e", "bar": "#2fbf71", "icon": "✅"},
    "주의": {"bg": "#fff6e0", "fg": "#9a6b00", "bar": "#f5b400", "icon": "⚠️"},
    "경보": {"bg": "#fdeaea", "fg": "#c62828", "bar": "#e63946", "icon": "🚨"},
    "데이터없음": {"bg": "#eef0f3", "fg": "#5b6470", "bar": "#9aa4b2", "icon": "❔"},
}

LEVEL_LABEL = {"정상": "정상", "주의": "선제주의", "경보": "선제경계", "데이터없음": "데이터없음"}

SKY_ICON = {"맑음": "☀️", "구름많음": "⛅", "흐림": "☁️"}
PTY_ICON = {"비": "🌧️", "비/눈": "🌨️", "눈": "❄️", "빗방울": "🌦️", "빗방울눈날림": "🌨️", "눈날림": "🌨️"}
# 중기예보 하늘상태(문자)용 아이콘 매핑
MID_SKY_ICON = {
    "맑음": "☀️", "구름많음": "⛅", "구름많고 비": "🌧️", "구름많고 눈": "🌨️", "구름많고 비/눈": "🌨️",
    "구름많고 소나기": "🌦️", "흐림": "☁️", "흐리고 비": "🌧️", "흐리고 눈": "🌨️",
    "흐리고 비/눈": "🌨️", "흐리고 소나기": "🌦️",
}
EVENT_ICON = {"폭염": "🥵", "폭염주의": "🥵", "강수": "🌧️", "강풍": "💨", "강풍주의": "💨", "한파": "🥶"}


def _weather_icon(sky, pty):
    if pty and pty not in ("없음", "", "-"):
        return PTY_ICON.get(pty, "🌧️")
    return SKY_ICON.get(sky, "🌤️")


def _mid_sky_icon(sky_text):
    if not sky_text:
        return "❔"
    return MID_SKY_ICON.get(sky_text, SKY_ICON.get(sky_text, "🌤️"))


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
    --bg: #edf3f0; --card: #ffffff; --ink: #10231d; --sub: #66756f;
    --line: rgba(15,23,42,0.07);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: "Pretendard", -apple-system, "Segoe UI", "Malgun Gothic", sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .hero {{
    background: linear-gradient(120deg, #003b2d 0%, #005b3c 58%, #009a44 100%);
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
  .stat.hi-데이터없음 .num {{ color: #c7ccd4; }}
  .stat.hi-법정 .num {{ color: #ff9aa5; }}
  .stat.hi-특보 .num {{ color: #ffcf70; }}

  .content {{ max-width: 1180px; margin: -26px auto 40px; padding: 0 24px; }}
  .toolbar {{
    background: var(--card); border-radius: 14px; box-shadow: 0 6px 24px rgba(15,23,42,0.08);
    padding: 12px 16px; margin-bottom: 18px; display: flex; gap: 10px; align-items: center;
  }}
  .toolbar input {{
    flex: 1; border: 1px solid var(--line); border-radius: 10px; padding: 9px 12px;
    font-size: 0.92rem; font-family: inherit; outline: none;
  }}
  .toolbar input:focus {{ border-color: #009a44; box-shadow: 0 0 0 3px rgba(0,154,68,.1); }}
  .toolbar .count {{ color: var(--sub); font-size: 0.82rem; white-space: nowrap; }}
  .toolbar .chip {{
    padding: 8px 14px; border-radius: 999px; border: 1px solid var(--line); cursor: pointer;
    font-size: 0.85rem; font-weight: 600; background: #f7f8fb; color: var(--sub); white-space: nowrap;
  }}
  .toolbar .chip.active {{ background: #003b2d; color: #fff; border-color: #003b2d; }}

  .system-status {{
    background: #fff; border: 1px solid var(--line); border-radius: 14px; margin-bottom: 14px;
    padding: 13px 16px; box-shadow: 0 4px 16px rgba(15,23,42,0.05);
    display: flex; align-items: center; gap: 10px; font-size: 0.86rem;
  }}
  .system-status .status-dot {{ width: 10px; height: 10px; border-radius: 50%; background: #2fbf71; flex: 0 0 auto; }}
  .system-status.delayed {{ background: #fff8e7; color: #7a5700; border-color: #f1cf72; }}
  .system-status.delayed .status-dot {{ background: #f5b400; }}
  .system-status.outage {{ background: #fff0f0; color: #9f2020; border-color: #efb0b0; }}
  .system-status.outage .status-dot {{ background: #e63946; }}
  .system-status strong {{ margin-right: 4px; }}
  .system-status .age {{ margin-left: auto; color: var(--sub); white-space: nowrap; }}

  .changes {{
    background: #fff; border: 1px solid var(--line); border-radius: 14px; margin-bottom: 14px;
    padding: 15px 16px; box-shadow: 0 4px 16px rgba(15,23,42,0.05);
  }}
  .changes-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 8px; }}
  .changes h2 {{ font-size: 0.95rem; margin: 0; }}
  .changes time {{ font-size: 0.76rem; color: var(--sub); }}
  .change-list {{ display: flex; gap: 7px; overflow-x: auto; padding-bottom: 2px; }}
  .change-item {{
    flex: 0 0 auto; border-radius: 10px; padding: 8px 11px; background: #f6f8fb;
    font-size: 0.78rem; color: var(--sub); border: 1px solid var(--line);
  }}
  .change-item strong {{ display: block; color: var(--ink); margin-bottom: 2px; }}

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
  .now .feels {{ font-size: 0.78rem; color: var(--sub); margin-top: -2px; }}
  .metrics {{ display: flex; gap: 16px; color: var(--sub); font-size: 0.82rem; margin-bottom: 4px; }}
  .metrics span.v {{ color: var(--ink); font-weight: 600; }}
  .reasons {{
    margin-top: 10px; font-size: 0.82rem; font-weight: 600; padding: 8px 10px; border-radius: 8px;
  }}
  .legal-signals {{ display: grid; gap: 7px; margin-top: 10px; }}
  .legal-signal {{ padding: 10px 11px; border-radius: 10px; background: #f3f7f5;
    border: 1px solid rgba(0,91,60,.14); font-size: 0.78rem; line-height: 1.45; }}
  .legal-signal.action {{ background: #fff3f3; border-color: #f3c2c7; }}
  .legal-signal.verify {{ background: #fff8e7; border-color: #f0d598; }}
  .legal-signal .legal-head {{ display:flex; justify-content:space-between; gap:8px; font-weight:750; }}
  .legal-signal .article {{ color:var(--sub); white-space:nowrap; font-size:.7rem; }}
  .legal-signal p {{ margin:4px 0 0; color:var(--sub); }}
  .weather-warnings {{ display:grid; gap:7px; margin-top:10px; }}
  .weather-warning {{ padding:10px 11px; border-radius:10px; background:#fff2e4;
    border:1px solid #efc27f; color:#764700; font-size:.78rem; line-height:1.45; }}
  .weather-warning strong {{ display:block; color:#9a4800; }}
  .forecast {{ display: flex; gap: 8px; overflow-x: auto; margin-top: 14px; padding-bottom: 2px; }}
  .fc {{
    flex: 0 0 auto; text-align: center; background: #f7f8fb; border-radius: 10px;
    padding: 8px 10px; min-width: 52px; font-size: 0.75rem; color: var(--sub);
  }}
  .fc .fc-icon {{ font-size: 1.15rem; margin: 3px 0; }}
  .fc .fc-temp {{ color: var(--ink); font-weight: 700; font-size: 0.82rem; }}
  .section-label {{ font-size: 0.72rem; color: var(--sub); font-weight: 700; margin: 14px 0 6px; letter-spacing: 0.02em; }}
  .weekly {{ display: flex; gap: 6px; overflow-x: auto; padding-bottom: 2px; }}
  .wk {{
    flex: 0 0 auto; text-align: center; background: linear-gradient(180deg, #f5f7fb, #eef2f8);
    border-radius: 10px; padding: 8px 8px; min-width: 54px; font-size: 0.72rem; color: var(--sub);
  }}
  .wk .wk-day {{ font-weight: 700; color: var(--ink); }}
  .wk .wk-icon {{ font-size: 1.15rem; margin: 3px 0; }}
  .wk .wk-tmp {{ color: var(--ink); font-weight: 700; font-size: 0.78rem; }}
  .wk .wk-tmp .lo {{ color: #3b82f6; }} .wk .wk-tmp .hi {{ color: #e63946; }}
  .events {{ margin-top: 10px; font-size: 0.78rem; }}
  .events .ev {{
    display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px; border-radius: 999px;
    background: #fff3f3; color: #a61b1b; margin: 3px 3px 0 0; font-weight: 600;
  }}
  footer {{ max-width: 1180px; margin: 0 auto 30px; padding: 0 24px; color: #98a2b3; font-size: 0.78rem; }}

  @media (max-width: 480px) {{
    .hero {{ padding: 28px 16px 42px; }}
    .content {{ padding: 0 14px; }}
    .system-status {{ align-items: flex-start; flex-wrap: wrap; }}
    .system-status .age {{ width: 100%; margin-left: 20px; }}
  }}
</style>
</head>
<body>
  <div class="hero">
    <div class="hero-inner">
      <div class="hero-top">
        <div>
          <h1>전 현장 기상 대시보드</h1>
          <div class="updated">최종 갱신 {updated} · 기상청 단기예보 2.0 기반</div>
        </div>
        <a class="navlink" href="index.html">← 지도 관제로 돌아가기</a>
      </div>
      <div class="stats">
        <div class="stat hi-특보"><div class="num">{count_특보}</div><div class="lbl">📢 기상특보</div></div>
        <div class="stat hi-법정"><div class="num">{count_법정}</div><div class="lbl">⚖️ 법정조치</div></div>
        <div class="stat hi-경보"><div class="num">{count_경보}</div><div class="lbl">🚨 선제경계</div></div>
        <div class="stat hi-주의"><div class="num">{count_주의}</div><div class="lbl">⚠️ 선제주의</div></div>
        <div class="stat hi-정상"><div class="num">{count_정상}</div><div class="lbl">✅ 정상</div></div>
        <div class="stat hi-데이터없음"><div class="num">{count_데이터없음}</div><div class="lbl">❔ 데이터없음</div></div>
      </div>
    </div>
  </div>
  <div class="content">
    <div class="system-status" id="systemStatus" data-generated-at="{generated_at_iso}"
         data-missing-sites="{missing_site_count}" data-total-sites="{total_site_count}">
      <span class="status-dot"></span>
      <span id="statusMessage"><strong>정상 수집</strong> 최신 기상자료를 표시하고 있습니다.</span>
      <span class="age" id="dataAge">갱신시각 확인 중</span>
    </div>
    {changes_html}
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
  <footer>기상청 공공데이터포털(단기예보 2.0·기상특보 조회서비스) 기반 · 담당자 정보는 비공개 처리됨</footer>
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

    function updateFreshness() {{
      const box = document.getElementById('systemStatus');
      const generated = new Date(box.dataset.generatedAt);
      if (Number.isNaN(generated.getTime())) return;
      const ageMinutes = Math.max(0, Math.floor((Date.now() - generated.getTime()) / 60000));
      const missingSites = Number(box.dataset.missingSites || 0);
      const totalSites = Number(box.dataset.totalSites || 0);
      const message = document.getElementById('statusMessage');
      box.classList.remove('delayed', 'outage');
      if (totalSites > 0 && missingSites >= totalSites) {{
        box.classList.add('outage');
        message.innerHTML = '<strong>전체 수집 실패</strong> 모든 현장의 기상자료를 받지 못했습니다. 별도 확인이 필요합니다.';
      }} else if (ageMinutes >= 70) {{
        box.classList.add('outage');
        message.innerHTML = '<strong>수집 장애 가능</strong> 70분 이상 새 자료가 없습니다. 현장 기상상황을 별도로 확인해 주세요.';
      }} else if (missingSites > 0) {{
        box.classList.add('delayed');
        message.innerHTML = '<strong>일부 수집 실패</strong> ' + missingSites + '개 현장의 자료를 받지 못했습니다.';
      }} else if (ageMinutes >= 40) {{
        box.classList.add('delayed');
        message.innerHTML = '<strong>갱신 지연</strong> 표시 정보가 최신이 아닐 수 있습니다.';
      }} else {{
        message.innerHTML = '<strong>정상 수집</strong> 최신 기상자료를 표시하고 있습니다.';
      }}
      document.getElementById('dataAge').textContent = ageMinutes + '분 전 갱신';
    }}
    filterCards();
    updateFreshness();
    setInterval(updateFreshness, 60000);
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


def _weekly_chips(mid_forecast):
    """중기예보(3~10일) 리스트를 요일별 칩 HTML로 변환."""
    from datetime import datetime
    chips = []
    for entry in mid_forecast:
        try:
            d = datetime.strptime(entry["date"], "%Y-%m-%d")
            day_label = "월화수목금토일"[d.weekday()]
            date_label = f"{d.month}/{d.day}"
        except Exception:
            day_label, date_label = "", entry.get("date", "")
        sky = entry.get("sky_pm") or entry.get("sky_am") or ""
        icon = _mid_sky_icon(sky)
        ta_min = entry.get("ta_min")
        ta_max = entry.get("ta_max")
        temp_html = ""
        if ta_min is not None and ta_max is not None:
            temp_html = f'<div class="wk-tmp"><span class="lo">{ta_min}°</span>/<span class="hi">{ta_max}°</span></div>'
        pop = entry.get("pop_pm") or entry.get("pop_am") or "-"
        chips.append(
            f'<div class="wk"><div class="wk-day">{escape(day_label)}</div>'
            f'<div>{escape(date_label)}</div>'
            f'<div class="wk-icon">{icon}</div>'
            f'{temp_html}'
            f'<div>💧{escape(str(pop))}%</div></div>'
        )
    return "".join(chips)


def _events_html(events):
    if not events:
        return ""
    chips = []
    for ev in events:
        icon = EVENT_ICON.get(ev["kind"], "⚠️")
        chips.append(f'<span class="ev">{icon} {escape(ev["date"])} {escape(ev["kind"])}</span>')
    return f'<div class="section-label">향후 10일 특이사항</div><div class="events">{"".join(chips)}</div>'


CATEGORY_ICON = {"건축": "🏗️", "토목": "🚧"}


def _legal_signals_html(signals):
    if not signals:
        return ""
    items = []
    for signal in signals:
        status = signal.get("status", "현장 확인 필요")
        css_class = "action" if status in ("법정 작업중지", "법정 조치 이행 필요") else "verify"
        items.append(
            f'<div class="legal-signal {css_class}">'
            f'<div class="legal-head"><span>{escape(status)} · {escape(signal.get("title", ""))}</span>'
            f'<span class="article">{escape(signal.get("article", ""))}</span></div>'
            f'<p>{escape(signal.get("reason", ""))}</p></div>'
        )
    return '<div class="section-label">법정 조치·현장 확인</div><div class="legal-signals">' + "".join(items) + "</div>"


def _warnings_html(warnings, available=True):
    if not available:
        return (
            '<div class="section-label">기상청 공식 발표</div>'
            '<div class="weather-warnings"><div class="weather-warning">'
            '<strong>❔ 특보 수신 실패</strong>기상청 특보를 별도로 확인해 주세요.</div></div>'
        )
    if not warnings:
        return ""
    items = []
    for warning in warnings:
        areas = warning.get("matched_areas") or warning.get("areas") or []
        area_text = ", ".join(areas)
        kind = "예비특보" if warning.get("kind") == "예비특보" else "기상특보"
        items.append(
            f'<div class="weather-warning"><strong>📢 {escape(kind)} · '
            f'{escape(warning.get("title", "-"))}</strong>{escape(area_text)}</div>'
        )
    return '<div class="section-label">기상청 공식 발표</div><div class="weather-warnings">' + "".join(items) + "</div>"


def _card(
    site_name, category, current, forecast, mid_forecast, events, level, reasons,
    legal_signals=None, weather_warnings=None, display_level=None, weather_warnings_available=True,
):
    display_level = display_level or level
    style = LEVEL_STYLE[display_level]
    icon = _weather_icon(None, current.get("PTY"))
    reasons_html = ""
    if reasons:
        reasons_html = (
            f'<div class="reasons" style="background:{style["bg"]};color:{style["fg"]}">'
            f'{escape(", ".join(reasons))}</div>'
        )
    forecast_html = ""
    if forecast:
        forecast_html = (
            f'<div class="section-label">단기 예보 (3일 이내, 시간별)</div>'
            f'<div class="forecast">{_forecast_chips(forecast)}</div>'
        )
    weekly_html = ""
    if mid_forecast:
        weekly_html = (
            f'<div class="section-label">주간 예보 (3~10일)</div>'
            f'<div class="weekly">{_weekly_chips(mid_forecast)}</div>'
        )
    events_html = _events_html(events)
    legal_html = _legal_signals_html(legal_signals or [])
    warnings_html = _warnings_html(weather_warnings or [], weather_warnings_available)

    temp = current.get("T1H", "-")
    wsd = current.get("WSD", "-")
    rn1 = current.get("RN1", "-")
    reh = current.get("REH", "-")
    feels = compute_feels_like(current.get("T1H"), current.get("REH"), current.get("WSD"))

    feels_html = ""
    try:
        if feels is not None and abs(feels - float(temp)) >= 1.0:
            feels_html = f'<div class="feels">체감 {feels}°C</div>'
    except (TypeError, ValueError):
        pass

    cat_icon = CATEGORY_ICON.get(category, "")
    if weather_warnings:
        official = "경보" if display_level == "경보" else "주의보"
        badge_text = f"📢 기상특보 {official}"
    else:
        badge_text = f"{style['icon']} {LEVEL_LABEL[level]}"

    return f"""
    <div class="card" data-name="{escape(site_name.lower())}" data-category="{escape(category)}">
      <div class="bar" style="background:{style['bar']}"></div>
      <div class="body">
        <div class="card-top">
          <div><span class="cat-tag">{cat_icon} {escape(category)}</span><h2>{escape(site_name)}</h2></div>
          <span class="badge" style="background:{style['bg']};color:{style['fg']}">{escape(badge_text)}</span>
        </div>
        <div class="now">
          <div class="icon">{icon}</div>
          <div><div class="temp">{escape(str(temp))}°C</div>{feels_html}</div>
        </div>
        <div class="metrics">
          <div>💨 <span class="v">{escape(str(wsd))}m/s</span></div>
          <div>💧 <span class="v">{escape(str(rn1))}mm</span></div>
          <div>💦 <span class="v">{escape(str(reh))}%</span></div>
        </div>
        {reasons_html}
        {warnings_html}
        {legal_html}
        {events_html}
        {forecast_html}
        {weekly_html}
      </div>
    </div>"""


def _changes_html(changes, last_change_at):
    if not changes:
        return ""
    items = []
    for change in changes[:8]:
        level = change.get("to_level") or "-"
        items.append(
            '<div class="change-item">'
            f'<strong>{escape(change.get("site_name", "-"))}</strong>'
            f'{escape(change.get("type", "변경"))} · {escape(level)}'
            '</div>'
        )
    change_time = ""
    if last_change_at:
        try:
            from datetime import datetime
            change_time = datetime.fromisoformat(last_change_at).strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            change_time = str(last_change_at)
    return (
        '<section class="changes"><div class="changes-head">'
        '<h2>최근 기상변화</h2>'
        f'<time>{escape(change_time)}</time></div>'
        f'<div class="change-list">{"".join(items)}</div></section>'
    )


def build_dashboard_html(
    updated_str,
    site_rows,
    generated_at_iso=None,
    recent_changes=None,
    last_change_at=None,
    missing_site_count=0,
):
    """site_rows: [{"site_name", "current": dict, "forecast": list, "level": str, "reasons": list}, ...]"""
    severity = {"경보": 3, "주의": 2, "데이터없음": 1, "정상": 0}
    ordered = sorted(site_rows, key=lambda r: severity[r.get("display_level", r["level"])], reverse=True)

    counts = {"경보": 0, "주의": 0, "정상": 0, "데이터없음": 0}
    for row in site_rows:
        counts[row["level"]] += 1
    legal_count = sum(
        1 for row in site_rows
        if row.get("legal_status") in ("법정 작업중지", "법정 조치 이행 필요")
    )
    warning_count = sum(1 for row in site_rows if row.get("weather_warnings"))

    cards = "".join(
        _card(
            row["site_name"], row["category"], row["current"], row["forecast"],
            row.get("mid_forecast", []), row.get("events", []),
            row["level"], row["reasons"], row.get("legal_signals", []),
            row.get("weather_warnings", []), row.get("display_level"),
            row.get("weather_warnings_available", True),
        )
        for row in ordered
    )

    return _PAGE_TEMPLATE.format(
        updated=escape(updated_str),
        count_특보=warning_count,
        count_경보=counts["경보"],
        count_법정=legal_count,
        count_주의=counts["주의"],
        count_정상=counts["정상"],
        count_데이터없음=counts["데이터없음"],
        generated_at_iso=escape(generated_at_iso or updated_str),
        changes_html=_changes_html(recent_changes or [], last_change_at),
        missing_site_count=missing_site_count,
        total_site_count=len(site_rows),
        cards=cards,
    )

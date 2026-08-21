"""현장 기상현황 대시보드(정적 HTML) 생성.

담당자 이름·연락처 등 개인정보는 포함하지 않는다 (GitHub Pages로 공개 게시되므로).
"""

from html import escape

LEVEL_COLOR = {
    "정상": ("#e6f4ea", "#1e7e34", "#1e7e34"),
    "주의": ("#fff8e1", "#8a6d00", "#f2c200"),
    "경보": ("#fdecea", "#a61b1b", "#e53935"),
}

_PAGE_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>전사 기상 자동감시 대시보드</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px; background: #f5f6f8; color: #1a1a1a;
    font-family: -apple-system, "Segoe UI", "Malgun Gothic", sans-serif;
  }}
  h1 {{ font-size: 1.4rem; margin: 0 0 4px; }}
  .updated {{ color: #666; font-size: 0.85rem; margin-bottom: 20px; }}
  .summary {{ display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }}
  .summary .pill {{
    padding: 10px 18px; border-radius: 10px; font-weight: 600; font-size: 0.95rem;
  }}
  .grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px;
  }}
  .card {{
    border-radius: 12px; padding: 16px; border: 1px solid rgba(0,0,0,0.08);
    background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }}
  .card.level-경보 {{ border-left: 6px solid #e53935; }}
  .card.level-주의 {{ border-left: 6px solid #f2c200; }}
  .card.level-정상 {{ border-left: 6px solid #34a853; }}
  .card h2 {{ font-size: 1.05rem; margin: 0 0 8px; }}
  .badge {{
    display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.78rem;
    font-weight: 700; margin-bottom: 8px;
  }}
  .metrics {{ display: flex; gap: 14px; margin: 10px 0; font-size: 0.88rem; color: #333; }}
  .metrics div span {{ display: block; color: #888; font-size: 0.72rem; }}
  .reasons {{ font-size: 0.82rem; color: #a61b1b; margin: 6px 0; }}
  table.forecast {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.78rem; }}
  table.forecast th, table.forecast td {{
    padding: 4px 6px; text-align: center; border-bottom: 1px solid #eee;
  }}
  table.forecast th {{ color: #888; font-weight: 500; }}
  footer {{ margin-top: 28px; color: #999; font-size: 0.75rem; }}
</style>
</head>
<body>
  <h1>전사 기상 자동감시 대시보드</h1>
  <div class="updated">최종 갱신: {updated}</div>
  <div class="summary">{summary_pills}</div>
  <div class="grid">
    {cards}
  </div>
  <footer>기상청 공공데이터포털(단기예보 2.0) 기반 · 담당자 정보는 비공개 처리됨</footer>
</body>
</html>
"""


def _summary_pill(level, count):
    bg, fg, _ = LEVEL_COLOR[level]
    return f'<div class="pill" style="background:{bg};color:{fg}">{escape(level)} {count}개 현장</div>'


def _forecast_rows(forecast, limit=6):
    rows = []
    for f in forecast[:limit]:
        time_label = f.get("fcst_time", "")[:2] + "시"
        rows.append(
            f"<tr><td>{escape(time_label)}</td><td>{escape(str(f.get('TMP', '-')))}°C</td>"
            f"<td>{escape(str(f.get('POP', '-')))}%</td><td>{escape(str(f.get('SKY', '-')))}</td></tr>"
        )
    return "".join(rows)


def _card(site_name, current, forecast, level, reasons):
    bg, fg, _ = LEVEL_COLOR[level]
    reasons_html = f'<div class="reasons">{escape(", ".join(reasons))}</div>' if reasons else ""
    forecast_html = ""
    if forecast:
        forecast_html = (
            '<table class="forecast"><tr><th>시각</th><th>기온</th><th>강수확률</th><th>하늘</th></tr>'
            + _forecast_rows(forecast) + "</table>"
        )
    return f"""
    <div class="card level-{escape(level)}">
      <span class="badge" style="background:{bg};color:{fg}">{escape(level)}</span>
      <h2>{escape(site_name)}</h2>
      <div class="metrics">
        <div><span>기온</span>{escape(str(current.get('T1H', '-')))}°C</div>
        <div><span>풍속</span>{escape(str(current.get('WSD', '-')))}m/s</div>
        <div><span>1시간강수</span>{escape(str(current.get('RN1', '-')))}mm</div>
        <div><span>습도</span>{escape(str(current.get('REH', '-')))}%</div>
      </div>
      {reasons_html}
      {forecast_html}
    </div>"""


def build_dashboard_html(updated_str, site_rows):
    """site_rows: [{"site_name", "current": dict, "forecast": list, "level": str, "reasons": list}, ...]"""
    counts = {"경보": 0, "주의": 0, "정상": 0}
    for row in site_rows:
        counts[row["level"]] += 1

    summary_pills = "".join(_summary_pill(lv, counts[lv]) for lv in ("경보", "주의", "정상") if counts[lv] > 0)
    cards = "".join(
        _card(row["site_name"], row["current"], row["forecast"], row["level"], row["reasons"])
        for row in site_rows
    )

    return _PAGE_TEMPLATE.format(updated=escape(updated_str), summary_pills=summary_pills, cards=cards)

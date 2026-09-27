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

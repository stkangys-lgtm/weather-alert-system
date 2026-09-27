/* 선택 현장 상세: 히어로(하늘 반응형)·특보/법정 칩·수치 4개·앞으로 24시간·법정 안내(설계서 3.2). */
(function () {
  "use strict";
  const { $, esc, fmt } = WX;
  const HQ = window.HQ, state = HQ.state;

  function heroClass(site, h) {
    const v = HQ.value(site, h);
    if (v && (v.rain || 0) >= 15) return "rain heavy";
    if (HQ.isRain(v)) return "rain";
    const sky = h === 0 ? (HQ.value(site, 1) || {}).sky : v && v.sky;
    return sky === "맑음" ? "clear" : "cloudy";
  }
  function heroSentence(site, h) {
    if (h === 0) return WX.leadBold(site.summary);
    const v = HQ.value(site, h), when = esc(HQ.hourText(h));
    if (!v) return `<b>${when} 예보 자료가 없습니다.</b>`;
    const rain = HQ.isRain(v) ? `비 ${esc(WX.mmText(v.rainText))}` : "비 없음";
    return `<b>${when} 예보: ${rain}.</b> 기온 ${fmt(v.temp, 1)}°, 바람 ${fmt(v.wind, 1)}m/s, 강수확률 ${v.pop == null ? "-" : v.pop}%.`;
  }
  function chips(site) {
    const out = [];
    if (site.state === "stale") out.push(`<span class="chip mute">${WX.icon("i-clock")}${WX.kst(site.as_of).hm} 관측 자료 · 이번 수집 실패</span>`);
    if (site.state === "missing") out.push(`<span class="chip mute">${WX.icon("i-clock")}자료 없음 · 이번 수집 실패</span>`);
    if (state.latest.status.warnings !== "ok") out.push(`<span class="chip mute">${WX.icon("i-alert")}특보 확인 실패</span>`);
    else if (!site.warnings.length) out.push('<span class="chip">기상특보 없음</span>');
    site.warnings.forEach(w => { const c = WX.warningChip(w); out.push(`<span class="chip ${c.cls}">${WX.icon("i-alert")}${esc(c.text)}</span>`); });
    site.legal.forEach(l => { const c = WX.legalChip(l); out.push(`<span class="chip ${c.cls || "mute"}">${WX.icon("i-shield")}${esc(c.text)}</span>`); });
    if (site.legal_profile && !site.legal.length) out.push('<span class="chip">법정조치 해당 없음</span>');
    return out.join("");
  }
  function tiles(site, h) {
    const v = HQ.value(site, h) || {};
    const items = [
      ["i-drop", "비", v.rainText == null ? "-" : v.rainText, "mm/h"],
      ["i-wind", "바람", fmt(v.wind, 1), "m/s"],
      ["i-temp", h === 0 ? "체감" : "기온", fmt(h === 0 ? v.feels : v.temp, 1), "°"],
      ["i-hum", "습도", v.humidity == null ? "-" : v.humidity, "%"],
    ];
    return items.map(([ic, name, value, unit]) =>
      `<div class="tile"><div class="l">${WX.icon(ic)}${name}<small>${unit}</small></div><div class="v num">${esc(value)}</div></div>`).join("");
  }
  function legalInfo(site) {
    if (!site.legal_profile) {
      return `${WX.icon("i-info")}<div>작업 정보가 등록되지 않아 <b>법정 기준(타워크레인·철골·폭염 작업 등)</b>은 확인하지 않았습니다.</div>`;
    }
    if (!site.legal.length) return `${WX.icon("i-info")}<div>등록된 작업 기준으로 확인한 법정 조치 대상이 없습니다.</div>`;
    return `${WX.icon("i-shield")}<div>${site.legal.map(l =>
      `<b>${esc(l.status)}</b> · ${esc(l.title)} <span class="art">${esc(l.article || "")}</span>`).join("<br>")}</div>`;
  }

  function buildTimeline(site) {
    const tl = $("#tl"), n = state.times.length;
    tl.classList.remove("shown");
    tl.style.setProperty("--n", n);
    const slots = state.times.map((_, k) => HQ.value(site, k));
    $("#cR").innerHTML = slots.map((v, k) => `<i class="${k === 0 ? "now" : ""}" style="background:${v ? WX.rainColor(v.rain, WX.CELL) : WX.CELL};transition-delay:${k * 18}ms" title="${esc(HQ.whenText(k))} · 비 ${v ? esc(WX.mmText(v.rainText)) : "-"}"></i>`).join("");
    $("#cW").innerHTML = slots.map((v, k) => `<i class="${k === 0 ? "now" : ""}" style="background:${v ? WX.windColor(v.wind) : WX.CELL};transition-delay:${k * 18 + 120}ms" title="${esc(HQ.whenText(k))} · 바람 ${v ? fmt(v.wind, 1) : "-"}m/s"></i>`).join("");
    const temps = slots.map(v => (v && v.temp != null ? v.temp : null)), known = temps.filter(t => t != null);
    if (known.length > 1) {
      const lo = Math.min(...known), hi = Math.max(...known), pts = [];
      temps.forEach((t, k) => { if (t != null) pts.push([((k + 0.5) / n) * 100, 36 - ((t - lo) / Math.max(1, hi - lo)) * 30]); });
      const d = pts.map((p, k) => `${k ? "L" : "M"}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(" ");
      $("#spark").innerHTML = '<svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="tgrad" x1="0" x2="0" y1="0" y2="1">'
        + '<stop offset="0" stop-color="#5598e7" stop-opacity=".22"/><stop offset="1" stop-color="#5598e7" stop-opacity="0"/></linearGradient></defs>'
        + `<path class="area" d="${d} L${pts[pts.length - 1][0]} 40 L${pts[0][0]} 40 Z"/><path class="line" d="${d}" vector-effect="non-scaling-stroke" pathLength="600"/></svg>`
        + `<span class="hi num">${fmt(hi, 1)}°</span><span class="lo num">${fmt(lo, 1)}°</span>`;
    } else {
      $("#spark").innerHTML = '<span class="empty">기온 자료 없음</span>';
    }
    $("#hours").innerHTML = state.times.map((t, k) => `<b class="${k === 0 ? "k" : ""}">${k === 0 ? "지금" : k % 3 === 0 ? WX.kst(t).h : ""}</b>`).join("");
    const L = state.latest;
    const obs = site.as_of ? `${WX.kst(site.as_of).hm} 관측` : "관측 자료 없음";
    const issued = L.forecast_issued_at ? `${WX.kst(L.forecast_issued_at).hm} 발표` : "발표 시각 없음";
    $("#tlNote").textContent = (site.hourly || []).length ? `지금 칸은 ${obs}, 나머지는 기상청 단기예보(${issued})입니다.`
      : `지금 칸은 ${obs}입니다. 이 현장은 이번 수집에서 기상청 예보 자료를 받지 못했습니다.`;
    requestAnimationFrame(() => requestAnimationFrame(() => tl.classList.add("shown")));
  }
  function moveCursor() {
    const cells = $("#cR");
    if (!cells || !cells.children.length) return;
    const cell = cells.children[Math.min(state.h, cells.children.length - 1)];
    const tl = $("#tl").getBoundingClientRect(), r = cell.getBoundingClientRect(), cursor = $("#cursor");
    cursor.style.left = `${r.left - tl.left + r.width / 2 - 1}px`;
    cursor.dataset.label = HQ.hourText(state.h);
  }
  function render(first) {
    const site = state.sel;
    if (!site) return;
    const h = state.h, v = HQ.value(site, h);
    $("#dCat").textContent = [site.category, site.region].filter(Boolean).join(" · ");
    $("#dName").textContent = site.name;
    $("#hero").className = `hero ${heroClass(site, h)}${h === 0 && site.state !== "ok" ? " dim" : ""}`;
    $("#hWhen").textContent = h > 0 ? `${HQ.hourText(h)} 예보`
      : site.as_of ? `${WX.kst(site.as_of).hm} 관측${site.state === "stale" ? " · 이번 수집 실패" : ""}` : "관측 자료 없음";
    WX.tween($("#hTemp"), v ? v.temp : null, 1, 600);
    $("#hSent").innerHTML = heroSentence(site, h);
    $("#dChips").innerHTML = chips(site);
    $("#dTiles").innerHTML = tiles(site, h);
    $("#dLegal").innerHTML = legalInfo(site);
    if (first) buildTimeline(site);
    moveCursor();
  }
  function bindTimeline() {
    const tl = $("#tl");
    let dragging = false;
    const at = e => {
      const r = $("#cR").getBoundingClientRect();
      return Math.floor(((e.clientX - r.left) / r.width) * state.times.length);
    };
    tl.addEventListener("pointerdown", e => { dragging = true; tl.setPointerCapture(e.pointerId); if (HQ.time) HQ.time.stop(); HQ.setHour(at(e)); });
    tl.addEventListener("pointermove", e => { if (dragging) HQ.setHour(at(e)); });
    tl.addEventListener("pointerup", () => { dragging = false; });
    tl.addEventListener("pointercancel", () => { dragging = false; });
  }

  HQ.detail = {
    init() {
      bindTimeline();
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

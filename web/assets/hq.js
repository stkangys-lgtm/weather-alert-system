/* 본사 화면의 뼈대: 자료 불러오기·수집 상태·요약·목록·정렬·화면 전환.
   지도(hq-map.js)·상세(hq-detail.js)·시간 이동(hq-time.js)·전파 문안(hq-notice.js)은 같은 HQ 객체에 붙는다.
   문장·집계·고정 여부는 Python이 만든 값을 그대로 쓰고, 여기서는 표시와 상호작용만 한다. */
(function () {
  "use strict";
  const { $, $$, esc, fmt } = WX;
  const HQ = (window.HQ = window.HQ || {});
  const state = (HQ.state = { latest: null, sites: [], times: [], h: 0, sel: null, sort: "rain", view: "map" });
  const UNIT = { rain: "MM/H", wind: "M/S", temp: "°C" };
  const REFRESH_MS = 5 * 60 * 1000;   // 자료 다시 불러오기(Pages 캐시 최대 10분 고려)
  const STATUS_MS = 60 * 1000;        // 수집 지연 여부는 1분마다 다시 판단
  let bound = false, timers = false;

  HQ.value = (site, h = state.h) => WX.valueAt(site, state.times, h);
  // 관측(지금)은 Python 판단(now.precip)을 따르고, 예보 시각은 예보 강수량으로 본다.
  HQ.isRain = v => !!v && (v.observed && v.precip !== undefined ? v.precip === "rain" : (v.rain || 0) >= WX.RAIN_BINS[0]);
  HQ.hourText = h => (h === 0 ? "지금" : WX.hourLabel(state.times[h], state.times[0]));
  HQ.whenText = h => {
    if (h > 0) return `${HQ.hourText(h)} 예보`;
    return state.latest.observed_at ? `${WX.kst(state.latest.observed_at).hm} 관측` : "관측 자료 없음";
  };
  HQ.metric = (site, h, sort) => {
    const v = HQ.value(site, h);
    if (!v) return null;
    return sort === "wind" ? v.wind : sort === "temp" ? v.temp : v.rain;
  };
  // 특보·법정(pinned) 맨 위 → 자료 없는 현장 맨 아래 → 고른 기준 값 큰 순 → 이름.
  HQ.ordered = (h = state.h, sort = state.sort) => state.sites.slice().sort((a, b) => {
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
    const am = a.state === "missing", bm = b.state === "missing";
    if (am !== bm) return am ? 1 : -1;
    const va = HQ.metric(a, h, sort), vb = HQ.metric(b, h, sort);
    if (va == null || vb == null) {
      if (va == null && vb == null) return a.short.localeCompare(b.short, "ko");
      return va == null ? 1 : -1;
    }
    return vb - va || a.short.localeCompare(b.short, "ko");
  });

  /* ── 상단 수집 상태 ── */
  function renderStatus() {
    const st = WX.collectionStatus(state.latest);
    $("#live").innerHTML = `<span class="dot ${st.level}"></span><span class="full">${st.html}</span><span class="short">${st.short}</span>`;
    const banner = $("#banner");
    banner.hidden = !st.banner;
    banner.innerHTML = st.banner ? `${WX.icon("i-clock")}<span>${esc(st.banner)}</span>` : "";
  }

  /* ── 요약 문장·숫자 ── */
  function setKpi(key, value, dec = 0) {
    const el = $(`[data-k="${key}"]`);
    WX.tween(el, value, dec);
    el.closest(".kpi").classList.toggle("zero", !value);
  }
  function hourSentence(h, rainy) {
    const L = state.latest, when = esc(HQ.hourText(h));
    const tail = L.status.warnings !== "ok" ? "기상청 특보는 확인하지 못했습니다."
      : L.national.warnings ? `기상청 특보가 ${L.national.warnings}개 현장에 발효 중입니다.` : "기상청 특보는 없습니다.";
    if (!rainy.length) return `<b>${when} 예보상 비 오는 현장이 없습니다.</b> ${tail}`;
    const top = rainy[0];
    return `<b>${when} 예보상 ${rainy.length}곳에 비</b>, 가장 많은 곳은 ${esc(top.s.short)}(${esc(WX.mmText(top.v.rainText))}). ${tail}`;
  }
  function renderSummary() {
    const L = state.latest, h = state.h, n = L.national;
    $("#siteCount").textContent = `전국 ${state.sites.length}개 현장`;
    $("#when").textContent = HQ.whenText(h);
    const rainy = state.sites.map(s => ({ s, v: HQ.value(s, h) })).filter(x => HQ.isRain(x.v))
      .sort((a, b) => b.v.rain - a.v.rain);
    setKpi("warn", n.warnings);
    setKpi("legal", n.legal);
    setKpi("rainN", h === 0 ? n.rain_sites : rainy.length);
    const top = rainy[0], mx = $('[data-k="rainMax"]');
    if (!top) {
      setKpi("rainMax", 0);
      $("#rainMaxL").textContent = "최대 시간당";
    } else if (!isFinite(Number(top.v.rainText))) {
      mx._tween = (mx._tween || 0) + 1;
      mx.dataset.v = String(top.v.rain);
      mx.textContent = top.v.rainText;
      mx.closest(".kpi").classList.remove("zero");
      $("#rainMaxL").textContent = `최대 · ${top.s.short}`;
    } else {
      setKpi("rainMax", h === 0 ? top.v.rain : Number(top.v.rainText), 1);
      $("#rainMaxL").textContent = `최대 · ${top.s.short}`;
    }
    $("#sentence").innerHTML = h === 0 ? WX.leadBold(n.summary) : hourSentence(h, rainy);
    $("#warnFail").hidden = L.status.warnings === "ok";
  }

  /* ── 현장 목록 ── */
  function statusLine(site, h) {
    if (site.state === "missing") return '<span class="mute">자료 없음 · 이번 수집 실패</span>';
    // 빨강·주황 글자는 특보·법정에만, 항상 아이콘과 함께(설계서 3.1).
    const official = site.warnings.filter(w => w.kind !== "예비특보");
    if (official.length) { const c = WX.warningChip(official[0]); return `<span class="${c.cls}">${WX.icon("i-alert")}${esc(c.text)}</span>`; }
    const legal = site.legal.find(l => WX.legalChip(l).cls);
    if (legal) { const c = WX.legalChip(legal); return `<span class="${c.cls}">${WX.icon("i-shield")}${esc(c.text)}</span>`; }
    if (site.warnings.length) return `<span class="warn">${WX.icon("i-alert")}${esc(WX.warningChip(site.warnings[0]).text)}</span>`;
    if (h === 0 && site.state === "stale") return `<span class="mute">${WX.kst(site.as_of).hm} 관측 자료 · 이번 수집 실패</span>`;
    const v = HQ.value(site, h), ahead = [];
    for (let k = h + 1; k <= Math.min(h + 12, state.times.length - 1); k++) {
      const f = HQ.value(site, k);
      if (f) ahead.push({ k, f });
    }
    const wet = ahead.filter(x => HQ.isRain(x.f));
    const noForecast = !(site.hourly || []).length;   // 예보를 받지 못한 현장을 "비 예보 없음"으로 적지 않는다
    if (HQ.isRain(v)) {
      const head = h === 0 ? "지금 비" : "비";
      if (noForecast) return `${head} · 예보 자료 없음`;
      return wet.length ? `${head} · 예보상 ${esc(HQ.hourText(wet[wet.length - 1].k))}까지` : `${head} · 이후 12시간 비 예보 없음`;
    }
    if (noForecast || (h > 0 && !v)) return '<span class="mute">예보 자료 없음</span>';
    if (wet.length) return `예보상 ${esc(HQ.hourText(wet[0].k))}부터 비`;
    const sky = (v && v.sky) || (ahead[0] && ahead[0].f.sky);
    return `${sky ? `${esc(sky)} · ` : ""}12시간 비 예보 없음`;
  }
  function buildList(intro = true) {
    const list = $("#list");
    list.innerHTML = "";
    state.sites.forEach(site => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = intro ? "row pre" : "row";
      row.dataset.id = site.id;
      row.innerHTML = '<span class="big"><span class="v num"></span><span class="u"></span></span>'
        + `<span class="mid"><span class="nm" title="${esc(site.name)}">${esc(site.short)}</span><span class="st"></span>`
        + `<span class="strip" aria-hidden="true">${"<i></i>".repeat(12)}</span></span>${WX.icon("i-chev", "ic chev")}`;
      row.addEventListener("click", () => HQ.select(site, true));
      list.appendChild(row);
      site._row = row;
    });
  }
  function renderList(animate) {
    const h = state.h, sort = state.sort, list = $("#list"), before = new Map();
    if (animate && !WX.REDUCED) state.sites.forEach(s => before.set(s, s._row.getBoundingClientRect().top));
    HQ.ordered(h, sort).forEach(s => list.appendChild(s._row));
    state.sites.forEach(site => {
      const row = site._row, v = HQ.value(site, h), m = HQ.metric(site, h, sort);
      const text = m == null ? "-" : sort === "rain" ? v.rainText : fmt(m, 1);
      const big = row.querySelector(".v");
      big.textContent = text;
      big.classList.toggle("long", String(text).length > 4);
      row.querySelector(".u").textContent = UNIT[sort];
      row.querySelector(".st").innerHTML = statusLine(site, h);
      row.classList.toggle("dim", m == null || (sort === "rain" && m < WX.RAIN_BINS[0]) || (sort === "wind" && m < 1));
      row.classList.toggle("stale", h === 0 && site.state !== "ok");
      row.classList.toggle("sel", state.sel === site);
      row.setAttribute("aria-label", `${site.name}. ${text} ${UNIT[sort]}. ${row.querySelector(".st").textContent}`);
      row.querySelectorAll(".strip i").forEach((cell, k) => {
        const f = HQ.value(site, h + k);
        cell.style.background = !f ? WX.CELL : sort === "wind" ? WX.windColor(f.wind)
          : sort === "temp" ? `rgba(16,24,32,${Math.max(0.08, Math.min(0.7, ((f.temp == null ? 12 : f.temp) - 12) / 22))})`
          : WX.rainColor(f.rain, WX.CELL);
      });
    });
    before.forEach((top, s) => {
      const d = top - s._row.getBoundingClientRect().top;
      if (!d) return;
      s._row.style.transition = "none";
      s._row.style.transform = `translateY(${d}px)`;
      requestAnimationFrame(() => { s._row.style.transition = ""; s._row.style.transform = ""; });
    });
  }

  /* ── 선택·시각·화면 전환 ── */
  HQ.select = (site, fly) => {
    const first = state.sel !== site;
    state.sel = site;
    document.body.classList.add("hasdetail");
    state.sites.forEach(s => s._row.classList.toggle("sel", s === site));
    if (HQ.detail) HQ.detail.open(site, first);
    if (HQ.map) HQ.map.focus(site, fly);
    site._row.scrollIntoView({ block: "nearest", behavior: WX.REDUCED ? "auto" : "smooth" });
  };
  HQ.close = () => {
    state.sel = null;
    document.body.classList.remove("hasdetail");
    state.sites.forEach(s => s._row.classList.remove("sel"));
    if (HQ.detail) HQ.detail.close();
    if (HQ.map) HQ.map.render();
  };
  HQ.setHour = (h, force) => {
    h = Math.max(0, Math.min(state.times.length - 1, Math.round(h)));
    if (h === state.h && !force) return;
    state.h = h;
    renderSummary();
    renderList(!force);
    if (HQ.map) HQ.map.render();
    if (HQ.detail) HQ.detail.render();
    if (HQ.time) HQ.time.render();
  };
  function segPill(seg) {
    const on = seg.querySelector("button.on"), pill = seg.querySelector(".pill");
    if (!on || !pill) return;
    pill.style.width = `${on.offsetWidth}px`;
    pill.style.transform = `translateX(${on.offsetLeft - pill.offsetLeft}px)`;
  }
  HQ.segPills = () => { segPill($("#nav")); segPill($("#sortSeg")); };
  HQ.setView = view => {
    state.view = view;
    document.body.dataset.view = view;
    $$("#nav button").forEach(b => {
      if (b.dataset.v === "notice") return;
      b.classList.toggle("on", b.dataset.v === view);
      b.setAttribute("aria-pressed", String(b.dataset.v === view));
    });
    segPill($("#nav"));
    $("#tableView").hidden = view !== "list";
    if (view === "list" && HQ.table) HQ.table.render();
  };
  HQ.setSort = sort => {
    state.sort = sort;
    $$("#sortSeg button").forEach(b => b.classList.toggle("on", b.dataset.m === sort));
    segPill($("#sortSeg"));
    renderList(true);
  };
  function bindControls() {
    if (bound) return;
    bound = true;
    $$("#nav button").forEach(b => b.addEventListener("click", () => {
      if (b.dataset.v === "notice") {
        if (HQ.notice) HQ.notice.open(null);
        return;
      }
      HQ.setView(b.dataset.v);
    }));
    $$("#sortSeg button").forEach(b => b.addEventListener("click", () => HQ.setSort(b.dataset.m)));
    $$(".handle").forEach(handle => handle.addEventListener("click", () => $(`#${handle.dataset.sheet}`).classList.toggle("expanded")));
    document.addEventListener("keydown", e => {
      if (e.key !== "Escape") return;
      if (HQ.notice && HQ.notice.close()) return;
      if (state.view === "list") { HQ.setView("map"); return; }
      if (state.sel) HQ.close();
    });
    window.addEventListener("resize", () => { HQ.segPills(); if (HQ.detail) HQ.detail.moveCursor(); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(HQ.segPills);
  }

  /* ── 시작 ── */
  function intro() {
    const delay = ms => (WX.REDUCED ? 0 : ms);
    $$(".intro-hide").forEach((el, k) => setTimeout(() => el.classList.remove("intro-hide"), delay(80 + k * 70)));
    $$("#list .row").forEach((row, k) => setTimeout(() => row.classList.remove("pre"), delay(350 + k * 35)));
    setTimeout(() => {
      HQ.segPills();
      // PC에서는 첫 현장을 골라 상세까지 한 화면에 보인다(설계서 1.3-1).
      if (HQ.detail && window.innerWidth >= 900 && state.view === "map" && state.sites.length) HQ.select(HQ.ordered()[0], false);
    }, delay(1300));
  }
  // 새 자료로 바꾼다. 고른 현장·시각·정렬·화면은 그대로 둔다.
  HQ.applyLatest = latest => {
    const selId = state.sel && state.sel.id;
    state.latest = latest;
    state.sites = latest.sites;
    state.times = WX.timeline(latest);
    state.h = Math.min(state.h, state.times.length - 1);
    state.sel = selId ? state.sites.find(s => s.id === selId) || null : null;
    renderStatus();
    buildList(false);
    if (HQ.time) HQ.time.retick();
    if (HQ.map) HQ.map.reload();
    if (state.sel) { if (HQ.detail) HQ.detail.open(state.sel, true); } else { HQ.close(); }
    HQ.setHour(state.h, true);
    if (state.view === "list" && HQ.table) HQ.table.render();
  };
  async function refresh() {
    try {
      const latest = await WX.load(WX.dataUrl("data/latest.json"));
      if (latest.generated_at !== state.latest.generated_at) HQ.applyLatest(latest);
      else renderStatus();
    } catch (error) {
      renderStatus();   // 다시 불러오기에 실패하면 이전 화면을 두고 수집 상태만 다시 판단한다
    }
  }
  function startTimers() {
    if (timers) return;
    timers = true;
    setInterval(renderStatus, STATUS_MS);
    setInterval(refresh, REFRESH_MS);
  }

  function start(latest) {
    state.latest = latest;
    state.sites = latest.sites;
    state.times = WX.timeline(latest);
    state.h = 0;
    state.sel = null;
    renderStatus();
    buildList();
    bindControls();
    if (HQ.detail) HQ.detail.init();
    if (HQ.time) HQ.time.init();
    if (HQ.notice) HQ.notice.init();
    HQ.setHour(0, true);
    if (HQ.map) HQ.map.init();
    HQ.setView(location.hash === "#list" ? "list" : "map");
    startTimers();
    intro();
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
    start(latest);
  }
  document.addEventListener("DOMContentLoaded", () => {
    $("#retry").addEventListener("click", boot);
    boot();
  });
})();

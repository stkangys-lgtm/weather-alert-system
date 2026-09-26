/* 본사 지도: 현장 표식(점 + 이름·수치), 가까운 표식 묶음, 선택 이동(설계서 3.2·5.7). */
(function () {
  "use strict";
  const { $, esc, fmt } = WX;
  const HQ = window.HQ, state = HQ.state;
  const CLUSTER_PX = 44;
  let adapter = null, groups = [];
  const marks = new Map();

  HQ.padding = () => {
    if (window.innerWidth < 900) return { left: 24, right: 24, top: 130, bottom: Math.round(window.innerHeight * 0.48) };
    return { left: 420, right: document.body.classList.contains("hasdetail") ? 430 : 70, top: 90, bottom: 110 };
  };
  const located = () => state.sites.filter(s => typeof s.lat === "number" && typeof s.lon === "number");
  const rainOf = site => { const v = HQ.value(site); return v && v.rain != null ? v.rain : 0; };
  // 묶음 대표: 특보·법정 → 비 많은 순 → 이름.
  const priority = (a, b) => (a.pinned !== b.pinned ? (a.pinned ? -1 : 1) : rainOf(b) - rainOf(a) || a.short.localeCompare(b.short, "ko"));

  function label(site) {
    const v = HQ.value(site), alert = site.pinned ? WX.icon("i-alert") : "";
    if (!v) return `${alert}<b>${esc(site.short)}</b><span class="mu">-</span>`;
    if (HQ.isRain(v)) return `${alert}<b>${esc(site.short)}</b><em class="num">${esc(v.rainText)}</em>`;
    return `${alert}<b>${esc(site.short)}</b><span class="mu num">${fmt(v.temp, 1)}°</span>`;
  }

  function attach(next) {
    marks.forEach(m => m.handle.remove());
    marks.clear();
    groups.forEach(g => g.handle.remove());
    groups = [];
    adapter = next;
    located().forEach(site => {
      const el = document.createElement("div");
      el.className = "mk";
      el.tabIndex = 0;
      el.setAttribute("role", "button");
      el.innerHTML = '<span class="d"></span><span class="lab"></span>';
      el.addEventListener("click", e => { e.stopPropagation(); HQ.select(site, true); });
      el.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); HQ.select(site, true); }
      });
      marks.set(site.id, { site, el, handle: adapter.addMarker(el, site.lon, site.lat, "left", [-7, 0]) });
    });
    adapter.onMove(regroup);
    $("#zIn").hidden = $("#zOut").hidden = !adapter.canZoom;
    render();
    adapter.fitBounds(WX.KOREA, { padding: HQ.padding() });
    popIn();
    if (state.sel) focus(state.sel, false);
  }

  function popIn() {
    const cx = window.innerWidth / 2, cy = window.innerHeight / 2;
    Array.from(marks.values())
      .map(m => ({ m, p: adapter.project(m.site.lon, m.site.lat) }))
      .sort((a, b) => Math.hypot(a.p.x - cx, a.p.y - cy) - Math.hypot(b.p.x - cx, b.p.y - cy))
      .forEach(({ m }, k) => setTimeout(() => m.el.classList.add("in"), WX.REDUCED ? 0 : 150 + k * 40));
  }

  function render() {
    if (!adapter) return;
    marks.forEach(({ site, el }) => {
      const v = HQ.value(site), rain = rainOf(site);
      el.style.setProperty("--c", HQ.isRain(v) ? WX.rainColor(rain) : WX.DRY);
      el.classList.toggle("big", rain >= 15);
      el.classList.toggle("sel", state.sel === site);
      el.classList.toggle("alert", !!site.pinned);
      el.classList.toggle("stale", site.state !== "ok");
      el.querySelector(".lab").innerHTML = label(site);
      el.setAttribute("aria-label", `${site.name} ${el.querySelector(".lab").textContent}`);
    });
    regroup();
  }

  function regroup() {
    if (!adapter) return;
    groups.forEach(g => g.handle.remove());
    groups = [];
    marks.forEach(m => m.el.classList.remove("hid", "nolab"));
    const pts = Array.from(marks.values()).map(m => ({ m, p: adapter.project(m.site.lon, m.site.lat) }))
      .sort((a, b) => priority(a.m.site, b.m.site));
    if (adapter.kind !== "maplibre") {
      // 자체 지도는 확대할 수 없어 묶지 않고, 특보·법정·비·선택 현장만 이름표를 보인다.
      pts.forEach(({ m }) => { if (!(m.site.pinned || state.sel === m.site || HQ.isRain(HQ.value(m.site)))) m.el.classList.add("nolab"); });
      declutter(pts.filter(x => !x.m.el.classList.contains("nolab")));
      return;
    }
    const used = new Set();
    pts.forEach(a => {
      if (used.has(a.m.site.id)) return;
      used.add(a.m.site.id);
      if (a.m.site === state.sel) return;
      const members = [a.m.site];
      pts.forEach(b => {
        if (used.has(b.m.site.id) || b.m.site === state.sel) return;
        if (Math.hypot(a.p.x - b.p.x, a.p.y - b.p.y) < CLUSTER_PX) { members.push(b.m.site); used.add(b.m.site.id); }
      });
      if (members.length > 1) group(members);
    });
    declutter(pts);
  }

  // 묶이지 않은 표식끼리 이름표가 겹치면 우선순위가 낮은 쪽은 점만 남긴다(선택·특보·법정 현장은 항상 이름표).
  function declutter(pts) {
    const hit = (a, b) => a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b;
    const placed = groups.map(g => {
      const p = adapter.project(g.lon, g.lat), w = g.el.offsetWidth, h = g.el.offsetHeight;
      return { l: p.x - w / 2, r: p.x + w / 2, t: p.y - h / 2, b: p.y + h / 2 };
    });
    pts.filter(x => !x.m.el.classList.contains("hid"))
      .sort((a, b) => (a.m.site === state.sel ? -1 : b.m.site === state.sel ? 1 : priority(a.m.site, b.m.site)))
      .forEach(({ m, p }) => {
        const w = m.el.offsetWidth, h = m.el.offsetHeight;
        const box = { l: p.x - 9, r: p.x - 7 + w + 2, t: p.y - h / 2 - 2, b: p.y + h / 2 + 2 };
        if (m.site !== state.sel && !m.site.pinned && placed.some(o => hit(o, box))) {
          m.el.classList.add("nolab");
          placed.push({ l: p.x - 9, r: p.x + 9, t: p.y - 9, b: p.y + 9 });
        } else {
          placed.push(box);
        }
      });
  }

  function group(sites) {
    sites.forEach(s => marks.get(s.id).el.classList.add("hid"));
    const lead = sites[0];
    const wettest = sites.reduce((best, s) => (rainOf(s) > rainOf(best) ? s : best), lead);
    const wv = HQ.value(wettest);
    const el = document.createElement("button");
    el.type = "button";
    el.className = "cl";
    el.style.setProperty("--c", HQ.isRain(wv) ? WX.rainColor(wv.rain) : "#9aa4ae");
    el.innerHTML = `<span class="n">${sites.length}</span>${esc(lead.short)} 외 ${sites.length - 1} · `
      + (HQ.isRain(wv) ? `비 최대 ${esc(wv.rainText)}` : "비 없음");
    el.setAttribute("aria-label", `${sites.map(s => s.name).join(", ")} 묶음. 누르면 확대합니다.`);
    el.addEventListener("click", e => {
      e.stopPropagation();
      const lons = sites.map(s => s.lon), lats = sites.map(s => s.lat);
      adapter.fitBounds([[Math.min(...lons) - 0.02, Math.min(...lats) - 0.02], [Math.max(...lons) + 0.02, Math.max(...lats) + 0.02]],
        { padding: HQ.padding(), maxZoom: 13 });
    });
    const lon = sites.reduce((sum, s) => sum + s.lon, 0) / sites.length;
    const lat = sites.reduce((sum, s) => sum + s.lat, 0) / sites.length;
    groups.push({ el, lon, lat, handle: adapter.addMarker(el, lon, lat, "center") });
  }

  function focus(site, fly) {
    render();
    if (fly && adapter && adapter.canZoom && typeof site.lat === "number") {
      adapter.flyTo({ center: [site.lon, site.lat], zoom: Math.max(adapter.getZoom(), 9.2), padding: HQ.padding() });
    }
  }

  function notice(mode) {
    const msg = $("#mapMsg");
    msg.textContent = mode === "svg" ? "지도 서비스를 불러오지 못해 간단한 지도로 표시합니다. 목록과 상세는 그대로 쓸 수 있습니다."
      : mode === "none" ? "지도를 불러오지 못했습니다. 목록과 상세는 그대로 쓸 수 있습니다." : "";
    msg.classList.toggle("show", !!mode);
    clearTimeout(msg._timer);
    if (mode) msg._timer = setTimeout(() => msg.classList.remove("show"), 8000);
  }

  HQ.map = {
    init() {
      $("#zIn").addEventListener("click", () => adapter && adapter.zoomIn());
      $("#zOut").addEventListener("click", () => adapter && adapter.zoomOut());
      $("#zHome").addEventListener("click", () => adapter && adapter.fitBounds(WX.KOREA, { padding: HQ.padding() }));
      window.addEventListener("resize", () => adapter && adapter.resize());
      WX.createMap({ container: $("#map"), padding: HQ.padding, onReady: attach, onNotice: notice });
    },
    render,
    focus,
  };
})();

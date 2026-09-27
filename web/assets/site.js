/* 현장 화면(설계서 3.3): 한 현장의 지금·앞으로 24시간·10일 예보·법정 안내·전파 문안.
   문장·판단은 Python이 만든 값을 그대로 쓰고, 여기서는 표시와 상호작용만 한다. 지도·시트 끌기는 site-map.js. */
(function () {
  "use strict";
  const { $, $$, esc, fmt } = WX;
  const P = WX.parts;
  const SITE = (window.SITE = window.SITE || {});
  const state = (SITE.state = { latest: null, site: null, times: [], h: 0 });
  const REFRESH_MS = 5 * 60 * 1000, STATUS_MS = 60 * 1000;
  const SKY_WORD = { heavy: "비", rain: "비", snow: "눈" };
  const SKY_ICON = { heavy: "i-rain", rain: "i-rain", snow: "i-snow", clear: "i-sun" };
  const els = () => ({ tl: $("#tl"), rain: $("#cR"), wind: $("#cW"), spark: $("#spark"), hours: $("#hours"), note: $("#tlNote"), cursor: $("#cursor") });
  let bound = false, timers = false;

  SITE.value = (h = state.h) => WX.valueAt(state.site, state.times, h);
  SITE.hourText = h => WX.hourText(state.times, h);
  const label = k => (k === 0 ? (state.site.as_of ? `${WX.kst(state.site.as_of).hm} 관측` : "관측 자료 없음") : `${SITE.hourText(k)} 예보`);

  const askedId = () => new URLSearchParams(location.search).get("id");
  function siteHref(id) {
    const query = new URLSearchParams(location.search);   // 확인용 시험 자료(?data=)는 그대로 둔다
    query.set("id", id);
    return `site.html?${query.toString()}`;
  }

  function renderStatus() {
    const st = WX.collectionStatus(state.latest);
    $("#live").innerHTML = `<span class="dot ${st.level}"></span><span class="full">${st.html}</span><span class="short">${st.short}</span>`;
    const banner = $("#banner");
    banner.hidden = !st.banner;
    banner.innerHTML = st.banner ? `${WX.icon("i-clock")}<span>${esc(st.banner)}</span>` : "";
  }

  function renderHero() {
    const site = state.site, h = state.h, v = SITE.value(h), sky = P.heroSky(site, state.times, h);
    $("#hero").className = `hero ${P.heroClass(sky)}${h === 0 && site.state !== "ok" ? " dim" : ""}`;
    const skyText = SKY_WORD[sky] || (h === 0 ? (SITE.value(1) || {}).sky : v && v.sky) || "";
    $("#hIcon").setAttribute("href", `${WX.ICONS}#${SKY_ICON[sky] || WX.skyIcon(skyText)}`);
    const when = h > 0 ? `${SITE.hourText(h)} 예보`
      : site.as_of ? `${WX.kst(site.as_of).hm} 관측${site.state === "stale" ? " · 이번 수집 실패" : ""}` : "관측 자료 없음";
    $("#hK").textContent = skyText ? `${when} · ${skyText}` : when;
    WX.tween($("#hT"), v ? v.temp : null, 1, h === 0 ? 750 : 350);
    const next = WX.dayOffset(WX.kst(Date.now()).date, 1), tomorrow = (site.daily || []).find(d => d.date === next);
    $("#hM").textContent = h === 0
      ? [v && v.feels != null ? `체감 ${fmt(v.feels, 1)}°` : "",
         tomorrow && !tomorrow.missing && tomorrow.tmin != null ? `내일 최저 ${fmt(tomorrow.tmin, 0)}° 최고 ${fmt(tomorrow.tmax, 0)}°` : ""].filter(Boolean).join(" · ")
      : v ? `강수확률 ${v.pop == null ? "-" : v.pop}% · 습도 ${v.humidity == null ? "-" : v.humidity}%` : "";
    $("#hS").innerHTML = h === 0 ? WX.leadBold(site.summary) : P.forecastSentence(v, SITE.hourText(h));
  }

  SITE.setHour = h => {
    h = Math.max(0, Math.min(state.times.length - 1, Math.round(h)));
    state.h = h;
    renderHero();
    const v = SITE.value(h);
    $("#tiles").innerHTML = P.tiles(v, h === 0);
    P.cursor(els(), h, SITE.hourText(h));
    $("#readout").innerHTML = h === 0 ? '<span class="hint">타임라인을 좌우로 문지르면 그 시각 예보가 보입니다</span>'
      : v ? `<b>${esc(SITE.hourText(h))}</b> ${fmt(v.temp, 1)}° · 비 ${esc(WX.mmText(v.rainText))} · 바람 ${fmt(v.wind, 1)}m/s · 강수확률 ${v.pop == null ? "-" : v.pop}%`
      : `<b>${esc(SITE.hourText(h))}</b> 예보 자료가 없습니다`;
    const chip = $("#nowchip");
    chip.textContent = h === 0 ? "지금" : "지금으로";
    chip.disabled = h === 0;
    chip.classList.toggle("back", h !== 0);
  };

  function reveal() {
    $$(".stack > *").forEach((el, k) => {
      el.classList.add("rv");
      el.classList.remove("in");
      setTimeout(() => el.classList.add("in"), WX.REDUCED ? 0 : 150 + k * 60);
    });
  }
  function renderSite(first) {
    const site = state.site;
    document.title = `${site.short} · 현대아산 기상안전`;
    $("#name").textContent = site.name;
    $("#sub").textContent = [site.category, site.region].filter(Boolean).join(" · ");
    $("#chips").innerHTML = P.chips(site, state.latest.status.warnings === "ok");
    $("#legal").innerHTML = P.legal(site);
    $("#d10").innerHTML = P.daily(site.daily);
    $("#nt").textContent = site.notice;
    if (first) {
      $("#nt").classList.remove("open");
      $("#ntMore").textContent = "전체 보기";
      reveal();
    }
    P.timeline(els(), site, state.times, state.latest.forecast_issued_at, label);
    SITE.setHour(first ? 0 : state.h);
  }

  function showPicker(message) {
    state.site = null;
    // 목록에 없는 현장이면 홈 화면 추가가 없는 설정 파일을 가리키지 않게 기본 설정으로 되돌린다.
    $("#manifest").setAttribute("href", "manifest.webmanifest");
    $("#sheet").hidden = true;
    $("#picker").hidden = false;
    $("#pickMsg").textContent = message;
    const sites = state.latest.sites.slice().sort((a, b) => a.short.localeCompare(b.short, "ko"));
    $("#pickList").innerHTML = sites.map(s => {
      const v = WX.valueAt(s, state.times, 0);
      const now = !v ? "자료 없음" : WX.isRain(v) ? `비 ${v.rainText}mm/h` : `${fmt(v.temp, 1)}°`;
      return `<a class="pick" href="${esc(siteHref(s.id))}"><b>${esc(s.short)}</b><small>${esc([s.region, s.name].filter(Boolean).join(" · "))}</small><span class="num">${esc(now)}</span></a>`;
    }).join("");
  }

  // 자료를 화면에 반영한다. 현장을 찾으면 true.
  function apply(latest, first) {
    state.latest = latest;
    state.times = WX.timeline(latest);
    renderStatus();
    const id = askedId();
    const site = id ? latest.sites.find(s => s.id === id) : null;
    if (!site) {
      showPicker(id ? "주소의 현장을 찾지 못했습니다(현장 이름이 바뀌면 주소도 바뀝니다). 현장을 다시 골라 주세요."
        : "현장을 골라 주세요.");
      return false;
    }
    $("#picker").hidden = true;
    $("#sheet").hidden = false;
    state.site = site;
    state.h = Math.min(state.h, state.times.length - 1);
    renderSite(first);
    return true;
  }

  async function copy() {
    if (await WX.copy($("#nt").textContent)) { WX.toast("전파 문안을 복사했습니다"); return; }
    $("#nt").classList.add("open");
    const range = document.createRange();
    range.selectNodeContents($("#nt"));
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    WX.toast("자동 복사가 막혀 있습니다. 선택된 문안을 직접 복사해 주세요");
  }
  function bind() {
    if (bound) return;
    bound = true;
    P.scrub(els(), () => state.times.length, h => SITE.setHour(h));
    $("#nowchip").addEventListener("click", () => SITE.setHour(0));
    $("#ntMore").addEventListener("click", () => {
      const open = $("#nt").classList.toggle("open");
      $("#ntMore").textContent = open ? "접기" : "전체 보기";
    });
    $("#copy").addEventListener("click", copy);
    window.addEventListener("resize", () => { if (state.site) P.cursor(els(), state.h, SITE.hourText(state.h)); });
  }
  // 새 자료로 바꾼다(고른 시각·펼친 문안은 그대로). 5분 갱신과 확인에 쓴다.
  SITE.applyLatest = latest => {
    const shown = apply(latest, false);
    if (shown && SITE.map) SITE.map.render();
    return shown;
  };
  async function refresh() {
    try {
      const latest = await WX.load(WX.dataUrl("data/latest.json"));
      if (latest.generated_at === state.latest.generated_at) { renderStatus(); return; }
      SITE.applyLatest(latest);
    } catch (error) {
      renderStatus();   // 다시 불러오기에 실패하면 이전 화면을 두고 수집 상태만 다시 판단한다
    }
  }
  function startTimers() {
    if (timers) return;
    timers = true;
    setInterval(() => { if (state.latest) renderStatus(); }, STATUS_MS);
    setInterval(refresh, REFRESH_MS);
    // 홈 화면 앱은 뒤로 가 있는 동안 타이머가 멈추므로, 다시 보이면 바로 수집 상태를 다시 판단하고 새 자료를 확인한다.
    const resume = () => { if (document.visibilityState === "visible" && state.latest) { renderStatus(); refresh(); } };
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("pageshow", e => { if (e.persisted) resume(); });
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
    bind();
    const shown = apply(latest, true);
    startTimers();
    if (shown && SITE.map) SITE.map.init();
  }
  document.addEventListener("DOMContentLoaded", () => {
    $("#retry").addEventListener("click", boot);
    boot();
  });
})();

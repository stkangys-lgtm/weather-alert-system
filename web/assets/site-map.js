/* 현장 화면의 지도와 끌어올리는 시트(설계서 3.3).
   휴대폰: 시트 세 위치(펼침·반·지도)를 손잡이로만 옮긴다(타임라인 문지르기와 겹치지 않게).
   PC(1024px 이상): 왼쪽 지도 + 오른쪽 내용 열(시트 이동 없음). */
(function () {
  "use strict";
  const { $, fmt } = WX;
  const SITE = window.SITE, state = SITE.state;
  const TOP_GAP = 60;                     // 다 펼쳤을 때 위 여백(상단 막대 자리)
  const ORDER = ["full", "half", "map"];
  let snap = "half", adapter = null, marker = null, started = false;
  const desktop = () => window.innerWidth >= 1024;

  // 시트가 내려간 정도(시트 높이의 %). 반 위치는 지도 띠가 화면 높이의 26%(최소 150px) 보이게 화면에 맞춰 정한다
  // → 작은 휴대폰에서도 첫 화면에 현장명·기온·요약·특보 칩이 보인다(설계서 1.3-2).
  function snapValue(name) {
    if (name === "full") return 0;
    if (name === "map") return 78;
    const sheetH = window.innerHeight - TOP_GAP, mapPx = Math.max(150, window.innerHeight * 0.26);
    return Math.max(0, Math.min(60, ((mapPx - TOP_GAP) / sheetH) * 100));
  }
  function currentValue() {
    const value = Number($("#sheet").style.getPropertyValue("--yn"));
    return isFinite(value) && $("#sheet").style.getPropertyValue("--yn") !== "" ? value : snapValue(snap);
  }
  SITE.padding = () => {
    if (desktop()) return { left: 40, right: Math.min(560, window.innerWidth * 0.46) + 40, top: 90, bottom: 40 };
    const visible = (window.innerHeight - TOP_GAP) * (1 - currentValue() / 100);
    return { left: 30, right: 30, top: 70, bottom: Math.round(visible) + 16 };
  };

  function center() {
    if (!adapter || !state.site || typeof state.site.lat !== "number") return;
    adapter.flyTo({ center: [state.site.lon, state.site.lat], zoom: Math.max(adapter.getZoom(), 9), padding: SITE.padding(),
      speed: WX.REDUCED ? 10 : 1.2 });
  }
  function setSnap(name, animate = true) {
    snap = name;
    const sheet = $("#sheet");
    sheet.classList.toggle("drag", !animate);
    sheet.style.setProperty("--yn", snapValue(name).toFixed(2));
    sheet.dataset.snap = name;
    $("#grab").setAttribute("aria-expanded", String(name === "full"));
    if (!animate) requestAnimationFrame(() => sheet.classList.remove("drag"));
    setTimeout(center, animate && !WX.REDUCED ? 560 : 0);
  }

  function bindSheet() {
    const sheet = $("#sheet"), grab = $("#grab");
    let drag = null;
    grab.addEventListener("pointerdown", e => {
      if (desktop()) return;
      drag = { y: e.clientY, from: currentValue(), t: performance.now(), moved: false };
      grab.setPointerCapture(e.pointerId);
      sheet.classList.add("drag");
    });
    grab.addEventListener("pointermove", e => {
      if (!drag) return;
      const dy = e.clientY - drag.y;
      if (Math.abs(dy) > 4) drag.moved = true;
      const value = Math.max(0, Math.min(85, drag.from + (dy / (window.innerHeight - TOP_GAP)) * 100));
      sheet.style.setProperty("--yn", value.toFixed(2));
    });
    const end = e => {
      if (!drag) return;
      sheet.classList.remove("drag");
      const moved = drag.moved, speed = (e.clientY - drag.y) / Math.max(1, performance.now() - drag.t), now = currentValue();
      drag = null;
      if (!moved) { setSnap(snap === "full" ? "half" : "full"); return; }
      let target = ORDER.reduce((a, b) => (Math.abs(snapValue(b) - now) < Math.abs(snapValue(a) - now) ? b : a));
      if (Math.abs(speed) > 0.5) target = ORDER[Math.max(0, Math.min(2, ORDER.indexOf(snap) + (speed > 0 ? 1 : -1)))];
      setSnap(target);
    };
    grab.addEventListener("pointerup", end);
    grab.addEventListener("pointercancel", end);
    grab.addEventListener("click", e => { if (e.detail === 0) setSnap(snap === "full" ? "half" : "full"); });   // 키보드(Enter·Space)
    $("#goMap").addEventListener("click", () => { $("#sc").scrollTo({ top: 0 }); setSnap("map"); });
    $(".ttl .names").addEventListener("click", () => { if (!desktop() && snap !== "full") setSnap("full"); });
    window.addEventListener("resize", () => { setSnap(snap, false); if (adapter) adapter.resize(); });
  }

  function markerText() {
    const v = WX.valueAt(state.site, state.times, 0);
    if (!v) return `${state.site.short} · -`;
    return WX.isRain(v) ? `${state.site.short} · 비 ${v.rainText}` : `${state.site.short} · ${fmt(v.temp, 1)}°`;
  }
  function render() {
    if (!marker || !state.site) return;
    marker.setLngLat(state.site.lon, state.site.lat);
    const text = markerText();
    marker.el.querySelector(".mlab").textContent = text;
    marker.el.setAttribute("aria-label", `${state.site.name} ${text}`);
  }
  function attach(next) {
    if (marker) marker.remove();
    adapter = next;
    const el = document.createElement("div");
    el.className = "mewrap";
    el.setAttribute("role", "img");
    el.innerHTML = '<div class="me"></div><div class="mlab"></div>';
    marker = adapter.addMarker(el, state.site.lon, state.site.lat, "center");
    render();
    center();
  }
  function notice(mode) {
    const msg = $("#mapMsg");
    msg.textContent = mode === "svg" ? "지도 서비스를 불러오지 못해 간단한 지도로 표시합니다."
      : mode === "none" ? "지도를 불러오지 못했습니다. 현장 정보는 그대로 볼 수 있습니다." : "";
    msg.classList.toggle("show", !!mode);
    clearTimeout(msg._timer);
    if (mode) msg._timer = setTimeout(() => msg.classList.remove("show"), 8000);
  }

  SITE.map = {
    init() {
      if (started || !state.site) return;
      started = true;
      bindSheet();
      setSnap(desktop() ? "full" : "half", false);
      if (typeof state.site.lat !== "number" || typeof state.site.lon !== "number") return;   // 위치 없는 현장은 지도 없이
      WX.createMap({ container: $("#map"), padding: SITE.padding, view: { center: [state.site.lon, state.site.lat], zoom: 9 },
        attribution: "top-left", onReady: attach, onNotice: notice });
    },
    render,
  };
})();

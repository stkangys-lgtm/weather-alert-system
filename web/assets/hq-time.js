/* 하단 시간 스크러버: 0 = 지금(관측), 1~24 = 시간별 예보. 바꾸면 지도·목록·요약·상세가 모두 그 시각으로 바뀐다. */
(function () {
  "use strict";
  const { $ } = WX;
  const HQ = window.HQ, state = HQ.state;
  let timer = null, dragging = false;
  const max = () => state.times.length - 1;

  function ticks() {
    $("#ticks").innerHTML = state.times.map((t, h) =>
      `<b class="${h === 0 ? "k" : ""}">${h === 0 ? "지금" : h % 3 === 0 ? `${WX.kst(t).h}시` : ""}</b>`).join("");
    $("#track").setAttribute("aria-valuemax", String(max()));
  }
  function render() {
    const pct = max() ? (state.h / max()) * 100 : 0, text = state.h === 0 ? `지금 · ${HQ.whenText(0)}` : `${HQ.hourText(state.h)} 예보`;
    $("#knob").style.left = `${pct}%`;
    $("#fill").style.width = `${pct}%`;
    $("#bubble").style.left = `${pct}%`;
    $("#bubble").textContent = text;
    $("#track").setAttribute("aria-valuenow", String(state.h));
    $("#track").setAttribute("aria-valuetext", text);
  }
  function stop() {
    clearInterval(timer);
    timer = null;
    $("#play use").setAttribute("href", `${WX.ICONS}#i-play`);
    $("#play").setAttribute("aria-label", "재생");
  }
  function play() {
    if (timer) { stop(); return; }
    if (state.h >= max()) HQ.setHour(0);
    $("#play use").setAttribute("href", `${WX.ICONS}#i-pause`);
    $("#play").setAttribute("aria-label", "멈춤");
    timer = setInterval(() => { if (state.h >= max()) { stop(); return; } HQ.setHour(state.h + 1); }, 650);
  }
  function init() {
    ticks();
    const track = $("#track");
    const at = e => { const r = track.getBoundingClientRect(); return ((e.clientX - r.left) / r.width) * max(); };
    track.addEventListener("pointerdown", e => { dragging = true; track.classList.add("drag"); track.setPointerCapture(e.pointerId); stop(); HQ.setHour(at(e)); });
    track.addEventListener("pointermove", e => { if (dragging) HQ.setHour(at(e)); });
    const end = () => { dragging = false; track.classList.remove("drag"); };
    track.addEventListener("pointerup", end);
    track.addEventListener("pointercancel", end);
    $("#play").addEventListener("click", play);
    document.addEventListener("keydown", e => {
      const target = e.target;
      if (target.closest && target.closest("input, textarea, select, [contenteditable], .maplibregl-canvas-container")) return;
      if (document.body.classList.contains("modal-open") || state.view !== "map") return;
      const moves = { ArrowRight: state.h + 1, ArrowLeft: state.h - 1, Home: 0, End: max() };
      if (!(e.key in moves)) return;
      if ((e.key === "Home" || e.key === "End") && target !== track) return;
      e.preventDefault();
      stop();
      HQ.setHour(moves[e.key]);
    });
  }
  HQ.time = { init, render, stop, retick: ticks };
})();

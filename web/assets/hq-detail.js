/* 선택 현장 상세: 히어로(하늘 반응형)·특보/법정 칩·수치 4개·앞으로 24시간·법정 안내(설계서 3.2).
   칩·수치·타임라인 부품은 현장 화면과 함께 쓰는 parts.js에 있다. */
(function () {
  "use strict";
  const { $ } = WX;
  const P = WX.parts;
  const HQ = window.HQ, state = HQ.state;
  const els = () => ({ tl: $("#tl"), rain: $("#cR"), wind: $("#cW"), spark: $("#spark"), hours: $("#hours"), note: $("#tlNote"), cursor: $("#cursor") });

  function moveCursor() { P.cursor(els(), state.h, HQ.hourText(state.h)); }
  function render(first) {
    const site = state.sel;
    if (!site) return;
    const h = state.h, v = HQ.value(site, h);
    $("#dCat").textContent = [site.category, site.region].filter(Boolean).join(" · ");
    $("#dName").textContent = site.name;
    $("#hero").className = `hero ${P.heroClass(P.heroSky(site, state.times, h))}${h === 0 && site.state !== "ok" ? " dim" : ""}`;
    $("#hWhen").textContent = h > 0 ? `${HQ.hourText(h)} 예보`
      : site.as_of ? `${WX.kst(site.as_of).hm} 관측${site.state === "stale" ? " · 이번 수집 실패" : ""}` : "관측 자료 없음";
    WX.tween($("#hTemp"), v ? v.temp : null, 1, 600);
    $("#hSent").innerHTML = h === 0 ? WX.leadBold(site.summary) : P.forecastSentence(v, HQ.hourText(h));
    $("#dChips").innerHTML = P.chips(site, state.latest.status.warnings === "ok");
    $("#dTiles").innerHTML = P.tiles(v, h === 0);
    $("#dLegal").innerHTML = P.legal(site);
    if (first) P.timeline(els(), site, state.times, state.latest.forecast_issued_at, HQ.whenText);
    moveCursor();
  }

  HQ.detail = {
    init() {
      P.scrub(els(), () => state.times.length, h => HQ.setHour(h), () => { if (HQ.time) HQ.time.stop(); });
      $("#dClose").addEventListener("click", () => HQ.close());
      $("#bNotice").addEventListener("click", () => { if (HQ.notice && state.sel) HQ.notice.open(state.sel); });
    },
    open(site, first) {
      $("#detail").classList.add("open");
      $("#detail").inert = false;
      const link = $("#bSite");
      link.setAttribute("href", `site.html?id=${encodeURIComponent(site.id)}`);
      link.hidden = false;
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

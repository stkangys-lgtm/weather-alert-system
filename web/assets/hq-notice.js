/* 전파 문안 창(현장·전 현장)과 현장 목록 표. 문안은 Python이 만든 사내 문체를 그대로 보여 준다. */
(function () {
  "use strict";
  const { $, $$, esc, fmt } = WX;
  const HQ = window.HQ, state = HQ.state;
  let lastFocus = null;
  // 모달이 열린 동안 나머지 화면은 초점·화면 읽기에서 뺀다(닫으면 원래대로).
  const PAGE = ["#map", "header.top", "#banner", "#sheet", "#detail", ".legend", ".mapctl", "#scrub", "#tableView"];
  let saved = null;

  function open(site) {
    const L = state.latest;
    lastFocus = document.activeElement;
    $("#mTitle").textContent = site ? `전파 문안 · ${site.short}` : "전파 문안 · 전 현장";
    $("#mNote").textContent = `${WX.kst(L.generated_at).hm} 수집 자료 기준 · 기상청 관측·예보`;
    $("#mText").textContent = site ? site.notice : L.national.notice;
    document.body.classList.add("modal-open");
    saved = PAGE.map(sel => { const el = $(sel); const was = el.inert; el.inert = true; return [el, was]; });
    $("#modal").inert = false;
    $("#scrim").classList.add("open");
    $("#modal").classList.add("open");
    $("#mCopy").focus();
  }
  function close() {
    if (!$("#modal").classList.contains("open")) return false;
    document.body.classList.remove("modal-open");
    $("#scrim").classList.remove("open");
    $("#modal").classList.remove("open");
    $("#modal").inert = true;
    if (saved) saved.forEach(([el, was]) => { el.inert = was; });
    saved = null;
    if (lastFocus && lastFocus.focus) lastFocus.focus();
    return true;
  }
  async function copy() {
    if (await WX.copy($("#mText").textContent)) {
      close();
      WX.toast("전파 문안을 복사했습니다");
      return;
    }
    // 브라우저가 자동 복사를 막으면 문안을 선택해 두고 직접 복사하도록 안내한다.
    const range = document.createRange();
    range.selectNodeContents($("#mText"));
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    WX.toast("자동 복사가 막혀 있습니다. 선택된 문안을 직접 복사해 주세요");
  }
  function trapFocus(e) {
    if (e.key !== "Tab" || !$("#modal").classList.contains("open")) return;
    const items = $$("#modal button"), first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  function renderTable() {
    $("#tvWhen").textContent = `${HQ.whenText(0)} 기준`;
    $("#tvBody").innerHTML = HQ.ordered(0, "rain").map(site => {
      const v = HQ.value(site, 0) || {};
      const flags = site.warnings.map(w => ({ c: WX.warningChip(w), icon: "i-alert" }))
        .concat(site.legal.map(l => ({ c: WX.legalChip(l), icon: "i-shield" })));
      const obs = site.state === "ok" ? `${WX.kst(site.as_of).hm} 관측`
        : site.state === "stale" ? `<span class="mute">${WX.kst(site.as_of).hm} 관측 · 이번 수집 실패</span>` : '<span class="mute">자료 없음</span>';
      return `<tr data-id="${esc(site.id)}" tabindex="0"><th scope="row"><b>${esc(site.short)}</b><small>${esc(site.name)}</small></th>`
        + `<td>${esc(site.region || "-")}</td><td>${obs}</td>`
        + `<td class="num">${v.temp == null ? "-" : `${fmt(v.temp, 1)}°`}</td>`
        + `<td class="num">${esc(v.rainText == null ? "-" : v.rainText)}</td>`
        + `<td class="num">${fmt(v.wind, 1)}</td><td class="num">${v.humidity == null ? "-" : `${v.humidity}%`}</td>`
        + `<td>${flags.map(f => `<span class="chip ${f.c.cls || "mute"}">${WX.icon(f.icon)}${esc(f.c.text)}</span>`).join("") || '<span class="mute">없음</span>'}</td>`
        + `<td class="sum">${esc(site.summary)}</td></tr>`;
    }).join("");
  }
  function bindTable() {
    const pick = row => {
      const site = state.sites.find(s => s.id === row.dataset.id);
      if (!site) return;
      HQ.setView("map");
      HQ.select(site, true);
    };
    $("#tvBody").addEventListener("click", e => { const row = e.target.closest("tr"); if (row) pick(row); });
    $("#tvBody").addEventListener("keydown", e => {
      if (e.key !== "Enter") return;
      const row = e.target.closest("tr");
      if (row) pick(row);
    });
  }

  HQ.notice = {
    init() {
      $("#mClose").addEventListener("click", close);
      $("#mCancel").addEventListener("click", close);
      $("#scrim").addEventListener("click", close);
      $("#mCopy").addEventListener("click", copy);
      document.addEventListener("keydown", trapFocus);
      bindTable();
    },
    open,
    close,
  };
  HQ.table = { render: renderTable };
})();

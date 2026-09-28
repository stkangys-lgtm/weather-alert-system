/* 기상안전 관제 공통 도우미 — 본사·현장 화면이 함께 쓴다.
   계산 규칙(문장·자료 상태·정렬 기준)은 Python이 만들고, 여기서는 표시 형식과 작은 UI 동작만 다룬다. */
(function () {
  "use strict";
  const WX = (window.WX = window.WX || {});

  WX.REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  // 범례 눈금(사내 위험 기준 아님): 0.1 빗방울 경계, 3·15·30 기상청 약한·보통·강한·매우 강한 비 경계, 1은 시각 구분.
  WX.RAIN_BINS = [0.1, 1, 3, 15, 30];
  WX.RAIN_COLORS = ["#cde2fb", "#9ec5f4", "#5598e7", "#256abf", "#0d366b"];
  // 기상청 풍속 표현 경계(약간 강한 4, 강한 9, 매우 강한 14 m/s)에 맞춘 범례 눈금.
  WX.WIND_BINS = [4, 9, 14];
  WX.WIND_COLORS = ["#e7ecf1", "#c9e6dd", "#6fb9a2", "#2a7d66"];
  WX.DRY = "#b8c0c9";
  WX.CELL = "#e7ecf1";
  WX.ICONS = "assets/icons.svg";

  WX.$ = (sel, root) => (root || document).querySelector(sel);
  WX.$$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
  WX.esc = value => String(value == null ? "" : value).replace(/[&<>"']/g, ch =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
  WX.icon = (name, cls = "ic") => `<svg class="${cls}" aria-hidden="true"><use href="${WX.ICONS}#${name}"/></svg>`;

  WX.fmt = (value, dec = 1) => {
    if (value == null || value === "" || !isFinite(value)) return "-";
    const rounded = Math.round(Number(value) * 10 ** dec) / 10 ** dec;
    const text = (rounded === 0 ? 0 : rounded).toFixed(dec);
    return dec > 0 ? text.replace(/\.?0+$/, "") : text;
  };
  WX.mmText = label => {
    if (label == null || label === "-") return "-";
    if (label === "<1") return "1mm 미만";
    if (/ 이상$/.test(label)) return label.replace(/ 이상$/, "mm 이상");
    return `${label}mm`;
  };

  WX.rainStep = mm => {
    let step = -1;
    if (mm == null) return step;
    WX.RAIN_BINS.forEach((bin, i) => { if (mm >= bin) step = i; });
    return step;
  };
  WX.rainColor = (mm, empty = WX.DRY) => { const step = WX.rainStep(mm); return step < 0 ? empty : WX.RAIN_COLORS[step]; };
  WX.windColor = ms => {
    if (ms == null) return WX.CELL;
    let step = 0;
    WX.WIND_BINS.forEach((bin, i) => { if (ms >= bin) step = i + 1; });
    return WX.WIND_COLORS[step];
  };

  const KST_PARTS = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit",
    day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  WX.kst = value => {
    const date = value instanceof Date ? value : new Date(value);
    const p = {};
    KST_PARTS.formatToParts(date).forEach(part => { p[part.type] = part.value; });
    return { y: +p.year, m: +p.month, d: +p.day, h: +p.hour, mi: +p.minute,
             date: `${p.year}-${p.month}-${p.day}`, hm: `${p.hour}:${p.minute}`, ms: date.getTime() };
  };
  // Python narrative._hour_label과 같은 규칙: 같은 날 "21시", 다음 날 "내일 3시", 그 뒤 "9/27 1시".
  WX.hourLabel = (at, ref) => {
    const a = WX.kst(at), r = WX.kst(ref);
    const diff = Math.round((Date.UTC(a.y, a.m - 1, a.d) - Date.UTC(r.y, r.m - 1, r.d)) / 86400000);
    const prefix = diff === 0 ? "" : diff === 1 ? "내일 " : `${a.m}/${a.d} `;
    return `${prefix}${a.h}시`;
  };

  // 0 = 지금(관측 시각), 1.. = 그 뒤 예보 시각. 현장마다 예보 시각이 조금 달라도 같은 시각끼리 비교한다.
  WX.timeline = (latest, count = 24) => {
    const base = latest.observed_at ? new Date(latest.observed_at).getTime()
      : Math.floor(new Date(latest.generated_at).getTime() / 3600000) * 3600000;
    const later = new Set();
    latest.sites.forEach(site => (site.hourly || []).forEach(hour => {
      const t = new Date(hour.at).getTime();
      if (t > base) later.add(t);
    }));
    return [base].concat(Array.from(later).sort((a, b) => a - b).slice(0, count));
  };
  WX.valueAt = (site, times, h) => {
    if (h === 0) {
      const now = site.now;
      if (!now) return null;
      // 강수량이 0.1mm 미만이어도 Python이 비로 판단(now.precip)했으면 빗방울로 보인다.
      const onset = now.precip === "rain" && !((now.rain_mm || 0) >= WX.RAIN_BINS[0]);
      return { temp: now.temp, feels: now.feels, rain: onset ? WX.RAIN_BINS[0] : now.rain_mm,
               rainText: onset ? "<0.1" : WX.fmt(now.rain_mm), wind: now.wind, humidity: now.humidity,
               pty: now.pty, precip: now.precip, sky: null, pop: null, observed: true };
    }
    if (!site._byTime) {
      site._byTime = new Map();
      (site.hourly || []).forEach(hour => site._byTime.set(new Date(hour.at).getTime(), hour));
    }
    const hour = site._byTime.get(times[h]);
    if (!hour) return null;
    return { temp: hour.temp, feels: hour.temp, rain: hour.rain_mm, rainText: hour.rain_label, wind: hour.wind,
             humidity: hour.humidity, pty: hour.pty, sky: hour.sky, pop: hour.pop, observed: false };
  };

  // 관측(지금)은 Python 판단(now.precip)을 따르고, 예보 시각은 예보 강수량으로 본다.
  WX.isRain = v => !!v && (v.observed && v.precip !== undefined ? v.precip === "rain" : (v.rain || 0) >= WX.RAIN_BINS[0]);
  // "내일"은 보는 사람의 오늘 기준(자정 뒤에 어제 자료를 보면 같은 시각이 "15시"로 바뀐다).
  WX.hourText = (times, h, now = Date.now()) => (h === 0 ? "지금" : WX.hourLabel(times[h], now));
  // "2026-09-30" + 1일 → "2026-10-01"
  WX.dayOffset = (date, n) => new Date(Date.UTC(+date.slice(0, 4), +date.slice(5, 7) - 1, +date.slice(8, 10) + n)).toISOString().slice(0, 10);
  // 하늘 상태 글자(단기·중기 예보) → 아이콘 이름
  WX.skyIcon = sky => {
    const s = sky || "";
    if (/비|소나기/.test(s)) return "i-rain";
    if (/눈/.test(s)) return "i-snow";
    if (/구름/.test(s)) return "i-csun";
    if (/맑/.test(s)) return "i-sun";
    return "i-cloud";
  };
  WX.weekday = date => "일월화수목금토"[new Date(`${date}T12:00:00+09:00`).getUTCDay()];
  WX.shortDate = date => `${Number(date.slice(5, 7))}/${Number(date.slice(8, 10))}`;

  // 상단 수집 상태(설계서 3.2·5.6·6). 실패·지연은 회색으로 두고 주황·빨강을 쓰지 않는다.
  // 보는 사람의 지금 시각(now)과 비교해, 예정된 다음 수집이 45분 넘게 지나면 "수집 지연"으로 표시한다.
  WX.STALL_MS = 45 * 60 * 1000;
  WX.collectionStatus = (latest, now = Date.now()) => {
    const g = WX.kst(latest.generated_at), today = WX.kst(now);
    const n = latest.schedule && latest.schedule.next_run_at ? WX.kst(latest.schedule.next_run_at) : null;
    const dayDiff = x => Math.round((Date.UTC(x.y, x.m - 1, x.d) - Date.UTC(today.y, today.m - 1, today.d)) / 86400000);
    const stamp = x => (dayDiff(x) === 0 ? x.hm : `${x.m}/${x.d} ${x.hm}`);
    const nextText = x => (dayDiff(x) === 0 ? x.hm : dayDiff(x) === 1 ? `내일 ${x.hm}` : `${x.m}/${x.d} ${x.hm}`);
    const next = n ? `다음 수집 <b class="num">${nextText(n)}</b>` : "";
    const status = latest.status || {};
    const failed = latest.sites.filter(s => s.state !== "ok").length;
    if (n && now > n.ms + WX.STALL_MS) {
      return { level: "fail", html: `수집 지연 · 마지막 수집 <b class="num">${stamp(g)}</b>`,
               short: `<b class="num">${stamp(g)}</b> 수집 지연`,
               banner: `수집이 지연되고 있습니다 · 마지막 수집 ${stamp(g)} (예정된 ${stamp(n)} 수집이 없었습니다)` };
    }
    if (status.current === "failed") {
      const shown = latest.sites.filter(s => s.as_of).map(s => new Date(s.as_of).getTime());
      const obs = shown.length ? `${stamp(WX.kst(Math.max(...shown)))} 관측 자료 표시 중` : "표시할 관측 자료 없음";
      return { level: "fail", html: `<b class="num">${stamp(g)}</b> 수집 실패 · ${obs}`,
               short: `<b class="num">${stamp(g)}</b> 수집 실패`, banner: `${stamp(g)} 수집 실패 · ${obs}` };
    }
    if (status.current === "partial") {
      return { level: "warn", html: `<b class="num">${stamp(g)}</b> 수집 · ${failed}곳 실패 · ${next}`,
               short: `<b class="num">${stamp(g)}</b> · ${failed}곳 실패`,
               banner: `${stamp(g)} 수집에서 ${failed}개 현장의 관측 자료를 받지 못해 이전 자료 또는 "자료 없음"으로 표시합니다.` };
    }
    if (status.forecast && status.forecast !== "ok") {
      return { level: "warn", html: `<b class="num">${stamp(g)}</b> 수집 · 예보 ${status.forecast === "failed" ? "수집 실패" : "일부 실패"} · ${next}`,
               short: `<b class="num">${stamp(g)}</b> · 예보 실패`,
               banner: `${stamp(g)} 수집에서 예보 자료를 받지 못한 현장이 있어 해당 현장은 "예보 자료 없음"으로 표시합니다.` };
    }
    if (n && n.date !== g.date) {
      return { level: "ok", html: `마지막 수집 <b class="num">${stamp(g)}</b> · ${next}`,
               short: `마지막 <b class="num">${stamp(g)}</b>`, banner: null };
    }
    return { level: "ok", html: `정상 수집 · <b class="num">${stamp(g)}</b> 수집 · ${next}`,
             short: `<b class="num">${stamp(g)}</b> 수집`, banner: null };
  };

  WX.warningChip = w => {
    const preliminary = w.kind === "예비특보";
    const title = preliminary && !/예비특보/.test(w.title || "") ? `예비특보(${w.title})` : w.title;
    const crit = !preliminary && (w.level === "경보" || w.level === "중대경보");
    return { cls: crit ? "crit" : "warn", text: `${title} ${preliminary ? "발표" : "발효 중"}` };
  };
  WX.legalChip = l => ({
    cls: l.status === "법정 작업중지" ? "crit" : (l.status === "법정 조치 이행 필요" || l.status === "현장 확인 필요") ? "warn" : "",
    text: `${l.status} · ${l.title}`,
  });

  WX.leadBold = text => {
    const safe = WX.esc(text), cut = safe.indexOf(". ");
    return cut < 0 ? `<b>${safe}</b>` : `<b>${safe.slice(0, cut + 1)}</b>${safe.slice(cut + 1)}`;
  };

  // ?data=는 화면 확인용 시험 자료를 같은 사이트 안에서만 불러온다(외부 주소 불가).
  WX.dataUrl = fallback => {
    const asked = new URLSearchParams(location.search).get("data");
    return asked && /^[\w\-./]+\.json$/.test(asked) && !asked.includes("//") ? asked : fallback;
  };
  // 레이더 비구름(설계서 5.8): 영상 경로는 latest.json 기준 상대 경로(같은 폴더의 파일 이름만 허용).
  // 관측 뒤 90분이 지난 영상은 fresh=false → 화면은 숨기고 "레이더 자료 없음".
  WX.RADAR_MAX_MIN = 90;
  WX.radarInfo = (latest, now = Date.now()) => {
    const radar = latest && latest.radar;
    if (!radar || typeof radar.image !== "string" || !/^[\w.-]+\.png(\?v=\w+)?$/.test(radar.image)) return null;
    const corners = radar.corners;
    if (!Array.isArray(corners) || corners.length !== 4 || !corners.every(c => Array.isArray(c) && c.length === 2
      && c.every(n => typeof n === "number" && isFinite(n)))) return null;
    const at = new Date(radar.observed_at).getTime();
    if (!isFinite(at)) return null;
    const url = new URL(radar.image, new URL(WX.dataUrl("data/latest.json"), location.href)).href;
    const age = (now - at) / 60000;
    return { url, corners, time: WX.kst(at).hm, fresh: age >= 0 && age <= WX.RADAR_MAX_MIN };
  };
  // 비구름 켜기·끄기는 이 브라우저에만 기억한다(기본 켜짐). 저장소가 막힌 환경에서도 화면은 그대로 쓴다.
  let radarMemo = true;      // 저장소를 못 쓸 때 이번 화면에서만 유지하는 값
  let radarMemoOnly = false; // 한 번이라도 저장소 읽기·쓰기가 실패하면, 그 뒤로는 저장소를 다시 믿지 않고 이 값만 쓴다
  WX.radarPref = {
    get() {
      if (radarMemoOnly) return radarMemo;
      try { return window.localStorage.getItem("wx.radar") !== "0"; }
      catch (e) { radarMemoOnly = true; return radarMemo; }
    },
    set(on) {
      radarMemo = !!on;
      try { window.localStorage.setItem("wx.radar", on ? "1" : "0"); }
      catch (e) { radarMemoOnly = true; /* 기억하지 못해도 이번 화면에는 반영 */ }
    },
  };

  // 화면 자료 모양 점검: 맞지 않으면 그리기 전에 "불러오지 못했습니다" 안내로 보낸다(반쯤 그린 화면 방지).
  WX.validLatest = data => {
    const isObj = v => !!v && typeof v === "object" && !Array.isArray(v);
    const isTime = v => typeof v === "string" && isFinite(new Date(v).getTime());
    if (!isObj(data) || data.schema !== 1 || !Array.isArray(data.sites) || !data.sites.length) return false;
    if (!isTime(data.generated_at) || !isObj(data.status) || !isObj(data.national) || !isObj(data.schedule)) return false;
    return data.sites.every(s => isObj(s) && typeof s.id === "string" && typeof s.name === "string" && typeof s.short === "string"
      && typeof s.state === "string" && Array.isArray(s.warnings) && Array.isArray(s.legal) && Array.isArray(s.hourly)
      && (s.as_of == null || isTime(s.as_of)));
  };
  WX.load = async url => {
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!WX.validLatest(data)) throw new Error("화면 자료 형식이 맞지 않습니다");
    return data;
  };

  // 숫자를 올라가며 표시한다. 탭이 가려져 애니메이션이 멈춰도 최종 값은 반드시 보이게 한다.
  WX.tween = (el, to, dec = 0, dur = 750) => {
    const suffix = el.dataset.suffix || "";
    if (to == null || !isFinite(to)) { el.dataset.v = ""; el.textContent = "-"; return; }
    const prev = parseFloat(el.dataset.v), from = isFinite(prev) ? prev : 0;
    el.dataset.v = String(to);
    const done = () => { el.textContent = WX.fmt(to, dec) + suffix; };
    if (WX.REDUCED || from === to) { done(); return; }
    const token = (el._tween = (el._tween || 0) + 1), start = performance.now();
    const step = t => {
      if (el._tween !== token) return;
      const p = Math.min(1, (t - start) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = WX.fmt(from + (to - from) * e, dec) + suffix;
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
    setTimeout(() => { if (el._tween === token) done(); }, dur + 80);
  };

  WX.toast = text => {
    let el = WX.$("#toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "toast"; el.className = "toast"; el.setAttribute("role", "status");
      el.innerHTML = `${WX.icon("i-check")}<span></span>`;
      document.body.appendChild(el);
    }
    el.querySelector("span").textContent = text;
    el.classList.add("show");
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.remove("show"), 2400);
  };
  WX.copy = async text => {
    try { await navigator.clipboard.writeText(text); return true; } catch (e) { /* 아래 대체 방식 */ }
    const area = document.createElement("textarea");
    area.value = text; area.setAttribute("readonly", "");
    area.style.cssText = "position:fixed;left:-9999px;top:0";
    document.body.appendChild(area); area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    area.remove();
    return ok;
  };
})();

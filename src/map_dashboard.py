"""지도 중심 전사 기상안전 관제 화면(정적 HTML)을 생성한다.

지도 경계 데이터: southkorea-maps의 KOSTAT 2018 시도 경계(MIT)를 단순화한
``src/kr_map_data.json``. 공개 화면에는 담당자 이름·연락처를 포함하지 않는다.
"""

import json
import os
from html import escape

from src.feels_like import compute_feels_like


LEVEL_COLOR = {
    "정상": "#18c875",
    "주의": "#ffb020",
    "경보": "#ff4d5f",
    "데이터없음": "#87948f",
}
LEVEL_LABEL = {"정상": "정상", "주의": "선제주의", "경보": "선제경계", "데이터없음": "데이터없음"}

_DATA_PATH = os.path.join(os.path.dirname(__file__), "kr_map_data.json")
with open(_DATA_PATH, encoding="utf-8") as _f:
    _MAP = json.load(_f)


def _project(lat, lon):
    x = (lon - _MAP["lon_min"]) * _MAP["cos"] * _MAP["scale"] + _MAP["pad"]
    y = (_MAP["lat_max"] - lat) * _MAP["scale"] + _MAP["pad"]
    return round(x, 1), round(y, 1)


def _province_paths_svg():
    return "".join(
        f'<path class="province" d="{info["d"]}" />'
        for info in _MAP["paths"].values()
    )


def _safe_json(value):
    """HTML script 문맥을 깨는 문자열을 차단하면서 UTF-8 JSON을 만든다."""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


_PAGE_TEMPLATE = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#003b2d">
<title>HYUNDAI ASAN · 기상안전 통합관제</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>
:root { --green:#009a44; --green2:#18c875; --deep:#003b2d; --ink:#10231d; --muted:#66756f;
  --line:rgba(0,59,45,.11); --surface:rgba(255,255,255,.94); --danger:#ff4d5f; --warn:#ffb020; }
* { box-sizing:border-box; }
html,body { margin:0; min-height:100%; }
body { background:#eaf1ee; color:var(--ink); font-family:"Pretendard",-apple-system,"Segoe UI",sans-serif;
  -webkit-font-smoothing:antialiased; overflow-x:hidden; }
button,input,a { font:inherit; }
button { -webkit-tap-highlight-color:transparent; }
.shell { min-height:100vh; background:
  radial-gradient(circle at 80% -10%,rgba(24,200,117,.2),transparent 28rem),
  linear-gradient(135deg,#f7faf9,#e6efeb); }
.topbar { height:72px; padding:0 26px; color:#fff; background:linear-gradient(110deg,#002f24,#00543c 60%,#007a3d);
  display:flex; align-items:center; justify-content:space-between; gap:18px; box-shadow:0 8px 30px rgba(0,59,45,.2); }
.brand { display:flex; align-items:center; gap:13px; min-width:220px; }
.brand-mark { width:38px; height:38px; display:grid; place-items:center; border:1px solid rgba(255,255,255,.42);
  color:#fff; font-weight:900; letter-spacing:-.1em; transform:skew(-7deg); }
.brand strong { display:block; font-size:.92rem; letter-spacing:.08em; }
.brand small { color:rgba(255,255,255,.66); font-size:.7rem; letter-spacing:.04em; }
.topstats { display:flex; align-items:center; gap:8px; }
.topstat { min-width:78px; padding:8px 11px; border-radius:10px; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.1); }
.topstat b { font-size:1.05rem; margin-right:4px; }.topstat span { font-size:.7rem; color:rgba(255,255,255,.7); }
.updated { display:flex; align-items:center; gap:8px; color:rgba(255,255,255,.75); font-size:.76rem; white-space:nowrap; }
.live { width:7px;height:7px;border-radius:50%;background:#60f2a6;box-shadow:0 0 0 5px rgba(96,242,166,.12); }
.workspace { display:grid; grid-template-columns:minmax(0,1fr) 390px; height:calc(100vh - 72px); min-height:650px; }
.map-column { min-width:0; display:flex; flex-direction:column; padding:18px 12px 18px 20px; }
.commandbar { display:flex; align-items:center; gap:9px; padding:0 4px 13px; }
.search { position:relative; width:min(300px,35vw); }.search span { position:absolute;left:13px;top:10px;color:#82918b; }
.search input { width:100%;height:40px;padding:0 12px 0 37px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.88);outline:none; }
.search input:focus { border-color:var(--green);box-shadow:0 0 0 3px rgba(0,154,68,.1); }
.filters { display:flex;gap:6px;overflow-x:auto;scrollbar-width:none; }
.filter { height:38px;padding:0 14px;border-radius:10px;border:1px solid var(--line);background:rgba(255,255,255,.72);color:var(--muted);font-size:.8rem;font-weight:700;cursor:pointer;white-space:nowrap; }
.filter:hover,.filter.active { background:var(--deep);color:#fff;border-color:var(--deep); }
.list-link { margin-left:auto;height:38px;padding:0 14px;border-radius:10px;background:#fff;border:1px solid var(--line);color:var(--deep);text-decoration:none;display:flex;align-items:center;gap:7px;font-size:.8rem;font-weight:750;white-space:nowrap; }
.map-stage { position:relative;flex:1;min-height:0;overflow:hidden;border-radius:22px;background:
  linear-gradient(rgba(0,74,52,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(0,74,52,.035) 1px,transparent 1px),#f9fcfb;
  background-size:34px 34px;box-shadow:0 18px 55px rgba(0,50,36,.11);border:1px solid rgba(255,255,255,.9); }
.map-label { position:absolute;left:22px;top:20px;z-index:3;pointer-events:none; }
.map-label small { display:block;color:var(--green);font-size:.67rem;font-weight:850;letter-spacing:.14em;margin-bottom:4px; }
.map-label strong { font-size:1rem; }.map-label span { color:var(--muted);font-size:.75rem;margin-left:8px; }
.map-viewport { width:100%;height:100%;overflow:hidden;touch-action:none;cursor:grab; }
.map-viewport.dragging { cursor:grabbing; }.map-canvas { width:100%;height:100%;transform-origin:center;transition:transform .18s ease; }
.kr-map { width:100%;height:100%;display:block;filter:drop-shadow(0 10px 22px rgba(0,70,45,.08)); }
.province { fill:#dceae4;stroke:#fff;stroke-width:1.7;transition:fill .2s; }.province:hover { fill:#cfe2d9; }
.marker { cursor:pointer;outline:none; }.marker-hit { fill:transparent; }.marker-core { fill:var(--marker);stroke:#fff;stroke-width:2.2;filter:drop-shadow(0 3px 4px rgba(0,0,0,.24));transition:transform .15s;transform-box:fill-box;transform-origin:center; }
.marker:hover .marker-core,.marker:focus .marker-core,.marker.selected .marker-core { transform:scale(1.45);stroke:var(--deep); }
.marker-legal { fill:#fff;stroke:#b31326;stroke-width:2; }.marker-legal-text { fill:#b31326;font-size:7px;font-weight:950;text-anchor:middle;pointer-events:none; }
.marker-halo { fill:none;stroke:var(--marker);stroke-width:2;opacity:.36;transform-box:fill-box;transform-origin:center;animation:pulse 2.3s ease-out infinite; }
.marker[data-level="정상"] .marker-halo,.marker[data-level="데이터없음"] .marker-halo { display:none; }
.marker-label { font-size:10px;font-weight:750;fill:#183b30;paint-order:stroke;stroke:#f9fcfb;stroke-width:3px;stroke-linejoin:round;pointer-events:none;opacity:0;transition:opacity .15s; }
.marker:hover .marker-label,.marker:focus .marker-label,.marker.selected .marker-label { opacity:1; }
.tooltip { position:absolute;z-index:6;display:none;pointer-events:none;background:rgba(0,43,32,.94);color:#fff;border-radius:9px;padding:8px 10px;font-size:.72rem;box-shadow:0 7px 20px rgba(0,0,0,.16); }
.tooltip.show { display:block; }.tooltip b { display:block;margin-bottom:2px; }.tooltip span { color:rgba(255,255,255,.65); }
.zoom { position:absolute;right:16px;bottom:16px;z-index:4;display:grid;gap:5px;padding:5px;background:rgba(255,255,255,.9);border:1px solid var(--line);border-radius:12px;box-shadow:0 6px 18px rgba(0,59,45,.1); }
.zoom button { width:34px;height:32px;border:0;border-radius:8px;background:transparent;color:var(--deep);font-size:1rem;cursor:pointer; }.zoom button:hover { background:#e7f3ed; }
.map-legend { position:absolute;left:18px;bottom:16px;z-index:3;display:flex;gap:12px;padding:8px 11px;border-radius:10px;background:rgba(255,255,255,.86);backdrop-filter:blur(8px);font-size:.68rem;color:var(--muted); }
.dot { display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px; }
.detail { margin:18px 20px 18px 8px;border-radius:22px;background:var(--surface);border:1px solid rgba(255,255,255,.9);box-shadow:0 18px 55px rgba(0,50,36,.1);overflow:hidden;display:flex;flex-direction:column;min-width:0; }
.detail-accent { height:4px;background:var(--selected,var(--green));transition:background .2s; }
.detail-scroll { overflow:auto;padding:22px;scrollbar-width:thin; }.detail-eyebrow { display:flex;justify-content:space-between;align-items:center;color:var(--green);font-size:.68rem;font-weight:850;letter-spacing:.12em; }
.status-badge { letter-spacing:0;padding:5px 9px;border-radius:999px;background:color-mix(in srgb,var(--selected) 12%,white);color:var(--selected); }
.detail h1 { margin:13px 0 3px;font-size:1.45rem;line-height:1.25;letter-spacing:-.035em; }.category { color:var(--muted);font-size:.78rem; }
.weather-main { margin:20px 0 14px;display:grid;grid-template-columns:1fr 1fr;gap:10px; }
.temperature { grid-row:span 2;border-radius:16px;padding:17px;background:linear-gradient(145deg,#e9f8f0,#f8fcfa); }
.temperature small,.metric small { display:block;color:var(--muted);font-size:.68rem;margin-bottom:6px; }.temperature b { font-size:2.5rem;letter-spacing:-.07em; }
.metric { padding:12px 14px;border:1px solid var(--line);border-radius:13px;background:#fff; }.metric b { font-size:1rem; }
.reasons { display:none;margin:0 0 16px;padding:12px;border-radius:12px;background:#fff3f4;color:#b42b3c;font-size:.76rem;font-weight:700;line-height:1.45; }.reasons.show { display:block; }
.legal-list { display:grid;gap:7px; }.legal-item { padding:10px 11px;border-radius:11px;background:#f3f7f5;border:1px solid rgba(0,91,60,.15);font-size:.72rem;line-height:1.42; }
.legal-item.action { background:#fff2f3;border-color:#f1bdc3;color:#8f2531; }.legal-item.verify { background:#fff8e8;border-color:#efd69a;color:#755000; }
.legal-item b { display:block;margin-bottom:3px; }.legal-item small { display:block;color:inherit;opacity:.72; }.legal-item p { margin:4px 0 0; }
.warning-list { display:grid;gap:7px; }.warning-item { padding:10px 11px;border-radius:11px;background:#fff2e4;border:1px solid #efc27f;color:#764700;font-size:.72rem;line-height:1.42; }
.warning-item b { display:block;color:#9a4800;margin-bottom:3px; }.warning-item small { display:block;color:inherit;opacity:.8; }
.section-head { margin:19px 0 9px;display:flex;justify-content:space-between;align-items:center; }.section-head b { font-size:.8rem; }.section-head span { color:var(--muted);font-size:.67rem; }
.forecast { display:flex;gap:7px;overflow-x:auto;padding:2px 0 7px;scroll-snap-type:x mandatory; }.fc { min-width:70px;padding:10px 7px;border:1px solid var(--line);border-radius:12px;text-align:center;scroll-snap-align:start;background:#fff; }.fc time { font-size:.66rem;color:var(--muted); }.fc .icon { font-size:1.2rem;margin:6px 0; }.fc b { display:block;font-size:.82rem; }.fc small { color:#39826a;font-size:.65rem; }
.event-list { display:grid;gap:7px; }.event { padding:10px 11px;border-radius:11px;background:#fff7eb;border:1px solid #ffe0ac;font-size:.73rem;color:#7d5200; }.event b { margin-right:5px; }.no-event { padding:12px;border-radius:11px;background:#edf8f2;color:#267556;font-size:.74rem; }
.actions { display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:20px; }.action { height:40px;border:1px solid var(--line);border-radius:11px;color:var(--deep);background:#fff;text-decoration:none;display:grid;place-items:center;font-size:.75rem;font-weight:750; }.action.primary { background:var(--deep);color:#fff;border-color:var(--deep); }
.drawer-handle { display:none; }
@keyframes pulse { 0%{transform:scale(.8);opacity:.55} 75%,100%{transform:scale(2.4);opacity:0} }
@media (max-width:900px) { .topbar { height:auto;min-height:66px;padding:13px 16px; }.topstats { display:none; }.updated span:last-child { display:none; }
  .workspace { display:block;height:auto;min-height:calc(100vh - 66px); }.map-column { height:calc(68vh - 30px);min-height:460px;padding:12px; }.detail { margin:-20px 12px 18px;position:relative;z-index:8;max-height:none; }.drawer-handle { display:block;width:42px;height:4px;background:#cbd8d2;border-radius:99px;margin:9px auto -7px; }.detail-scroll { padding:18px; }.list-link span { display:none; } }
@media (max-width:560px) { .brand small{display:none}.brand{min-width:0}.brand strong{font-size:.8rem}.updated{font-size:.67rem}.commandbar{flex-wrap:wrap}.search{width:100%;order:1}.filters{max-width:calc(100% - 48px);order:2}.list-link{order:2;width:40px;padding:0;justify-content:center}.map-column{height:62vh;min-height:430px}.map-label span{display:none}.map-legend{gap:7px;left:10px;bottom:10px}.marker-label{display:none}.detail h1{font-size:1.28rem} }
@media (prefers-reduced-motion:reduce) { * { scroll-behavior:auto!important;animation:none!important;transition:none!important; } }
</style>
</head>
<body><main class="shell">
  <header class="topbar">
    <div class="brand"><div class="brand-mark">HA</div><div><strong>HYUNDAI ASAN</strong><small>기상안전 통합관제</small></div></div>
    <div class="topstats">
      <div class="topstat"><b>__TOTAL__</b><span>전체</span></div><div class="topstat"><b style="color:#ffcf70">__WARNING__</b><span>기상특보</span></div><div class="topstat"><b style="color:#ff9aa5">__LEGAL__</b><span>법정조치</span></div>
      <div class="topstat"><b style="color:#ff7784">__ALERT__</b><span>선제경계</span></div><div class="topstat"><b style="color:#ffc65d">__CAUTION__</b><span>선제주의</span></div>
    </div>
    <div class="updated"><i class="live"></i><span>LIVE</span><span>__UPDATED__ 갱신</span></div>
  </header>
  <section class="workspace">
    <div class="map-column">
      <nav class="commandbar" aria-label="현장 필터">
        <label class="search"><span>⌕</span><input id="search" type="search" placeholder="현장명 검색" aria-label="현장명 검색"></label>
        <div class="filters"><button class="filter active" data-filter="all">전체</button><button class="filter" data-filter="risk">위험 현장</button><button class="filter" data-filter="건축">건축</button><button class="filter" data-filter="토목">토목</button></div>
        <a class="list-link" href="sites.html" aria-label="대시보드 목록 보기">▦ <span>목록 보기</span></a>
      </nav>
      <div class="map-stage">
        <div class="map-label"><small>ALL SITES OVERVIEW</small><strong>전국 현장 분포</strong><span id="visibleCount">__TOTAL__개 현장</span></div>
        <div class="map-viewport" id="viewport"><div class="map-canvas" id="canvas">
          <svg class="kr-map" viewBox="0 0 __WIDTH__ __HEIGHT__" role="img" aria-label="대한민국 현장 기상 지도">
            <g id="provinces">__PROVINCES__</g><g id="markers">__MARKERS__</g>
          </svg>
        </div></div>
        <div class="tooltip" id="tooltip"></div>
        <div class="map-legend"><span><i class="dot" style="background:#18c875"></i>정상</span><span><i class="dot" style="background:#ffb020"></i>선제주의</span><span><i class="dot" style="background:#ff4d5f"></i>선제경계</span><span>⚖ 법정조치</span></div>
        <div class="zoom"><button id="zoomIn" aria-label="지도 확대">＋</button><button id="zoomOut" aria-label="지도 축소">−</button><button id="zoomReset" aria-label="지도 원위치">⌂</button></div>
      </div>
    </div>
    <aside class="detail" id="detail"><div class="drawer-handle"></div><div class="detail-accent"></div><div class="detail-scroll">
      <div class="detail-eyebrow"><span>SELECTED SITE</span><span class="status-badge" id="level"></span></div>
      <h1 id="siteName"></h1><div class="category" id="category"></div>
      <div class="weather-main"><div class="temperature"><small>현재 기온</small><b id="temp"></b><small id="feels"></small></div><div class="metric"><small>풍속</small><b id="wind"></b></div><div class="metric"><small>1시간 강수</small><b id="rain"></b></div></div>
      <div class="reasons" id="reasons"></div>
      <div class="section-head"><b>기상청 공식 발표</b><span>특보 조회서비스</span></div><div class="warning-list" id="weatherWarnings"></div>
      <div class="section-head"><b>법정 조치·현장 확인</b><span>작업·실측 기반</span></div><div class="legal-list" id="legalSignals"></div>
      <div class="section-head"><b>시간대별 예보</b><span>좌우로 밀어 보기</span></div><div class="forecast" id="forecast"></div>
      <div class="section-head"><b>예상 특이기상</b><span>향후 10일</span></div><div class="event-list" id="events"></div>
      <div class="actions"><a class="action primary" href="latest-alert.txt">전파 문안 보기</a><a class="action" href="sites.html">전체 현장 목록</a></div>
    </div></aside>
  </section>
</main>
<script>
const SITES=__SITES__;
const LEVEL_COLOR={"정상":"#18c875","주의":"#ffb020","경보":"#ff4d5f","데이터없음":"#87948f"};
const LEVEL_LABEL={"정상":"정상","주의":"선제주의","경보":"선제경계","데이터없음":"데이터없음"};
const iconFor=(f)=>{const p=f.PTY||"";if(p&&p!=="없음"&&p!=="-")return p.includes("눈")?"🌨️":"🌧️";return f.SKY==="맑음"?"☀️":f.SKY==="흐림"?"☁️":"⛅"};
const safe=(v,fallback="-")=>v===null||v===undefined||v===""?fallback:String(v);
const esc=(v)=>safe(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let selected=0,activeFilter="all",scale=1,panX=0,panY=0,drag=null;
function renderDetail(idx){selected=idx;const s=SITES[idx];if(!s)return;document.documentElement.style.setProperty("--selected",LEVEL_COLOR[s.level]);
 document.querySelectorAll(".marker").forEach(m=>m.classList.toggle("selected",Number(m.dataset.idx)===idx));
 document.getElementById("level").textContent=s.status_label||LEVEL_LABEL[s.level]||s.level;document.getElementById("siteName").textContent=s.site_name;document.getElementById("category").textContent=`${s.category} 현장 · 위도 ${s.lat.toFixed(2)}, 경도 ${s.lon.toFixed(2)}`;
 document.getElementById("temp").textContent=`${safe(s.temp)}°`;document.getElementById("feels").textContent=s.feels===null?"체감온도 정보 없음":`체감 ${s.feels}°C`;
 document.getElementById("wind").textContent=`${safe(s.wsd)} m/s`;document.getElementById("rain").textContent=`${safe(s.rn1)} mm`;
 const reasons=document.getElementById("reasons");reasons.textContent=s.reasons.length?s.reasons.join(" · "):"";reasons.classList.toggle("show",s.reasons.length>0);
 document.getElementById("weatherWarnings").innerHTML=!s.weather_warnings_available?'<div class="warning-item"><b>❔ 특보 수신 실패</b><small>기상청 특보를 별도로 확인해 주세요.</small></div>':s.weather_warnings.length?s.weather_warnings.map(w=>`<div class="warning-item"><b>📢 ${esc(w.kind)} · ${esc(w.title)}</b><small>${esc((w.matched_areas||w.areas||[]).join(", "))}</small></div>`).join(""):'<div class="no-event">현재 해당 현장에 발표된 기상특보 없음</div>';
 document.getElementById("legalSignals").innerHTML=s.legal_signals.length?s.legal_signals.map(x=>{const cls=["법정 작업중지","법정 조치 이행 필요"].includes(x.status)?"action":"verify";return `<div class="legal-item ${cls}"><b>${esc(x.status)} · ${esc(x.title)}</b><small>${esc(x.article)}</small><p>${esc(x.reason)}</p></div>`}).join(""):'<div class="no-event">등록된 법정 조치 신호 없음</div>';
 document.getElementById("forecast").innerHTML=(s.forecast.length?s.forecast.slice(0,12):[{}]).map(f=>`<div class="fc"><time>${esc((f.fcst_time||"").slice(0,2)||"--")}시</time><div class="icon">${f.fcst_time?iconFor(f):"·"}</div><b>${esc(f.TMP)}°</b><small>강수 ${esc(f.POP)}%</small></div>`).join("");
 document.getElementById("events").innerHTML=s.events.length?s.events.map(e=>`<div class="event"><b>${esc(e.date)}</b>${esc(e.kind)} · ${esc(e.detail)}</div>`).join(""):'<div class="no-event">예보 기간 내 주요 위험기상 없음</div>';
}
function applyFilter(){const q=document.getElementById("search").value.trim().toLowerCase();let count=0,first=null;document.querySelectorAll(".marker").forEach(m=>{const s=SITES[Number(m.dataset.idx)];const category=activeFilter==="all"||s.category===activeFilter||(activeFilter==="risk"&&["주의","경보"].includes(s.level));const show=category&&s.site_name.toLowerCase().includes(q);m.style.display=show?"":"none";if(show){count++;if(first===null)first=Number(m.dataset.idx)}});document.getElementById("visibleCount").textContent=`${count}개 현장`;if(first!==null&&document.querySelector(`.marker[data-idx="${selected}"]`).style.display==="none")renderDetail(first)}
document.querySelectorAll(".filter").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll(".filter").forEach(x=>x.classList.remove("active"));b.classList.add("active");activeFilter=b.dataset.filter;applyFilter()}));document.getElementById("search").addEventListener("input",applyFilter);
document.querySelectorAll(".marker").forEach(m=>{const idx=Number(m.dataset.idx);m.addEventListener("click",()=>renderDetail(idx));m.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();renderDetail(idx)}});m.addEventListener("mouseenter",e=>{const s=SITES[idx],t=document.getElementById("tooltip");t.innerHTML=`<b>${esc(s.site_name)}</b><span>${esc(s.status_label||LEVEL_LABEL[s.level]||s.level)} · ${esc(s.temp)}°C · 풍속 ${esc(s.wsd)}m/s</span>`;t.classList.add("show")});m.addEventListener("mousemove",e=>{const r=document.querySelector(".map-stage").getBoundingClientRect(),t=document.getElementById("tooltip");t.style.left=`${e.clientX-r.left+12}px`;t.style.top=`${e.clientY-r.top+12}px`});m.addEventListener("mouseleave",()=>document.getElementById("tooltip").classList.remove("show"))});
const canvas=document.getElementById("canvas"),viewport=document.getElementById("viewport");function transform(){canvas.style.transform=`translate(${panX}px,${panY}px) scale(${scale})`};function zoom(delta){scale=Math.min(2.2,Math.max(.82,scale+delta));if(scale===1){panX=0;panY=0}transform()};document.getElementById("zoomIn").onclick=()=>zoom(.2);document.getElementById("zoomOut").onclick=()=>zoom(-.2);document.getElementById("zoomReset").onclick=()=>{scale=1;panX=panY=0;transform()};viewport.addEventListener("pointerdown",e=>{if(e.target.closest(".marker"))return;drag={x:e.clientX,y:e.clientY,px:panX,py:panY};viewport.setPointerCapture(e.pointerId);viewport.classList.add("dragging")});viewport.addEventListener("pointermove",e=>{if(!drag)return;panX=drag.px+e.clientX-drag.x;panY=drag.py+e.clientY-drag.y;transform()});viewport.addEventListener("pointerup",()=>{drag=null;viewport.classList.remove("dragging")});
renderDetail(0);
</script></body></html>'''


def build_map_html(updated_str, site_rows):
    """현장 실황·예보·위험 이벤트를 지도 중심 단일 HTML로 만든다."""
    payload, markers = [], []
    for idx, row in enumerate(site_rows):
        current = row.get("current") or {}
        x, y = _project(row["lat"], row["lon"])
        level = row.get("display_level", row.get("level", "데이터없음"))
        color = LEVEL_COLOR.get(level, LEVEL_COLOR["데이터없음"])
        label = escape(row["site_name"] if len(row["site_name"]) <= 11 else row["site_name"][:10] + "…")
        markers.append(
            f'<g class="marker" tabindex="0" role="button" aria-label="{escape(row["site_name"])} {escape(level)}" '
            f'data-idx="{idx}" data-level="{escape(level)}" style="--marker:{color}" transform="translate({x} {y})">'
            '<circle class="marker-hit" r="15"/><circle class="marker-halo" r="7"/>'
            f'<circle class="marker-core" r="6.5"/>'
            + ('<circle class="marker-legal" cx="8" cy="-8" r="5"/><text class="marker-legal-text" x="8" y="-5.5">L</text>'
               if row.get("legal_status") in ("법정 작업중지", "법정 조치 이행 필요") else '')
            + f'<text class="marker-label" x="10" y="3">{label}</text></g>'
        )
        payload.append({
            "site_name": row["site_name"], "category": row["category"],
            "lat": row["lat"], "lon": row["lon"], "level": level,
            "reasons": row.get("reasons") or [], "temp": current.get("T1H"),
            "legal_signals": row.get("legal_signals") or [],
            "weather_warnings": row.get("weather_warnings") or [],
            "weather_warnings_available": row.get("weather_warnings_available", True),
            "status_label": (
                f"기상특보 {'경보' if level == '경보' else '주의보'}"
                if row.get("weather_warnings") else LEVEL_LABEL.get(level, level)
            ),
            "feels": compute_feels_like(current.get("T1H"), current.get("REH"), current.get("WSD")),
            "wsd": current.get("WSD"), "rn1": current.get("RN1"),
            "forecast": row.get("forecast") or [], "events": row.get("events") or [],
        })

    counts = {
        level: sum(1 for row in site_rows if row.get("display_level", row.get("level")) == level)
        for level in LEVEL_COLOR
    }
    warning_count = sum(1 for row in site_rows if row.get("weather_warnings"))
    legal_count = sum(
        1 for row in site_rows
        if row.get("legal_status") in ("법정 작업중지", "법정 조치 이행 필요")
    )
    replacements = {
        "__UPDATED__": escape(updated_str), "__TOTAL__": str(len(site_rows)),
        "__LEGAL__": str(legal_count),
        "__WARNING__": str(warning_count),
        "__ALERT__": str(counts["경보"]), "__CAUTION__": str(counts["주의"]),
        "__NORMAL__": str(counts["정상"]), "__WIDTH__": str(_MAP["width"]),
        "__HEIGHT__": str(_MAP["height"]), "__PROVINCES__": _province_paths_svg(),
        "__MARKERS__": "".join(markers), "__SITES__": _safe_json(payload),
    }
    html = _PAGE_TEMPLATE
    for token, value in replacements.items():
        html = html.replace(token, value)
    return html

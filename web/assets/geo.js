/* 지도: MapLibre 실지도를 우선 쓰고, 준비되지 않으면 자체 SVG 지도로 바꾼다(설계서 5.7).
   화면 코드는 어느 지도든 같은 방법(표식 추가·좌표 변환·이동)으로 다룬다. */
(function () {
  "use strict";
  const WX = window.WX;
  const STYLE = "https://tiles.openfreemap.org/styles/positron";
  const WAIT_MS = 9000;
  WX.KOREA = [[125.6, 34.1], [130.1, 38.75]];

  // 도시·도·바다 이름만 한국어로 남기고 나머지 글자는 숨긴다.
  function koreanLabels(map) {
    map.getStyle().layers.forEach(layer => {
      if (layer.type !== "symbol") return;
      if (/label_(city|town|state|country)|water_name/.test(layer.id)) {
        map.setLayoutProperty(layer.id, "text-field", ["coalesce", ["get", "name:ko"], ["get", "name:nonlatin"], ["get", "name"]]);
        map.setPaintProperty(layer.id, "text-color", "#8a8d8f");
        map.setPaintProperty(layer.id, "text-halo-color", "rgba(255,255,255,.9)");
      } else {
        map.setLayoutProperty(layer.id, "visibility", "none");
      }
    });
  }

  function maplibreAdapter(map) {
    let radarUrl = null;
    return {
      kind: "maplibre",
      canZoom: true,
      canRadar: true,
      // 레이더 비구름: 영상 한 장을 지명 글자(첫 symbol 레이어) 아래에 겹친다. 현장 표식은 HTML이라 늘 위에 있다.
      // 보일 때만 영상을 불러오고, 주소(?v=)가 바뀌면 같은 source의 영상만 바꾼다.
      setRadar(info, visible) {
        const shown = !!(info && visible);
        if (!shown) {
          if (map.getLayer("radar")) map.setLayoutProperty("radar", "visibility", "none");
          return;
        }
        if (!map.getSource("radar")) {
          const firstSymbol = map.getStyle().layers.find(layer => layer.type === "symbol");
          map.addSource("radar", { type: "image", url: info.url, coordinates: info.corners });
          map.addLayer({ id: "radar", type: "raster", source: "radar",
            paint: { "raster-opacity": 0.72, "raster-fade-duration": 0 } }, firstSymbol && firstSymbol.id);
        } else if (info.url !== radarUrl) {
          map.getSource("radar").updateImage({ url: info.url, coordinates: info.corners });
        }
        radarUrl = info.url;
        map.setLayoutProperty("radar", "visibility", "visible");
      },
      addMarker(el, lon, lat, anchor = "center", offset = [0, 0]) {
        const marker = new maplibregl.Marker({ element: el, anchor, offset }).setLngLat([lon, lat]).addTo(map);
        return { el, remove: () => marker.remove(), setLngLat: (x, y) => marker.setLngLat([x, y]) };
      },
      project: (lon, lat) => map.project([lon, lat]),
      fitBounds: (bounds, opts) => map.fitBounds(bounds, Object.assign({ duration: WX.REDUCED ? 0 : 1000 }, opts)),
      flyTo: opts => map.flyTo(Object.assign({ speed: WX.REDUCED ? 10 : 0.9, curve: 1.35, essential: true }, opts)),
      zoomIn: () => map.zoomIn(),
      zoomOut: () => map.zoomOut(),
      getZoom: () => map.getZoom(),
      onMove: fn => map.on("moveend", fn),
      resize: () => map.resize(),
      destroy: () => {},
    };
  }

  // 자체 지도: 기존 kr_map_data.json(docs/data/kr-map.json)의 시·도 경계와 같은 투영식을 쓴다.
  async function svgAdapter(container, padding) {
    const res = await fetch("data/kr-map.json", { cache: "force-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const geo = await res.json();
    const layer = document.createElement("div");
    layer.className = "svgmap";
    layer.innerHTML = `<svg viewBox="0 0 ${geo.width} ${geo.height}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">`
      + Object.values(geo.paths).map(p => `<path d="${p.d}"/>`).join("") + '</svg><div class="svgmap-marks"></div>';
    container.appendChild(layer);
    const svg = layer.querySelector("svg"), marks = layer.querySelector(".svgmap-marks");
    const handles = new Set(), moveFns = [];
    let box = { s: 1, x: 0, y: 0 };
    const project = (lon, lat) => ({
      x: box.x + ((lon - geo.lon_min) * geo.cos * geo.scale + geo.pad) * box.s,
      y: box.y + ((geo.lat_max - lat) * geo.scale + geo.pad) * box.s,
    });
    const layout = () => {
      const p = padding(), cw = container.clientWidth, ch = container.clientHeight;
      const w = Math.max(80, cw - p.left - p.right), h = Math.max(80, ch - p.top - p.bottom);
      const s = Math.min(w / geo.width, h / geo.height);
      box = { s, x: p.left + (w - geo.width * s) / 2, y: p.top + (h - geo.height * s) / 2 };
      Object.assign(svg.style, { left: `${box.x}px`, top: `${box.y}px`, width: `${geo.width * s}px`, height: `${geo.height * s}px` });
      handles.forEach(handle => handle.place());
    };
    const adapter = {
      kind: "svg",
      canZoom: false,
      canRadar: false,   // 자체 지도는 투영이 달라 비구름을 겹치지 않는다
      setRadar() {},
      addMarker(el, lon, lat, anchor = "center", offset = [0, 0]) {
        const wrap = document.createElement("div");
        wrap.className = "svgmark";
        wrap.style.transform = anchor === "left" ? "translate(0,-50%)" : "translate(-50%,-50%)";
        wrap.appendChild(el);
        marks.appendChild(wrap);
        const handle = {
          el, lon, lat,
          place() { const pt = project(handle.lon, handle.lat); wrap.style.left = `${pt.x + offset[0]}px`; wrap.style.top = `${pt.y + offset[1]}px`; },
          setLngLat(x, y) { handle.lon = x; handle.lat = y; handle.place(); },
          remove() { wrap.remove(); handles.delete(handle); },
        };
        handles.add(handle);
        handle.place();
        return handle;
      },
      project,
      fitBounds() {}, flyTo() {}, zoomIn() {}, zoomOut() {},
      getZoom: () => 0,
      onMove: fn => moveFns.push(fn),
      resize: () => { layout(); moveFns.forEach(fn => fn()); },
      destroy: () => { window.removeEventListener("resize", onResize); layer.remove(); },
    };
    const onResize = () => adapter.resize();
    window.addEventListener("resize", onResize);
    layout();
    return adapter;
  }

  // attribution: 지도 출처 표기 위치(기본 오른쪽 아래). 현장 화면은 시트가 아래·오른쪽을 가리므로 왼쪽 위.
  WX.createMap = ({ container, padding, onReady, onNotice, view, attribution }) => {
    let svg = null, ready = false, fellBack = false, started = false, waited = 0;
    const notice = mode => { if (onNotice) onNotice(mode); };

    async function fallBack() {
      if (ready || fellBack) return;
      fellBack = true;
      try {
        svg = await svgAdapter(container, padding);
        if (ready) { svg.destroy(); svg = null; return; }   // 그 사이 실지도가 준비됐다
        notice("svg");
        onReady(svg);
      } catch (error) {
        notice("none");   // 자체 지도도 없으면 목록·상세만 쓴다
      }
    }
    function startReal() {
      if (started || !window.maplibregl) return;
      started = true;
      let map;
      try {
        // view가 있으면(현장 화면) 그 위치에서, 없으면(본사) 전국이 보이게 시작한다.
        const start = view ? { center: view.center, zoom: view.zoom } : { bounds: WX.KOREA, fitBoundsOptions: { padding: padding() } };
        map = new maplibregl.Map(Object.assign({ container, style: STYLE, attributionControl: attribution ? false : { compact: true },
          dragRotate: false, pitchWithRotate: false, touchPitch: false }, start));
        if (attribution) map.addControl(new maplibregl.AttributionControl({ compact: true }), attribution);
        map.touchZoomRotate.disableRotation();
      } catch (error) {
        fallBack();
        return;
      }
      map.on("load", () => {
        ready = true;
        try { koreanLabels(map); } catch (error) { /* 스타일 이름이 바뀌어도 지도는 쓴다 */ }
        if (svg) { svg.destroy(); svg = null; }
        notice(null);
        onReady(maplibreAdapter(map));
      });
    }
    // 뒤쪽 탭에서는 브라우저가 그리기를 늦추므로 화면이 보이는 동안의 시간만 센다.
    const tick = () => {
      if (ready || fellBack) return;
      if (!document.hidden) waited += 500;
      if (waited >= WAIT_MS) fallBack();
      else setTimeout(tick, 500);
    };
    setTimeout(tick, 500);

    if (new URLSearchParams(location.search).get("map") === "svg") { fallBack(); return; }
    if (window.maplibregl) { startReal(); return; }
    if (window.__maplibreFailed) { fallBack(); return; }
    const script = document.getElementById("maplibre-js");
    if (!script) { fallBack(); return; }
    // 스크립트가 늦게 도착하면 대체 지도에서 실지도로 돌아간다.
    script.addEventListener("load", startReal, { once: true });
    script.addEventListener("error", fallBack, { once: true });
  };
})();

// 화면 확인 도구(자동 테스트 체계 아님): 사용자 Chrome과 분리된 임시 프로필의 헤드리스 Chrome을 띄워
// 페이지를 열고, 단계별 JS 식 결과·콘솔 오류·캡처를 JSON으로 남긴다. 앱 미리보기 창이 가려지면 지도가 그려지지 않을 때 쓴다.
// 사용: node scripts/ui_check.mjs steps.json
//   steps.json = {"width":1440,"height":900,"mobile":false,"steps":[{"nav":url,"after":ms}|{"wait":ms}|{"eval":js,"label":s}
//                |{"click":jsElementExpr,"label":s,"after":ms}|{"drag":jsElementExpr,"dx":px,"dy":px,"after":ms}
//                |{"key":"ArrowRight","after":ms}|{"size":[w,h,mobile]}|{"shot":path}]}
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const spec = JSON.parse(readFileSync(process.argv[2], "utf8"));
const port = 9333 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), "ui-check-"));
const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--no-first-run",
  "--no-default-browser-check", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--hide-scrollbars",
  `--window-size=${spec.width || 1440},${spec.height || 900}`, "about:blank",
], { stdio: "ignore" });
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function pageSocket() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find(t => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch (e) { /* 아직 준비 안 됨 */ }
    await sleep(200);
  }
  throw new Error("Chrome 연결 실패");
}

const ws = new WebSocket(await pageSocket());
await new Promise(r => ws.addEventListener("open", r, { once: true }));
let seq = 0;
const waiting = new Map(), logs = [];
ws.addEventListener("message", ev => {
  const msg = JSON.parse(ev.data);
  if (msg.id && waiting.has(msg.id)) { waiting.get(msg.id)(msg); waiting.delete(msg.id); }
  if (msg.method === "Runtime.consoleAPICalled" && ["error", "warning"].includes(msg.params.type)) {
    logs.push(`[${msg.params.type}] ${msg.params.args.map(a => a.value ?? a.description ?? "").join(" ")}`);
  }
  if (msg.method === "Runtime.exceptionThrown") logs.push(`[exception] ${msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text}`);
  if (msg.method === "Log.entryAdded" && msg.params.entry.level === "error") logs.push(`[log] ${msg.params.entry.text} ${msg.params.entry.url || ""}`);
});
const send = (method, params = {}) => new Promise(r => { const n = ++seq; waiting.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
const size = (w, h, mobile) => send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: !!mobile });

await send("Runtime.enable");
await send("Log.enable");
await send("Page.enable");
await size(spec.width || 1440, spec.height || 900, spec.mobile);
const out = [];
for (const step of spec.steps) {
  if (step.nav) { await send("Page.navigate", { url: step.nav }); await sleep(step.after ?? 3000); }
  if (step.size) { await size(step.size[0], step.size[1], step.size[2]); await sleep(500); }
  if (step.wait) await sleep(step.wait);
  if (step.eval) {
    const res = await send("Runtime.evaluate", { expression: step.eval, returnByValue: true, awaitPromise: true });
    const r = res.result;
    out.push({ eval: step.label || step.eval.slice(0, 60), value: r.exceptionDetails ? `EXCEPTION ${r.exceptionDetails.exception?.description}` : r.result.value });
  }
  if (step.click) {
    const res = await send("Runtime.evaluate", { expression: `(() => { const el = ${step.click}; if (!el) return false; el.scrollIntoView({block:"center"}); const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()`, returnByValue: true });
    const xy = res.result.result.value;
    if (xy) for (const type of ["mousePressed", "mouseReleased"]) await send("Input.dispatchMouseEvent", { type, x: xy[0], y: xy[1], button: "left", clickCount: 1 });
    out.push({ click: step.label || step.click.slice(0, 60), ok: !!xy });
    await sleep(step.after ?? 800);
  }
  if (step.drag) {
    const res = await send("Runtime.evaluate", { expression: `(() => { const el = ${step.drag}; if (!el) return false; const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()`, returnByValue: true });
    const xy = res.result.result.value;
    if (xy) {
      const [x, y] = xy, dx = step.dx || 0, dy = step.dy || 0;
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      for (let k = 1; k <= 10; k++) {
        await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: x + (dx * k) / 10, y: y + (dy * k) / 10, button: "left", buttons: 1 });
        await sleep(16);
      }
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: x + dx, y: y + dy, button: "left", clickCount: 1 });
    }
    out.push({ drag: step.label || step.drag.slice(0, 60), ok: !!xy });
    await sleep(step.after ?? 800);
  }
  if (step.key) {
    for (const type of ["keyDown", "keyUp"]) await send("Input.dispatchKeyEvent", { type, key: step.key, code: step.key, windowsVirtualKeyCode: { ArrowRight: 39, ArrowLeft: 37, Escape: 27, Enter: 13, Tab: 9 }[step.key] || 0 });
    await sleep(step.after ?? 400);
  }
  if (step.shot) {
    const res = await send("Page.captureScreenshot", { format: "png" });
    writeFileSync(step.shot, Buffer.from(res.result.data, "base64"));
    out.push({ shot: step.shot });
  }
}
console.log(JSON.stringify({ results: out, console: logs }, null, 1));
ws.close();
chrome.kill();
await sleep(300);
try { rmSync(profile, { recursive: true, force: true }); } catch (e) { /* 임시 폴더 */ }

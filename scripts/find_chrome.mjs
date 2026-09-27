// 화면 확인 도구가 띄울 브라우저 찾기: CHROME 환경변수 → 운영체제별 Chrome 기본 위치 → (Windows) Edge. 못 찾으면 null.
import { existsSync } from "node:fs";
import { win32 } from "node:path";

export function findChrome({ platform = process.platform, env = process.env, exists = existsSync } = {}) {
  if (env.CHROME) return env.CHROME;
  let candidates;
  if (platform === "win32") {
    const roots = [env.ProgramFiles, env["ProgramFiles(x86)"], env.LOCALAPPDATA].filter(Boolean);
    candidates = [
      ...roots.map(root => win32.join(root, "Google", "Chrome", "Application", "chrome.exe")),
      ...roots.map(root => win32.join(root, "Microsoft", "Edge", "Application", "msedge.exe")),   // 업무용 PC에 크롬이 없을 때
    ];
  } else if (platform === "darwin") {
    candidates = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      `${env.HOME || ""}/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`];
  } else {
    candidates = ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"];
  }
  return candidates.find(path => exists(path)) || null;
}

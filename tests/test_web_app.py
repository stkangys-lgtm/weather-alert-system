import json
import os
import struct
import unittest
import zlib

from src.publish import WEB_DIR


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def png_pixels(path):
    """8비트 RGB/RGBA PNG를 풀어 [(r, g, b), ...] 줄 목록으로 돌려준다(외부 라이브러리 없이)."""
    with open(path, "rb") as f:
        data = f.read()
    pos, idat, width = 8, b"", 0
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color = struct.unpack(">IIBB", body[:10])
            assert depth == 8 and color in (2, 6), (depth, color)
            step = 3 if color == 2 else 4
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    raw, rows, prev = zlib.decompress(idat), [], bytearray(width * step)
    for y in range(height):
        start = y * (width * step + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + width * step])
        for i in range(len(line)):
            a = line[i - step] if i >= step else 0
            b, c = prev[i], prev[i - step] if i >= step else 0
            if kind == 1:
                line[i] = (line[i] + a) & 255
            elif kind == 2:
                line[i] = (line[i] + b) & 255
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(line[x * step:x * step + 3]) for x in range(width)])
        prev = line
    return rows


def ink_box(rows):
    """흰색이 아닌 픽셀이 차지하는 (왼, 위, 오른, 아래)."""
    ink = [(x, y) for y, row in enumerate(rows) for x, px in enumerate(row) if min(px) < 235]
    xs, ys = [p[0] for p in ink], [p[1] for p in ink]
    return min(xs), min(ys), max(xs), max(ys)


def read(name):
    with open(os.path.join(WEB_DIR, name), encoding="utf-8") as f:
        return f.read()


class AppManifestTests(unittest.TestCase):
    def test_hq_manifest(self):
        data = json.loads(read("manifest.webmanifest"))
        self.assertEqual(("현대아산 기상안전", "./", "#2b4775", "standalone"),
                         (data["name"], data["start_url"], data["theme_color"], data["display"]))
        sizes = {icon["sizes"]: icon["src"] for icon in data["icons"]}
        self.assertEqual({"192x192", "512x512"}, set(sizes))
        for size, src in sizes.items():
            width = int(size.split("x")[0])
            self.assertEqual((width, width), png_size(os.path.join(WEB_DIR, src)))

    def test_apple_touch_icon(self):
        self.assertEqual((180, 180), png_size(os.path.join(WEB_DIR, "assets", "icons", "apple-touch-icon.png")))

    def test_icons_show_whole_symbol_centered(self):
        # 헤드리스 Chrome 최소 창 너비 때문에 작은 아이콘이 모서리만 잘려 저장된 적이 있다.
        for name in ("app-512.png", "app-192.png", "apple-touch-icon.png"):
            with self.subTest(name=name):
                rows = png_pixels(os.path.join(WEB_DIR, "assets", "icons", name))
                size = len(rows)
                left, top, right, bottom = ink_box(rows)
                margin = size * 0.1
                self.assertTrue(min(left, top, size - 1 - right, size - 1 - bottom) >= margin,
                                (name, left, top, right, bottom))
                self.assertLessEqual(abs(left - (size - 1 - right)), 3, (name, left, right))
                self.assertLessEqual(abs(top - (size - 1 - bottom)), 3, (name, top, bottom))

    def test_hq_page_links_manifest_and_icon(self):
        html = read("index.html")
        self.assertIn('<link rel="manifest" href="manifest.webmanifest">', html)
        self.assertIn('<link rel="apple-touch-icon" href="assets/icons/apple-touch-icon.png">', html)

    def test_site_page_uses_its_own_manifest(self):
        html = read("site.html")
        self.assertIn('<link rel="manifest" id="manifest" href="manifest.webmanifest">', html)
        self.assertIn("/^[A-Za-z0-9_-]{1,64}$/.test(id)", html)
        self.assertIn('"manifests/" + id + ".webmanifest"', html)
        self.assertIn('<link rel="apple-touch-icon" href="assets/icons/apple-touch-icon.png">', html)

    def test_hq_site_button_opens_new_window(self):
        # iOS 홈 화면 앱에는 뒤로 가기가 없어, 같은 창으로 넘어가면 본사 화면으로 돌아올 수 없다.
        html = read("index.html")
        button = html.split('id="bSite"')[0].rsplit("<a ", 1)[1] + html.split('id="bSite"')[1].split(">", 1)[0]
        self.assertIn('target="_blank"', button)
        self.assertIn('rel="noopener"', button)

    def test_site_screen_has_no_notice(self):
        # 전파 문안은 본사 안전관리자가 검토해 현장에 보내는 문서라 현장 화면에는 두지 않는다(본사 화면에만).
        html, js = read("site.html"), read("assets/site.js")
        for text in ("전파 문안", "문안 복사", 'id="nt"', 'id="copy"'):
            self.assertNotIn(text, html)
        self.assertNotIn("notice", js)
        self.assertIn('id="bNotice"', read("index.html"))

    def test_hq_list_table_has_no_sideways_scroll_on_phones(self):
        # 휴대폰 폭에서는 현장 목록 표를 현장별 카드로 바꾼다(좌우 스크롤이 불편하다는 사용자 의견, 2026-09-28).
        css, js = read("assets/hq.css"), read("assets/hq-notice.js")
        self.assertNotIn("min-width: 760px", css)
        self.assertIn("content: attr(data-l)", css)
        for label in ("기온", "비 mm/h", "바람 m/s", "습도"):
            self.assertIn(f'data-l="{label}"', js)

    def test_hq_narrow_legend_keeps_radar_source(self):
        # 좁은 화면에서도 비구름 출처(자료: 기상청, 공공누리 1유형)와 레이더 시각을 보인다.
        narrow = read("assets/hq.css").split("@media (max-width: 899px)")[1]
        self.assertNotIn(".legend .src { display: none; }", narrow)
        self.assertIn(".legend .src { position: absolute;", narrow)

    def test_site_footer_credits_map_sources(self):
        foot = read("site.html").split('<p class="foot">')[1].split("</p>")[0]
        for name in ("OpenStreetMap", "OpenFreeMap", "OpenMapTiles"):
            self.assertIn(name, foot)

if __name__ == "__main__":
    unittest.main()

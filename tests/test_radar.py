"""src.radar 테스트 — 레이더 영상 틀 확인, 비 단계 추출, LCC 투영, 웹 지도 영상, 조회·저장."""

import contextlib
import io
import math
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import requests
from PIL import Image

from src import radar

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "radar", "RDR_CMP_WRC_202609280930.png")


def sample():
    """표본 레이더 영상을 RGB numpy 배열로 읽는다."""
    with Image.open(FIXTURE) as img:
        return np.array(img.convert("RGB"))


def window(img, lat, lon):
    """(구현 코드를 쓰지 않고) BOUNDS와 메르카토르 식으로 img 위 위치를 계산해 그 둘레 5x5칸 값의 집합을 돌려준다."""
    lon0, lat0, lon1, lat1 = radar.BOUNDS

    def merc(phi):
        return math.log(math.tan(math.pi / 4 + math.radians(phi) / 2))

    y0, y1 = merc(lat1), merc(lat0)
    px = (lon - lon0) / (lon1 - lon0) * img.width
    py = (merc(lat) - y0) / (y1 - y0) * img.height
    x, y = int(px), int(py)
    values = set()
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            xi, yi = x + dx, y + dy
            if 0 <= xi < img.width and 0 <= yi < img.height:
                values.add(img.getpixel((xi, yi)))
    return values


class FrameTests(unittest.TestCase):
    def test_sample_frame_passes(self):
        radar.check_frame(sample())

    def test_changed_legend_is_rejected(self):
        rgb = sample().copy()
        rgb[33 + 24 * 10, 600:606] = (1, 2, 3)
        with self.assertRaises(radar.RadarFormatError):
            radar.check_frame(rgb)

    def test_moved_graticule_is_rejected(self):
        rgb = sample().copy()
        rgb[(rgb == radar.GRATICULE).all(-1)] = (250, 250, 250)
        with self.assertRaises(radar.RadarFormatError):
            radar.check_frame(rgb)

    def test_wrong_size_is_rejected(self):
        with self.assertRaises(radar.RadarFormatError):
            radar.check_frame(sample()[:600])


class StepTests(unittest.TestCase):
    def test_legend_colours_map_to_our_bins(self):
        # (0,155,245)=0.1~0.5 -> 0, (0,255,0)=1~2 -> 1, (0,140,0)=3~4 -> 2, (255,50,0)=15~20 -> 3, (224,169,255)=30~40 -> 4
        steps = radar.rain_steps(sample())
        self.assertEqual(0, steps[490, 302])
        self.assertEqual(2, steps[527, 199])
        self.assertEqual(3, steps[548, 274])
        self.assertEqual(4, steps[546, 212])

    def test_below_point_one_background_and_outside_are_empty(self):
        steps = radar.rain_steps(sample())
        self.assertEqual(-1, steps[490, 231])    # (0,200,255) = 0.0~0.1
        self.assertEqual(-1, steps[196, 306])    # 서울 부근, 비 없음
        self.assertEqual(-1, steps[300, 610])    # 범례
        self.assertEqual(-1, steps[5, 100])      # 제목 줄

    def test_line_pixels_inside_rain_are_filled(self):
        rgb = np.full((620, 635, 3), 250, np.uint8)
        rgb[100:110, 100:110] = (255, 50, 0)
        rgb[105, 100:110] = (0, 0, 0)
        self.assertEqual(3, radar.rain_steps(rgb)[105, 105])

    def test_background_pixels_at_rain_edge_are_not_filled(self):
        # 배경(250,250,250)은 회색조지만 LINE_COLORS가 아니므로 비 옆이어도 채우지 않는다.
        rgb = np.full((620, 635, 3), 250, np.uint8)
        rgb[100:110, 100:110] = (255, 50, 0)
        steps = radar.rain_steps(rgb)
        self.assertEqual(-1, steps[105, 110])
        self.assertEqual(-1, steps[110, 105])

    def test_sample_background_pixel_stays_unfilled(self):
        steps = radar.rain_steps(sample())
        self.assertEqual(-1, steps[256, 575])


class ProjectionTests(unittest.TestCase):
    def test_round_trip(self):
        px, py = radar.latlon_to_pixel(36.35, 127.385)
        lat, lon = radar.pixel_to_latlon(px, py)
        self.assertAlmostEqual(36.35, float(lat), places=4)
        self.assertAlmostEqual(127.385, float(lon), places=4)

    def test_graticule_error_within_acceptance(self):
        # 설계서 5.8 수용 기준 5km. 시험 결과 평균 0.57km·최대 1.6km.
        ys, xs = np.nonzero((sample() == radar.GRATICULE).all(-1))
        keep = (xs < 596) & (ys >= 20)
        lat, lon = radar.pixel_to_latlon(xs[keep] + 0.5, ys[keep] + 0.5)
        d_lon = (lon - np.round(lon)) * 111.32 * np.cos(np.radians(lat))
        d_lat = (lat - np.round(lat)) * 111.0
        err = np.minimum(abs(d_lon), abs(d_lat))
        self.assertLess(float(np.sqrt((err ** 2).mean())), 1.0)
        self.assertLess(float(err.max()), 2.0)

    def test_islands_land_on_coastline(self):
        black = np.argwhere((sample() == (0, 0, 0)).all(-1)) + 0.5
        for lat, lon in ((37.242, 131.867), (34.684, 125.435)):   # 독도, 흑산도
            px, py = radar.latlon_to_pixel(lat, lon)
            self.assertLess(np.hypot(black[:, 1] - px, black[:, 0] - py).min(), 2.0)


class OverlayTests(unittest.TestCase):
    def test_overlay_shape_palette_and_colours(self):
        img = radar.render_overlay(sample())
        self.assertEqual(("P", 760), (img.mode, img.width))
        self.assertTrue(880 < img.height < 900)

    def test_overlay_places_rain_where_it_was_observed(self):
        img = radar.render_overlay(sample())
        self.assertIn(4 + 1, window(img, 32.096, 125.188))    # 30mm/h 이상
        self.assertIn(3 + 1, window(img, 32.068, 126.317))    # 15~30
        self.assertEqual({0}, window(img, 37.5665, 126.978))  # 서울, 비 없음


def _png_bytes(rgb=None):
    """레이더 영상을 PNG 바이트로 인코딩한다(영상 응답 흉내)."""
    img = Image.fromarray(sample() if rgb is None else rgb)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _list_response(urls):
    return {
        "response": {
            "header": {"resultCode": "00"},
            "body": {"items": {"item": [{"rdr-img-file": urls}]}},
        }
    }


def _ok(json_value=None, content=None):
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    if json_value is not None:
        resp.json.return_value = json_value
    if content is not None:
        resp.content = content
    return resp


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = os.path.join(self._tmp.name, "radar.png")
        self.now = datetime(2026, 9, 28, 9, 35, tzinfo=timezone(timedelta(hours=9)))

    def tearDown(self):
        self._tmp.cleanup()

    def test_image_urls_accepts_list_and_string(self):
        a = "http://www.kma.go.kr/repositary/image/rdr/img/RDR_CMP_WRC_202609280925.png"
        b = a.replace("0925", "0930")
        expected = [a.replace("http://", "https://"), b.replace("http://", "https://")]
        self.assertEqual(expected, radar.image_urls({"rdr-img-file": [a, b]}))
        self.assertEqual(expected, radar.image_urls({"rdr-img-file": f"[{a}, {b}]"}))

    def test_observed_at_from_file_name(self):
        self.assertEqual(
            "2026-09-28T09:30:00+09:00",
            radar.observed_at("https://x/RDR_CMP_WRC_202609280930.png").isoformat(),
        )
        with self.assertRaises(ValueError):
            radar.observed_at("https://x/other.png")

    @patch("src.radar.requests.get")
    def test_success_writes_png_and_returns_view(self, get):
        get.side_effect = [
            _ok(json_value=_list_response([
                "http://x/RDR_CMP_WRC_202609280925.png",
                "http://x/RDR_CMP_WRC_202609280930.png",
            ])),
            _ok(content=_png_bytes()),
        ]

        view = radar.update_radar("KEY", self.out, self.now)

        self.assertEqual(
            {
                "image": "radar.png?v=202609280930",
                "observed_at": "2026-09-28T09:30:00+09:00",
                "corners": radar.CORNERS,
            },
            view,
        )
        self.assertEqual(760, Image.open(self.out).width)
        self.assertTrue(get.call_args_list[-1].args[0].endswith("RDR_CMP_WRC_202609280930.png"))

    @patch("src.radar.requests.get")
    def test_network_error_keeps_old_file(self, get):
        with open(self.out, "wb") as f:
            f.write(b"old")
        get.side_effect = requests.exceptions.ConnectionError("boom")

        view = radar.update_radar("KEY", self.out, self.now)

        self.assertIsNone(view)
        with open(self.out, "rb") as f:
            self.assertEqual(b"old", f.read())

    @patch("src.radar.requests.get")
    def test_empty_list_returns_none(self, get):
        with open(self.out, "wb") as f:
            f.write(b"old")
        get.return_value = _ok(json_value=_list_response([]))

        view = radar.update_radar("KEY", self.out, self.now)

        self.assertIsNone(view)
        with open(self.out, "rb") as f:
            self.assertEqual(b"old", f.read())

    @patch("src.radar.requests.get")
    def test_changed_frame_returns_none_and_keeps_old_file(self, get):
        with open(self.out, "wb") as f:
            f.write(b"old")
        bad_rgb = sample().copy()
        bad_rgb[33, 603] = (1, 2, 3)  # 범례 칸 한 색을 바꿔 형식 확인에 걸리게 함
        get.side_effect = [
            _ok(json_value=_list_response(["http://x/RDR_CMP_WRC_202609280930.png"])),
            _ok(content=_png_bytes(bad_rgb)),
        ]

        view = radar.update_radar("KEY", self.out, self.now)

        self.assertIsNone(view)
        with open(self.out, "rb") as f:
            self.assertEqual(b"old", f.read())

    @patch("src.radar.requests.get")
    def test_changed_legend_prints_cell_index_and_never_the_key(self, get):
        bad_rgb = sample().copy()
        bad_rgb[33 + 24 * 10, 600:606] = (1, 2, 3)  # 칸 10을 바꿔 형식 확인에 걸리게 함
        get.side_effect = [
            _ok(json_value=_list_response(["http://x/RDR_CMP_WRC_202609280930.png"])),
            _ok(content=_png_bytes(bad_rgb)),
        ]
        buf = io.StringIO()

        with contextlib.redirect_stdout(buf):
            view = radar.update_radar("SECRETKEY", self.out, self.now)

        self.assertIsNone(view)
        output = buf.getvalue()
        self.assertIn("[레이더 오류] 영상 형식:", output)
        self.assertIn("칸 10", output)
        self.assertNotIn("SECRETKEY", output)

    @patch("src.radar.requests.get")
    def test_newest_image_is_fetched_even_if_list_is_out_of_order(self, get):
        get.side_effect = [
            _ok(json_value=_list_response([
                "http://x/RDR_CMP_WRC_202609280930.png",
                "http://x/RDR_CMP_WRC_202609280915.png",
                "http://x/RDR_CMP_WRC_202609280925.png",
            ])),
            _ok(content=_png_bytes()),
        ]

        view = radar.update_radar("KEY", self.out, self.now)

        self.assertEqual("radar.png?v=202609280930", view["image"])
        self.assertTrue(get.call_args_list[-1].args[0].endswith("RDR_CMP_WRC_202609280930.png"))

    @patch("src.radar.requests.get")
    def test_unparseable_urls_are_skipped_when_choosing_newest(self, get):
        get.side_effect = [
            _ok(json_value=_list_response([
                "http://x/other.png",
                "http://x/RDR_CMP_WRC_202609280925.png",
            ])),
            _ok(content=_png_bytes()),
        ]

        view = radar.update_radar("KEY", self.out, self.now)

        self.assertEqual("radar.png?v=202609280925", view["image"])

    @patch("src.radar.requests.get")
    def test_all_urls_unparseable_returns_none(self, get):
        get.return_value = _ok(json_value=_list_response(["http://x/other.png", "http://x/also-other.png"]))

        view = radar.update_radar("KEY", self.out, self.now)

        self.assertIsNone(view)

    @patch("src.radar.os.replace")
    @patch("src.radar.requests.get")
    def test_save_error_keeps_old_file_and_no_leftover_temp(self, get, replace):
        with open(self.out, "wb") as f:
            f.write(b"old")
        get.side_effect = [
            _ok(json_value=_list_response(["http://x/RDR_CMP_WRC_202609280930.png"])),
            _ok(content=_png_bytes()),
        ]
        replace.side_effect = OSError("disk full")

        view = radar.update_radar("KEY", self.out, self.now)

        self.assertIsNone(view)
        with open(self.out, "rb") as f:
            self.assertEqual(b"old", f.read())
        leftovers = [n for n in os.listdir(self._tmp.name) if n != "radar.png"]
        self.assertEqual([], leftovers)

    @patch("src.radar.requests.get")
    def test_tripped_breaker_skips_request(self, get):
        breaker = MagicMock()
        breaker.is_tripped.return_value = True

        view = radar.update_radar("KEY", self.out, self.now, breaker=breaker)

        self.assertIsNone(view)
        get.assert_not_called()

    @patch("src.radar.requests.get")
    def test_key_is_not_printed(self, get):
        get.side_effect = requests.exceptions.ConnectionError("http://x?serviceKey=SECRETKEY")
        buf = io.StringIO()

        with contextlib.redirect_stdout(buf):
            radar.update_radar("SECRETKEY", self.out, self.now)

        self.assertNotIn("SECRETKEY", buf.getvalue())


if __name__ == "__main__":
    unittest.main()

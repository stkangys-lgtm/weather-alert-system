"""레이더 합성 영상(공공데이터포털 CMP_WRC) 처리 핵심.

기상청 레이더 합성 영상은 배경·범례가 함께 그려진 완성 이미지(기상청 LCC 투영)다.
이 모듈은 순수 이미지 처리만 담당한다(망 접속 없음):

1. `check_frame` — 영상 크기·범례 색·격자선 픽셀 수를 확인해, 기상청이 틀이나 색을
   바꾸면(다른 영상이 오면) 잘못 칠하지 않고 실패를 알린다.
2. `rain_steps` — 범례 색을 우리 강수 5단계(RAIN_BINS)로 재분류한다.
3. `lcc_km`/`pixel_to_latlon`/`latlon_to_pixel` — 영상 픽셀 <-> 위경도 변환
   (`src/grid_converter.py`와 같은 기상청 LCC, 격자 반올림 없는 연속 km).
4. `render_overlay` — 위 결과를 웹 메르카토르 격자(우리 지도가 쓰는 방식)로 다시
   투영해 투명 배경 팔레트 PNG를 만든다.

네트워크 조회·저장(Task 2)과 화면 연동(Task 3~)은 이 모듈을 가져다 쓴다.
"""

import math

import numpy as np
from PIL import Image

from src.grid_converter import DEGRAD, OLAT, OLON, RE, SLAT1, SLAT2

# 범례 24칸(위→아래, 2026-09-28 시험으로 확정). 칸의 색과 하한 mm/h.
LEGEND: tuple[tuple[tuple[int, int, int], float], ...] = (
    ((51, 51, 51), 150),
    ((0, 3, 144), 110),
    ((76, 78, 177), 90),
    ((179, 180, 222), 70),
    ((147, 0, 228), 60),
    ((179, 41, 255), 50),
    ((201, 105, 255), 40),
    ((224, 169, 255), 30),
    ((180, 0, 0), 25),
    ((210, 0, 0), 20),
    ((255, 50, 0), 15),
    ((255, 102, 0), 10),
    ((204, 170, 0), 9),
    ((224, 185, 0), 8),
    ((249, 205, 0), 7),
    ((255, 220, 31), 6),
    ((255, 255, 0), 5),
    ((0, 90, 0), 4),
    ((0, 140, 0), 3),
    ((0, 190, 0), 2),
    ((0, 255, 0), 1),
    ((0, 74, 245), 0.5),
    ((0, 155, 245), 0.1),
    ((0, 200, 255), 0.0),
)

# 우리 강수 5단계(눈금)와 색(web/assets/common.js의 WX.RAIN_BINS·WX.RAIN_COLORS와 같은 값).
RAIN_BINS = (0.1, 1, 3, 15, 30)
RAIN_COLORS = (
    (205, 226, 251),  # #cde2fb
    (158, 197, 244),  # #9ec5f4
    (85, 152, 231),   # #5598e7
    (37, 106, 191),   # #256abf
    (13, 54, 107),    # #0d366b
)

# 영상 픽셀(가장자리 기준, 픽셀 중심 i+0.5) -> 기상청 LCC km(2026-09-28 좌표 보정 시험).
# X = a*px + b*py + c, Y = d*px + e*py + f
PIXEL_TO_KM = (1.70090916, 0.000800691565, -437.740555, 0.000205876798, -1.71024429, 290.302204)

# 출력(웹 메르카토르) 영상 범위: 경도 122.5~132.0, 위도 31.0~40.0.
BOUNDS = (122.5, 31.0, 132.0, 40.0)
OUT_WIDTH = 760

# latest.json radar.corners에 쓰는 MapLibre 순서(왼쪽 위·오른쪽 위·오른쪽 아래·왼쪽 아래).
CORNERS = ((122.5, 40.0), (132.0, 40.0), (132.0, 31.0), (122.5, 31.0))

# 영상 틀 확인용 격자선 색과 지도 영역(x<596, y>=20) 안 픽셀 수(2026-09-28 시험).
GRATICULE = (80, 80, 80)
GRATICULE_COUNT = 3223

_FRAME_SHAPE = (620, 635, 3)
_MAP_Y0 = 20
_MAP_X1 = 596
_GRATICULE_TOLERANCE = 50


class RadarFormatError(Exception):
    """레이더 영상의 크기·범례·격자선이 예상과 달라 안전하게 처리할 수 없을 때."""


def check_frame(rgb: np.ndarray) -> None:
    """영상 크기·범례 24칸 색·지도 영역 격자선 픽셀 수를 확인한다.

    기상청이 영상 틀이나 색을 바꾸면(달라지면), 잘못 칠한 비구름 대신 실패로
    처리하도록 `RadarFormatError`를 낸다.
    """
    if tuple(rgb.shape) != _FRAME_SHAPE:
        raise RadarFormatError(f"영상 크기가 예상과 다릅니다: {tuple(rgb.shape)} != {_FRAME_SHAPE}")

    for k, (color, _value) in enumerate(LEGEND):
        y = 33 + 24 * k
        actual = tuple(int(c) for c in rgb[y, 603])
        if actual != color:
            raise RadarFormatError(f"범례 색이 바뀌었습니다(칸 {k}): {actual} != {color}")

    graticule_mask = (rgb[_MAP_Y0:, :_MAP_X1] == np.array(GRATICULE, dtype=rgb.dtype)).all(-1)
    count = int(graticule_mask.sum())
    if abs(count - GRATICULE_COUNT) > _GRATICULE_TOLERANCE:
        raise RadarFormatError(f"격자선 픽셀 수가 바뀌었습니다: {count} (기준 {GRATICULE_COUNT}±{_GRATICULE_TOLERANCE})")


def _bin_step(value: float) -> int:
    """범례 칸 하한 mm/h를 우리 강수 단계(0~4)로 재분류한다. 0.1 미만이면 −1."""
    step = sum(1 for b in RAIN_BINS if b <= value) - 1
    return step


def _neighbor_rain(steps: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """각 픽셀의 8방향 이웃 중 비 단계가 있는 칸의 수와 그중 가장 높은 단계."""
    rain_mask = steps >= 0
    padded_mask = np.pad(rain_mask, 1, mode="constant", constant_values=False)
    padded_steps = np.pad(steps, 1, mode="constant", constant_values=-1)
    count = np.zeros(steps.shape, dtype=np.int16)
    best = np.full(steps.shape, -1, dtype=np.int8)
    h, w = steps.shape
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            m = padded_mask[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            s = padded_steps[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            count += m
            best = np.where(m & (s > best), s, best)
    return count, best


def rain_steps(rgb: np.ndarray) -> np.ndarray:
    """범례 색을 우리 강수 5단계(0~4)로 재분류한다. 없음/지도 영역 밖은 −1.

    Ruling(선 채우기): 해안선·경계선·격자선(검정·회색) 픽셀이라 비 색이 확인되지
    않는 칸은, 주변 8칸 중 2칸 이상이 비이면 그중 가장 높은 단계로 채운다.
    """
    h, w = rgb.shape[:2]
    steps = np.full((h, w), -1, dtype=np.int8)

    in_map = np.zeros((h, w), dtype=bool)
    in_map[_MAP_Y0:, :_MAP_X1] = True

    for color, value in LEGEND:
        if value <= 0.0:
            continue  # 0.1mm/h 미만 칸은 그리지 않음(Ruling)
        step = _bin_step(value)
        if step < 0:
            continue
        mask = (rgb == np.array(color, dtype=rgb.dtype)).all(-1) & in_map
        steps[mask] = step

    gray = (rgb[..., 0] == rgb[..., 1]) & (rgb[..., 1] == rgb[..., 2])
    count, best = _neighbor_rain(steps)
    fill_mask = gray & in_map & (steps == -1) & (count >= 2)
    steps = np.where(fill_mask, best, steps).astype(np.int8)
    return steps


def _lcc_params():
    """기상청 LCC 투영 상수(sn·sf·ro·olon)를 계산한다. km 단위(그리드 반올림 없음)."""
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(
        math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    )
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5) ** sn * math.cos(slat1) / sn
    ro = RE * sf / math.tan(math.pi * 0.25 + olat * 0.5) ** sn
    return sn, sf, ro, olon


def lcc_km(lat, lon):
    """(위도, 경도) -> 기상청 LCC (X, Y) km. 격자 반올림 없는 연속값. numpy 배열 지원."""
    sn, sf, ro, olon = _lcc_params()
    lat = np.asarray(lat, dtype=np.float64)
    lon = np.asarray(lon, dtype=np.float64)

    ra = RE * sf / np.tan(np.pi * 0.25 + np.radians(lat) * 0.5) ** sn
    theta = np.radians(lon) - olon
    theta = np.where(theta > np.pi, theta - 2.0 * np.pi, theta)
    theta = np.where(theta < -np.pi, theta + 2.0 * np.pi, theta)
    theta = theta * sn

    x = ra * np.sin(theta)
    y = ro - ra * np.cos(theta)
    return x, y


def _km_to_latlon(x, y):
    """기상청 LCC (X, Y) km -> (위도, 경도). `lcc_km`의 역변환."""
    sn, sf, ro, olon = _lcc_params()
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    ra = np.sign(sn) * np.sqrt(x ** 2 + (ro - y) ** 2)
    alat = 2.0 * np.arctan((RE * sf / ra) ** (1.0 / sn)) - np.pi / 2.0
    theta = np.arctan2(x, ro - y) / sn

    lat = np.degrees(alat)
    lon = np.degrees(theta + olon)
    return lat, lon


def pixel_to_latlon(px, py):
    """영상 픽셀(가장자리 기준 연속 좌표) -> (위도, 경도). numpy 배열 지원."""
    a, b, c, d, e, f = PIXEL_TO_KM
    px = np.asarray(px, dtype=np.float64)
    py = np.asarray(py, dtype=np.float64)
    x = a * px + b * py + c
    y = d * px + e * py + f
    return _km_to_latlon(x, y)


def latlon_to_pixel(lat, lon):
    """(위도, 경도) -> 영상 픽셀(가장자리 기준 연속 좌표). numpy 배열 지원."""
    a, b, c, d, e, f = PIXEL_TO_KM
    x, y = lcc_km(lat, lon)
    det = a * e - b * d
    px = ((x - c) * e - b * (y - f)) / det
    py = (a * (y - f) - d * (x - c)) / det
    return px, py


def _mercator_y(lat_deg: float) -> float:
    return math.log(math.tan(math.pi / 4 + math.radians(lat_deg) / 2))


def render_overlay(rgb: np.ndarray) -> Image.Image:
    """레이더 영상을 확인하고, 웹 메르카토르 격자의 투명 배경 팔레트 영상으로 만든다.

    색 번호 0 = 투명, 1~5 = 우리 강수 단계(0~4) + 1.
    """
    check_frame(rgb)
    steps = rain_steps(rgb)

    lon0, lat0, lon1, lat1 = BOUNDS
    merc_top = _mercator_y(lat1)
    merc_bottom = _mercator_y(lat0)

    width = OUT_WIDTH
    height = round(width * (merc_top - merc_bottom) / math.radians(lon1 - lon0))

    j = np.arange(height, dtype=np.float64)
    i = np.arange(width, dtype=np.float64)
    merc_y = merc_top - (j + 0.5) / height * (merc_top - merc_bottom)
    lat = np.degrees(2.0 * np.arctan(np.exp(merc_y)) - math.pi / 2.0)
    lon = lon0 + (i + 0.5) / width * (lon1 - lon0)

    lat_grid, lon_grid = np.meshgrid(lat, lon, indexing="ij")
    px, py = latlon_to_pixel(lat_grid, lon_grid)
    ix = np.floor(px).astype(np.int64)
    iy = np.floor(py).astype(np.int64)

    h, w = steps.shape
    valid = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
    step_vals = np.full((height, width), -1, dtype=np.int8)
    step_vals[valid] = steps[iy[valid], ix[valid]]

    indices = np.where(step_vals >= 0, step_vals + 1, 0).astype(np.uint8)

    img = Image.new("P", (width, height))
    palette = [0, 0, 0]
    for color in RAIN_COLORS:
        palette.extend(color)
    palette.extend([0, 0, 0] * (256 - len(palette) // 3))
    img.putpalette(palette)
    img.putdata(indices.reshape(-1).tolist())
    img.info["transparency"] = 0
    return img

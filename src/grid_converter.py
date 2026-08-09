"""위도/경도 <-> 기상청 격자좌표(nx, ny) 변환.

기상청 단기예보 API는 5km 간격의 격자좌표(Lambert Conformal Conic 투영법)를 사용하므로,
일반적인 위경도(GPS 좌표)를 그대로 쓸 수 없다. 이 변환식은 기상청이 공식 배포하는 알고리즘이다.

사용법 (프로젝트 루트에서, 가상환경 활성화 후):
    python -m src.grid_converter 37.5665 126.9780
"""

import math
import sys

RE = 6371.00877  # 지구 반경(km)
GRID = 5.0  # 격자 간격(km)
SLAT1 = 30.0  # 투영 위도 1(degree)
SLAT2 = 60.0  # 투영 위도 2(degree)
OLON = 126.0  # 기준점 경도(degree)
OLAT = 38.0  # 기준점 위도(degree)
XO = 43  # 기준점 X좌표(격자 단위)
YO = 136  # 기준점 Y좌표(격자 단위)

DEGRAD = math.pi / 180.0


def latlon_to_grid(lat, lon):
    """(위도, 경도) -> (nx, ny) 정수 격자좌표."""
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    x = ra * math.sin(theta) + XO + 0.5
    y = ro - ra * math.cos(theta) + YO + 0.5

    return int(x), int(y)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python -m src.grid_converter <위도> <경도>")
        print("예시:   python -m src.grid_converter 37.5665 126.9780")
        sys.exit(1)

    lat, lon = float(sys.argv[1]), float(sys.argv[2])
    nx, ny = latlon_to_grid(lat, lon)
    print(f"위도={lat}, 경도={lon}  ->  nx={nx}, ny={ny}")

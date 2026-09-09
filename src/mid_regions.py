"""기상청 중기예보 API 예보구역코드 매핑.

기상청 중기예보 서비스(MidFcstInfoService)는 위경도가 아닌 광역/시군 단위 코드를 사용한다.
- getMidLandFcst (육상 광역 예보): regId — 10개 광역 구역
- getMidTa (기온 예보): regId — 시군 단위 대표 지점 코드

여기서는 위경도로부터 각 현장을 가장 가까운 광역/시군 코드에 자동 매핑한다.
정확한 시군 코드가 아니라 광역별 대표 도시 코드를 사용하므로, 기온은 대략적인 광역 대푯값이 된다.
(중기예보 자체가 시군 단위 대푯값이라 실용적으로 충분한 정확도.)

지역코드 출처: 기상청 중기예보 조회서비스 활용가이드 (data.go.kr 15059468).
"""

# 광역 육상예보 구역 (getMidLandFcst용). key: 코드, value: (대표 위경도 lat, lon, 이름)
LAND_REGIONS = {
    "11B00000": (37.5665, 126.9780, "서울·인천·경기"),
    "11D10000": (37.8813, 127.7298, "강원영서"),
    "11D20000": (37.7519, 128.8761, "강원영동"),
    "11C20000": (36.3504, 127.3845, "대전·세종·충남"),
    "11C10000": (36.6357, 127.4917, "충북"),
    "11F20000": (35.1595, 126.8526, "광주·전남"),
    "21F10000": (35.8242, 127.1480, "전북"),
    "11H10000": (36.1919, 128.4360, "경북"),
    "11H20000": (35.2384, 128.6924, "부산·울산·경남"),
    "11G00000": (33.4996, 126.5312, "제주"),
}

# 시군 단위 기온예보 구역 (getMidTa용). 각 광역별 대표 도시 하나씩만 매핑.
TA_REGIONS = {
    "11B10101": (37.5665, 126.9780, "서울"),
    "11B20201": (37.4563, 126.7052, "인천"),
    "11B20601": (37.2636, 127.0286, "수원"),
    "11D10301": (37.8813, 127.7298, "춘천"),
    "11D10501": (37.1806, 128.4611, "영월"),
    "11D20501": (37.7519, 128.8761, "강릉"),
    "11D20601": (37.1641, 128.9856, "태백"),
    "11C10101": (36.9910, 127.9259, "충주"),
    "11C10301": (36.6424, 127.4890, "청주"),
    "11C20401": (36.3504, 127.3845, "대전"),
    "11F20501": (35.1595, 126.8526, "광주"),
    "21F20801": (34.8118, 126.3922, "목포"),
    "11F10201": (35.8242, 127.1480, "전주"),
    "11H10201": (36.9917, 129.4131, "울진"),
    "11H10501": (36.0190, 129.3435, "포항"),
    "11H10611": (36.8058, 128.6242, "영주"),
    "11H10701": (35.8714, 128.6014, "대구"),
    "11H10702": (35.6470, 128.7345, "청도"),
    "11H20201": (35.1796, 129.0756, "부산"),
    "11G00201": (33.4996, 126.5312, "제주"),
}


def _haversine_km(lat1, lon1, lat2, lon2):
    import math
    r = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_region(lat, lon, regions):
    """lat/lon에서 가장 가까운 (코드, 이름) 반환."""
    best_code, best_dist, best_name = None, float("inf"), None
    for code, (rlat, rlon, name) in regions.items():
        d = _haversine_km(lat, lon, rlat, rlon)
        if d < best_dist:
            best_code, best_dist, best_name = code, d, name
    return best_code, best_name


def resolve_region_codes(lat, lon):
    """(land_reg_id, ta_reg_id, land_name, ta_name) 튜플 반환."""
    land_code, land_name = nearest_region(lat, lon, LAND_REGIONS)
    ta_code, ta_name = nearest_region(lat, lon, TA_REGIONS)
    return land_code, ta_code, land_name, ta_name

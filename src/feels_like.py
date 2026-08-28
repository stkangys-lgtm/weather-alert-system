"""체감온도 계산.

기상청이 실제 특보(폭염/한파) 판단에 사용하는 공식을 그대로 구현한다.
- 여름철(더위) 체감온도: 국립기상과학원(2011) 공식. 기온+습도로 습구온도를 먼저 구하고(Stull, 2011 근사식),
  그 습구온도와 기온으로 체감온도를 계산한다. 기온 20°C 이상에서 사용.
- 겨울철(추위) 체감온도(=풍속냉각지수): 기상청(2001) 공식. 기온 10°C 이하 & 풍속 1.3m/s 이상에서 사용.
- 그 사이 구간(10~20°C)은 두 공식 모두 적용 범위 밖이므로 기온을 그대로 체감온도로 본다.
"""

import math


def _wet_bulb(ta, rh):
    """Stull(2011) 근사식으로 습구온도(°C) 계산. rh: 상대습도(%)."""
    rh = max(5.0, min(99.0, rh))  # 공식이 불안정해지는 극단값 방지
    return (
        ta * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(ta + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )


def _summer_heat_index(ta, rh):
    tw = _wet_bulb(ta, rh)
    return -0.2442 + 0.55399 * tw + 0.45535 * ta - 0.0022 * tw ** 2 + 0.00278 * tw * ta + 3.0


def _winter_wind_chill(ta, wsd_ms):
    v_kmh = wsd_ms * 3.6
    return 13.12 + 0.6215 * ta - 11.37 * (v_kmh ** 0.16) + 0.3965 * ta * (v_kmh ** 0.16)


def compute_feels_like(t1h, reh=None, wsd=None):
    """기온(T1H), 습도(REH), 풍속(WSD) 문자열/숫자를 받아 체감온도(°C, 소수 1자리)를 반환.

    적용 공식 밖의 값이거나 필요한 값이 없으면 기온을 그대로 반환한다. 기온이 없으면 None.
    """
    try:
        ta = float(t1h)
    except (TypeError, ValueError):
        return None

    if ta <= 10:
        try:
            wsd_v = float(wsd)
        except (TypeError, ValueError):
            wsd_v = None
        if wsd_v is not None and wsd_v >= 1.3:
            return round(_winter_wind_chill(ta, wsd_v), 1)
        return round(ta, 1)

    if ta >= 20:
        try:
            reh_v = float(reh)
        except (TypeError, ValueError):
            reh_v = None
        if reh_v is not None:
            return round(_summer_heat_index(ta, reh_v), 1)
        return round(ta, 1)

    return round(ta, 1)

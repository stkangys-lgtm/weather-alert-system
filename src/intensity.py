"""기상청 예보용어의 강수·바람 세기 표현.

출처: 기상청 예보용어(2025-06-11, 예보업무규정 제5조에 따른 세부지침)
https://www.weather.go.kr/w/resources/pdf/forecast_terms_list_20250611.pdf
- 강수(시간당): 빗방울 0.1mm 미만, 약한 비 3mm 미만, (보통) 비 3~15mm 미만,
  강한 비 15~30mm 미만, 매우 강한 비 30mm 이상
- 바람: 약한 바람 4m/s 미만, 약간 강한 바람 4~9m/s 미만, 강한 바람 9~14m/s 미만,
  매우 강한 바람 14m/s 이상(강풍주의보 수준)
- 원문 규칙상 바람은 수치를 기본으로 쓰고 주의가 필요한 단계부터 표현을 붙인다.
사내 위험 기준이 아니며 문장에서 세기를 부를 때만 쓴다.
"""

DRIZZLE_MAX_MM = 0.1
_RAIN_STEPS = ((3, "약한 비"), (15, "비"), (30, "강한 비"))
_WIND_NOTICE_MIN = 4
_WIND_STEPS = ((9, "약간 강한 바람"), (14, "강한 바람"))
SNOW_TYPES = ("눈", "눈날림")  # 강수형태 중 비가 섞이지 않은 눈. 비/눈·빗방울눈날림·소나기는 비로 본다.


def is_snow(pty):
    return pty in SNOW_TYPES


def rain_term(mm):
    if mm is None or mm < DRIZZLE_MAX_MM:
        return None
    for upper, term in _RAIN_STEPS:
        if mm < upper:
            return term
    return "매우 강한 비"


def wind_term(ms):
    if ms is None or ms < _WIND_NOTICE_MIN:
        return None
    for upper, term in _WIND_STEPS:
        if ms < upper:
            return term
    return "매우 강한 바람"


def fmt_number(value):
    """31.0 → "31", 2.5 → "2.5", None → "-"."""
    if value is None:
        return "-"
    value = round(float(value), 1)
    return str(int(value)) if value.is_integer() else f"{value:.1f}"

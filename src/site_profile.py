"""현장의 공개용 식별자·짧은 이름·지역을 정한다. 담당자 정보는 다루지 않는다."""

import hashlib

from src.warning_client import site_warning_regions

# 2026-09 운영 현장의 짧은 이름(사용자 확인). 설정의 short_name이 있으면 그것을 우선한다.
SITE_SHORT_NAMES = {
    "오리온 진천신공장": "진천 신공장",
    "오리온 진천 기숙사": "진천 기숙사",
    "연희·연남동 공공주택": "연희·연남",
    "청정고원 스포츠센터": "청정고원",
    "LX 논현 업무시설": "LX 논현",
    "양산 부산대병원": "양산 부산대병원",
    "군포복합개발": "군포복합개발",
    "오리온수협 목포 김공장": "목포 김공장",
    "렉서스 동탄 네트워크": "렉서스 동탄",
    "화천군부대 시설공사": "화천 군부대",
    "반얀트리호텔 근생동": "반얀트리",
    "포항~안동2 국도건설공사": "포항~안동 국도",
    "시흥능곡 주변도로": "시흥능곡",
    "뇌죽천 하천재해예방": "뇌죽천",
    "산솔면 하수처리장": "산솔면",
    "단월정수장 시설공사": "단월정수장",
    "후포 공공하수처리": "후포",
    "동해안 바닷가 자동차길": "동해안 자동차길",
    "풍각지구 정비사업": "풍각지구",
    "영주 가흥정수장": "가흥정수장",
    "송산그린시티 용수공급시설": "송산그린시티",
}


def site_id(site):
    """설정의 id, 없으면 현장명 SHA-1 앞 8자리. 이름을 바꾸면 id도 바뀐다."""
    configured = str(site.get("id") or "").strip()
    if configured:
        return configured
    return hashlib.sha1(site["site_name"].encode("utf-8")).hexdigest()[:8]


def short_name(site):
    configured = str(site.get("short_name") or "").strip()
    return configured or SITE_SHORT_NAMES.get(site["site_name"]) or site["site_name"]


def region_label(site):
    """설정의 region, 없으면 특보 구역의 광역 정식명 + 첫 세부 구역."""
    configured = str(site.get("region") or "").strip()
    if configured:
        return configured
    local, broad = site_warning_regions(site)
    province = max(broad, key=len) if broad else ""
    parts = [part for part in (province, local[0] if local else "") if part]
    return " ".join(parts) or None

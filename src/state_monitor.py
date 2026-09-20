"""현장별 기상 상태를 저장하고 의미 있는 변화만 감지한다.

GitHub Actions는 실행할 때마다 새 환경에서 시작하므로, 공개해도 되는 최소 상태만
docs/weather-state.json에 저장해 다음 실행과 비교한다. 담당자 정보와 연락처는 저장하지 않는다.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone


STATE_VERSION = 1
SEVERITY = {"정상": 0, "데이터없음": 1, "주의": 2, "경보": 3}

ACTION_ITEMS = {
    "강풍": [
        "가설시설물·자재 결속 상태 확인",
        "타워크레인 및 고소작업 제한 여부 확인",
        "낙하·비래물 위험구간 통제",
    ],
    "호우": [
        "배수로·집수정·양수기 작동상태 확인",
        "굴착부·흙막이·비탈면 이상 유무 확인",
        "침수 우려 장비와 자재 안전지대 이동",
    ],
    "폭염": [
        "물·그늘·휴식 제공 및 휴식시간 운영 확인",
        "옥외작업 시간 조정과 민감군 근로자 상태 확인",
        "온열질환 증상자 발생 시 즉시 작업중지·응급조치",
    ],
    "폭염주의": [
        "물·그늘·휴식 제공 및 휴식시간 운영 확인",
        "옥외작업 시간 조정과 민감군 근로자 상태 확인",
    ],
    "강수": [
        "배수로·집수정과 수방자재 사전 점검",
        "굴착부·비탈면·저지대 위험구간 사전 확인",
    ],
    "한파": [
        "급수·소방·가설배관 보온 및 동파 취약부 점검",
        "결빙구간 미끄럼 방지와 근로자 방한조치 확인",
        "난방기구 사용에 따른 화재·질식 위험 점검",
    ],
    "강풍주의": [
        "가설시설물·자재 결속 상태 사전 확인",
        "고소작업과 양중작업 계획 재검토",
    ],
}


def load_state(path):
    """상태 파일을 읽는다. 최초 실행이나 손상된 파일은 빈 상태로 취급한다."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") != STATE_VERSION or not isinstance(data.get("sites"), dict):
            return None
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def save_state(path, state):
    """중간에 프로세스가 종료돼도 기존 파일이 깨지지 않도록 원자적으로 저장한다."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="weather-state-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def build_snapshot(collected, mid_forecasts, generated_at):
    """수집 결과에서 공개 가능한 비교용 상태만 추린다."""
    from src.forecast_analyzer import analyze_mid_term, analyze_short_term, summarize_events

    sites = {}
    for item in collected:
        name = item["site"]["site_name"]
        current = item.get("current") or {}
        forecast_events = summarize_events(
            analyze_short_term(item.get("forecast") or []),
            analyze_mid_term(mid_forecasts.get(name, [])),
        )
        sites[name] = {
            "level": item["judgment"]["level"],
            "categories": sorted(set(item["judgment"].get("categories") or [])),
            "reasons": item["judgment"].get("reasons") or [],
            "observation_id": f"{current.get('base_date', '')}-{current.get('base_time', '')}",
            "forecast_risks": forecast_events,
            "legal_signals": item.get("legal_signals") or [],
            "weather_warnings": item.get("weather_warnings") or [],
            "weather_warnings_available": item.get("weather_warnings_available", True),
        }
    successful_sites = sum(1 for item in collected if item.get("current") is not None)
    warning_available = all(item.get("weather_warnings_available", True) for item in collected)
    total_sites = len(collected)
    if successful_sites == total_sites:
        collection_status = "healthy"
    elif successful_sites == 0:
        collection_status = "failed"
    else:
        collection_status = "partial"
    return {
        "version": STATE_VERSION,
        "updated_at": generated_at,
        "successful_sites": successful_sites,
        "total_sites": total_sites,
        "collection_status": collection_status,
        "warning_collection_status": "healthy" if warning_available else "failed",
        "sites": sites,
    }


def _forecast_keys(site_state):
    return {
        (event.get("date"), event.get("kind"))
        for event in site_state.get("forecast_risks", [])
        if event.get("date") and event.get("kind")
    }


def _warning_key(warning):
    areas = warning.get("matched_areas") or warning.get("areas") or []
    return (
        warning.get("kind"),
        warning.get("title"),
        warning.get("announced_at"),
        tuple(sorted(areas)),
    )


def _warning_reason(warning):
    areas = warning.get("matched_areas") or warning.get("areas") or []
    area_text = ", ".join(areas)
    return f"{warning.get('title', '기상특보')} · {area_text}".rstrip(" ·")


def detect_changes(previous, current):
    """알림이 필요한 상태 변화와 새 예보 위험을 반환한다.

    수치가 조금 변한 것만으로는 알리지 않는다. 위험 단계·종류가 변했거나 새로운
    날짜/종류의 예보 위험이 생긴 경우만 이벤트로 만든다.
    """
    changes = []
    old_sites = (previous or {}).get("sites", {})

    old_warning_status = (previous or {}).get("warning_collection_status", "healthy")
    new_warning_status = current.get("warning_collection_status", "healthy")
    if new_warning_status == "failed" and old_warning_status != "failed":
        changes.append({
            "site_name": "전 현장",
            "type": "기상특보 수집 장애",
            "from_level": old_warning_status,
            "to_level": "별도 확인 필요",
            "categories": [],
            "reasons": ["기상청 특보 API 응답을 받지 못했습니다."],
        })
    elif new_warning_status == "healthy" and old_warning_status == "failed":
        changes.append({
            "site_name": "전 현장",
            "type": "기상특보 수집 정상화",
            "from_level": "수집 장애",
            "to_level": "정상",
            "categories": [],
            "reasons": ["기상청 특보 API 수신이 정상화되었습니다."],
        })

    for name, new in current["sites"].items():
        old = old_sites.get(name)
        new_level = new["level"]

        if old is None:
            if new_level != "정상":
                changes.append({
                    "site_name": name,
                    "type": "위험 발생" if new_level != "데이터없음" else "수집 장애",
                    "from_level": None,
                    "to_level": new_level,
                    "categories": new.get("categories", []),
                    "reasons": new.get("reasons", []),
                })
        elif old.get("level") != new_level or set(old.get("categories", [])) != set(new.get("categories", [])):
            old_level = old.get("level", "정상")
            if old_level == "데이터없음" and new_level != "데이터없음":
                change_type = "수집 정상화"
            elif new_level == "데이터없음":
                change_type = "수집 장애"
            elif new_level == "정상":
                change_type = "위험 해제"
            elif SEVERITY.get(new_level, 0) > SEVERITY.get(old_level, 0):
                change_type = "위험 상승"
            elif SEVERITY.get(new_level, 0) < SEVERITY.get(old_level, 0):
                change_type = "위험 완화"
            else:
                change_type = "위험 종류 변경"
            changes.append({
                "site_name": name,
                "type": change_type,
                "from_level": old_level,
                "to_level": new_level,
                "categories": new.get("categories", []),
                "reasons": new.get("reasons", []),
            })

        old_forecast = _forecast_keys(old or {})
        for event in new.get("forecast_risks", []):
            key = (event.get("date"), event.get("kind"))
            if key not in old_forecast:
                changes.append({
                    "site_name": name,
                    "type": "새 예보 위험",
                    "from_level": None,
                    "to_level": new_level,
                    "categories": [event.get("kind")],
                    "reasons": [f"{event.get('date')} {event.get('detail', '')}".strip()],
                })

        if new.get("weather_warnings_available", True):
            old_warnings = {
                _warning_key(warning): warning
                for warning in (old or {}).get("weather_warnings", [])
            }
            new_warnings = {
                _warning_key(warning): warning
                for warning in new.get("weather_warnings", [])
            }
            for key, warning in new_warnings.items():
                if key in old_warnings:
                    continue
                changes.append({
                    "site_name": name,
                    "type": "기상특보 발효" if warning.get("kind") == "기상특보" else "예비특보 발표",
                    "from_level": None,
                    "to_level": warning.get("level") or warning.get("kind"),
                    "categories": [warning.get("phenomenon")] if warning.get("phenomenon") else [],
                    "reasons": [_warning_reason(warning)],
                })
            for key, warning in old_warnings.items():
                if key in new_warnings:
                    continue
                changes.append({
                    "site_name": name,
                    "type": "기상특보 해제" if warning.get("kind") == "기상특보" else "예비특보 변경",
                    "from_level": warning.get("level") or warning.get("kind"),
                    "to_level": "해제",
                    "categories": [],
                    "reasons": [_warning_reason(warning)],
                })

        old_legal = {
            (signal.get("status"), signal.get("work_type"), signal.get("article"), signal.get("title"))
            for signal in (old or {}).get("legal_signals", [])
        }
        for signal in new.get("legal_signals", []):
            key = (signal.get("status"), signal.get("work_type"), signal.get("article"), signal.get("title"))
            if key in old_legal or signal.get("status") == "데이터 부족":
                continue
            changes.append({
                "site_name": name,
                "type": "법정 조치 발생",
                "from_level": None,
                "to_level": signal.get("status"),
                "categories": ["법정조치"],
                "reasons": [f"{signal.get('title')} ({signal.get('article')})"],
                "actions": signal.get("actions") or [],
            })

        new_legal = {
            (signal.get("status"), signal.get("work_type"), signal.get("article"), signal.get("title"))
            for signal in new.get("legal_signals", [])
        }
        new_legal_identities = {
            (signal.get("work_type"), signal.get("article"), signal.get("title"))
            for signal in new.get("legal_signals", [])
        }
        new_has_data_gap = any(signal.get("status") == "데이터 부족" for signal in new.get("legal_signals", []))
        for signal in (old or {}).get("legal_signals", []):
            key = (signal.get("status"), signal.get("work_type"), signal.get("article"), signal.get("title"))
            identity = (signal.get("work_type"), signal.get("article"), signal.get("title"))
            if key in new_legal or identity in new_legal_identities or signal.get("status") == "데이터 부족":
                continue
            changes.append({
                "site_name": name,
                "type": "법정 조치 재확인" if new_has_data_gap else "법정 조치 상태 변경",
                "from_level": signal.get("status"),
                "to_level": "데이터 부족" if new_has_data_gap else "조건 해소 확인",
                "categories": ["법정조치"],
                "reasons": [f"기존 {signal.get('title')} ({signal.get('article')})"],
                "actions": ["현장 작업상태와 조치 지속 여부 확인"],
            })
    return changes


def carry_change_summary(previous, current, changes):
    """최근 변화 요약을 다음 실행에도 유지해 대시보드에서 사라지지 않게 한다."""
    if current.get("collection_status") != "failed":
        current["last_success_at"] = current["updated_at"]
    else:
        current["last_success_at"] = (previous or {}).get("last_success_at")
    if changes:
        current["last_change_at"] = current["updated_at"]
        current["last_changes"] = changes[:20]
    elif previous:
        current["last_change_at"] = previous.get("last_change_at")
        current["last_changes"] = previous.get("last_changes", [])
    else:
        current["last_change_at"] = None
        current["last_changes"] = []
    return current


def build_alert_message(generated_at, changes):
    """알림톡 템플릿 변수와 현장 전파에 함께 쓸 수 있는 텍스트를 만든다."""
    lines = [
        "[현대아산 기상안전 알림]",
        "",
        f"기준시각: {generated_at}",
        f"기상·안전 상태변화 {len(changes)}건이 감지되었습니다.",
        "",
        "■ 변동 현황",
    ]
    action_categories = []
    actions = []
    for change in changes:
        level = change.get("to_level") or "-"
        reasons = ", ".join(change.get("reasons") or [])
        detail = f" / {reasons}" if reasons else ""
        lines.append(f"- {change['site_name']}: {change['type']} ({level}){detail}")
        action_categories.extend(change.get("categories") or [])
        for action in change.get("actions") or []:
            if action not in actions:
                actions.append(action)

    # 기상 카테고리의 공통 확인사항을 법정 신호의 구체 조치 뒤에 추가한다.
    for category in action_categories:
        for action in ACTION_ITEMS.get(category, []):
            if action not in actions:
                actions.append(action)
    if actions:
        lines.extend(["", "■ 본사·현장 확인사항"])
        lines.extend(f"- {action}" for action in actions)

    if any(str(change.get("type", "")).startswith(("기상특보", "예비특보")) for change in changes):
        lines.extend(["", "※ 기상특보·예비특보는 기상청 공식 발표를 현장 행정구역과 연결한 정보입니다."])
    lines.extend([
        "",
        "※ 선제기상 신호는 기상청 인근 격자자료 기반이며 기상특보가 아닙니다.",
        "※ 법정 신호는 표시된 조문과 현장 작업·실측값을 함께 확인해 이행해 주시기 바랍니다.",
    ])
    return "\n".join(lines)


def display_time(iso_value):
    """ISO 시각을 사람이 읽기 쉬운 분 단위 문자열로 변환한다."""
    try:
        return datetime.fromisoformat(iso_value).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(iso_value or "-")


def state_age_minutes(state, now=None):
    """마지막 성공 상태가 몇 분 전인지 반환한다. 계산할 수 없으면 None."""
    try:
        if state.get("collection_status") == "failed":
            return None
        updated = datetime.fromisoformat(state.get("last_success_at") or state["updated_at"])
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        current = now or datetime.now().astimezone()
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return max(0, (current - updated).total_seconds() / 60)
    except (KeyError, TypeError, ValueError):
        return None

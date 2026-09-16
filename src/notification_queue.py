"""기상변화 알림을 유실 없이 외부 메시징 Webhook으로 전달한다.

Webhook이 설정되지 않은 환경에서는 외부 통신 없이 대기열만 유지한다. 알림톡
발송사 또는 사내 중계 API가 정해지면 동일한 payload를 받는 연결부만 구성하면 된다.
"""

import hashlib
import json
import os
from datetime import datetime

import requests

MAX_DELIVERY_AGE_HOURS = 6


def _empty_queue():
    return {"version": 1, "alerts": []}


def load_queue(path):
    if not os.path.exists(path):
        return _empty_queue()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data.get("alerts"), list):
            return _empty_queue()
        return data
    except (OSError, ValueError, TypeError):
        return _empty_queue()


def save_queue(path, queue):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(temp_path, path)


def enqueue_alert(queue, message, changes, created_at):
    """동일 문안은 한 번만 적재하고 알림 식별자를 반환한다."""
    alert_id = hashlib.sha256(message.encode("utf-8")).hexdigest()[:20]
    if any(item.get("id") == alert_id for item in queue["alerts"]):
        return alert_id, False
    queue["alerts"].append({
        "id": alert_id,
        "created_at": created_at,
        "status": "pending",
        "attempts": 0,
        "message": message,
        "changes": changes,
        "sent_at": None,
        "last_error": None,
    })
    # 운영 파일이 무한히 커지지 않도록 최신 100건만 유지한다.
    queue["alerts"] = queue["alerts"][-100:]
    return alert_id, True


def dispatch_pending(queue, webhook_url, webhook_token=None, now_iso=None, session=requests, timeout=10):
    """미발송 건을 순서대로 전송한다. 실패 건은 다음 실행에서 다시 시도한다."""
    if not webhook_url:
        return {"sent": 0, "failed": 0, "waiting": sum(a.get("status") != "sent" for a in queue["alerts"])}

    sent = failed = expired = 0
    headers = {"Content-Type": "application/json"}
    if webhook_token:
        headers["Authorization"] = f"Bearer {webhook_token}"
    sent_at = now_iso or datetime.now().astimezone().isoformat(timespec="seconds")

    for alert in queue["alerts"]:
        if alert.get("status") == "sent":
            continue
        try:
            created = datetime.fromisoformat(alert["created_at"])
            current = datetime.fromisoformat(sent_at)
            if created.tzinfo is not None and current.tzinfo is not None:
                age_hours = (current - created).total_seconds() / 3600
                if age_hours > MAX_DELIVERY_AGE_HOURS:
                    alert.update(status="expired", last_error="delivery_window_expired")
                    expired += 1
                    continue
        except (KeyError, TypeError, ValueError):
            # 과거 형식이나 테스트 데이터는 만료 판단 없이 전송을 시도한다.
            pass
        alert["attempts"] = int(alert.get("attempts") or 0) + 1
        payload = {
            "event": "weather_safety_alert",
            "idempotency_key": alert["id"],
            "created_at": alert["created_at"],
            "message": alert["message"],
            "changes": alert.get("changes") or [],
        }
        try:
            response = session.post(webhook_url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            alert.update(status="sent", sent_at=sent_at, last_error=None)
            sent += 1
        except requests.RequestException as exc:
            alert.update(status="failed", last_error=type(exc).__name__)
            failed += 1

    return {
        "sent": sent,
        "failed": failed,
        "expired": expired,
        "waiting": sum(a.get("status") in ("pending", "failed") for a in queue["alerts"]),
    }


def process_notifications(path, message, changes, created_at, webhook_url=None, webhook_token=None, session=requests):
    """신규 문안 적재와 기존 실패 건 재전송을 한 번에 수행한다."""
    queue = load_queue(path)
    if message:
        enqueue_alert(queue, message, changes, created_at)
    result = dispatch_pending(queue, webhook_url, webhook_token, session=session)
    save_queue(path, queue)
    return result

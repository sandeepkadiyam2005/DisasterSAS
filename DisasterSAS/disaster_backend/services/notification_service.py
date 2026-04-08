from __future__ import annotations

import logging

from extensions import socketio
from services.sms_service import send_sms_alert

logger = logging.getLogger(__name__)


def notify_emergency_assignment(
    request_id: int,
    requester_name: str | None,
    priority: str,
    status: str,
    allocation_summary: dict | None = None,
) -> None:
    payload = {
        "request_id": request_id,
        "requester_name": requester_name,
        "priority": priority,
        "status": status,
        "allocation": allocation_summary or {},
    }

    try:
        socketio.emit("emergency_assignment", payload)
    except Exception as exc:  # pragma: no cover
        logger.warning("socket emit failed for request %s: %s", request_id, exc)


def notify_critical_emergency_sms(city: str, severity_text: str) -> None:
    """
    Reuses existing SMS pipeline for critical emergency escalation.
    """
    try:
        send_sms_alert(
            city=city or "Unknown",
            alert=f"Critical Emergency: {severity_text}",
            temperature=0,
            humidity=0,
            wind_speed=0,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("critical SMS dispatch failed: %s", exc)

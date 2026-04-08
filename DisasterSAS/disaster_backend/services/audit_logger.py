from __future__ import annotations

import json
from typing import Any, Dict

from extensions import db
from models import AuditLog


def log_audit_event(
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    actor: str | None = None,
    details: Dict[str, Any] | None = None,
) -> AuditLog:
    payload = json.dumps(details or {}, ensure_ascii=True)
    row = AuditLog(
        actor=(actor or "system")[:100],
        action=(action or "unknown")[:100],
        entity_type=(entity_type or "unknown")[:100],
        entity_id=entity_id,
        details=payload[:4000],
    )
    db.session.add(row)
    return row

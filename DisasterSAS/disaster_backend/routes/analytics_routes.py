from flask import Blueprint, jsonify
from auth import require_permission

from models import AuditLog
from services.analytics_engine import emergency_analytics_snapshot

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics/overview", methods=["GET"])
@require_permission("analytics:view")
def analytics_overview():
    return jsonify(emergency_analytics_snapshot())


@analytics_bp.route("/audit/logs", methods=["GET"])
@require_permission("audit:view")
def audit_logs():
    rows = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return jsonify(
        [
            {
                "id": row.id,
                "actor": row.actor,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "details": row.details,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    )

from flask import Blueprint, request, jsonify
from auth import require_permission
from extensions import db
from models import Alert

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/alerts", methods=["GET"])
@require_permission("alerts:view")
def get_alerts():
    alerts = Alert.query.order_by(Alert.created_at.desc()).all()
    return jsonify([
        {
            "id": a.id,
            "title": a.title,
            "message": a.message,
            "severity": a.severity,
            "date": a.date,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in alerts
    ])


@alerts_bp.route("/alerts", methods=["POST"])
@require_permission("alerts:manage")
def add_alert():
    data = request.json

    if not data or not data.get("title") or not data.get("message"):
        return jsonify({"error": "Title and message are required"}), 400

    new_alert = Alert(
        title=data["title"],
        message=data["message"],
        severity=data.get("severity", "medium"),
        date=data.get("date")
    )
    db.session.add(new_alert)
    db.session.commit()

    return jsonify({"message": "Alert added successfully", "id": new_alert.id}), 201


@alerts_bp.route("/alerts/<int:alert_id>", methods=["PUT"])
@require_permission("alerts:manage")
def update_alert(alert_id):
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({"error": "Alert not found"}), 404

    data = request.json
    alert.title = data.get("title", alert.title)
    alert.message = data.get("message", alert.message)
    alert.severity = data.get("severity", alert.severity)
    alert.date = data.get("date", alert.date)

    db.session.commit()
    return jsonify({"message": "Alert updated successfully"})


@alerts_bp.route("/alerts/<int:alert_id>", methods=["DELETE"])
@require_permission("alerts:manage")
def delete_alert(alert_id):
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({"error": "Alert not found"}), 404

    db.session.delete(alert)
    db.session.commit()
    return jsonify({"message": "Alert deleted successfully"})

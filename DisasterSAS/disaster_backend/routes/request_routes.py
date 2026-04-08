from flask import Blueprint, request, jsonify
from sqlalchemy import case, desc, asc

from auth import require_permission
from extensions import db
from models import EmergencyRequest, Shelter, Resource
from services.allocation_engine import auto_allocate_resource, release_one_unit
from services.audit_logger import log_audit_event
from services.notification_service import (
    notify_critical_emergency_sms,
    notify_emergency_assignment,
)
from services.rate_limiter import rate_limit
from services.reallocation_engine import reallocate_for_new_emergency
from services.severity_engine import analyze_severity

request_bp = Blueprint("requests", __name__)

VALID_TYPES = ["food", "water", "medical", "evacuation"]
VALID_PRIORITIES = ["low", "medium", "high", "critical"]
VALID_STATUSES = ["pending", "in_progress", "resolved"]


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _parse_lat_lng(data):
    lat = data.get("latitude")
    lng = data.get("longitude")
    if lat in (None, "") and lng in (None, ""):
        return None, None, None

    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        return None, None, "latitude and longitude must be numeric values"

    if not (-90 <= lat_f <= 90 and -180 <= lng_f <= 180):
        return None, None, "Invalid latitude/longitude values"
    return lat_f, lng_f, None


def _queue_ordering():
    priority_rank = case(
        (EmergencyRequest.priority == "critical", 4),
        (EmergencyRequest.priority == "high", 3),
        (EmergencyRequest.priority == "medium", 2),
        (EmergencyRequest.priority == "low", 1),
        else_=0,
    )
    return [
        desc(EmergencyRequest.severity_score),
        desc(priority_rank),
        asc(EmergencyRequest.created_at),
    ]


@request_bp.route("/emergency-requests", methods=["POST"])
@require_permission("requests:create")
@rate_limit(max_requests=20, window_seconds=60)
def create_request():
    data = _json_body()

    if not data or not data.get("request_type"):
        return jsonify({"error": "request_type is required"}), 400

    request_type = str(data.get("request_type", "")).strip().lower()
    if request_type not in VALID_TYPES:
        return jsonify({"error": f"request_type must be one of: {', '.join(VALID_TYPES)}"}), 400

    user_priority = str(data.get("priority", "medium")).strip().lower()
    if user_priority not in VALID_PRIORITIES:
        return jsonify({"error": f"priority must be one of: {', '.join(VALID_PRIORITIES)}"}), 400

    description = (data.get("description") or "").strip()
    if len(description) > 4000:
        return jsonify({"error": "description is too long (max 4000 chars)"}), 400

    shelter_id = data.get("shelter_id")
    if shelter_id is not None:
        shelter = Shelter.query.get(shelter_id)
        if not shelter:
            return jsonify({"error": "Shelter not found"}), 404

    lat, lng, loc_err = _parse_lat_lng(data)
    if loc_err:
        return jsonify({"error": loc_err}), 400

    intelligence = analyze_severity(
        request_type=request_type,
        description=description,
        user_priority=user_priority,
    )
    final_priority = (
        intelligence["suggested_priority"] if intelligence["auto_override"] else user_priority
    )

    req = EmergencyRequest(
        request_type=request_type,
        description=description or None,
        priority=final_priority,
        severity_score=intelligence["severity_score"],
        auto_priority_override=bool(intelligence["auto_override"]),
        requester_name=(data.get("requester_name") or "").strip()[:100] or None,
        shelter_id=shelter_id,
        latitude=lat,
        longitude=lng,
    )

    db.session.add(req)
    db.session.flush()

    allocation_report = reallocate_for_new_emergency(req)
    allocation = allocation_report.get("allocation", {}) if isinstance(allocation_report, dict) else {}
    moved_requests = allocation_report.get("moved_requests", []) if isinstance(allocation_report, dict) else []

    if not allocation.get("allocated"):
        fallback = auto_allocate_resource(req)
        if fallback.get("allocated"):
            allocation = fallback

    actor = (data.get("requester_name") or "public").strip() or "public"
    log_audit_event(
        action="request_created",
        entity_type="EmergencyRequest",
        entity_id=req.id,
        actor=actor,
        details={
            "request_type": req.request_type,
            "severity_score": req.severity_score,
            "priority": req.priority,
            "auto_priority_override": req.auto_priority_override,
            "matched_keywords": intelligence.get("matched_keywords", []),
            "allocation": allocation,
            "moved_requests": moved_requests,
        },
    )

    if req.priority == "critical":
        city_hint = None
        if req.shelter and req.shelter.location:
            city_hint = req.shelter.location
        notify_critical_emergency_sms(city=city_hint or "Unknown", severity_text=req.request_type)

    notify_emergency_assignment(
        request_id=req.id,
        requester_name=req.requester_name,
        priority=req.priority,
        status=req.status,
        allocation_summary=allocation,
    )

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Emergency request created",
                "id": req.id,
                "severity_score": req.severity_score,
                "priority": req.priority,
                "auto_priority_override": req.auto_priority_override,
                "allocation": allocation,
                "reallocated_request_ids": moved_requests,
            }
        ),
        201,
    )


@request_bp.route("/emergency-requests", methods=["GET"])
@require_permission("requests:view")
def get_requests():
    status = request.args.get("status")
    req_type = request.args.get("type")
    shelter_id = request.args.get("shelter_id")

    query = EmergencyRequest.query

    if status:
        query = query.filter_by(status=status)
    if req_type:
        query = query.filter_by(request_type=req_type)
    if shelter_id:
        query = query.filter_by(shelter_id=shelter_id)

    requests_list = query.order_by(*_queue_ordering()).all()

    return jsonify(
        [
            {
                "id": r.id,
                "request_type": r.request_type,
                "description": r.description,
                "status": r.status,
                "priority": r.priority,
                "severity_score": r.severity_score,
                "auto_priority_override": bool(r.auto_priority_override),
                "requester_name": r.requester_name,
                "shelter_id": r.shelter_id,
                "shelter_name": r.shelter.name if r.shelter else None,
                "assigned_to": r.assigned_to,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "allocated_resource_id": r.allocated_resource_id,
                "allocation_eta_minutes": r.allocation_eta_minutes,
                "allocation_distance_km": r.allocation_distance_km,
                "allocation_status": r.allocation_status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in requests_list
        ]
    )


@request_bp.route("/emergency-requests/<int:req_id>", methods=["PUT"])
@require_permission("requests:manage")
@rate_limit(max_requests=60, window_seconds=60)
def update_request(req_id):
    req = EmergencyRequest.query.filter(EmergencyRequest.id == req_id).with_for_update().first()
    if not req:
        return jsonify({"error": "Request not found"}), 404

    data = _json_body()
    previous_state = {
        "status": req.status,
        "priority": req.priority,
        "severity_score": req.severity_score,
        "allocated_resource_id": req.allocated_resource_id,
    }

    if "status" in data:
        status = str(data.get("status", "")).strip().lower()
        if status not in VALID_STATUSES:
            return jsonify({"error": f"status must be one of: {', '.join(VALID_STATUSES)}"}), 400
        req.status = status

    if "priority" in data:
        priority = str(data.get("priority", "")).strip().lower()
        if priority not in VALID_PRIORITIES:
            return jsonify({"error": f"priority must be one of: {', '.join(VALID_PRIORITIES)}"}), 400
        req.priority = priority

    if "description" in data:
        text = (data.get("description") or "").strip()
        if len(text) > 4000:
            return jsonify({"error": "description is too long (max 4000 chars)"}), 400
        req.description = text or None

    if "assigned_to" in data:
        req.assigned_to = (data.get("assigned_to") or "").strip()[:100] or None

    if "shelter_id" in data:
        shelter_id = data.get("shelter_id")
        if shelter_id is not None:
            if not Shelter.query.get(shelter_id):
                return jsonify({"error": "Shelter not found"}), 404
        req.shelter_id = shelter_id

    if "latitude" in data or "longitude" in data:
        lat, lng, loc_err = _parse_lat_lng(data)
        if loc_err:
            return jsonify({"error": loc_err}), 400
        req.latitude = lat
        req.longitude = lng

    if any(key in data for key in ["priority", "description", "request_type"]):
        intelligence = analyze_severity(
            request_type=req.request_type,
            description=req.description or "",
            user_priority=req.priority,
        )
        req.severity_score = intelligence["severity_score"]
        req.auto_priority_override = bool(intelligence["auto_override"])
        if intelligence["auto_override"]:
            req.priority = intelligence["suggested_priority"]

    allocation = {}
    if req.status in {"pending", "in_progress"} and not req.allocated_resource_id:
        reallocated = reallocate_for_new_emergency(req)
        allocation = reallocated.get("allocation", {}) if isinstance(reallocated, dict) else {}

    log_audit_event(
        action="request_updated",
        entity_type="EmergencyRequest",
        entity_id=req.id,
        actor=(data.get("assigned_to") or "system")[:100] if isinstance(data, dict) else "system",
        details={
            "before": previous_state,
            "after": {
                "status": req.status,
                "priority": req.priority,
                "severity_score": req.severity_score,
                "allocated_resource_id": req.allocated_resource_id,
            },
            "allocation": allocation,
        },
    )

    db.session.commit()
    return jsonify({"message": "Request updated", "allocation": allocation})


@request_bp.route("/emergency-requests/<int:req_id>", methods=["DELETE"])
@require_permission("requests:manage")
@rate_limit(max_requests=30, window_seconds=60)
def delete_request(req_id):
    req = EmergencyRequest.query.get(req_id)
    if not req:
        return jsonify({"error": "Request not found"}), 404

    if req.allocated_resource_id:
        resource = Resource.query.get(req.allocated_resource_id)
        if resource:
            release_one_unit(resource, req.request_type or "")

    log_audit_event(
        action="request_deleted",
        entity_type="EmergencyRequest",
        entity_id=req.id,
        actor="system",
        details={"request_type": req.request_type, "priority": req.priority},
    )
    db.session.delete(req)
    db.session.commit()
    return jsonify({"message": "Request deleted"})


@request_bp.route("/emergency-requests/queue", methods=["GET"])
@require_permission("requests:queue")
def get_request_queue():
    limit = max(1, min(200, request.args.get("limit", default=100, type=int) or 100))
    rows = (
        EmergencyRequest.query.filter(EmergencyRequest.status.in_(["pending", "in_progress"]))
        .order_by(*_queue_ordering())
        .limit(limit)
        .all()
    )
    return jsonify(
        [
            {
                "id": r.id,
                "request_type": r.request_type,
                "priority": r.priority,
                "severity_score": r.severity_score,
                "status": r.status,
                "shelter_id": r.shelter_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    )


@request_bp.route("/emergency-requests/stats", methods=["GET"])
@require_permission("requests:stats")
def request_stats():
    total = EmergencyRequest.query.count()
    pending = EmergencyRequest.query.filter_by(status="pending").count()
    in_progress = EmergencyRequest.query.filter_by(status="in_progress").count()
    resolved = EmergencyRequest.query.filter_by(status="resolved").count()
    auto_assigned = EmergencyRequest.query.filter_by(allocation_status="auto_assigned").count()

    return jsonify(
        {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "resolved": resolved,
            "auto_assigned": auto_assigned,
        }
    )

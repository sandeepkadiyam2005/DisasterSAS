from __future__ import annotations

from typing import Dict, List

from models import EmergencyRequest, Resource
from services.allocation_engine import auto_allocate_resource, release_one_unit


_PRIORITY_ORDER = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def _priority_value(priority: str | None) -> int:
    return _PRIORITY_ORDER.get((priority or "").lower(), 0)


def reallocate_for_new_emergency(new_request: EmergencyRequest) -> Dict:
    """
    Tries to preserve critical path by reassigning lower-priority in-progress requests
    if the new request cannot be allocated directly.
    Caller owns transaction commit.
    """
    initial = auto_allocate_resource(new_request)
    if initial.get("allocated"):
        return {"reallocated": False, "allocation": initial, "moved_requests": []}

    current_priority = _priority_value(new_request.priority)
    if current_priority < _PRIORITY_ORDER["high"]:
        return {"reallocated": False, "allocation": initial, "moved_requests": []}

    moved: List[int] = []
    candidates = (
        EmergencyRequest.query.filter(EmergencyRequest.status == "in_progress")
        .filter(EmergencyRequest.allocated_resource_id.isnot(None))
        .order_by(EmergencyRequest.severity_score.asc(), EmergencyRequest.created_at.asc())
        .all()
    )

    for req in candidates:
        if req.id == new_request.id:
            continue
        if _priority_value(req.priority) >= current_priority:
            continue

        if req.allocated_resource_id:
            resource = Resource.query.get(req.allocated_resource_id)
            if resource:
                release_one_unit(resource, req.request_type or "")

        req.status = "pending"
        req.allocation_status = "reallocated_out"
        req.assigned_to = None
        req.allocated_resource_id = None
        req.allocation_eta_minutes = None
        req.allocation_distance_km = None
        moved.append(req.id)

        retried = auto_allocate_resource(new_request)
        if retried.get("allocated"):
            return {"reallocated": True, "allocation": retried, "moved_requests": moved}

    return {"reallocated": bool(moved), "allocation": initial, "moved_requests": moved}


def rebalance_stuck_assignments(eta_threshold_minutes: int = 180) -> Dict:
    """
    Lightweight rebalancing:
    - requests with very high ETA are moved back to pending to be re-allocated.
    """
    touched = []
    rows = (
        EmergencyRequest.query.filter(EmergencyRequest.status == "in_progress")
        .filter(EmergencyRequest.allocation_eta_minutes.isnot(None))
        .all()
    )

    for req in rows:
        eta = int(req.allocation_eta_minutes or 0)
        if eta > eta_threshold_minutes:
            if req.allocated_resource_id:
                resource = Resource.query.get(req.allocated_resource_id)
                if resource:
                    release_one_unit(resource, req.request_type or "")
            req.status = "pending"
            req.allocation_status = "reallocation_needed"
            req.allocated_resource_id = None
            req.assigned_to = None
            req.allocation_eta_minutes = None
            req.allocation_distance_km = None
            touched.append(req.id)

    return {"rebalanced_count": len(touched), "request_ids": touched}

from __future__ import annotations

import math
from typing import Dict, Optional

from models import EmergencyRequest, Resource


REQUEST_TYPE_TO_FIELD = {
    "food": "food_packets",
    "water": "water_bottles",
    "medical": "medical_kits",
    "evacuation": "blankets",
}

_PROFILE_SPEED_KMPH = {
    "critical": 42.0,
    "high": 36.0,
    "medium": 30.0,
    "low": 26.0,
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return radius_km * 2 * math.asin(math.sqrt(a))


def _has_required_stock(resource: Resource, request_type: str) -> bool:
    field = REQUEST_TYPE_TO_FIELD.get(request_type)
    if not field:
        return False
    return int(getattr(resource, field, 0) or 0) > 0


def _distance_for_request(resource: Resource, req: EmergencyRequest) -> Optional[float]:
    shelter = resource.shelter
    if not shelter:
        return None

    if req.latitude is not None and req.longitude is not None:
        if shelter.latitude is None or shelter.longitude is None:
            return None
        return haversine_km(
            float(req.latitude),
            float(req.longitude),
            float(shelter.latitude),
            float(shelter.longitude),
        )

    if req.shelter_id and req.shelter_id == resource.shelter_id:
        return 0.0

    return None


def _eta_minutes(distance_km: float, priority: str) -> int:
    speed_kmph = _PROFILE_SPEED_KMPH.get((priority or "").lower(), 30.0)
    hours = distance_km / max(1.0, speed_kmph)
    return max(3, int(round(hours * 60)))


def _consume_one_unit(resource: Resource, request_type: str) -> None:
    field = REQUEST_TYPE_TO_FIELD.get(request_type)
    if not field:
        return
    current = int(getattr(resource, field, 0) or 0)
    setattr(resource, field, max(0, current - 1))

    total_left = (
        int(resource.food_packets or 0)
        + int(resource.water_bottles or 0)
        + int(resource.medical_kits or 0)
        + int(resource.blankets or 0)
    )
    resource.is_available = total_left > 0


def release_one_unit(resource: Resource, request_type: str) -> None:
    field = REQUEST_TYPE_TO_FIELD.get(request_type)
    if not field:
        return
    current = int(getattr(resource, field, 0) or 0)
    setattr(resource, field, current + 1)
    resource.is_available = True


def auto_allocate_resource(req: EmergencyRequest) -> Dict:
    """
    Finds best-fit resource and applies assignment to request in current DB session.
    Caller owns commit/rollback.
    """
    req_type = (req.request_type or "").lower()
    if req_type not in REQUEST_TYPE_TO_FIELD:
        return {"allocated": False, "reason": "unsupported_request_type"}

    resources = (
        Resource.query.filter_by(is_available=True)
        .join(Resource.shelter)
        .all()
    )

    candidates = []
    for res in resources:
        if not _has_required_stock(res, req_type):
            continue
        if not res.shelter or (res.shelter.status or "").lower() != "open":
            continue

        distance_km = _distance_for_request(res, req)
        if distance_km is None:
            # Unknown geospatial distance; keep as less-preferred fallback.
            distance_km = 999.0

        stock_field = REQUEST_TYPE_TO_FIELD[req_type]
        stock_left = int(getattr(res, stock_field, 0) or 0)
        # Lower score is better: prioritize closer and better stocked resources.
        fit_score = (distance_km * 2.5) - min(stock_left, 100) * 0.1
        candidates.append((fit_score, distance_km, res))

    if not candidates:
        req.allocation_status = "unassigned"
        return {"allocated": False, "reason": "no_resource_available"}

    candidates.sort(key=lambda item: item[0])
    _, distance_km, selected = candidates[0]
    eta = _eta_minutes(distance_km, req.priority or "medium")

    _consume_one_unit(selected, req_type)
    req.allocated_resource_id = selected.id
    req.allocation_distance_km = round(distance_km, 3)
    req.allocation_eta_minutes = eta
    req.allocation_status = "auto_assigned"
    req.status = "in_progress" if req.status == "pending" else req.status
    req.assigned_to = req.assigned_to or f"resource:{selected.id}"

    return {
        "allocated": True,
        "resource_id": selected.id,
        "shelter_id": selected.shelter_id,
        "distance_km": round(distance_km, 3),
        "eta_minutes": eta,
    }

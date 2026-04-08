from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict

from models import EmergencyRequest, Resource


def _minutes_between(start: datetime | None, end: datetime | None) -> float | None:
    if not start or not end:
        return None
    return max(0.0, (end - start).total_seconds() / 60.0)


def emergency_analytics_snapshot() -> Dict:
    rows = EmergencyRequest.query.all()
    resources = Resource.query.all()

    if not rows:
        return {
            "total_requests": 0,
            "average_response_minutes": 0,
            "resource_utilization_percent": 0,
            "request_type_distribution": {},
            "priority_distribution": {},
            "heatmap_density": {},
        }

    response_times = []
    type_dist = Counter()
    priority_dist = Counter()
    heatmap = defaultdict(int)

    for req in rows:
        type_dist[req.request_type or "unknown"] += 1
        priority_dist[req.priority or "unknown"] += 1

        if req.status == "resolved":
            mins = _minutes_between(req.created_at, req.updated_at)
            if mins is not None:
                response_times.append(mins)

        if req.latitude is not None and req.longitude is not None:
            grid_key = f"{round(float(req.latitude), 1)},{round(float(req.longitude), 1)}"
        elif req.shelter_id:
            grid_key = f"shelter:{req.shelter_id}"
        else:
            grid_key = "unknown"
        heatmap[grid_key] += 1

    avg_response = round(sum(response_times) / len(response_times), 2) if response_times else 0

    total_resources = len(resources)
    active_allocations = sum(
        1
        for req in rows
        if req.allocated_resource_id is not None and req.status in {"in_progress", "resolved"}
    )
    unavailable_resources = sum(1 for res in resources if not bool(res.is_available))
    effective_busy = max(active_allocations, unavailable_resources)
    utilization = (
        round((effective_busy / float(total_resources)) * 100.0, 2) if total_resources > 0 else 0.0
    )
    utilization = max(0.0, min(100.0, utilization))

    return {
        "total_requests": len(rows),
        "average_response_minutes": avg_response,
        "resource_utilization_percent": utilization,
        "request_type_distribution": dict(type_dist),
        "priority_distribution": dict(priority_dist),
        "heatmap_density": dict(heatmap),
    }

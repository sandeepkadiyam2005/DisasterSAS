import math
from datetime import datetime, timedelta

import requests
from flask import Blueprint, jsonify, request

from auth import require_permission
from models import Shelter, WeatherLog

map_system_bp = Blueprint("map_system", __name__)

# Lightweight fallback coordinates for weather-alert cities.
CITY_COORDS = {
    "hyderabad": {"lat": 17.3850, "lng": 78.4867},
    "delhi": {"lat": 28.6139, "lng": 77.2090},
    "mumbai": {"lat": 19.0760, "lng": 72.8777},
    "bengaluru": {"lat": 12.9716, "lng": 77.5946},
    "bangalore": {"lat": 12.9716, "lng": 77.5946},
    "chennai": {"lat": 13.0827, "lng": 80.2707},
    "kolkata": {"lat": 22.5726, "lng": 88.3639},
    "pune": {"lat": 18.5204, "lng": 73.8567},
    "ahmedabad": {"lat": 23.0225, "lng": 72.5714},
    "jaipur": {"lat": 26.9124, "lng": 75.7873},
    "lucknow": {"lat": 26.8467, "lng": 80.9462},
    "patna": {"lat": 25.5941, "lng": 85.1376},
    "bhubaneswar": {"lat": 20.2961, "lng": 85.8245},
    "guwahati": {"lat": 26.1445, "lng": 91.7362},
    "kochi": {"lat": 9.9312, "lng": 76.2673},
    "surat": {"lat": 21.1702, "lng": 72.8311},
}


def _haversine_km(lat1, lon1, lat2, lon2):
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


def _bearing_deg(lat1, lon1, lat2, lon2):
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = (
        math.cos(math.radians(lat1)) * math.sin(math.radians(lat2))
        - math.sin(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.cos(dlon)
    )
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _cardinal_from_bearing(deg):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[int(round(deg / 45.0)) % 8]


def _city_to_coords(city_name):
    if not city_name:
        return None
    key = city_name.strip().lower()
    if key in CITY_COORDS:
        return CITY_COORDS[key]
    for name, coords in CITY_COORDS.items():
        if name in key or key in name:
            return coords
    return None


def _parse_lat_lng():
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    if lat is None or lng is None:
        return None, None, jsonify({"error": "lat and lng query parameters are required"}), 400
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None, None, jsonify({"error": "Invalid lat/lng values"}), 400
    return lat, lng, None, None


def _normalize_osrm_steps(route):
    steps = []
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            maneuver = step.get("maneuver", {})
            m_type = str(maneuver.get("type", "continue")).replace("_", " ")
            modifier = maneuver.get("modifier")
            road = step.get("name")

            if maneuver.get("type") == "depart":
                instruction = f"Start{' on ' + road if road else ''}"
            elif maneuver.get("type") == "arrive":
                instruction = "Arrive at destination"
            elif maneuver.get("type") in {"roundabout", "rotary"}:
                exit_num = maneuver.get("exit")
                exit_hint = f", take exit {exit_num}" if exit_num else ""
                instruction = f"Enter roundabout{exit_hint}{' on ' + road if road else ''}"
            else:
                phrase = m_type[:1].upper() + m_type[1:]
                if modifier:
                    phrase = f"{phrase} {modifier}"
                if road:
                    phrase = f"{phrase} on {road}"
                instruction = phrase.strip()

            steps.append({
                "instruction": instruction,
                "distance": float(step.get("distance", 0) or 0),
            })
    return steps


def _direct_fallback_route(start_lat, start_lng, end_lat, end_lng):
    distance_km = _haversine_km(start_lat, start_lng, end_lat, end_lng)
    bearing = _bearing_deg(start_lat, start_lng, end_lat, end_lng)
    heading = _cardinal_from_bearing(bearing)
    distance_m = max(1, int(round(distance_km * 1000)))
    duration_s = max(60, int(round((distance_km / 4.5) * 3600)))  # ~4.5 km/h walking

    return {
        "mode": "offline_fallback",
        "source": "direct",
        "profile": "direct",
        "distance": distance_m,
        "duration": duration_s,
        "geometry": [
            [float(start_lng), float(start_lat)],
            [float(end_lng), float(end_lat)],
        ],
        "steps": [
            {
                "instruction": f"Head {heading} ({round(bearing)}°) toward destination",
                "distance": distance_m,
            },
            {
                "instruction": "Continue directly to destination",
                "distance": 0,
            },
        ],
    }


@map_system_bp.route("/map/shelters/nearby", methods=["GET"])
@require_permission("map:view")
def map_nearby_shelters():
    lat, lng, error_resp, error_code = _parse_lat_lng()
    if error_resp:
        return error_resp, error_code

    radius_km = max(1.0, min(500.0, request.args.get("radius_km", default=20.0, type=float) or 20.0))
    limit = max(1, min(200, request.args.get("limit", default=50, type=int) or 50))

    shelters = Shelter.query.filter_by(status="open").all()
    items = []
    missing_coordinates = 0

    for shelter in shelters:
        s_lat = shelter.latitude
        s_lng = shelter.longitude
        if s_lat is None or s_lng is None:
            missing_coordinates += 1
            continue

        distance_km = _haversine_km(lat, lng, float(s_lat), float(s_lng))
        available_beds = int((shelter.capacity or 0) - (shelter.current_occupancy or 0))
        items.append({
            "id": shelter.id,
            "name": shelter.name,
            "location": shelter.location,
            "latitude": float(s_lat),
            "longitude": float(s_lng),
            "capacity": int(shelter.capacity or 0),
            "current_occupancy": int(shelter.current_occupancy or 0),
            "available_beds": available_beds,
            "contact": shelter.contact,
            "status": shelter.status or "open",
            "distance_km": round(distance_km, 3),
            "inside_radius": distance_km <= radius_km,
        })

    items.sort(key=lambda item: item["distance_km"])
    inside = [item for item in items if item["inside_radius"]]
    selected = inside[:limit] if inside else items[: min(limit, 5)]

    return jsonify({
        "center": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "total_open_shelters": len(items),
        "missing_coordinates": missing_coordinates,
        "returned": len(selected),
        "items": selected,
    })


@map_system_bp.route("/map/alerts/nearby", methods=["GET"])
@require_permission("map:view")
def map_nearby_alerts():
    lat, lng, error_resp, error_code = _parse_lat_lng()
    if error_resp:
        return error_resp, error_code

    radius_km = max(1.0, min(500.0, request.args.get("radius_km", default=20.0, type=float) or 20.0))
    limit = max(1, min(200, request.args.get("limit", default=50, type=int) or 50))
    lookback_hours = max(1, min(168, request.args.get("lookback_hours", default=72, type=int) or 72))
    include_outside_if_empty = request.args.get("include_outside_if_empty", "true").lower() != "false"

    threshold = datetime.utcnow() - timedelta(hours=lookback_hours)
    rows = (
        WeatherLog.query.filter(WeatherLog.timestamp >= threshold)
        .filter(WeatherLog.disaster_alert != "No severe weather conditions.")
        .order_by(WeatherLog.timestamp.desc())
        .limit(300)
        .all()
    )

    items = []
    missing_coordinates = 0
    for row in rows:
        coords = _city_to_coords(row.city)
        if not coords:
            missing_coordinates += 1
            continue

        dist = _haversine_km(lat, lng, coords["lat"], coords["lng"])
        items.append({
            "city": row.city,
            "alert": row.disaster_alert,
            "temperature": row.temperature,
            "humidity": row.humidity,
            "wind_speed": row.wind_speed,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "latitude": float(coords["lat"]),
            "longitude": float(coords["lng"]),
            "distance_km": round(dist, 3),
            "inside_radius": dist <= radius_km,
        })

    items.sort(key=lambda item: item["distance_km"])
    inside = [item for item in items if item["inside_radius"]]
    selected = inside[:limit]
    if not selected and include_outside_if_empty:
        selected = items[: min(limit, 5)]

    return jsonify({
        "center": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "total_alerts_considered": len(items),
        "missing_coordinates": missing_coordinates,
        "returned": len(selected),
        "items": selected,
    })


@map_system_bp.route("/map/route", methods=["POST"])
@require_permission("map:view")
def map_route():
    payload = request.get_json(silent=True) or {}
    start = payload.get("start") or {}
    end = payload.get("end") or {}
    preferred_profiles = payload.get("preferred_profiles") or ["driving", "foot"]

    try:
        start_lat = float(start.get("lat"))
        start_lng = float(start.get("lng"))
        end_lat = float(end.get("lat"))
        end_lng = float(end.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"error": "start/end coordinates are required"}), 400

    if not (-90 <= start_lat <= 90 and -180 <= start_lng <= 180 and -90 <= end_lat <= 90 and -180 <= end_lng <= 180):
        return jsonify({"error": "Invalid start/end coordinates"}), 400

    profile_alias = {
        "driving": "driving",
        "car": "driving",
        "foot": "foot",
        "walking": "foot",
        "walk": "foot",
        "bike": "bike",
        "cycling": "bike",
    }
    route_profiles = []
    for item in preferred_profiles:
        normalized = profile_alias.get(str(item).lower().strip())
        if normalized and normalized not in route_profiles:
            route_profiles.append(normalized)
    if not route_profiles:
        route_profiles = ["driving", "foot"]

    osrm_base = "https://router.project-osrm.org/route/v1"
    start_pair = f"{start_lng},{start_lat}"
    end_pair = f"{end_lng},{end_lat}"
    last_error = None

    for profile in route_profiles:
        url = (
            f"{osrm_base}/{profile}/{start_pair};{end_pair}"
            "?overview=full&geometries=geojson&steps=true&alternatives=true"
        )
        try:
            response = requests.get(url, timeout=12)
            if response.status_code != 200:
                last_error = f"osrm status {response.status_code}"
                continue

            data = response.json()
            if data.get("code") != "Ok" or not data.get("routes"):
                last_error = "osrm no route"
                continue

            route = data["routes"][0]
            geometry = route.get("geometry", {}).get("coordinates") or []
            if len(geometry) < 2:
                last_error = "invalid route geometry"
                continue

            steps = _normalize_osrm_steps(route)
            return jsonify({
                "mode": "online",
                "source": "osrm",
                "profile": profile,
                "distance": float(route.get("distance", 0) or 0),
                "duration": float(route.get("duration", 0) or 0),
                "geometry": geometry,
                "steps": steps,
            })
        except requests.RequestException as exc:
            last_error = str(exc)
            continue

    fallback = _direct_fallback_route(start_lat, start_lng, end_lat, end_lng)
    fallback["reason"] = last_error or "routing unavailable"
    return jsonify(fallback)

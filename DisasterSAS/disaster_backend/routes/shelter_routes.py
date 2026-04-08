from flask import Blueprint, request, jsonify
from auth import require_permission
from extensions import db
from models import Shelter

shelter_bp = Blueprint("shelter", __name__)


@shelter_bp.route("/shelters", methods=["GET"])
@require_permission("shelters:view")
def get_shelters():
    status = request.args.get("status")

    query = Shelter.query
    if status:
        query = query.filter_by(status=status)

    shelters = query.all()

    return jsonify([
        {
            "id": s.id,
            "name": s.name,
            "location": s.location,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "capacity": s.capacity,
            "current_occupancy": s.current_occupancy,
            "contact": s.contact,
            "status": s.status
        }
        for s in shelters
    ])


@shelter_bp.route("/shelters", methods=["POST"])
@require_permission("shelters:manage")
def add_shelter():
    data = request.json

    if not data or not data.get("name") or not data.get("location"):
        return jsonify({"error": "Name and location are required"}), 400

    shelter = Shelter(
        name=data["name"],
        location=data["location"],
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        capacity=data.get("capacity", 0),
        contact=data.get("contact"),
        status=data.get("status", "open")
    )

    db.session.add(shelter)
    db.session.commit()

    return jsonify({"message": "Shelter added successfully", "id": shelter.id}), 201


@shelter_bp.route("/shelters/<int:shelter_id>", methods=["PUT"])
@require_permission("shelters:manage")
def update_shelter(shelter_id):
    shelter = Shelter.query.get(shelter_id)
    if not shelter:
        return jsonify({"error": "Shelter not found"}), 404

    data = request.json
    shelter.name = data.get("name", shelter.name)
    shelter.location = data.get("location", shelter.location)
    shelter.latitude = data.get("latitude", shelter.latitude)
    shelter.longitude = data.get("longitude", shelter.longitude)
    shelter.capacity = data.get("capacity", shelter.capacity)
    shelter.current_occupancy = data.get("current_occupancy", shelter.current_occupancy)
    shelter.contact = data.get("contact", shelter.contact)
    shelter.status = data.get("status", shelter.status)

    db.session.commit()

    return jsonify({"message": "Shelter updated successfully"})


@shelter_bp.route("/shelters/<int:shelter_id>", methods=["DELETE"])
@require_permission("shelters:manage")
def delete_shelter(shelter_id):
    shelter = Shelter.query.get(shelter_id)
    if not shelter:
        return jsonify({"error": "Shelter not found"}), 404

    db.session.delete(shelter)
    db.session.commit()

    return jsonify({"message": "Shelter deleted successfully"})


@shelter_bp.route("/shelters/nearest", methods=["GET"])
@require_permission("shelters:view")
def nearest_shelters():
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)

    if lat is None or lng is None:
        return jsonify({"error": "lat and lng parameters are required"}), 400

    shelters = Shelter.query.filter_by(status="open").all()

    import math

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    results = []
    for s in shelters:
        if s.latitude and s.longitude:
            dist = haversine(lat, lng, s.latitude, s.longitude)
            results.append({
                "id": s.id,
                "name": s.name,
                "location": s.location,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "capacity": s.capacity,
                "current_occupancy": s.current_occupancy,
                "available_beds": s.capacity - s.current_occupancy,
                "contact": s.contact,
                "status": s.status,
                "distance_km": round(dist, 2)
            })

    results.sort(key=lambda x: x["distance_km"])
    return jsonify(results)


@shelter_bp.route("/shelters/stats", methods=["GET"])
@require_permission("shelters:view")
def shelter_stats():
    total = Shelter.query.count()
    open_count = Shelter.query.filter_by(status="open").count()
    full_count = Shelter.query.filter_by(status="full").count()
    closed_count = Shelter.query.filter_by(status="closed").count()
    total_capacity = sum(s.capacity for s in Shelter.query.all())
    total_occupancy = sum(s.current_occupancy for s in Shelter.query.all())

    return jsonify({
        "total_shelters": total,
        "open": open_count,
        "full": full_count,
        "closed": closed_count,
        "total_capacity": total_capacity,
        "total_occupancy": total_occupancy,
        "available_beds": total_capacity - total_occupancy
    })

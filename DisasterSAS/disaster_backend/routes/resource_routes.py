from flask import Blueprint, request, jsonify
from auth import require_permission
from extensions import db
from models import Resource, Shelter

resource_bp = Blueprint("resource", __name__)


@resource_bp.route("/resources", methods=["GET"])
@require_permission("resources:view")
def get_resources():
    shelter_id = request.args.get("shelter_id")

    query = Resource.query

    if shelter_id:
        query = query.filter_by(shelter_id=shelter_id)

    resources = query.all()

    return jsonify([
        {
            "id": r.id,
            "shelter_id": r.shelter_id,
            "shelter_name": r.shelter.name if r.shelter else None,
            "food_packets": r.food_packets,
            "water_bottles": r.water_bottles,
            "medical_kits": r.medical_kits,
            "blankets": r.blankets,
            "is_available": bool(r.is_available),
            "last_updated": r.last_updated.isoformat() if r.last_updated else None
        }
        for r in resources
    ])


@resource_bp.route("/resources", methods=["POST"])
@require_permission("resources:manage")
def add_resources():
    data = request.json

    if not data or not data.get("shelter_id"):
        return jsonify({"error": "shelter_id is required"}), 400

    shelter = Shelter.query.get(data["shelter_id"])
    if not shelter:
        return jsonify({"error": "Shelter not found"}), 404

    # Check if resource record already exists for this shelter
    existing = Resource.query.filter_by(shelter_id=data["shelter_id"]).first()

    if existing:
        existing.food_packets = data.get("food_packets", existing.food_packets)
        existing.water_bottles = data.get("water_bottles", existing.water_bottles)
        existing.medical_kits = data.get("medical_kits", existing.medical_kits)
        existing.blankets = data.get("blankets", existing.blankets)
        total_units = int(existing.food_packets or 0) + int(existing.water_bottles or 0) + int(existing.medical_kits or 0) + int(existing.blankets or 0)
        existing.is_available = total_units > 0
        db.session.commit()
        return jsonify({"message": "Resources updated", "id": existing.id})

    resource = Resource(
        shelter_id=data["shelter_id"],
        food_packets=data.get("food_packets", 0),
        water_bottles=data.get("water_bottles", 0),
        medical_kits=data.get("medical_kits", 0),
        blankets=data.get("blankets", 0),
        is_available=True,
    )
    total_units = int(resource.food_packets or 0) + int(resource.water_bottles or 0) + int(resource.medical_kits or 0) + int(resource.blankets or 0)
    resource.is_available = total_units > 0

    db.session.add(resource)
    db.session.commit()

    return jsonify({"message": "Resources added", "id": resource.id}), 201


@resource_bp.route("/resources/<int:resource_id>", methods=["PUT"])
@require_permission("resources:manage")
def update_resources(resource_id):
    resource = Resource.query.get(resource_id)
    if not resource:
        return jsonify({"error": "Resource not found"}), 404

    data = request.json
    resource.food_packets = data.get("food_packets", resource.food_packets)
    resource.water_bottles = data.get("water_bottles", resource.water_bottles)
    resource.medical_kits = data.get("medical_kits", resource.medical_kits)
    resource.blankets = data.get("blankets", resource.blankets)
    total_units = int(resource.food_packets or 0) + int(resource.water_bottles or 0) + int(resource.medical_kits or 0) + int(resource.blankets or 0)
    resource.is_available = total_units > 0

    db.session.commit()
    return jsonify({"message": "Resources updated"})


@resource_bp.route("/resources/<int:resource_id>", methods=["DELETE"])
@require_permission("resources:manage")
def delete_resources(resource_id):
    resource = Resource.query.get(resource_id)
    if not resource:
        return jsonify({"error": "Resource not found"}), 404

    db.session.delete(resource)
    db.session.commit()
    return jsonify({"message": "Resource record deleted"})


@resource_bp.route("/resources/summary", methods=["GET"])
@require_permission("resources:view")
def resource_summary():
    resources = Resource.query.all()

    total_food = sum(r.food_packets for r in resources)
    total_water = sum(r.water_bottles for r in resources)
    total_medical = sum(r.medical_kits for r in resources)
    total_blankets = sum(r.blankets for r in resources)

    low_stock = []
    for r in resources:
        issues = []
        if r.food_packets < 10:
            issues.append("food")
        if r.water_bottles < 10:
            issues.append("water")
        if r.medical_kits < 5:
            issues.append("medical")
        if r.blankets < 10:
            issues.append("blankets")

        if issues:
            low_stock.append({
                "shelter_id": r.shelter_id,
                "shelter_name": r.shelter.name if r.shelter else None,
                "low_items": issues
            })

    return jsonify({
        "total_food_packets": total_food,
        "total_water_bottles": total_water,
        "total_medical_kits": total_medical,
        "total_blankets": total_blankets,
        "shelters_with_low_stock": low_stock
    })

from flask import Blueprint, request, jsonify
from auth import require_permission
from extensions import db
from models import Survivor, Shelter

survivor_bp = Blueprint("survivor", __name__)


@survivor_bp.route("/survivors", methods=["POST"])
@require_permission("survivors:manage")
def register_survivor():
    data = request.json

    if not data or not data.get("name"):
        return jsonify({"error": "Name is required"}), 400

    shelter_id = data.get("shelter_id")

    # Validate shelter exists and has capacity
    if shelter_id:
        shelter = Shelter.query.get(shelter_id)
        if not shelter:
            return jsonify({"error": "Shelter not found"}), 404
        if shelter.current_occupancy >= shelter.capacity:
            return jsonify({"error": "Shelter is full"}), 400

    survivor = Survivor(
        name=data["name"],
        age=data.get("age"),
        gender=data.get("gender"),
        contact=data.get("contact"),
        health_status=data.get("health_status", "stable"),
        shelter_id=shelter_id,
        registered_by=data.get("registered_by"),
        notes=data.get("notes")
    )

    db.session.add(survivor)

    # Auto-update shelter occupancy
    if shelter_id:
        shelter = Shelter.query.get(shelter_id)
        shelter.current_occupancy += 1
        if shelter.current_occupancy >= shelter.capacity:
            shelter.status = "full"

    db.session.commit()

    return jsonify({"message": "Survivor registered", "id": survivor.id}), 201


@survivor_bp.route("/survivors", methods=["GET"])
@require_permission("survivors:view")
def get_survivors():
    shelter_id = request.args.get("shelter_id")
    health = request.args.get("health_status")

    query = Survivor.query

    if shelter_id:
        query = query.filter_by(shelter_id=shelter_id)
    if health:
        query = query.filter_by(health_status=health)

    survivors = query.order_by(Survivor.registered_at.desc()).all()

    return jsonify([
        {
            "id": s.id,
            "name": s.name,
            "age": s.age,
            "gender": s.gender,
            "contact": s.contact,
            "health_status": s.health_status,
            "shelter_id": s.shelter_id,
            "shelter_name": s.shelter.name if s.shelter else None,
            "registered_by": s.registered_by,
            "notes": s.notes,
            "registered_at": s.registered_at.isoformat() if s.registered_at else None
        }
        for s in survivors
    ])


@survivor_bp.route("/survivors/search", methods=["GET"])
@require_permission("survivors:view")
def search_survivors():
    name = request.args.get("name", "").strip()

    if not name:
        return jsonify({"error": "Name parameter is required"}), 400

    survivors = Survivor.query.filter(
        Survivor.name.ilike(f"%{name}%")
    ).order_by(Survivor.registered_at.desc()).all()

    return jsonify([
        {
            "id": s.id,
            "name": s.name,
            "age": s.age,
            "gender": s.gender,
            "contact": s.contact,
            "health_status": s.health_status,
            "shelter_id": s.shelter_id,
            "shelter_name": s.shelter.name if s.shelter else None,
            "registered_by": s.registered_by,
            "notes": s.notes,
            "registered_at": s.registered_at.isoformat() if s.registered_at else None
        }
        for s in survivors
    ])


@survivor_bp.route("/survivors/<int:survivor_id>", methods=["PUT"])
@require_permission("survivors:manage")
def update_survivor(survivor_id):
    survivor = Survivor.query.get(survivor_id)
    if not survivor:
        return jsonify({"error": "Survivor not found"}), 404

    data = request.json
    old_shelter_id = survivor.shelter_id
    new_shelter_id = data.get("shelter_id", old_shelter_id)

    survivor.name = data.get("name", survivor.name)
    survivor.age = data.get("age", survivor.age)
    survivor.gender = data.get("gender", survivor.gender)
    survivor.contact = data.get("contact", survivor.contact)
    survivor.health_status = data.get("health_status", survivor.health_status)
    survivor.notes = data.get("notes", survivor.notes)

    # Handle shelter transfer
    if new_shelter_id != old_shelter_id:
        if old_shelter_id:
            old_shelter = Shelter.query.get(old_shelter_id)
            if old_shelter:
                old_shelter.current_occupancy = max(0, old_shelter.current_occupancy - 1)
                if old_shelter.status == "full":
                    old_shelter.status = "open"

        if new_shelter_id:
            new_shelter = Shelter.query.get(new_shelter_id)
            if not new_shelter:
                return jsonify({"error": "Target shelter not found"}), 404
            new_shelter.current_occupancy += 1
            if new_shelter.current_occupancy >= new_shelter.capacity:
                new_shelter.status = "full"

        survivor.shelter_id = new_shelter_id

    db.session.commit()
    return jsonify({"message": "Survivor updated"})


@survivor_bp.route("/survivors/<int:survivor_id>", methods=["DELETE"])
@require_permission("survivors:manage")
def remove_survivor(survivor_id):
    survivor = Survivor.query.get(survivor_id)
    if not survivor:
        return jsonify({"error": "Survivor not found"}), 404

    # Update shelter occupancy
    if survivor.shelter_id:
        shelter = Shelter.query.get(survivor.shelter_id)
        if shelter:
            shelter.current_occupancy = max(0, shelter.current_occupancy - 1)
            if shelter.status == "full":
                shelter.status = "open"

    db.session.delete(survivor)
    db.session.commit()
    return jsonify({"message": "Survivor record removed"})

from flask import Blueprint, request, jsonify
from auth import require_permission
from extensions import db
from models import Volunteer, Shelter

volunteer_bp = Blueprint("volunteer", __name__)

SKILL_CATEGORIES = ["doctor", "nurse", "rescue", "logistics", "cooking", "driving", "first_aid", "counseling", "other"]


@volunteer_bp.route("/volunteers/register", methods=["POST"])
@require_permission("volunteers:manage")
def register_volunteer():
    data = request.json

    if not data or not data.get("name") or not data.get("phone"):
        return jsonify({"error": "Name and phone are required"}), 400

    shelter_id = data.get("shelter_id")

    # Enforce max volunteers per shelter (1 per 10 capacity)
    if shelter_id:
        shelter = Shelter.query.get(shelter_id)
        if not shelter:
            return jsonify({"error": "Shelter not found"}), 404
        current_vols = Volunteer.query.filter_by(shelter_id=shelter_id).count()
        max_vols = max(5, shelter.capacity // 10)
        if current_vols >= max_vols:
            return jsonify({"error": f"Shelter has reached volunteer limit ({max_vols})"}), 400

    volunteer = Volunteer(
        name=data["name"],
        phone=data["phone"],
        city=data.get("city"),
        skills=data.get("skills"),
        availability=data.get("availability"),
        shelter_id=shelter_id
    )

    db.session.add(volunteer)
    db.session.commit()

    return jsonify({"message": "Volunteer registered successfully", "id": volunteer.id}), 201


@volunteer_bp.route("/volunteers", methods=["GET"])
@require_permission("volunteers:view")
def get_volunteers():
    city = request.args.get("city")
    skill = request.args.get("skill")
    shelter_id = request.args.get("shelter_id")

    query = Volunteer.query
    if city:
        query = query.filter_by(city=city)
    if shelter_id:
        query = query.filter_by(shelter_id=shelter_id)
    if skill:
        query = query.filter(Volunteer.skills.ilike(f"%{skill}%"))

    volunteers = query.order_by(Volunteer.registered_at.desc()).all()

    return jsonify([
        {
            "id": v.id,
            "name": v.name,
            "phone": v.phone,
            "city": v.city,
            "skills": v.skills,
            "availability": v.availability,
            "shelter_id": v.shelter_id,
            "shelter_name": v.shelter.name if v.shelter else None,
            "registered_at": v.registered_at.isoformat() if v.registered_at else None
        }
        for v in volunteers
    ])


@volunteer_bp.route("/volunteers/<int:volunteer_id>", methods=["PUT"])
@require_permission("volunteers:manage")
def update_volunteer(volunteer_id):
    volunteer = Volunteer.query.get(volunteer_id)
    if not volunteer:
        return jsonify({"error": "Volunteer not found"}), 404

    data = request.json
    volunteer.name = data.get("name", volunteer.name)
    volunteer.phone = data.get("phone", volunteer.phone)
    volunteer.city = data.get("city", volunteer.city)
    volunteer.skills = data.get("skills", volunteer.skills)
    volunteer.availability = data.get("availability", volunteer.availability)
    volunteer.shelter_id = data.get("shelter_id", volunteer.shelter_id)

    db.session.commit()
    return jsonify({"message": "Volunteer updated successfully"})


@volunteer_bp.route("/volunteers/<int:volunteer_id>", methods=["DELETE"])
@require_permission("volunteers:manage")
def delete_volunteer(volunteer_id):
    volunteer = Volunteer.query.get(volunteer_id)
    if not volunteer:
        return jsonify({"error": "Volunteer not found"}), 404

    db.session.delete(volunteer)
    db.session.commit()
    return jsonify({"message": "Volunteer deleted successfully"})


@volunteer_bp.route("/volunteers/skills", methods=["GET"])
@require_permission("volunteers:view")
def get_skill_categories():
    return jsonify({"skills": SKILL_CATEGORIES})

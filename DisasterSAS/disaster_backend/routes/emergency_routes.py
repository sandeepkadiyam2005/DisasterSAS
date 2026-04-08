from flask import Blueprint, request, jsonify
from auth import require_permission
from extensions import db
from models import EmergencyContact

emergency_bp = Blueprint("emergency", __name__)


@emergency_bp.route("/emergency-contacts", methods=["GET"])
@require_permission("emergency_contacts:view")
def get_contacts():
    city = request.args.get("city")

    query = EmergencyContact.query
    if city:
        query = query.filter_by(city=city)

    contacts = query.all()

    return jsonify([
        {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "service_type": c.service_type,
            "city": c.city
        }
        for c in contacts
    ])


@emergency_bp.route("/emergency-contacts", methods=["POST"])
@require_permission("emergency_contacts:manage")
def add_contact():
    data = request.json

    if not data or not data.get("name") or not data.get("phone") or not data.get("service_type"):
        return jsonify({"error": "Name, phone, and service_type are required"}), 400

    contact = EmergencyContact(
        name=data["name"],
        phone=data["phone"],
        service_type=data["service_type"],
        city=data.get("city")
    )

    db.session.add(contact)
    db.session.commit()

    return jsonify({"message": "Emergency contact added", "id": contact.id}), 201


@emergency_bp.route("/emergency-contacts/<int:contact_id>", methods=["PUT"])
@require_permission("emergency_contacts:manage")
def update_contact(contact_id):
    contact = EmergencyContact.query.get(contact_id)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404

    data = request.json
    contact.name = data.get("name", contact.name)
    contact.phone = data.get("phone", contact.phone)
    contact.service_type = data.get("service_type", contact.service_type)
    contact.city = data.get("city", contact.city)

    db.session.commit()
    return jsonify({"message": "Emergency contact updated"})


@emergency_bp.route("/emergency-contacts/<int:contact_id>", methods=["DELETE"])
@require_permission("emergency_contacts:manage")
def delete_contact(contact_id):
    contact = EmergencyContact.query.get(contact_id)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404

    db.session.delete(contact)
    db.session.commit()

    return jsonify({"message": "Emergency contact deleted"})

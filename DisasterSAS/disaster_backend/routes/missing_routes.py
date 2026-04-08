import os
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, url_for
from werkzeug.utils import secure_filename
from sqlalchemy import and_, or_
from auth import require_permission
from extensions import db
from models import MissingPerson

missing_bp = Blueprint("missing", __name__)
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}


def _allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _photo_url(photo_filename):
    if not photo_filename:
        return None
    return url_for("uploaded_file", filename=photo_filename, _external=True)


def _person_payload(person):
    return {
        "id": person.id,
        "name": person.name,
        "age": person.age,
        "city": person.city,
        "description": person.description,
        "contact": person.contact,
        "photo_filename": person.photo_filename,
        "photo_url": _photo_url(person.photo_filename),
        "status": person.status,
        "found_at": person.found_at.isoformat() if person.found_at else None,
        "reported_at": person.reported_at.isoformat() if person.reported_at else None,
    }


def _remove_photo_if_exists(photo_filename):
    if not photo_filename:
        return

    photo_path = os.path.join(current_app.config["UPLOAD_FOLDER"], photo_filename)
    if os.path.exists(photo_path):
        try:
            os.remove(photo_path)
        except OSError:
            pass


def _cleanup_found_reports():
    """
    Auto-delete reports that were marked found more than 24 hours ago.
    Runs opportunistically when missing-person endpoints are called.
    """
    threshold = datetime.utcnow() - timedelta(hours=24)
    stale_people = MissingPerson.query.filter(
        MissingPerson.status == "found",
        or_(
            and_(MissingPerson.found_at.isnot(None), MissingPerson.found_at < threshold),
            and_(MissingPerson.found_at.is_(None), MissingPerson.reported_at < threshold),
        ),
    ).all()

    if not stale_people:
        return 0

    for person in stale_people:
        _remove_photo_if_exists(person.photo_filename)
        db.session.delete(person)

    db.session.commit()
    return len(stale_people)


@missing_bp.route("/missing/upload-photo", methods=["POST"])
@require_permission("missing:report")
def upload_missing_photo():
    _cleanup_found_reports()

    photo = request.files.get("photo")
    if photo is None or not photo.filename:
        return jsonify({"error": "Photo file is required"}), 400

    if not _allowed_image(photo.filename):
        return jsonify({"error": "Only JPG, JPEG, PNG, WEBP, and GIF images are allowed"}), 400

    file_ext = secure_filename(photo.filename).rsplit(".", 1)[1].lower()
    saved_name = f"missing_{uuid.uuid4().hex}.{file_ext}"
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], saved_name)
    photo.save(save_path)

    return jsonify({
        "message": "Photo uploaded successfully",
        "photo_filename": saved_name,
        "photo_url": _photo_url(saved_name),
    }), 201


@missing_bp.route("/missing/report", methods=["POST"])
@require_permission("missing:report")
def report_missing():
    _cleanup_found_reports()
    data = request.json

    if not data or not data.get("name") or not data.get("contact"):
        return jsonify({"error": "Name and contact are required"}), 400

    person = MissingPerson(
        name=data["name"],
        age=data.get("age"),
        city=data.get("city"),
        description=data.get("description"),
        contact=data["contact"],
        photo_filename=data.get("photo_filename"),
    )

    db.session.add(person)
    db.session.commit()

    return jsonify({
        "message": "Missing person reported",
        "id": person.id,
        "photo_url": _photo_url(person.photo_filename),
    }), 201


@missing_bp.route("/missing", methods=["GET"])
@require_permission("missing:view")
def get_missing():
    _cleanup_found_reports()
    city = request.args.get("city")

    query = MissingPerson.query.filter_by(status="missing")
    if city:
        query = query.filter_by(city=city)

    people = query.order_by(MissingPerson.reported_at.desc()).all()
    return jsonify([_person_payload(person) for person in people])


@missing_bp.route("/missing/<int:person_id>", methods=["PUT"])
@require_permission("missing:manage")
def update_missing(person_id):
    _cleanup_found_reports()
    person = MissingPerson.query.get(person_id)
    if not person:
        return jsonify({"error": "Person not found"}), 404

    data = request.json or {}

    person.name = data.get("name", person.name)
    person.age = data.get("age", person.age)
    person.city = data.get("city", person.city)
    person.description = data.get("description", person.description)
    person.contact = data.get("contact", person.contact)

    if "photo_filename" in data:
        old_photo = person.photo_filename
        person.photo_filename = data.get("photo_filename")
        if old_photo and old_photo != person.photo_filename:
            _remove_photo_if_exists(old_photo)

    new_status = data.get("status", person.status)
    if new_status == "found" and person.status != "found":
        person.found_at = datetime.utcnow()
    elif new_status != "found":
        person.found_at = None

    person.status = new_status

    db.session.commit()
    return jsonify({"message": "Missing person report updated"})


@missing_bp.route("/missing/<int:person_id>/found", methods=["PUT"])
@require_permission("missing:manage")
def mark_found(person_id):
    _cleanup_found_reports()
    person = MissingPerson.query.get(person_id)
    if not person:
        return jsonify({"error": "Person not found"}), 404

    person.status = "found"
    person.found_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "message": f"{person.name} marked as found. This report will auto-delete after 24 hours."
    })


@missing_bp.route("/missing/<int:person_id>", methods=["DELETE"])
@require_permission("missing:manage")
def delete_missing(person_id):
    _cleanup_found_reports()
    person = MissingPerson.query.get(person_id)
    if not person:
        return jsonify({"error": "Person not found"}), 404

    _remove_photo_if_exists(person.photo_filename)
    db.session.delete(person)
    db.session.commit()
    return jsonify({"message": "Missing person report deleted"})

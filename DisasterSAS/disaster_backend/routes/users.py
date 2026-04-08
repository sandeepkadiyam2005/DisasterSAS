from flask import Blueprint, request, jsonify
from extensions import db
from auth import VALID_ROLES, normalize_role, permissions_for_role
from models import User
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import time

users_bp = Blueprint("users", __name__)
RESET_CODE_TTL_SECONDS = 10 * 60
password_reset_codes = {}


def _cleanup_expired_reset_codes():
    now = time.time()
    expired = [username for username, meta in password_reset_codes.items() if meta.get("expires_at", 0) <= now]
    for username in expired:
        password_reset_codes.pop(username, None)


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@users_bp.route("/register", methods=["POST"])
def register():
    data = _json_body()

    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required"}), 400

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 409

    requested_role = str(data.get("role", "public")).strip().lower()
    if requested_role not in VALID_ROLES:
        return jsonify({"error": "Role must be one of: public, volunteer, admin"}), 400

    new_user = User(
        username=data["username"],
        password=generate_password_hash(data["password"]),
        role=normalize_role(requested_role)
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@users_bp.route("/login", methods=["POST"])
def login():
    data = _json_body()

    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=data["username"]).first()

    if user and check_password_hash(user.password, data["password"]):
        user_role = normalize_role(user.role)
        user_permissions = permissions_for_role(user_role)
        token_kwargs = {
            "identity": user.username,
            "additional_claims": {"role": user_role},
        }
        # Keep public users signed in until they clear app/browser storage.
        if user_role == "public":
            token_kwargs["expires_delta"] = False

        access_token = create_access_token(**token_kwargs)

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "role": user_role,
            "permissions": user_permissions,
        })

    return jsonify({"error": "Invalid credentials"}), 401


@users_bp.route("/forgot-password/request", methods=["POST"])
def request_password_reset():
    data = _json_body()
    username = str(data.get("username", "")).strip()

    if not username:
        return jsonify({"error": "Username is required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "Username not found"}), 404

    _cleanup_expired_reset_codes()
    reset_code = f"{secrets.randbelow(1_000_000):06d}"
    password_reset_codes[username] = {
        "code": reset_code,
        "expires_at": time.time() + RESET_CODE_TTL_SECONDS
    }

    return jsonify({
        "message": "Reset code generated. Use it to set a new password.",
        "reset_code": reset_code,
        "expires_in_seconds": RESET_CODE_TTL_SECONDS
    })


@users_bp.route("/forgot-password/confirm", methods=["POST"])
def confirm_password_reset():
    data = _json_body()
    username = str(data.get("username", "")).strip()
    code = str(data.get("code", "")).strip()
    new_password = str(data.get("new_password", ""))

    if not username or not code or not new_password:
        return jsonify({"error": "Username, reset code, and new password are required"}), 400

    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "Username not found"}), 404

    _cleanup_expired_reset_codes()
    reset_meta = password_reset_codes.get(username)
    if not reset_meta:
        return jsonify({"error": "No active reset request found. Request a new code."}), 400

    if reset_meta.get("code") != code:
        return jsonify({"error": "Invalid reset code"}), 400

    user.password = generate_password_hash(new_password)
    db.session.commit()
    password_reset_codes.pop(username, None)

    return jsonify({"message": "Password reset successful. Please log in with your new password."})

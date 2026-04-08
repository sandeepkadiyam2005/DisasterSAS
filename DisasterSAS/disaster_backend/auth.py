from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, jwt_required

VALID_ROLES = {"public", "volunteer", "admin"}

PUBLIC_PERMISSIONS = {
    "dashboard:view",
    "weather:view",
    "map:view",
    "shelters:view",
    "missing:view",
    "emergency_contacts:view",
    "requests:create",
}

VOLUNTEER_EXTRA_PERMISSIONS = {
    "weather:view",
    "weather:forecast",
    "alerts:view",
    "shelters:view",
    "map:view",
    "missing:report",
    "survivors:view",
    "survivors:manage",
    "missing:view",
    "missing:manage",
    "requests:view",
    "requests:manage",
    "requests:queue",
    "requests:stats",
    "volunteers:view",
    "resources:view",
}

ROLE_PERMISSIONS = {
    "public": set(PUBLIC_PERMISSIONS),
    "volunteer": set(PUBLIC_PERMISSIONS | VOLUNTEER_EXTRA_PERMISSIONS),
    "admin": {"*"},
}


def normalize_role(role):
    normalized = str(role or "public").strip().lower()
    return normalized if normalized in VALID_ROLES else "public"


def permissions_for_role(role):
    normalized = normalize_role(role)
    permissions = ROLE_PERMISSIONS.get(normalized, set())
    if "*" in permissions:
        return ["*"]
    return sorted(permissions)


def role_has_permission(role, permission):
    role_permissions = ROLE_PERMISSIONS.get(normalize_role(role), set())
    return "*" in role_permissions or permission in role_permissions


def current_role():
    claims = get_jwt() or {}
    return normalize_role(claims.get("role"))


def require_auth():
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def require_permission(permission):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args, **kwargs):
            role = current_role()
            if not role_has_permission(role, permission):
                return jsonify({"error": f"Permission denied: {permission}"}), 403
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def init_jwt_error_handlers(jwt):
    @jwt.unauthorized_loader
    def _missing_token(reason):
        return jsonify({"error": "Authentication required"}), 401

    @jwt.invalid_token_loader
    def _invalid_token(reason):
        return jsonify({"error": "Invalid authentication token"}), 401

    @jwt.expired_token_loader
    def _expired_token(jwt_header, jwt_payload):
        return jsonify({"error": "Authentication token expired"}), 401

    @jwt.needs_fresh_token_loader
    def _fresh_token_required(jwt_header, jwt_payload):
        return jsonify({"error": "Fresh authentication required"}), 401

    @jwt.revoked_token_loader
    def _revoked_token(jwt_header, jwt_payload):
        return jsonify({"error": "Authentication token revoked"}), 401

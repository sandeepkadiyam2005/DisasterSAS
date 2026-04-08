import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from sqlalchemy import inspect, text
from auth import init_jwt_error_handlers
from extensions import db, socketio


def _sqlite_type_for_column(column):
    try:
        py_type = column.type.python_type
    except Exception:
        return "TEXT"

    if py_type is int:
        return "INTEGER"
    if py_type is float:
        return "REAL"
    if py_type is bool:
        return "INTEGER"
    return "TEXT"


def _sql_literal(value):
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, bool):
        return "1" if value else "0"
    if value is None:
        return "NULL"
    return str(value)


def _ensure_sqlite_schema_compatibility():
    """
    Lightweight SQLite compatibility fix:
    - keeps existing data
    - creates missing tables via create_all()
    - adds missing columns for older local databases
    """
    if db.engine.dialect.name != "sqlite":
        return

    from models import (
        User,
        Alert,
        WeatherLog,
        MissingPerson,
        Volunteer,
        Shelter,
        EmergencyContact,
        Survivor,
        EmergencyRequest,
        Resource,
        AuditLog,
    )

    models = [
        User,
        Alert,
        WeatherLog,
        MissingPerson,
        Volunteer,
        Shelter,
        EmergencyContact,
        Survivor,
        EmergencyRequest,
        Resource,
        AuditLog,
    ]

    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    with db.engine.begin() as connection:
        for model in models:
            table = model.__table__
            table_name = table.name

            if table_name not in table_names:
                continue

            existing_columns = {
                col["name"] for col in inspector.get_columns(table_name)
            }

            for column in table.columns:
                if column.primary_key or column.name in existing_columns:
                    continue

                sql_type = _sqlite_type_for_column(column)
                default_clause = ""

                if column.default is not None and getattr(column.default, "is_scalar", False):
                    default_clause = f" DEFAULT {_sql_literal(column.default.arg)}"

                alter_sql = (
                    f'ALTER TABLE "{table_name}" '
                    f'ADD COLUMN "{column.name}" {sql_type}{default_clause}'
                )
                connection.execute(text(alter_sql))
                existing_columns.add(column.name)


def create_app():
    app = Flask(__name__)

    # ── Configuration ──────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secretkey")
    app.config["JWT_SECRET_KEY"] = os.environ.get(
        "JWT_SECRET_KEY", "this-is-a-very-long-super-secure-secret-key-123456"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URI", "sqlite:///database.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.environ.get("MAX_UPLOAD_BYTES", 5 * 1024 * 1024)
    )
    app.config["UPLOAD_FOLDER"] = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(app.root_path, "uploads")
    )
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Initialize extensions ──────────────────────────────────────
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    CORS(app)
    jwt = JWTManager(app)
    init_jwt_error_handlers(jwt)

    # ── Register blueprints ────────────────────────────────────────
    from routes.weather import weather_bp
    from routes.alerts import alerts_bp
    from routes.users import users_bp
    from routes.shelter_routes import shelter_bp
    from routes.missing_routes import missing_bp
    from routes.volunteer_routes import volunteer_bp
    from routes.emergency_routes import emergency_bp
    from routes.survivor_routes import survivor_bp
    from routes.request_routes import request_bp
    from routes.resource_routes import resource_bp
    from routes.map_system import map_system_bp
    from routes.analytics_routes import analytics_bp

    app.register_blueprint(weather_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(shelter_bp)
    app.register_blueprint(missing_bp)
    app.register_blueprint(volunteer_bp)
    app.register_blueprint(emergency_bp)
    app.register_blueprint(survivor_bp)
    app.register_blueprint(request_bp)
    app.register_blueprint(resource_bp)
    app.register_blueprint(map_system_bp)
    app.register_blueprint(analytics_bp)

    # ── Database bootstrap (works for run.py and flask run) ──────
    with app.app_context():
        db.create_all()
        _ensure_sqlite_schema_compatibility()
        from services.scheduler import start_background_scheduler

        start_background_scheduler(app)

    frontend_dir = os.path.abspath(os.path.join(app.root_path, "..", "disaster_frontend"))

    # ── App/Frontend routes ────────────────────────────────────────
    @app.route("/api/health")
    def api_health():
        return {"status": "ok", "message": "Disaster Safety Backend Running Successfully 🚀"}

    @app.route("/")
    def home():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.isfile(index_file):
            return send_from_directory(frontend_dir, "index.html")
        return "Disaster Safety Backend Running Successfully 🚀"

    @app.route("/dashboard")
    def dashboard_page():
        dashboard_file = os.path.join(frontend_dir, "dashboard.html")
        if os.path.isfile(dashboard_file):
            return send_from_directory(frontend_dir, "dashboard.html")
        return {"error": "Resource not found"}, 404

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/<path:asset_path>")
    def frontend_assets(asset_path):
        asset_abs = os.path.join(frontend_dir, asset_path)
        if os.path.isfile(asset_abs):
            return send_from_directory(frontend_dir, asset_path)

        html_alias = f"{asset_path}.html"
        html_abs = os.path.join(frontend_dir, html_alias)
        if os.path.isfile(html_abs):
            return send_from_directory(frontend_dir, html_alias)

        return {"error": "Resource not found"}, 404

    # ── Error handlers ─────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Resource not found"}, 404

    @app.errorhandler(413)
    def payload_too_large(error):
        return {"error": "File too large. Max allowed size is 5 MB."}, 413

    @app.errorhandler(500)
    def server_error(error):
        return {"error": "Internal server error"}, 500

    return app

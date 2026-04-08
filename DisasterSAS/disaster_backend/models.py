from datetime import datetime
from extensions import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default="public")  # admin / volunteer / public

    def __repr__(self):
        return f"<User {self.username}>"


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default="medium")  # low / medium / high / critical
    date = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Alert {self.title}>"


class WeatherLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Integer)
    wind_speed = db.Column(db.Float)
    weather = db.Column(db.String(200))
    disaster_alert = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<WeatherLog {self.city} @ {self.timestamp}>"


class MissingPerson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    city = db.Column(db.String(100))
    description = db.Column(db.String(300))
    contact = db.Column(db.String(20))
    photo_filename = db.Column(db.String(255))
    status = db.Column(db.String(20), default="missing")  # missing / found
    found_at = db.Column(db.DateTime, nullable=True)
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MissingPerson {self.name}>"


class Volunteer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(100))
    skills = db.Column(db.String(200))  # doctor / nurse / rescue / logistics / cooking / driving
    availability = db.Column(db.String(100))
    shelter_id = db.Column(db.Integer, db.ForeignKey("shelter.id"), nullable=True)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    shelter = db.relationship("Shelter", backref="volunteers")

    def __repr__(self):
        return f"<Volunteer {self.name}>"


class Shelter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    capacity = db.Column(db.Integer, default=0)
    current_occupancy = db.Column(db.Integer, default=0)
    contact = db.Column(db.String(20))
    status = db.Column(db.String(20), default="open")  # open / full / closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Shelter {self.name}>"


class EmergencyContact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service_type = db.Column(db.String(50), nullable=False)  # police / fire / medical / rescue
    city = db.Column(db.String(100))

    def __repr__(self):
        return f"<EmergencyContact {self.name} ({self.service_type})>"


class Survivor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    contact = db.Column(db.String(20))
    health_status = db.Column(db.String(50), default="stable")  # stable / injured / critical
    shelter_id = db.Column(db.Integer, db.ForeignKey("shelter.id"), nullable=True)
    registered_by = db.Column(db.String(100))  # volunteer username
    notes = db.Column(db.String(300))
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    shelter = db.relationship("Shelter", backref="survivors")

    def __repr__(self):
        return f"<Survivor {self.name}>"


class EmergencyRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(db.String(50), nullable=False)  # food / water / medical / evacuation
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")  # pending / in_progress / resolved
    priority = db.Column(db.String(20), default="medium")  # low / medium / high / critical
    severity_score = db.Column(db.Integer, default=0)
    auto_priority_override = db.Column(db.Boolean, default=False)
    requester_name = db.Column(db.String(100))
    shelter_id = db.Column(db.Integer, db.ForeignKey("shelter.id"), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    allocated_resource_id = db.Column(db.Integer, db.ForeignKey("resource.id"), nullable=True)
    allocation_eta_minutes = db.Column(db.Integer, nullable=True)
    allocation_distance_km = db.Column(db.Float, nullable=True)
    allocation_status = db.Column(db.String(20), default="unassigned")
    assigned_to = db.Column(db.String(100))  # volunteer username
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shelter = db.relationship("Shelter", backref="emergency_requests")
    allocated_resource = db.relationship("Resource", foreign_keys=[allocated_resource_id])

    def __repr__(self):
        return f"<EmergencyRequest {self.request_type} ({self.status})>"


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shelter_id = db.Column(db.Integer, db.ForeignKey("shelter.id"), nullable=False)
    food_packets = db.Column(db.Integer, default=0)
    water_bottles = db.Column(db.Integer, default=0)
    medical_kits = db.Column(db.Integer, default=0)
    blankets = db.Column(db.Integer, default=0)
    is_available = db.Column(db.Boolean, default=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shelter = db.relationship("Shelter", backref="resources")

    def __repr__(self):
        return f"<Resource for Shelter {self.shelter_id}>"


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(100), default="system")
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(100), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog {self.action} {self.entity_type}:{self.entity_id}>"

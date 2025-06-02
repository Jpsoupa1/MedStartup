import datetime
from . import db

class Doctor(db.Model):
    __tablename__ = "doctor"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    crm = db.Column(db.String(20), unique=True, nullable=False)
    specialization = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    patients = db.relationship("Patient", backref="doctor", lazy=True)

class Patient(db.Model):
    __tablename__ = "patient"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    birth_date = db.Column(db.Date)
    address = db.Column(db.String(200))
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    records = db.relationship("MedicalRecord", backref="patient", lazy=True)

class MedicalRecord(db.Model):
    __tablename__ = "medical_record"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(200))
    record_date = db.Column(db.Date, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

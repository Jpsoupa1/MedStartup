import datetime
import jwt
from flask import request, jsonify
from flask_restx import Namespace, fields, Resource
from werkzeug.security import generate_password_hash, check_password_hash
from .models import Doctor
from . import db, bcrypt
from functools import wraps

auth_ns = Namespace("auth", description="Autenticação e registro")

register_model = auth_ns.model("Register", {
    "name": fields.String(required=True, description="Nome do médico"),
    "email": fields.String(required=True, description="E-mail válido"),
    "password": fields.String(required=True, description="Senha com mínimo de 6 caracteres"),
    "crm": fields.String(required=True, description="Número do CRM"),
    "specialization": fields.String(description="Especialização (opcional)")
})

login_model = auth_ns.model("Login", {
    "email": fields.String(required=True, description="E-mail cadastrado"),
    "password": fields.String(required=True, description="Senha")
})

def token_required(f):
    """Decorator para rotas protegidas, verificando JWT."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("x-access-token")
        if not token:
            return {"message": "Token está faltando!"}, 401
        try:
            data = jwt.decode(token, auth_ns.api.app.config["SECRET_KEY"], algorithms=["HS256"])
            current_doctor = Doctor.query.get(data["id"])
            if not current_doctor:
                return {"message": "Token inválido!"}, 401
        except Exception as e:
            return {"message": "Token inválido!", "error": str(e)}, 401
        return f(current_doctor, *args, **kwargs)
    return wrapper

@auth_ns.route("/register")
class Register(Resource):
    @auth_ns.expect(register_model, validate=True)
    def post(self):
        data = request.get_json()
        if Doctor.query.filter_by(email=data["email"]).first():
            return {"message": "Médico já cadastrado!"}, 400

        hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
        new_doctor = Doctor(
            name=data["name"],
            email=data["email"],
            password=hashed_pw,
            crm=data["crm"],
            specialization=data.get("specialization")
        )
        try:
            db.session.add(new_doctor)
            db.session.commit()
            return {"message": "Médico registrado com sucesso!"}, 201
        except Exception as e:
            db.session.rollback()
            return {"message": "Erro ao cadastrar médico.", "error": str(e)}, 500

@auth_ns.route("/login")
class Login(Resource):
    @auth_ns.expect(login_model, validate=True)
    def post(self):
        data = request.get_json()
        doctor = Doctor.query.filter_by(email=data["email"]).first()
        if not doctor or not bcrypt.check_password_hash(doctor.password, data["password"]):
            return {"message": "E-mail ou senha inválidos!"}, 401

        token = jwt.encode({
            "id": doctor.id,
            "exp": datetime.datetime.utcnow() + auth_ns.api.app.config["JWT_ACCESS_TOKEN_EXPIRES"]
        }, auth_ns.api.app.config["SECRET_KEY"], algorithm="HS256")

        return {
            "token": token,
            "doctor": {
                "id": doctor.id,
                "name": doctor.name,
                "email": doctor.email,
                "specialization": doctor.specialization
            }
        }, 200

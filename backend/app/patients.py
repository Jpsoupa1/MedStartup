from flask import request
from flask_restx import Namespace, fields, Resource
from .models import Patient
from . import db
from .auth import token_required

patients_ns = Namespace("patients", description="Gerenciamento de pacientes")

patient_model = patients_ns.model("Patient", {
    "name": fields.String(required=True, description="Nome do paciente"),
    "email": fields.String(description="E-mail do paciente"),
    "phone": fields.String(description="Telefone"),
    "birth_date": fields.String(description="Data de nascimento (YYYY-MM-DD)"),
    "address": fields.String(description="Endereço"),
})

@patients_ns.route("/")
class PatientList(Resource):
    @token_required
    def get(current_doctor, self):
        """
        Listagem de pacientes com paginação e busca por nome:
        /api/patients?page=1&per_page=10&search=Joao
        """
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)

        query = Patient.query.filter_by(doctor_id=current_doctor.id)
        if search:
            query = query.filter(Patient.name.ilike(f"%{search}%"))
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        items = pagination.items

        output = []
        for p in items:
            output.append({
                "id": p.id,
                "name": p.name,
                "email": p.email,
                "phone": p.phone
            })

        return {
            "status": "success",
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "patients": output
        }, 200

    @token_required
    @patients_ns.expect(patient_model, validate=True)
    def post(current_doctor, self):
        """
        Cria um novo paciente para o médico autenticado.
        """
        data = request.get_json()
        new_patient = Patient(
            name=data["name"],
            email=data.get("email"),
            phone=data.get("phone"),
            birth_date=data.get("birth_date"),
            address=data.get("address"),
            doctor_id=current_doctor.id
        )
        try:
            db.session.add(new_patient)
            db.session.commit()
            return {"message": "Paciente criado com sucesso!", "id": new_patient.id}, 201
        except Exception as e:
            db.session.rollback()
            return {"message": "Erro ao criar paciente.", "error": str(e)}, 500

@patients_ns.route("/<int:id>")
class PatientDetail(Resource):
    @token_required
    def get(current_doctor, self, id):
        """
        Busca um paciente específico (por ID) apenas se pertencer ao médico autenticado.
        """
        paciente = Patient.query.filter_by(id=id, doctor_id=current_doctor.id).first_or_404()
        return {
            "id": paciente.id,
            "name": paciente.name,
            "email": paciente.email,
            "phone": paciente.phone,
            "birth_date": str(paciente.birth_date),
            "address": paciente.address
        }, 200

    @token_required
    @patients_ns.expect(patient_model, validate=False)
    def put(current_doctor, self, id):
        """
        Atualiza dados de um paciente (JSON parcial permitido).
        """
        paciente = Patient.query.filter_by(id=id, doctor_id=current_doctor.id).first_or_404()
        data = request.get_json()
        paciente.name = data.get("name", paciente.name)
        paciente.email = data.get("email", paciente.email)
        paciente.phone = data.get("phone", paciente.phone)
        paciente.birth_date = data.get("birth_date", paciente.birth_date)
        paciente.address = data.get("address", paciente.address)

        try:
            db.session.commit()
            return {"message": "Paciente atualizado com sucesso!"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": "Erro ao atualizar paciente.", "error": str(e)}, 500

    @token_required
    def delete(current_doctor, self, id):
        """
        Exclui um paciente (verifica propriedade pelo médico).
        """
        paciente = Patient.query.filter_by(id=id, doctor_id=current_doctor.id).first_or_404()
        try:
            db.session.delete(paciente)
            db.session.commit()
            return {"message": "Paciente excluído com sucesso!"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": "Erro ao excluir paciente.", "error": str(e)}, 500

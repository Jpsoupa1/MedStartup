import os
from flask import request, send_from_directory, current_app
from flask_restx import Namespace, fields, Resource
from werkzeug.utils import secure_filename
from .models import MedicalRecord, Patient
from . import db
from .auth import token_required

records_ns = Namespace("records", description="Prontuários médicos")

record_model = records_ns.model("MedicalRecord", {
    "title": fields.String(required=True, description="Título do prontuário"),
    "description": fields.String(description="Descrição detalhada"),
    "record_date": fields.String(required=True, description="Data do prontuário (YYYY-MM-DD)"),
})

def allowed_file(filename):
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", set())
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

@records_ns.route("/<int:patient_id>")
class PatientRecords(Resource):
    @token_required
    def get(current_doctor, self, patient_id):
        """
        Lista todos os prontuários de um paciente específico (pertencente ao médico autenticado).
        """
        patient = Patient.query.filter_by(id=patient_id, doctor_id=current_doctor.id).first_or_404()
        records = MedicalRecord.query.filter_by(patient_id=patient.id).all()
        output = []
        for r in records:
            output.append({
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "record_date": str(r.record_date),
                "file_path": r.file_path
            })
        return {"patient_id": patient.id, "records": output}, 200

    @token_required
    @records_ns.expect(record_model, validate=True)
    def post(current_doctor, self, patient_id):
        """
        Cria um novo prontuário para um paciente (JSON + opcional upload de arquivo via form-data).
        Se houver arquivo, envie em campo “file” multipart/form-data.
        """
        patient = Patient.query.filter_by(id=patient_id, doctor_id=current_doctor.id).first_or_404()
        data = request.get_json()
        
        new_record = MedicalRecord(
            title=data["title"],
            description=data.get("description"),
            record_date=data["record_date"],
            patient_id=patient.id
        )

        try:
            db.session.add(new_record)
            db.session.flush()  # para obter new_record.id antes do commit

            # Se for enviado arquivo em form-data, trate-o:
            if "file" in request.files:
                file = request.files["file"]
                if file.filename != "" and allowed_file(file.filename):
                    filename = secure_filename(f"{new_record.id}_{file.filename}")
                    upload_folder = current_app.config.get("UPLOAD_FOLDER")
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    new_record.file_path = filename

            db.session.commit()
            return {"message": "Prontuário criado com sucesso!", "id": new_record.id}, 201

        except Exception as e:
            db.session.rollback()
            return {"message": "Erro ao criar prontuário.", "error": str(e)}, 500

@records_ns.route("/download/<string:filename>")
class DownloadRecord(Resource):
    def get(self, filename):
        """
        Baixa/visualiza o arquivo de prontuário (PDF, PNG, JPG, etc).
        """
        folder = current_app.config.get("UPLOAD_FOLDER")
        return send_from_directory(folder, filename, as_attachment=True)

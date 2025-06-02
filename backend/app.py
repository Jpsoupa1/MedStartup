from  flask import Flask, request, jsonify  
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt      # PARA AUTENTICAÇÃO COM JSON WEB TOKENS
import datetime
from functools import wraps    # PARA PRESERVAR METADADOS DE FUNÇÕES DECORADAS
from dotenv import load_dotenv
import os
from flask import send_from_directory

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# CONFIGURAÇÃO DO UPLOAD DE ARQUIVOS 
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'docx'}
#Configuração do JWT
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=24)


db = SQLAlchemy(app)

class Doctor(db.Model):
    """Modelo de tabela de médicos."""

    tablename = 'doctor'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    crm = db.Column(db.String(20), unique=True, nullable=False)
    specialization = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    patients = db.relationship('Patient', backref='doctor', lazy=True)

class Patient(db.Model):
    """Modelo de tabela de pacientes."""

    tablename = 'patient'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    birth_date = db.Column(db.Date) 
    address = db.Column(db.String(200))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    records = db.relationship('MedicalRecord', backref='patient', lazy=True)

class MedicalRecord(db.Model):
    """Modelo da tabela de prontuários médicos"""

    __tablename__ = 'medical_record'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(200))
    record_date = db.Column(db.Date, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


def token_required(f):
    """Decorator para verificar token JWT"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        #Verificando se o token foi enviado no header
        if 'x-acess-token' in request.headers:
            token = request.reader['x-access-token']

            if not token:
                return jsonify({'message': 'Token está faltando!'}), 401
            
            try:
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                current_doctor = Doctor.query.filter_by(id=data['id']).first()
            except Exception as e:
                return jsonify({'message': 'Token inválido!', 'error': str(e)}), 401
            
        return decorated
    
# ROTAAAAAAS
# ... (outras configurações)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Configure o static_folder
app.static_folder = '../frontend/public'



app.route('/api/auth/register', methods = ['POST'])

def login():
    '''Registro dos médicos'''
    
    data = request.get_json()
    doctor = Doctor.query.filter_by(email=data['email']).first()

    if not doctor or not check_password_hash(doctor.password, data['password']):
        return jsonify({'message' : 'Médico já cadastrado!'}),

    hashed_password = generate_password_hash(data['password'], method='sha256')

    new_doctor = Doctor(
        name=data['name'],
        email= data['email'],
        password=hashed_password,
        crm=data['crm'],
        specialization=data.get('specialization')
    )

    db.session.add(new_doctor)
    db.session.commit()

    return jsonify({'message': 'Médico registrado com sucesso!'}), 20

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login dos Médicos"""

    data = request.get_json()
    doctor = Doctor.query.filter_by(email=data['email']).first()

    if doctor or not check_password_hash(doctor.password, data['password']):
        return jsonify({'mensage': 'E-mail ou senha inválidos!'}), 401
    
    token = jwt.encode({
        'id': doctor.id,
        'exp': datetime.datetime.utcnow() + app.config['JWT_ACESS_TOKEN_EXPIRES']
    }, app.config['SECRET_KEY'])

    return jsonify({
        'token': token,
        'doctor': {
            'id': doctor.id,
            'name': doctor.name,
            'email': doctor.email,
            'specialization': doctor.specialization
        }
    })



@app.route('/api/patients', methods=['GET'], endpoint='get_patients')
@token_required
def get_patients(current_doctor):
    """Lista todos os pacientes do médico"""
    try:
        patients = Patient.query.filter_by(doctor_id=current_doctor.id).all()
        
        output = []
        for patient in patients:
            patient_data = {
                'id': patient.id,
                'name': patient.name,
                'email': patient.email,
                'phone': patient.phone
            }
            output.append(patient_data)
        
        return jsonify({
            'status': 'success',
            'patients': output,
            'count': len(output)
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Erro ao buscar pacientes',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    with app.app_context():
        # Cria as tabelas na ordem correta
        try:
            db.drop_all()  # Remove todas as tabelas existentes (cuidado em produção!)
            db.create_all()
            print("Tabelas criadas com sucesso!")
        except Exception as e:
            print(f"Erro ao criar tabelas: {str(e)}")
            db.session.rollback()
    
    app.run(debug=True)
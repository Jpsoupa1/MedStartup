from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt      # PARA AUTENTICAÇÃO COM JSON WEB TOKENS
import datetime
from functools import wraps    # PARA PRESERVAR METADADOS DE FUNÇÕES DECORADAS
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente (.env)
load_dotenv()

app = Flask(__name__)

# Configurações principais
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração do JWT (expira em 24 horas)
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=24)

# Configurações de upload de arquivos (caso precise futuramente)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'docx'}

db = SQLAlchemy(app)


# ======================
# MODELS
# ======================

class Doctor(db.Model):
    """Modelo de tabela de médicos."""
    __tablename__ = 'doctor'

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
    __tablename__ = 'patient'

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
    """Modelo da tabela de prontuários médicos."""
    __tablename__ = 'medical_record'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(200))
    record_date = db.Column(db.Date, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


# ======================
# DECORATOR DE AUTENTICAÇÃO
# ======================

def token_required(f):
    """Decorator para verificar token JWT em rotas protegidas."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token')

        if not token:
            return jsonify({'message': 'Token está faltando!'}), 401

        try:
            # Decodifica o token usando a SECRET_KEY
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_doctor = Doctor.query.filter_by(id=data['id']).first()
            if not current_doctor:
                return jsonify({'message': 'Token inválido!'}), 401

        except Exception as e:
            return jsonify({'message': 'Token inválido!', 'error': str(e)}), 401

        # Chama a função original, passando o current_doctor como primeiro argumento
        return f(current_doctor, *args, **kwargs)

    return decorated



# ROTAS


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """
    Se existir algum arquivo estático (frontend) no caminho, serve-o; 
    caso contrário, serve o index.html para o SPA.
    """
    # Ajuste de acordo com a pasta onde seu front-end está
    app.static_folder = './frontend/public'
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Registro de novos médicos.
    Espera um corpo JSON com:
    {
      "name": "Nome do Médico",
      "email": "email@example.com",
      "password": "senha123",
      "crm": "123456",
      "specialization": "Especialidade"
    }
    """
    data = request.get_json()

    # Verifica se já existe um médico com esse email
    doctor = Doctor.query.filter_by(email=data.get('email')).first()
    if doctor:
        return jsonify({'message': 'Médico já cadastrado!'}), 400


    hashed_password = generate_password_hash(data.get('password'), method='pbkdf2:sha256')


    new_doctor = Doctor(
        name=data.get('name'),
        email=data.get('email'),
        password=hashed_password,
        crm=data.get('crm'),
        specialization=data.get('specialization')
    )

    try:
        db.session.add(new_doctor)
        db.session.commit()
        return jsonify({'message': 'Médico registrado com sucesso!'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Erro ao cadastrar médico.', 'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Login de médicos cadastrados.
    Espera um corpo JSON com:
    {
      "email": "email@example.com",
      "password": "senha123"
    }
    Retorna um token JWT e dados do médico em caso de sucesso.
    """
    data = request.get_json()
    doctor = Doctor.query.filter_by(email=data.get('email')).first()

    if not doctor or not check_password_hash(doctor.password, data.get('password')):
        return jsonify({'message': 'E-mail ou senha inválidos!'}), 401

    # Gera token com prazo de expiração
    token = jwt.encode({
        'id': doctor.id,
        'exp': datetime.datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({
        'token': token,
        'doctor': {
            'id': doctor.id,
            'name': doctor.name,
            'email': doctor.email,
            'specialization': doctor.specialization
        }
    }), 200


@app.route('/api/patients', methods=['GET'])
@token_required
def get_patients(current_doctor):
    """
    Lista todos os pacientes associados ao médico que fez o login.
    Precisa receber o header 'x-access-token' com o JWT.
    Retorna JSON com:
    {
      "status": "success",
      "patients": [ ... ],
      "count": n
    }
    """
    try:
        patients = Patient.query.filter_by(doctor_id=current_doctor.id).all()

        output = []
        for patient in patients:
            paciente_data = {
                'id': patient.id,
                'name': patient.name,
                'email': patient.email,
                'phone': patient.phone
            }
            output.append(paciente_data)

        return jsonify({
            'status': 'success',
            'patients': output,
            'count': len(output)
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Erro ao buscar pacientes',
            'error': str(e)
        }), 500



if __name__ == '__main__':
    # Cria as tabelas (drop_all apenas para desenvolvimento!
    with app.app_context():
        try:
            db.drop_all()
            db.create_all()
            print("Tabelas criadas com sucesso!")
        except Exception as e:
            print(f"Erro ao criar tabelas: {str(e)}")
            db.session.rollback()

    # Inicializa o servidor Flask em modo debug
    app.run(debug=True)

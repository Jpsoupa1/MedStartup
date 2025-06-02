import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api
from config import DevConfig, ProdConfig

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)

def create_app():
    app = Flask(__name__, static_folder="../frontend/public", static_url_path="/")
    env = os.getenv("FLASK_ENV", "development")
    app.config.from_object(ProdConfig if env == "production" else DevConfig)

    # Inicializa extensões
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    limiter.init_app(app)

    # Configurar RESTX (Swagger)
    api = Api(
        app,
        version="1.0",
        title="API Médica",
        description="Cadastro de médicos, pacientes e prontuários"
    )

    # Registrar Blueprints/Namespaces
    from .auth import auth_ns
    from .patients import patients_ns
    from .records import records_ns

    api.add_namespace(auth_ns, path="/api/auth")
    api.add_namespace(patients_ns, path="/api/patients")
    api.add_namespace(records_ns, path="/api/records")

    return app

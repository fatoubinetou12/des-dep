import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_mail import Mail

db = SQLAlchemy()
csrf = CSRFProtect()
mail = Mail()

def create_app():
    app = Flask(__name__)

    # Charger la configuration
    app.config.from_object('config.Config')

    # Initialiser les extensions
    db.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # Enregistrer les blueprints
    from app.models import models
    from app.routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # ✅ Injection du token CSRF utilisable partout
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    return app

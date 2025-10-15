# app/__init__.py
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

    # 1) Charger la configuration (config.py -> class Config)
    app.config.from_object('config.Config')

    # (optionnel) tolérer /route et /route/
    app.url_map.strict_slashes = False

    # 2) Filets de sécurité MAIL (évite "default sender not configured")
    if not app.config.get("MAIL_DEFAULT_SENDER"):
        # si l'env n'a pas fourni MAIL_DEFAULT_SENDER mais a fourni MAIL_USERNAME, on s'en sert
        if app.config.get("MAIL_USERNAME"):
            app.config["MAIL_DEFAULT_SENDER"] = app.config["MAIL_USERNAME"]

    # 3) Initialiser les extensions
    db.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # 4) (facultatif) logs de contrôle utiles sur Render
    app.logger.info(f"[MAIL] DEFAULT_SENDER={app.config.get('MAIL_DEFAULT_SENDER')!r}")
    app.logger.info(f"[MAIL] USERNAME={app.config.get('MAIL_USERNAME')!r}")
    app.logger.info(f"[MAIL] SUPPRESS_SEND={app.config.get('MAIL_SUPPRESS_SEND')}")

    # 5) Enregistrer les blueprints & models
    from app.models import models  # garde si tu veux forcer le chargement des modèles
    from app.routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # 6) Injection CSRF utilisable partout dans les templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    return app

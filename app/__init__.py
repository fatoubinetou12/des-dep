# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_mail import Mail

db = SQLAlchemy()
csrf = CSRFProtect()
mail = Mail()

def create_app():
    app = Flask(__name__)

    # 1) Charger la config (config.py -> class Config)
    app.config.from_object('config.Config')

    # 2) Filet de sécurité : si DEFAULT_SENDER manquant mais USERNAME présent
    if not app.config.get("MAIL_DEFAULT_SENDER") and app.config.get("MAIL_USERNAME"):
        app.config["MAIL_DEFAULT_SENDER"] = app.config["MAIL_USERNAME"]

    # (optionnel) tolérer /route et /route/
    app.url_map.strict_slashes = False

    # 3) Initialiser extensions
    db.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # 4) Logs utiles
    app.logger.info(f"[MAIL] DEFAULT_SENDER={app.config.get('MAIL_DEFAULT_SENDER')!r}")
    app.logger.info(f"[MAIL] USERNAME={app.config.get('MAIL_USERNAME')!r}")
    app.logger.info(f"[MAIL] SUPPRESS_SEND={app.config.get('MAIL_SUPPRESS_SEND')}")

    # 5) Blueprints
    from app.routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # 6) CSRF token dispo dans les templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    return app

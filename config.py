# config.py
import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key')

    # 🔹 Utilise DATABASE_URL (Render Postgres) sinon SQLite par défaut
    SQLALCHEMY_DATABASE_URI = (
        os.getenv('DATABASE_URL')
        or os.getenv('SQLALCHEMY_DATABASE_URI')
        or "sqlite:///app.db"
    )

    # Compatibilité Render (Postgres => postgresql)
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

     # E-mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')

    # Google Maps API
    GOOGLE_MAPS_KEY = os.getenv('GOOGLE_MAPS_KEY', '')

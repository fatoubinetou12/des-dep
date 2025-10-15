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

    # ======================
    # ✉️ Config Mail
    # ======================
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', '1') == '1'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)

    # ⚠️ désactive les envois si =1 → sur Render, mets MAIL_SUPPRESS_SEND=0
    MAIL_SUPPRESS_SEND = os.getenv('MAIL_SUPPRESS_SEND', '1') == '1'

    # ======================
    # 🔑 Google Maps
    # ======================
    GOOGLE_MAPS_KEY = os.getenv('GOOGLE_MAPS_KEY', '')

import os
from dotenv import load_dotenv

# Charger les variables depuis le fichier .env
load_dotenv()

class Config:
    # Clé secrète Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_key_change_me'

    # Base de données
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:@localhost/ds-travel'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # E-mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')

    # ✅ Clé Google Maps (Places + Distance Matrix)
    GOOGLE_MAPS_KEY = os.environ.get('GOOGLE_MAPS_KEY') or "AIzaSyBy8naZgWRwxtGy7lztqvaEhb0L6ODbJMs"

    # ✅ Empêche l'expiration du token CSRF (solution propre pour ton cas)
    WTF_CSRF_TIME_LIMIT = None

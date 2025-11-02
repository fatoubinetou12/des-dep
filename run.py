# run.py
import os
from dotenv import load_dotenv
from app import create_app, db
from sqlalchemy import inspect

# 🔹 Charger le fichier .env avant tout
load_dotenv()

app = create_app()

# 🔹 Créer les tables si besoin
with app.app_context():
    db.create_all()
    print(" Tables créées :", inspect(db.engine).get_table_names())

if __name__ == "__main__":
    # 🔹 Mode debug = voir les logs dans le terminal
    app.run(debug=True, host="127.0.0.1", port=5000)

from app import create_app, db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    db.create_all()
    print("Tables créées :", inspect(db.engine).get_table_names())

if __name__ == '__main__':
    app.run(debug=True)


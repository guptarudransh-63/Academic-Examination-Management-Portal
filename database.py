import sqlite3
import os
from flask import g, current_app

def get_db():
    if 'db' not in g:
        db_path = current_app.config['DATABASE_PATH']
        g.db = sqlite3.connect(db_path)
        g.db.execute("PRAGMA foreign_keys = ON;")
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None):
    schema_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'schema.sql')
    with open(schema_path, mode='r') as f:
        schema_sql = f.read()

    if app:
        with app.app_context():
            db = get_db()
            db.executescript(schema_sql)
            db.commit()
    else:
        db = get_db()
        db.executescript(schema_sql)
        db.commit()

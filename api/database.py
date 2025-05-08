from flask import g
import sqlite3

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('db/database.sqlite')
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            language TEXT,
            date_range TEXT,
            user TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS repositories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            url TEXT,
            description TEXT,
            language TEXT,
            stars INTEGER,
            request_id INTEGER,
            FOREIGN KEY (request_id) REFERENCES requests (id)
        )
    ''')
    db.commit()

def get_db_connection():
    """Crea una conexión directa a la base de datos SQLite (sin usar Flask)."""
    connection = sqlite3.connect('db/database.sqlite')
    connection.row_factory = sqlite3.Row
    return connection
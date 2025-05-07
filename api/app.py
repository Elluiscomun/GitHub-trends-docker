from flask import Flask, g
import sqlite3

app = Flask(__name__)
DATABASE = 'db/database.sqlite'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    return "Welcome to the SQLite API!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
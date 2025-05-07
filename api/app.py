from flask import Flask, g, request, jsonify
import sqlite3
import requests
from datetime import datetime
from bs4 import BeautifulSoup

app = Flask(__name__)
DATABASE = 'db/database.sqlite'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database with the required tables."""
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

def setup():
    with app.app_context():  # Usa el contexto de la aplicación
        init_db()

@app.route('/')
def index():
    return "Welcome to the SQLite API!"

@app.route('/tendencias', methods=['GET'])
def tendencias():
    language = request.args.get('language', 'all')
    date_range = request.args.get('date_range', 'daily')  # Options: daily, weekly, monthly
    user = request.args.get('user', 'anonymous')

    # Validate date_range
    if date_range not in ['daily', 'weekly', 'monthly']:
        return jsonify({'error': 'Invalid date_range. Use daily, weekly, or monthly.'}), 400

    # Fetch trending repositories from GitHub
    url = f'https://github.com/trending/{language}?since={date_range}'
    response = requests.get(url)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch data from GitHub.'}), 500

    # Parse the response
    soup = BeautifulSoup(response.text, 'html.parser')
    repo_list = soup.find_all('article', class_='Box-row')

    trending_repos = []
    for repo in repo_list:
        name = repo.find('h2', class_='h3').text.strip().replace('\n', '').replace(' ', '')
        url = f"https://github.com{name}"
        description = repo.find('p', class_='col-9').text.strip() if repo.find('p', class_='col-9') else ''
        language_tag = repo.find('span', itemprop='programmingLanguage')
        repo_language = language_tag.text.strip() if language_tag else 'Unknown'
        stars = repo.find('a', class_='Link--muted').text.strip().replace(',', '')

        trending_repos.append({
            'name': name,
            'url': url,
            'description': description,
            'language': repo_language,
            'stars': int(stars) if stars.isdigit() else 0
        })

    # Save the request to the database
    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO requests (language, date_range, user) VALUES (?, ?, ?)',
                   (language, date_range, user))
    request_id = cursor.lastrowid

    # Save repositories to the database
    for repo in trending_repos:
        cursor.execute('''
            INSERT INTO repositories (name, url, description, language, stars, request_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (repo['name'], repo['url'], repo['description'], repo['language'], repo['stars'], request_id))

    db.commit()
    
    return jsonify({'message': 'Request saved successfully!', 'repositories': trending_repos})

if __name__ == '__main__':
    setup()  # Llama a setup() para inicializar la base de datos
    app.run(host='0.0.0.0', port=5000)
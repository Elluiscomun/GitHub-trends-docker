from flask import request, jsonify
from rabbitmq import send_to_queue
from database import get_db
from utils import fetch_trending_repos
import json

def register_routes(app):
    @app.route('/')
    def index():
        return "Welcome to the SQLite API!"

    @app.route('/tendencias', methods=['POST'])
    def tendencias():
        language = request.json.get('language', 'all')
        date_range = request.json.get('date_range', 'daily')
        user = request.json.get('user', 'anonymous')

        # Guarda la solicitud en la base de datos
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO requests (language, date_range, user) VALUES (?, ?, ?)',
                       (language, date_range, user))
        request_id = cursor.lastrowid
        db.commit()

        # Envía la solicitud a RabbitMQ
        message = {
            "request_id": request_id,
            "language": language,
            "date_range": date_range,
            "user": user
        }
        send_to_queue("scraping_queue", message)

        return jsonify({"message": "Request added to queue", "request_id": request_id})

    @app.route('/resultado/<int:request_id>', methods=['GET'])
    def resultado(request_id):
        """Devuelve el estado o los datos procesados para un request_id."""
        db = get_db()
        cursor = db.cursor()

        # Verifica si el request_id existe en la base de datos
        cursor.execute('SELECT * FROM requests WHERE id = ?', (request_id,))
        request = cursor.fetchone()
        if not request:
            return jsonify({"error": "Request ID not found"}), 404

        # Obtiene los repositorios asociados al request_id
        cursor.execute('''
            SELECT repositories.*, evaluation.evaluation 
            FROM repositories
            LEFT JOIN evaluation ON repositories.id = evaluation.repository_id
            WHERE repositories.request_id = ?
        ''', (request_id,))
        repositories = cursor.fetchall()

        # Si no hay repositorios, el procesamiento aún no está completo
        if not repositories:
            return jsonify({"request_id": request_id, "status": "Processed" if request["status"] == 1 else "Processing", "data": []})


        # Devuelve los datos procesados
        data = []
        for repo in repositories:
            evaluation = None
            if repo["evaluation"]:
                try:
                    evaluation = json.loads(repo["evaluation"])  # Convierte el texto plano a JSON
                except json.JSONDecodeError:
                    evaluation = repo["evaluation"]  # Si falla, deja el texto plano

            data.append({
                "name": repo["name"],
                "url": repo["url"],
                "description": repo["description"],
                "language": repo["language"],
                "stars": repo["stars"] if "stars" in repo else None,
                "evaluation": evaluation
            })
            
        return jsonify({"request_id": request_id, "status": "Processed", "data": data})
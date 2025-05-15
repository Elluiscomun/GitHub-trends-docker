import sqlite3
import pika
import json
import os
import time
import requests

# Configuración de RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
DATABASE_PATH = "db/database.sqlite"  # Ruta directa al archivo de la base de datos
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def get_db_connection():
    """Crea una conexión directa a la base de datos SQLite."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def process_message(ch, method, properties, body):
    """Procesa un mensaje de la cola de RabbitMQ."""
    message = json.loads(body)
    request_id = message["request_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    # Consultar los repositorios que coincidan con el request_id
    cursor.execute('SELECT name, id FROM repositories WHERE request_id = ?', (request_id,))

    repositories = []

    for row in cursor.fetchall():
        repositories.append([row["id"],row["name"]])  

    connection.close()
    ch.basic_ack(delivery_tag=method.delivery_tag)

    evaluate_repositories(repositories, request_id)
    

def evaluate_repositories(repositories, request_id):

    for repo in repositories:
        url = f"https://api.github.com/repos/{repo[1]}/readme"
        headers = {"Accept": "application/vnd.github.v3.raw"}

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("Error al obtener README:", response.status_code)
            exit()

        readme = response.text

        # 🧠 Pregunta para el modelo
        pregunta = "devuelme un json con resumen de habilidades detectadas"

        # ✉️ Construcción del mensaje para el LLM
        mensajes = [
            {"role": "system", "content": "Eres un experto en análisis de proyectos de software."},
            {"role": "user", "content": f"Aquí está el README de un proyecto:\n\n{readme}"},
            {"role": "user", "content": pregunta}
        ]

        respuesta = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nousresearch/deephermes-3-mistral-24b-preview:free",  # Puedes usar otros modelos como openchat, llama3, etc.
                "messages": mensajes
            }
        )

        response_ia =""

        if respuesta.status_code == 200:
            response_ia = respuesta.json()
        else:
            print("Error al llamar a OpenRouter:", respuesta.status_code)
            print(respuesta.text)
            return

        try:
            evaluation = json.loads(response_ia["choices"][0]["message"]["content"])
            evaluation = json.dumps(evaluation)  # Convertir a JSON para almacenar
        except Exception as e:
            print("Error al procesar la respuesta de IA:", e)
            evaluation = ""

        # Guardar la evaluación en la base de datos
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO evaluation (request_id, repository_id, evaluation)
            VALUES (?, ?, ?)
        ''', (request_id, repo[0], evaluation))

        connection.commit()
        connection.close()

def start_worker():
    """Inicia el worker de RabbitMQ con lógica de reintento."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)
            )
            channel = connection.channel()
            channel.queue_declare(queue="evaluation_queue", durable=True)
            channel.basic_consume(queue="evaluation_queue", on_message_callback=process_message)
            print("Scraper started. Waiting for messages...")
            channel.start_consuming()
            break
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ is not ready. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    start_worker()
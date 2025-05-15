import sqlite3
import pika
import json
import os
import time
from utils import fetch_trending_repos

# Configuración de RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
DATABASE_PATH = "db/database.sqlite"  # Ruta directa al archivo de la base de datos

def get_db_connection():
    """Crea una conexión directa a la base de datos SQLite."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def process_message(ch, method, properties, body):
    """Procesa un mensaje de la cola de RabbitMQ."""
    message = json.loads(body)
    request_id = message["request_id"]
    language = message["language"]
    date_range = message["date_range"]

    print(f"Processing request_id: {request_id} with language={language} and date_range={date_range}")

    # Fetch trending repositories
    trending_repos = fetch_trending_repos(language, date_range)

    # Save the results to the database
    connection = get_db_connection()
    cursor = connection.cursor()
    for repo in trending_repos:
        cursor.execute('''
            INSERT INTO repositories (name, url, description, language, stars, request_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (repo['name'], repo['url'], repo['description'], repo['language'], repo['stars'], request_id))
    
    # Cambia el status a 1 en la tabla requests
    cursor.execute('UPDATE requests SET status = 1 WHERE id = ?', (request_id,))
    
    connection.commit()
    connection.close()

    print(f"Processed request_id: {request_id}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

    evaluation_message = json.dumps({"request_id":  request_id})
    ch.basic_publish(
        exchange='',
        routing_key='evaluation_queue',
        body=evaluation_message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # Make message persistent
        )
    )

def start_worker():
    """Inicia el worker de RabbitMQ con lógica de reintento."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)
            )
            channel = connection.channel()
            channel.queue_declare(queue="scraping_queue", durable=True)
            channel.basic_consume(queue="scraping_queue", on_message_callback=process_message)
            print("Worker started. Waiting for messages...")
            channel.start_consuming()
            break
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ is not ready. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    start_worker()
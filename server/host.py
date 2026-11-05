import os
import json
import uuid
import sqlite3
import threading
import time
import pika

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

RABBITMQ = os.getenv("RABBITMQ", "amqp://bird:birdpass@rabbitmq:5672/")
DATABASE = "/data/host.db"


def initialize_database():
    os.makedirs("/data", exist_ok=True)

    with sqlite3.connect(DATABASE) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result TEXT
            )
        """)


def save_task(task_id, status, result=None):
    with sqlite3.connect(DATABASE) as connection:
        connection.execute("""
            INSERT OR REPLACE INTO tasks (task_id, status, result)
            VALUES (?, ?, ?)
        """, (task_id, status, result))


def receive_results():
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.URLParameters(RABBITMQ)
            )
            channel = connection.channel()

            channel.queue_declare(
                queue="bird_results",
                durable=True
            )

            def callback(ch, method, properties, body):
                try:
                    data = json.loads(body)

                    save_task(
                        data["task_id"],
                        "completed",
                        json.dumps(data["result"], ensure_ascii=False)
                    )

                    ch.basic_ack(delivery_tag=method.delivery_tag)

                except Exception:
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=True
                    )

            channel.basic_qos(prefetch_count=1)

            channel.basic_consume(
                queue="bird_results",
                on_message_callback=callback
            )

            channel.start_consuming()

        except Exception as error:
            print(error)
            time.sleep(5)


@app.on_event("startup")
def startup_event():
    initialize_database()

    thread = threading.Thread(
        target=receive_results,
        daemon=True
    )
    thread.start()


@app.get("/")
def home():
    return {"message": "Central server is running"}


@app.post("/analyze")
def analyze(file: UploadFile = File(...)):
    extension = os.path.splitext(file.filename or "")[1].lower()

    if extension not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(
            status_code=400,
            detail="Only JPG and PNG"
        )

    try:
        image_data = file.file.read()

        if not image_data:
            raise HTTPException(
                status_code=400,
                detail="Empty image"
            )

        task_id = str(uuid.uuid4())

        message = {
            "task_id": task_id,
            "image_name": file.filename,
            "image": image_data.hex()
        }

        save_task(task_id, "processing")

        connection = pika.BlockingConnection(
            pika.URLParameters(RABBITMQ)
        )

        channel = connection.channel()

        channel.queue_declare(
            queue="bird_tasks",
            durable=True
        )

        channel.basic_publish(
            exchange="",
            routing_key="bird_tasks",
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2
            )
        )

        connection.close()

        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Image added"
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        file.file.close()


@app.get("/result/{task_id}")
def get_result(task_id: str):
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute("""
            SELECT status, result
            FROM tasks
            WHERE task_id = ?
        """, (task_id,)).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return {
        "task_id": task_id,
        "status": row[0],
        "result": json.loads(row[1]) if row[1] else None
    }
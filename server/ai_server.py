import os
import json
import time
import sqlite3
import shutil
import tempfile
import threading
import pika
import main

from fastapi import FastAPI
from PIL import Image

app = FastAPI()
model = None

RABBITMQ = os.getenv(
    "RABBITMQ",
    "amqp://guest:guest@rabbitmq:5672/"
)


def process_task(data, channel):
    image_data = bytes.fromhex(data["image"])
    image_name = data["image_name"]
    task_id = data["task_id"]

    extension = os.path.splitext(image_name)[1].lower()
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=extension,
            delete=False
        ) as temp_file:
            temp_file.write(image_data)
            temp_path = temp_file.name

        with Image.open(temp_path) as source:
            image = source.convert("RGB")

        predictions = model(image, top_k=3)

        main.analyze_image(temp_path, model)

        with sqlite3.connect(main.DATABASE) as connection:
            row = connection.execute("""
                SELECT predicted_species, confidence,
                       analysis_date, description
                FROM bird_analysis
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

        if row is None:
            raise ValueError("Analysis result wasnt saved")

        result = {
            "image_name": image_name,
            "predicted_species": predictions[0]["label"].replace("_", " "),
            "confidence": predictions[0]["score"] * 100,
            "predictions": [
                {
                    "species": item["label"].replace("_", " "),
                    "confidence": item["score"] * 100
                }
                for item in predictions
            ],
            "analysis_date": row[2],
            "description": row[3]
        }

        channel.queue_declare(
            queue="bird_results",
            durable=True
        )

        channel.basic_publish(
            exchange="",
            routing_key="bird_results",
            body=json.dumps({
                "task_id": task_id,
                "result": result
            }),
            properties=pika.BasicProperties(
                delivery_mode=2
            )
        )

        print("Task completed:", task_id)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def start_worker():
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.URLParameters(RABBITMQ)
            )
            channel = connection.channel()

            channel.queue_declare(
                queue="bird_tasks",
                durable=True
            )

            channel.queue_declare(
                queue="bird_results",
                durable=True
            )

            def callback(ch, method, properties, body):
                try:
                    data = json.loads(body)
                    process_task(data, ch)
                    ch.basic_ack(
                        delivery_tag=method.delivery_tag
                    )
                except Exception as error:
                    print("Task processing error:", error)
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=False
                    )

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue="bird_tasks",
                on_message_callback=callback
            )

            channel.start_consuming()

        except Exception as error:
            print(error)
            time.sleep(5)


@app.on_event("startup")
def startup_event():
    global model

    main.initialize_database()
    model = main.load_model()

    thread = threading.Thread(
        target=start_worker,
        daemon=True
    )
    thread.start()


@app.get("/")
def home():
    return {"message": "AI Bird Server is running"}
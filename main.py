import csv
import os
import sqlite3
from datetime import datetime
import torch
from PIL import Image
from transformers import pipeline

MODEL = "chriamue/bird-species-classifier"
DATABASE = "bird_database.db"
CSV = "bird_analysis.csv"


def initialize_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS bird_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_name TEXT NOT NULL,
                predicted_species TEXT NOT NULL,
                confidence REAL,
                analysis_date TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)


def load_model():
    model = pipeline(
        "image-classification",
        model=MODEL
    )
    return model


def analyze_image(image_path, model):
    if not os.path.isfile(image_path):
        raise FileNotFoundError("Изображение не найдено")

    if os.path.splitext(image_path)[1].lower() not in (
        ".jpg", ".jpeg", ".png"
    ):
        raise ValueError("Только JPG, JPEG и PNG")

    with Image.open(image_path) as source:
        image = source.convert("RGB")

    predictions = model(image, top_k=3)

    if not predictions:
        raise ValueError("Не удалось определить")

    species = predictions[0]["label"].replace("_", " ")
    confidence = predictions[0]["score"] * 100
    image_name = os.path.basename(image_path)
    analysis_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    description = (
        f"Предполагаемый вид: {species} "
        f"Определено с уверенностью {confidence:.2f}%"
    )

    with sqlite3.connect(DATABASE) as connection:
        connection.execute("""
            INSERT INTO bird_analysis (
                image_name, predicted_species, confidence,
                analysis_date, description
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            image_name,
            species,
            confidence,
            analysis_date,
            description
        ))

    export_csv()

    print("Птица:", species)
    print(f"Уверенность: {confidence:.2f}%")
    print("3 наиболее вероятных:")

    for prediction in predictions:
        print(
            f"- {prediction['label'].replace('_', ' ')}: "
            f"{prediction['score'] * 100:.2f}%"
        )

    print("Описание:", description)
    print("Результат сохранён")


def export_csv():
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute("""
            SELECT image_name, predicted_species, confidence,
                   analysis_date, description
            FROM bird_analysis
            ORDER BY id
        """).fetchall()

    with open(CSV, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow([
            "image_name",
            "predicted_species",
            "confidence",
            "analysis_date",
            "description"
        ])
        writer.writerows(rows)


def main():
    initialize_database()

    try:
        model = load_model()
        image_path = input("Введите путь к изображению: ").strip().strip('"')
        analyze_image(image_path, model)

    except Exception as error:
        print("Ошибка:", error)


if __name__ == "__main__":
    main()

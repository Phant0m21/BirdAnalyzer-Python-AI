from fastapi import *
import sqlite3
import os
import shutil
import main
from PIL import Image
import tempfile

app = FastAPI()
model = None


@app.on_event("startup")
def startup_event():
    global model
    main.initialize_database()
    model = main.load_model()


@app.get("/")
def home():
    return {"message": "AI Bird Server is running"}


@app.post("/analyze")
def analyze(file: UploadFile = File(...)):
    extension = os.path.splitext(file.filename or "")[1].lower()

    if extension not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPG, JPEG and PNG are allowed"
        )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=extension,
            delete=False
        ) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
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
            raise HTTPException(
                status_code=500,
                detail="Analysis result was not saved"
            )

        return {
            "image_name": file.filename,
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

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        file.file.close()
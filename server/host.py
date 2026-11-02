import os
import requests
from fastapi import *

app = FastAPI()

AI_SERVER = os.getenv(
    "http://127.0.0.1:8000"
)

@app.get("/")
def home():
    return {"message": "Central server is running"}

@app.post("/analyze")
def analyze(file: UploadFile = File(...)):
    try:
        response = requests.post(
            f"{AI_SERVER}/analyze",
            files={
                "file": (
                    file.filename,
                    file.file,
                    file.content_type
                )
            },
            timeout=300
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"AI server error: {error}"
        )
    finally:
        file.file.close()

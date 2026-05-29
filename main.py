from fastapi import FastAPI
import json
from pathlib import Path
from app.schemas import UserInput
from app.services import run_scoring_algorithm

app = FastAPI(title="GPN Scoring API")

DATA_PATH = Path(__file__).parent.parent / "baza.json"
with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
    database = json.load(f)

@app.post("/api/score")
def score_regions(payload: UserInput):
    best_regions = run_scoring_algorithm(payload.model_dump(), database["regions"])
    return {
        "status": "success",
        "top_regions": best_regions
    }

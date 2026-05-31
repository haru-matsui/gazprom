from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path
from schemas import UserInput
from services import run_scoring_algorithm
import base64
import os

app = FastAPI(title="GPN Scoring API")

# CORS for local dev: allow Streamlit iframe to POST images
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).parent / "baza.json"
with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
    database = json.load(f)

@app.post("/api/score")
def score_regions(payload: UserInput):
    best_regions = run_scoring_algorithm(payload.model_dump(), database["regions"])
    return {
        "status": "success",
        "top_regions": best_regions
    }


@app.post("/api/save_screenshots")
async def save_screenshots(request: Request):
    """Принимает JSON: { "screens": [dataURL,...], "collage": dataURL }
    Сохраняет файлы в ./renders с фиксированными именами, перезаписывая их.
    """
    data = await request.json()
    screens = data.get("screens", [])
    collage = data.get("collage")
    out_dir = Path(__file__).parent / "renders"
    out_dir.mkdir(exist_ok=True)
    saved = {"screens": [], "collage": None}
    try:
        for idx, d in enumerate(screens, start=1):
            if "," in d:
                header, b64 = d.split(",", 1)
            else:
                b64 = d
            img_bytes = base64.b64decode(b64)
            fname = out_dir / f"factory_view_{idx}.png"
            with open(fname, "wb") as f:
                f.write(img_bytes)
            saved["screens"].append(str(fname.name))
        if collage:
            if "," in collage:
                _, b64c = collage.split(",", 1)
            else:
                b64c = collage
            coll_path = out_dir / "factory_collage.png"
            with open(coll_path, "wb") as f:
                f.write(base64.b64decode(b64c))
            saved["collage"] = str(coll_path.name)
        return JSONResponse({"status": "ok", "saved": saved})
    except Exception as e:
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)


# Serve saved renders
@app.get("/renders/{filename}")
def get_render_file(filename: str):
    p = Path(__file__).parent / "renders" / filename
    if p.exists():
        return FileResponse(p)
    return JSONResponse({"error": "not found"}, status_code=404)

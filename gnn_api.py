"""
gnn_api.py - FastAPI endpoints for the AtmoGraph GNN

Needs, in the same folder: atmograph_gnn.py, atmograph_hetero_gnn.pt, gnn_service.py, data/synthetic/, Index.html

Run it alone to test:
    pip install fastapi uvicorn
    python -m uvicorn gnn_api:app --reload
    then open http://127.0.0.1:8000/
"""

# =====================================================================
# WHAT THIS FILE IS
# ---------------------------------------------------------------------
# It defines the web addresses (endpoints) of the GNN service using FastAPI.
# There is no model logic here: that lives in gnn_service.py. This file only
# checks the input, calls the service and shapes the answer.
#   GET  /gnn/options  valid ports, routes and event types
#   POST /gnn/predict  the main call: a disruption in, the predicted ripple out
#   GET  /health       'is the server running?'
#   GET  /             serves the web page (Index.html)
# =====================================================================
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import List

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from gnn_service import AtmoGraphPredictor

# Folder this file lives in, so Index.html is found no matter where the server is started.
BASE_DIR = Path(__file__).parent


# lru_cache(maxsize=1): the function runs once and the same result is reused afterwards.
# So the model loads on the first request only and is shared by all later requests.
@lru_cache(maxsize=1)
def get_predictor() -> AtmoGraphPredictor:
    """Loads the model the first time it is asked for, then reuses the same one forever."""
    return AtmoGraphPredictor()


# Called at server start-up to load the model early, so the first request is not slow.
def preload():
    get_predictor()


# The INPUT the API accepts. Pydantic checks it automatically: a wrong type or an
# out-of-range value gives an HTTP 422 error with a clear message.
# Field(...) adds limits (ge = at least, le = at most) and descriptions for the /docs page.
class PredictRequest(BaseModel):
    event_type: str = Field(..., examples=["strike"])
    severity: int = Field(..., ge=1, le=5, description="1 (mild) to 5 (severe)")
    duration_days: int = Field(..., ge=1, le=60)
    target_ids: List[str] = Field(..., min_length=1, examples=[["P1"]],
                                  description="Port ids (P..) and/or route ids (R..) hit by the disruption")


# A router groups related endpoints under /gnn, so this module can be plugged into a
# bigger app with app.include_router(router).
router = APIRouter(prefix="/gnn", tags=["GNN"])


# GET /gnn/options: lists the valid inputs (useful for filling dropdowns).
@router.get("/options")
def options():
    """What values the frontend is allowed to send."""
    p = get_predictor()
    return {
        "event_types": p.S["etypes"],
        "ports": list(p.S["ids"]["port"].keys()),
        "routes": list(p.S["ids"]["route"].keys()),
        "severity_range": [1, 5],
        "duration_days_range": [1, 60],
    }


# POST /gnn/predict: the main endpoint. Send a disruption, get the predicted ripple effect.
@router.post("/predict")
def predict(req: PredictRequest):
    # A ValueError from the service (unknown event type or id) becomes a clean HTTP 422
    # response instead of a server crash.
    try:
        out = get_predictor().predict(req.event_type, req.severity, req.duration_days, req.target_ids)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    # Add the 5 most affected industries, highest first, for convenience.
    top = sorted(out["industry_impact"].items(), key=lambda kv: kv[1], reverse=True)[:5]
    out["top_industries"] = [{"id": k, "impact": v} for k, v in top]
    return out


# Code before 'yield' runs when the server starts, code after it when it stops.
@asynccontextmanager
async def lifespan(app: FastAPI):
    preload()  # load the model once, when the server starts
    yield


# The web application itself. uvicorn runs this object.
app = FastAPI(title="AtmoGraph GNN API", lifespan=lifespan)

# Attach the /gnn endpoints to the app.
app.include_router(router)


# GET /health: a quick 'are you alive?' check, used by monitoring tools.
@app.get("/health")
def health():
    return {"status": "ok"}


# GET /: serves Index.html (hidden from the /docs page) so the page and API share one address.
@app.get("/", include_in_schema=False)
def home():
    """Serves the web page, so the page and the API share one address."""
    return FileResponse(BASE_DIR / "Index.html")

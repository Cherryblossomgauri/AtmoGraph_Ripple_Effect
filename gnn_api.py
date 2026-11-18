"""
gnn_api.py - FastAPI endpoints for the AtmoGraph GNN

Needs, in the same folder: atmograph_gnn.py, atmograph_hetero_gnn.pt, gnn_service.py, data/synthetic/

Run it alone to test:
    pip install fastapi uvicorn
    uvicorn gnn_api:app --reload
    then open http://127.0.0.1:8000/docs

Plug into the main project (friend's FastAPI app):
    from gnn_api import router as gnn_router, preload
    app.include_router(gnn_router)
    # and call preload() once at startup so the first request is not slow
"""
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import List

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from gnn_service import AtmoGraphPredictor


@lru_cache(maxsize=1)
def get_predictor() -> AtmoGraphPredictor:
    """Loads the model the first time it is asked for, then reuses the same one forever."""
    return AtmoGraphPredictor()


def preload():
    get_predictor()


class PredictRequest(BaseModel):
    event_type: str = Field(..., examples=["strike"])
    severity: int = Field(..., ge=1, le=5, description="1 (mild) to 5 (severe)")
    duration_days: int = Field(..., ge=1, le=60)
    target_ids: List[str] = Field(..., min_length=1, examples=[["P1"]],
                                  description="Port ids (P..) and/or route ids (R..) hit by the disruption")


router = APIRouter(prefix="/gnn", tags=["GNN"])


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


@router.post("/predict")
def predict(req: PredictRequest):
    try:
        out = get_predictor().predict(req.event_type, req.severity, req.duration_days, req.target_ids)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    top = sorted(out["industry_impact"].items(), key=lambda kv: kv[1], reverse=True)[:5]
    out["top_industries"] = [{"id": k, "impact": v} for k, v in top]
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    preload()  # load the model once, when the server starts
    yield


app = FastAPI(title="AtmoGraph GNN API", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}

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

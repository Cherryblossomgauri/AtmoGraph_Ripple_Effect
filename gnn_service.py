"""
gnn_service.py - inference wrapper for the AtmoGraph GNN (for the FastAPI person)

Put these 3 files in the same folder / repo root:
    atmograph_gnn.py          (your training script, keep its name)
    atmograph_hetero_gnn.pt   (trained weights, created when the training script finishes)
    gnn_service.py            (this file)
and keep data/synthetic/*.csv available (the graph structure is rebuilt from it at startup).

Usage in FastAPI:

    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from gnn_service import AtmoGraphPredictor

    app = FastAPI()
    predictor = AtmoGraphPredictor()          # load ONCE at startup, not per request

    class Req(BaseModel):
        event_type: str                        # e.g. "storm", "strike", "congestion", "flood"
        severity: int                          # 1..5
        duration_days: int                     # 2..30
        target_ids: list[str]                  # e.g. ["P2"] or ["R1"] (port / route ids)

    @app.post("/gnn/predict")
    def gnn_predict(r: Req):
        try:
            return predictor.predict(r.event_type, r.severity, r.duration_days, r.target_ids)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
"""
import os
import torch

import atmograph_gnn as g

WEIGHTS_PATH = os.getenv("GNN_WEIGHTS", "atmograph_hetero_gnn.pt")
LAYERS = 5  # the script saves models[5], i.e. the 5-layer GNN


def _load_raw():
    if g.USE_NEO4J:
        return g.fetch_from_neo4j()
    if os.path.isdir(g.CSV_DIR):
        return g.load_from_csv(g.CSV_DIR)
    return g.make_mock_raw()


class AtmoGraphPredictor:
    def __init__(self, weights_path: str = WEIGHTS_PATH):
        self.raw = _load_raw()
        self.S = g.build_static(self.raw)
        # The model needs a sample graph only to learn the node types, feature sizes, edge types
        dummy = dict(event_type=self.S["etypes"][0], severity=1, duration_days=2)
        sample = g.make_scenario(self.S, dummy, [("port", 0)])
        self.model = g.HeteroGNN(sample, LAYERS)
        self.model.load_state_dict(torch.load(weights_path, map_location="cpu"))
        self.model.eval()

    @torch.no_grad()
    def predict(self, event_type: str, severity: int, duration_days: int, target_ids: list):
        ids = self.S["ids"]
        if event_type not in self.S["etypes"]:
            raise ValueError(f"event_type must be one of {self.S['etypes']}")
        if not target_ids:
            raise ValueError("target_ids must contain at least one port or route id")
        targets = []
        for t in target_ids:
            if t in ids["port"]:
                targets.append(("port", ids["port"][t]))
            elif t in ids["route"]:
                targets.append(("route", ids["route"][t]))
            else:
                raise ValueError(f"unknown port/route id: {t}")
        d = dict(event_type=event_type, severity=int(severity), duration_days=int(duration_days))
        sc = g.make_scenario(self.S, d, targets)
        batch = next(iter(g.DataLoader([sc], batch_size=1)))
        pred = self.model(batch)  # eval mode -> already clamped to 0..1

        def as_dict(kind, key):
            return {r["id"]: round(float(v), 4) for r, v in zip(self.raw[kind], pred[key])}

        return {
            "input": {**d, "targets": target_ids},
            "port_impact": as_dict("port", "port"),
            "industry_impact": as_dict("industry", "industry"),
            "country_impact": as_dict("country", "country"),
        }

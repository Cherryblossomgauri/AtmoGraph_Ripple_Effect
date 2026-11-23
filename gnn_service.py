"""
gnn_service.py - inference wrapper for the AtmoGraph GNN (for the FastAPI person)

Put these files in the same folder / repo root:
    atmograph_gnn.py          (training script, keep its name)
    atmograph_hetero_gnn.pt   (trained weights, created when the training script finishes)
    gnn_service.py            (this file)
and keep data/synthetic/*.csv available (the graph structure is rebuilt from it at startup).

IMPORTANT: the .pt file must be trained on the SAME data that is loaded here.
If the CSVs (or the feature code) change, run `python atmograph_gnn.py` again.
At startup this file checks that weights and data match and raises a clear error if not.

Usage in FastAPI:

    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from gnn_service import AtmoGraphPredictor

    app = FastAPI()
    predictor = AtmoGraphPredictor()          # load ONCE at startup, not per request

    class Req(BaseModel):
        event_type: str                        # one of the event types in the data, e.g. "storm", "strike"
        severity: int                          # 1..5
        duration_days: int                     # 2..30 (longer values are treated as 30)
        target_ids: list[str]                  # e.g. ["P2"] or ["R1"] (port / route ids)

    @app.post("/gnn/predict")
    def gnn_predict(r: Req):
        try:
            return predictor.predict(r.event_type, r.severity, r.duration_days, r.target_ids)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
"""

# ==========================================================================================
# WHERE THIS FILE FITS
# ------------------------------------------------------------------------------------------
# browser page / other apps  ->  gnn_api.py (web addresses)  ->  THIS FILE  ->  trained model
# This file has no web code. It loads the saved weights, rebuilds the model, checks that the
# weights match the data, and turns one request into one prediction.
# ==========================================================================================
import os
import torch

import atmograph_gnn as g

# Where the trained weights file lives. Can be changed with the GNN_WEIGHTS environment variable.
WEIGHTS_PATH = os.getenv("GNN_WEIGHTS", "atmograph_hetero_gnn.pt")

# layers = how many link-hops the model sees. 5 is what the training script saves. Only used for
# old weights files that do not record it.
DEFAULT_LAYERS = 5  # the training script saves the 5-layer GNN

# Message shown when the weights file and the data disagree.
RETRAIN_HINT = (
    "The saved weights do not match the data/code being loaded. "
    "Fix: run `python atmograph_gnn.py` from the project folder (it must say "
    "'source: CSV files in data/synthetic', not MOCK) to create a new "
    f"{WEIGHTS_PATH}, then start the app again."
)


# Loads the graph data using the same rules as training: Neo4j, else the CSV folder, else fake data.
# NOTE: CSV_DIR is a relative path, so start the server from the project folder; otherwise the
# CSVs are not found and the fake fallback causes the 'weights/data mismatch' error below.
def _load_raw():
    if g.USE_NEO4J:
        return g.fetch_from_neo4j()
    if os.path.isdir(g.CSV_DIR):
        return g.load_from_csv(g.CSV_DIR)
    return g.make_mock_raw()


# Safety check. A weights file only fits the exact data it was trained on (same number of
# features, same categories). If not, stop early with a clear message instead of silently
# returning wrong numbers.
def _check_compatible(state, meta, sample, S):
    """Raise a readable error if the weights were trained on different data than we loaded."""
    problems = []
    # Compare the number of features per node type.
    for nt in sample.node_types:
        key = f"enc.{nt}.weight"
        want = sample[nt].x.shape[1]
        if key not in state:
            problems.append(f"  - weights have no encoder for node type '{nt}'")
        elif state[key].shape[1] != want:
            problems.append(f"  - '{nt}' features: weights expect {state[key].shape[1]}, current data gives {want}")
    # Newer weights files also record the category lists, which catches mismatches of equal size.
    if meta:  # new-format checkpoint: also catch same-size-but-different categories
        for name, cur in (("regions", S["regions"]), ("categories", S["cats"]), ("etypes", S["etypes"])):
            if list(meta.get(name, cur)) != list(cur):
                problems.append(f"  - {name} differ: weights trained on {meta[name]}, current data has {list(cur)}")
    if problems:
        raise RuntimeError("\n".join(["Weights/data mismatch:"] + problems + [RETRAIN_HINT]))


# The object the API uses. Create it ONCE (loading takes a moment), then call .predict(...)
# for every request.
class AtmoGraphPredictor:
    def __init__(self, weights_path: str = WEIGHTS_PATH):
        if not os.path.isfile(weights_path):
            raise FileNotFoundError(f"{weights_path} not found. Run `python atmograph_gnn.py` first.")
        # 1. Load the graph data and build the static tensors, exactly like training.
        self.raw = _load_raw()
        self.S = g.build_static(self.raw)
        # The model needs a sample graph only to learn the node types, feature sizes, edge types
        # 2. The model class needs one example scenario, only to learn the node/link types and sizes.
        dummy = dict(event_type=self.S["etypes"][0], severity=1, duration_days=2)
        sample = g.make_scenario(self.S, dummy, [("port", 0)])

        # 3. Read the saved weights (map_location='cpu': works on any computer, no GPU needed).
        ckpt = torch.load(weights_path, map_location="cpu")
        # Supports the current file format and the older one (plain weights, no 'meta').
        if isinstance(ckpt, dict) and "state_dict" in ckpt:   # current format
            state, meta = ckpt["state_dict"], ckpt.get("meta")
        else:                                                  # old format: bare state_dict
            state, meta = ckpt, None
        # 4. Make sure the weights and the data match.
        _check_compatible(state, meta, sample, self.S)

        # 5. Rebuild the model structure, load the learned weights into it, and switch to prediction
        # mode (.eval()).
        layers = (meta or {}).get("layers", DEFAULT_LAYERS)
        self.model = g.HeteroGNN(sample, layers)
        self.model.load_state_dict(state)
        self.model.eval()

    # Answers one request: event type, severity, duration and the port(s)/route(s) hit go in, the
    # predicted impact for every port, industry and country comes out. @torch.no_grad() = no learning
    # happens here, which makes it faster.
    @torch.no_grad()
    def predict(self, event_type: str, severity: int, duration_days: int, target_ids: list):
        # 1. Validate the input. Unknown event types or ids raise ValueError, which the API turns into
        # an HTTP 422 response.
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
        # 2. Describe the disruption the same way training does and build its graph.
        # (Durations above DUR_MAX days are treated as DUR_MAX.)
        d = dict(event_type=event_type, severity=int(severity), duration_days=int(duration_days))
        sc = g.make_scenario(self.S, d, targets)
        # The model expects a batch, so we make a batch containing one scenario.
        batch = next(iter(g.DataLoader([sc], batch_size=1)))
        # 3. Run the model.
        pred = self.model(batch)  # eval mode -> already clamped to 0..1

        # Helper: pair each node's readable id with its predicted number (4 decimals).
        def as_dict(kind, key):
            return {r["id"]: round(float(v), 4) for r, v in zip(self.raw[kind], pred[key])}

        # 4. The response handed back to the API.
        return {
            "input": {**d, "targets": target_ids},
            "port_impact": as_dict("port", "port"),
            "industry_impact": as_dict("industry", "industry"),
            "country_impact": as_dict("country", "country"),
        }

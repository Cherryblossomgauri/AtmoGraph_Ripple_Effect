# AtmoGraph GNN – Ripple Effect Model and API

Given one supply-chain disruption (event type, severity, duration, and the port or route it hits), the GNN predicts an impact score from 0 to 1 for every **port, industry and country**. This is the "ripple effect" shown on the dashboard.

> Note: the training labels come from a rule-based simulator (`simulate()` in `atmograph_gnn.py`), not from real-world outcomes. Treat the GNN as a fast scenario simulator. The ranking of affected industries is more reliable than the exact values.

## Files

| File | Purpose |
|---|---|
| `atmograph_gnn.py` | Builds the graph, trains the GNN, saves the weights |
| `atmograph_hetero_gnn.pt` | Trained model weights (created by training) |
| `gnn_service.py` | Loads the weights and runs predictions |
| `gnn_api.py` | FastAPI endpoints |
| `data/synthetic/*.csv` | Graph data (ports, routes, industries, countries, disruptions) |

All files must be in the same folder.

## 1. Install

```
pip install torch torch_geometric numpy fastapi uvicorn
```

## 2. Train (only when the data changes)

```
python atmograph_gnn.py
```

The first output line shows the data source. It should say `CSV files in data/synthetic`. If it says `MOCK`, the CSV folder was not found and the model trained on fake backup data.

Training overwrites `atmograph_hetero_gnn.pt`. The `.pt` file and the `data/synthetic` folder must always come from the same run.

## 3. Run the API

```
uvicorn gnn_api:app --reload
```

Open http://127.0.0.1:8000/docs to try the endpoints in the browser.

## Endpoints

### `GET /gnn/options`
Returns the valid event types, port ids, route ids and allowed ranges.

### `POST /gnn/predict`
Request:
```json
{
  "event_type": "strike",
  "severity": 5,
  "duration_days": 20,
  "target_ids": ["P1"]
}
```
- `severity`: 1 to 5
- `duration_days`: 1 to 60
- `target_ids`: one or more port ids (P..) or route ids (R..)

Response:
```json
{
  "input": {"event_type": "strike", "severity": 5, "duration_days": 20, "targets": ["P1"]},
  "port_impact": {"P0": 0.0, "P1": 0.41},
  "industry_impact": {"I0": 0.02},
  "country_impact": {"C0": 0.06},
  "top_industries": [{"id": "I48", "impact": 0.53}]
}
```
A wrong event type or unknown id returns HTTP 422 with a message listing what is allowed.

### `GET /health`
Returns `{"status": "ok"}`.

## Use inside the main FastAPI project

```python
from gnn_api import router as gnn_router
app.include_router(gnn_router)
```

The model loads once on first use. To load it at startup instead, call `gnn_api.preload()` when the app starts.

## Switching to real data

1. Put the real CSVs in `data/synthetic/`.
2. Run `python atmograph_gnn.py` again.
3. Commit the new `atmograph_hetero_gnn.pt` together with the CSV folder.

No code changes are needed.

## Common errors

| Error | Fix |
|---|---|
| `ModuleNotFoundError: gnn_service` | Run the command from the project folder and make sure `gnn_service.py` is there |
| `FileNotFoundError ... .pt` | Run `python atmograph_gnn.py` first |
| HTTP 422 on `/gnn/predict` | Check allowed values with `GET /gnn/options` |

# AtmoGraph GNN – Ripple Effect Model, API and Dashboard

Given one supply-chain disruption (event type, severity, duration, and the port(s) or route(s) it hits), the GNN predicts an impact score from 0 to 1 for every **port, industry and country**. This is the "ripple effect" shown on the dashboard.

> **Note:** the training labels come from a rule-based simulator (`simulate()` in `atmograph_gnn.py`), not from real-world outcomes. The real graph has no impact labels. Treat the GNN as a fast scenario simulator that imitates that rule. The ranking of affected industries is more reliable than the exact values. The rule constants (severity scale, route-to-port share, supplier damping) are assumptions and should be agreed with the team.

## How it works

1. **Graph.** A heterogeneous graph of 5 node types: Country, Industry, Port, ShippingRoute and Disruption. Edges: `HAS_INDUSTRY`, `SUPPLIES` (directional: supplier → buyer), `USES_PORT`, `LOCATED_IN`, `FROM_PORT`, `TO_PORT`, `AFFECTS`. Reverse edges are added automatically.
2. **Model.** A 5-layer heterogeneous GNN (`HeteroConv` + `GraphConv`, hidden size 48, residual connections). Five layers are used because the country-level ripple needs about 5 hops: disruption → route → port → industry → industry → country. Three output heads predict port, industry and country impact. Outputs are clamped to 0..1 at prediction time.
3. **Training.** 2,000 random synthetic scenarios (1 to 3 targets, ports and routes mixed), 40 epochs, Adam (lr 2e-3), MSE loss. The best epoch on a validation set is kept.
4. **Labels (the rule).** Disruption magnitude grows with severity and duration. A port hit loses a little less when its capacity is high. A route hit passes half of its impact to its two end ports. Port impact then flows to industries through `USES_PORT`, spreads between industries through `SUPPLIES` (3 rounds, damped by half), and is averaged per country.

## Files

| File | Purpose |
|---|---|
| `atmograph_gnn.py` | Builds the graph, trains the GNN, saves the weights |
| `atmograph_hetero_gnn.pt` | Trained weights plus metadata (created by training) |
| `gnn_service.py` | Loads the weights and runs predictions (`AtmoGraphPredictor`) |
| `gnn_api.py` | FastAPI endpoints, and serves the web page at `/` |
| `Index.html` | Dashboard web page (single file, no build step) |
| `data/synthetic/*.csv` | Graph data (see "Data files" below) |

All files must be in the same project folder, and the file names must match exactly (no `(4)`, `(5)` suffixes from repeated downloads), because the code imports them by name.

```
project/
├── atmograph_gnn.py
├── atmograph_hetero_gnn.pt
├── gnn_service.py
├── gnn_api.py
├── Index.html
├── README.md
└── data/synthetic/
    ├── countries.csv
    ├── industries.csv
    ├── ports.csv
    ├── shipping_routes.csv
    ├── disruptions.csv
    ├── transactions.csv
    └── industry_port_links.csv
```

## 1. Install

```
pip install torch torch_geometric numpy fastapi uvicorn
```

Only if you read the graph from Neo4j instead of CSV files:

```
pip install neo4j
```

## 2. Train (only when the data or the model code changes)

Run from the project folder, so that `data/synthetic` is found:

```
python atmograph_gnn.py
```

The first output line shows the data source. It should say `source: CSV files in data/synthetic`. If it says `MOCK`, the CSV folder was not found and the model trained on fake backup data.

Training also prints test tables (MAE for port, industry and country, plus a "top5" score for finding the most affected industries) for the GNN against two baselines (predict zero, per-node average), on random scenarios, on unseen port/route targets, and on the 10 real disruption rows. It then prints a demo for one real disruption and saves the weights.

Training overwrites `atmograph_hetero_gnn.pt`. The `.pt` file and the `data/synthetic` folder must always come from the same run.

The `.pt` file also stores the number of layers and the region, industry-category and event-type lists it was trained on. At startup `gnn_service.py` compares them with the loaded data and stops with a clear message if they differ.

## 3. Run the API and the dashboard

```
python -m uvicorn gnn_api:app --reload
```

| Address | What you get |
|---|---|
| http://127.0.0.1:8000/ | The dashboard (`Index.html`) |
| http://127.0.0.1:8000/docs | Interactive API docs |
| http://127.0.0.1:8000/health | Health check |

The model is loaded once, when the server starts.

## Dashboard (`Index.html`)

The page asks the API what is allowed (`GET /gnn/options`), so you can only choose values the model understands:

- **What happened?** Event type, taken from the data.
- **How severe?** Slider from 1 to 5.
- **How long?** Slider from 2 to 30 days (the range the model was trained on).
- **Where does it hit?** Choose one or more ports and routes.

After **Show the ripple effect** it shows a summary headline, the top 5 most affected industries, and full lists for ports, industries and countries (first 8 shown, with a "Show all" button). Targets are marked "(hit)". Each score has a level:

| Score | Level |
|---|---|
| below 10% | Minimal |
| 10% to 30% | Low |
| 30% to 50% | Moderate |
| 50% to 70% | High |
| 70% and above | Severe |

Notes:

- Open the page through the server (http://127.0.0.1:8000/), not by double-clicking the file. This way the page and the API share one address. To point a page at an API on another address, add `?api=http://host:8000` to the page URL. Note that `gnn_api.py` has no CORS settings, so a different address only works if you add them.
- Fonts load from Google Fonts. Without internet the page falls back to system fonts.
- There are three looks of the same page. Pick one and save it as `Index.html`:

| File | Look |
|---|---|
| `Index.html` (default) | Soft teal, follows the device light/dark setting |
| `Index_chart.html` | "Chart paper": white, blue, hard borders and offset shadows |
| `Index_night.html` | "Night ops": dark navy with cyan accents and glowing bars |

Only the styling differs. The behaviour and the API calls are identical.

## Endpoints

### `GET /gnn/options`
Returns the valid event types, port ids, route ids and allowed ranges.

```json
{
  "event_types": ["EQUIPMENT_FAILURE", "FLOOD", "PORT_STRIKE", "ROUTE_CLOSURE", "STORM"],
  "ports": ["P1", "P2"],
  "routes": ["R1", "R2"],
  "severity_range": [1, 5],
  "duration_days_range": [1, 60]
}
```
(Lists shortened. The real response lists all 5 ports and 8 routes. Event types come from the data, so always check this endpoint instead of guessing.)

### `POST /gnn/predict`
Request:
```json
{
  "event_type": "PORT_STRIKE",
  "severity": 5,
  "duration_days": 20,
  "target_ids": ["P1"]
}
```
- `event_type`: one of the values from `/gnn/options`
- `severity`: 1 to 5
- `duration_days`: 1 to 60 (the model was trained on 2 to 30, so values above 30 are treated as 30)
- `target_ids`: one or more port ids (P..) or route ids (R..), mixed allowed

Response:
```json
{
  "input": {"event_type": "PORT_STRIKE", "severity": 5, "duration_days": 20, "targets": ["P1"]},
  "port_impact": {"P0": 0.0, "P1": 0.41},
  "industry_impact": {"I0": 0.02},
  "country_impact": {"C0": 0.06},
  "top_industries": [{"id": "I48", "impact": 0.53}]
}
```
(Maps shortened. The real response has every port, industry and country, and `top_industries` holds the 5 highest.)

Errors return HTTP 422: an unknown event type or id gives a message listing what is allowed, and a value outside the allowed range (for example severity 6) is rejected by the request validation.

### `GET /health`
Returns `{"status": "ok"}`.

## Use inside the main FastAPI project

```python
from gnn_api import router as gnn_router
app.include_router(gnn_router)
```

This adds `/gnn/options` and `/gnn/predict` only. The `/` page and `/health` belong to the standalone app in `gnn_api.py`. When used this way, the model loads on first use. To load it at startup instead, call `gnn_api.preload()` when your app starts.

You can also call the model directly from Python:

```python
from gnn_service import AtmoGraphPredictor
predictor = AtmoGraphPredictor()      # load once, not per request
predictor.predict("STORM", 4, 10, ["P2", "R1"])
```

## Data files

The graph is rebuilt from these CSV files at startup (and for training). The listed columns are the ones used:

| File | Columns used |
|---|---|
| `countries.csv` | `country_id`, `region` |
| `industries.csv` | `industry_id`, `industry_category`, `country_id` |
| `ports.csv` | `port_id`, `capacity_index` (0 to 100), `country_id` |
| `shipping_routes.csv` | `route_id`, `source_port_id`, `destination_port_id`, `transit_days`, `route_capacity_index` (0 to 100) |
| `disruptions.csv` | `disruption_id`, `event_type`, `severity`, `duration_days`, `target_id` (a port or route id) |
| `transactions.csv` | `supplier_industry_id`, `buyer_industry_id`, `dependency_strength` |
| `industry_port_links.csv` | `industry_id`, `port_id`, `share` |

The current weights were trained on 5 countries, 50 industries, 5 ports and 8 routes, 4 regions, 10 industry categories and 5 event types.

## Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `CSV_DIR` | `data/synthetic` | Folder with the CSV files |
| `GNN_WEIGHTS` | `atmograph_hetero_gnn.pt` | Weights file to save (training) or load (API) |
| `USE_NEO4J` | off | Set to `1` to read the live Neo4j graph instead of CSV |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j address. Use the bolt port 7687, not 7474 (that is the browser) |
| `NEO4J_USER` | `neo4j` | Neo4j user |
| `NEO4J_PASSWORD` | none (required) | Neo4j password. Never hard-code or commit it |

If you use Neo4j, train and run the API with the same variables set, for example `USE_NEO4J=1 python atmograph_gnn.py`.

## Switching to real data

1. Put the real CSVs in `data/synthetic/` (or set `CSV_DIR`, or use Neo4j).
2. Run `python atmograph_gnn.py` again.
3. Commit the new `atmograph_hetero_gnn.pt` together with the CSV folder.

No code changes are needed. The event types, regions and industry categories are read from the data. Note that the training script still creates its labels with the rule-based simulator. Real impact labels would need a change in `simulate()`.

## Common errors

| Error | Fix |
|---|---|
| `ModuleNotFoundError: gnn_service` | Run the command from the project folder and make sure `gnn_service.py` is there |
| `ModuleNotFoundError: atmograph_gnn` | A file still has a download suffix, such as `atmograph_gnn (8).py`. Rename it to `atmograph_gnn.py` |
| `FileNotFoundError ... .pt` | Run `python atmograph_gnn.py` first |
| `FileNotFoundError ... .csv` | A file from the "Data files" table is missing from `data/synthetic/`, or you started from the wrong folder |
| `size mismatch for enc.country.weight` / `Weights/data mismatch` | The `.pt` was trained on different data (often MOCK data) than the CSVs now loaded. Run `python atmograph_gnn.py`, check the first line says `CSV files in data/synthetic`, then restart the API |
| `KeyError: 'NEO4J_PASSWORD'` | Set `NEO4J_PASSWORD` before using `USE_NEO4J=1` |
| HTTP 422 on `/gnn/predict` | Check allowed values with `GET /gnn/options` (event types are written like `PORT_STRIKE`, not `strike`) |
| Page says "Can't reach the AtmoGraph API" | Start the API with `python -m uvicorn gnn_api:app --reload`, open http://127.0.0.1:8000/ and reload |

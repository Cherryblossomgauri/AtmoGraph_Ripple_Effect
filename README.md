## My Work: Supply Chain Risk Graph (Riya Chaudhari)

**Branch:** `riya-data`

This part of AtmoGraph turns shipment data into a supply network, spreads a disruption through it, and shows the result in a browser. It covers the "Graph Foundations" and "Visualization" items in the project plan.

### What it does

1. Reads supplier-to-destination shipments from a CSV file.
2. Builds a network where every country or company is a node, and every shipment route is a link.
3. Takes a news-style sentence (for example, "Tsunami hits China"), finds the affected node, and spreads risk along the links.
4. Saves the network with risk values to `graph.json`.
5. Draws the network in the browser with D3.js. Nodes are colored by risk, and clicking a node shows its shipments.

### Files I worked on

| File | Purpose |
|---|---|
| `riya/shipments.csv` | Input data. One row per shipment: `supplier, destination, quantity`. |
| `riya/supply_graph.py` | Builds `graph.json` from the CSV. Resets all risk values to 0. |
| `riya/risk_check.py` | Takes a disruption sentence, marks matching nodes as hit, and spreads risk to connected nodes. Updates `graph.json`. |
| `riya/graph.json` | The network: nodes with risk values, and links with weights. Written by the scripts, not edited by hand. |
| `riya/graph.html` | The D3.js viewer. Reads `graph.json` and draws the network. |
| `riya/load_to_neo4j.py` | Loads `graph.json` into a Neo4j database. |
| `riya/ner_entities.py` | Finds companies and countries in sentences using spaCy. Not yet connected to `risk_check.py`. |
| `riya/csv_to_sentence.py` | Turns CSV rows into sentences. Used for the NER work. |

### Risk rules

- The directly hit node gets risk **1.0**.
- Each step away from it halves the risk: **0.5**, then **0.25**.
- Risk spreads in both directions along shipment links.
- It stops after **3 steps** (`MAX_HOPS` in `risk_check.py`).
- Disruption words that trigger the check: tsunami, earthquake, flood, strike, fire, storm, closure, sanction.

### Colors in the viewer

| Color | Meaning |
|---|---|
| Red | Directly hit (1.0) |
| Orange | Strong ripple (0.5) |
| Yellow | Weak ripple (0.25) |
| Blue | No risk |

### How to run

Run these from the `riya` folder, with the virtual environment active (`(virtual_env)` shows in the terminal):

```powershell
python supply_graph.py
python risk_check.py "Tsunami hits China"
python -m http.server 8000
```

Then open `http://localhost:8000/graph.html` in Chrome. The page must be served over HTTP. Opening the file directly will not load `graph.json`.

To reset the view, run `python supply_graph.py` again.

### Neo4j

`load_to_neo4j.py` reads `graph.json` and writes each node (with its risk) and each shipment link into Neo4j. It reads the connection details from a `.env` file, which is not committed to GitHub.

```powershell
python load_to_neo4j.py
```

The `.env` file needs three lines:

```
NEO4J_URI=your-connection-uri
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

Never commit `.env` or paste its contents into this README.

### Known limits

- Risk matching uses exact names. "China" matches, but "Chinese" does not.
- The news sentence is typed by hand. Automatic news reading is not built yet.
- Propagation uses simple rules, not a trained model.
- The viewer redraws the whole network each time. Very large graphs (thousands of nodes) may be slow in the browser.

### Next steps

- Connect `ner_entities.py` to `risk_check.py`, so full news sentences can be read.
- Confirm the Neo4j load runs end to end and check the results in Neo4j Browser.
- Add the 30/60/90-day timeline view.
- Replace the rule-based spread with a Graph Neural Network, once there is enough data to train it.

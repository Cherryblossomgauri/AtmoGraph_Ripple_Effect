## My Work: Supply Chain Risk Graph (Riya)

I built the data pipeline and risk viewer for AtmoGraph.

### Completed
- **Graph from shipments:** `supply_graph.py` reads `shipments.csv` and builds countries and companies as nodes, with shipments as links.
- **Ripple effect:** `risk_check.py` takes a news sentence such as "Tsunami hits China," marks the matching nodes as directly hit, and spreads lower risk along supply links. Risk halves at each step away from the event.
- **Interactive viewer:** `graph.html` draws the network with D3.js, colors nodes by risk level, and shows shipment details when a node is clicked.
- **Entity extraction:** `ner_entities.py` uses spaCy to find companies and countries in sentences.

### In progress
- Loading the graph into Neo4j (`load_to_neo4j.py`)
- Reading live news automatically
- 30/60/90-day timeline predictions
- Graph Neural Network model

### How to run
Run these from the `riya` folder, with the virtual environment active:
1. `pip install -r requirements.txt`
2. `python supply_graph.py`
3. `python risk_check.py "Tsunami hits China"`
4. `python -m http.server 8000`, then open `http://localhost:8000/graph.html`

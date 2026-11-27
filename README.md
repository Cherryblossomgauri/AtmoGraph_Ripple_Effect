# 🌐 AtmoGraph
### Supply Chain Ripple Effect Predictor

<p align="center">
  <strong>Connecting global supply chains. Predicting the ripple effects of disruption.</strong>
</p>

<p align="center">
  <a href="https://atmograph-ripple-effect.onrender.com"><img src="https://img.shields.io/badge/API-Live-16A34A?style=for-the-badge&logo=fastapi&logoColor=white" /></a>
  <a href="https://atmograph-ripple-effect.onrender.com/docs"><img src="https://img.shields.io/badge/Swagger-Explore-85EA2D?style=for-the-badge&logo=swagger&logoColor=black" /></a>
  <img src="https://img.shields.io/badge/Python-Backend-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Neo4j-Graph%20Database-008CC1?style=for-the-badge&logo=neo4j&logoColor=white" />
</p>

---

## ⚡ The Idea

A port strike in Europe doesn't just affect one port.

It can delay shipping routes, disrupt manufacturers, create shortages, and impact industries thousands of miles away.

**AtmoGraph aims to make these hidden connections visible.**

It is a graph-based supply chain intelligence system designed to analyze disruptions and understand how their effects can propagate across interconnected global supply chains.

## 🧠 How It Works

```mermaid
flowchart LR
    A["📰 News & Data"] --> B["🔍 NLP Engine"]
    B --> C["🕸️ Neo4j Graph"]
    C --> D["🧠 Graph Learning"]
    D --> E["📊 Impact Insights"]

    style A fill:#172554,stroke:#3B82F6,color:#fff
    style B fill:#312E81,stroke:#818CF8,color:#fff
    style C fill:#164E63,stroke:#06B6D4,color:#fff
    style D fill:#4C1D95,stroke:#A78BFA,color:#fff
    style E fill:#14532D,stroke:#22C55E,color:#fff
```

| Layer | Responsibility |
|---|---|
| 📰 Data Ingestion | Collect and process supply chain data |
| 🔍 NLP Engine | Extract and resolve disruption-related entities |
| 🕸️ Knowledge Graph | Represent countries, industries, ports and routes |
| 🧠 Graph Learning | Develop graph-based impact prediction |
| 📊 Visualization | Present disruption insights and propagation |

## ✨ Core Modules

<details>
<summary><strong>🔍 NLP & Entity Resolution</strong></summary>

Processes disruption-related text using spaCy and matches extracted entities against the Neo4j knowledge graph.

- Graph-based entity dictionary
- Country-aware entity resolution
- Port and shipping-route context detection
- Route endpoint validation
- Matched, ambiguous and unmatched results

</details>

<details>
<summary><strong>🕸️ Knowledge Graph</strong></summary>

Represents supply chain dependencies through connected entities.

**Nodes:** Country, Industry, Port, Shipping Route, Disruption.

**Relationships:** `HAS_INDUSTRY`, `SUPPLIES`, `USES_PORT`, `LOCATED_IN`, `FROM_PORT`, `TO_PORT`, `AFFECTS`.

</details>

<details>
<summary><strong>🧠 Graph Learning & Prediction</strong></summary>

Contains graph loading, conversion, feature engineering and prediction-related modules for the graph learning workflow.

</details>

<details>
<summary><strong>⚙️ FastAPI Backend</strong></summary>

Provides API access to backend functionality and NLP analysis.

| Resource | Link |
|---|---|
| Live API | [atmograph-ripple-effect.onrender.com](https://atmograph-ripple-effect.onrender.com) |
| Swagger UI | [Explore API endpoints](https://atmograph-ripple-effect.onrender.com/docs) |
| ReDoc | [API reference](https://atmograph-ripple-effect.onrender.com/redoc) |

</details>

## 🛠️ Tech Stack

<p align="center">
  <img src="https://skillicons.dev/icons?i=python,fastapi,neo4j,pytorch,git" />
</p>

**Core tools:** Python · FastAPI · spaCy · Neo4j · PyTorch · PyTorch Geometric · Pandas · NumPy

## 📁 Project Structure

```text
AtmoGraph/
│
├── backend/          # FastAPI application
├── NLP/              # Entity extraction & resolution
├── src/
│   ├── graph/        # Graph construction & schema
│   ├── ingestion/    # Data ingestion
│   ├── features/     # Graph features
│   ├── prediction/   # Baseline prediction
│   └── simulation/   # Disruption simulation
│
├── gnn/              # Graph learning pipeline
├── scripts/          # Data loading & validation
├── notebooks/        # Experiments
├── tests/            # Tests
├── docs/             # Technical documentation
│
├── database.py
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

**1. Clone the repository**

```bash
git clone <YOUR_REPOSITORY_URL>
cd AtmoGraph
```

**2. Create an environment**

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

**4. Configure environment**

Create `.env` using `.env.example` and configure your Neo4j connection credentials.

**5. Start the backend**

```bash
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to explore the API.

## 🧪 Example: News Analysis

**Input**

```json
{
  "text": "A port strike disrupted operations in India."
}
```

**What the NLP engine does:**

- Identifies the disruption.
- Extracts the country.
- Resolves entities against graph records.
- Checks contextual and relationship evidence.
- Returns matched, ambiguous or unmatched results.

Try the deployed endpoint through [Swagger UI](https://atmograph-ripple-effect.onrender.com/docs).

## 📚 Documentation

| Resource | Description |
|---|---|
| [Architecture](docs/architecture.md) | System design |
| [Graph Schema](docs/graph_schema.md) | Nodes and relationships |
| [Data Dictionary](docs/data_dictionary.md) | Data definitions |
| [GNN Documentation](gnn/README.md) | Graph learning workflow |
| [Notebook Guide](notebooks/README.md) | Experiments and notebooks |

## 🗺️ Roadmap

- [x] Knowledge graph foundation
- [x] Neo4j integration
- [x] FastAPI backend foundation
- [x] NLP entity extraction and resolution
- [x] Country-aware and route-aware matching
- [ ] Expanded real-world news validation
- [ ] Automated disruption event updates
- [ ] GNN training and evaluation
- [ ] Multi-hop ripple effect prediction
- [ ] Interactive impact visualization

## ⚠️ Project Status

AtmoGraph is under active development. Some current graph records, including ports, routes and disruptions, are synthetic development scenarios. NLP matching against these records does not independently verify real-world events.

Graph-based prediction and end-to-end dashboard integration are ongoing development areas.

---

<p align="center">
  <strong>🌍 AtmoGraph</strong><br/>
  <sub>Making global supply chain dependencies easier to understand.</sub>
</p>
<h1 align="center">🌐 ATMOGRAPH</h1>
<h2 align="center">SUPPLY CHAIN RIPPLE EFFECT</h2>

**Visualizing Global Supply Chain Disruptions Through Graph-Based Intelligence.**

AtmoGraph is a graph-based neural network project designed to track and analyze disruptions across global supply chain networks. It explores how a disruption in one node can create ripple effects across interconnected suppliers, manufacturers, and distributors.

###Technology Stack
- **Frontend:** React.js
- **Visualization:** D3.js
- **Backend:** Python
- **Database:** Neo4j
- **Query Language:** Cypher

### Key Objective
To understand supply chain dependencies, identify disruption propagation, and visualize the ripple effect across interconnected networks.

###Vision
Building smarter, more connected, and resilient supply chain networks through graph-based intelligence.

## Project Architecture

```mermaid
flowchart TD
    A["External Data Sources"]

    A --> B["OECD ICIO"]
    A --> C["UN Comtrade"]
    A --> D["World Port Index"]
    A --> E["GDELT News Data"]

    B --> F["Data Ingestion Layer"]
    C --> F
    D --> F
    E --> F

    F --> G["Data Cleaning & Preprocessing"]
    G --> H["Entity & Relationship Extraction"]

    H --> I["Country-Industry Mapping"]
    H --> J["Trade Flow Mapping"]
    H --> K["Port & Route Mapping"]
    H --> L["Disruption Event Extraction"]

    I --> M["Unified Supply Chain Graph"]
    J --> M
    K --> M
    L --> M

    M --> N[("Neo4j Graph Database")]

    N --> O["Graph Feature Engineering"]
    O --> P["Graph Neural Network (GNN)"]

    Q["Disruption Event"] --> R["Event Impact Analysis"]
    R --> P

    P --> S["Multi-hop Ripple Effect Prediction"]
    S --> T["Risk & Delay Estimation"]
    T --> U["Interactive Dashboard"]

    U --> V["Supply Chain Network Visualization"]
    U --> W["Disruption Impact Reports"]
    U --> X["Predicted Risk & Delay Insights"]

    style A fill:#dbeafe,stroke:#2563eb,color:#111827
    style N fill:#dcfce7,stroke:#16a34a,color:#111827
    style P fill:#fef3c7,stroke:#d97706,color:#111827
    style U fill:#ede9fe,stroke:#7c3aed,color:#111827
```

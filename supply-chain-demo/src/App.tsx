
import { useState } from "react";
import ForceGraph2D  from "react-force-graph-2d";
import { type NodeObject } from "force-graph";
import "./App.css";

type CustomNode = NodeObject & {
  name: string;
  group: string | number;
};

const graphData = {
  nodes: [
    { id: "S1", name: "Supplier A", group: "Supplier" },
    { id: "S2", name: "Supplier B", group: "Supplier" },
    { id: "F1", name: "Factory A", group: "Factory" },
    { id: "F2", name: "Factory B", group: "Factory" },
    { id: "P1", name: "Product A", group: "Product" },
    { id: "P2", name: "Product B", group: "Product" },
    { id: "PT1", name: "Port A", group: "Port" },
    { id: "R1", name: "Port Congestion", group: "Risk" }
  ],

  links: [
    { source: "S1", target: "F1", label: "SUPPLIES_TO" },
    { source: "S2", target: "F2", label: "SUPPLIES_TO" },
    { source: "F1", target: "P1", label: "PRODUCES" },
    { source: "F2", target: "P2", label: "PRODUCES" },
    { source: "P1", target: "PT1", label: "SHIPS_THROUGH" },
    { source: "PT1", target: "R1", label: "HAS_RISK" }
  ]
};

function App() {
  const [selectedNode, setSelectedNode] = useState<CustomNode | null>(null);

  const stats = [
    { title: "Suppliers", value: 120, color: "#3B82F6" },
    { title: "Factories", value: 45, color: "#16A34A" },
    { title: "Ports", value: 18, color: "#F59E0B" },
    { title: "Risks", value: 12, color: "#EF4444" }
  ];

  return (
    <div className="dashboard">

      {/* Sidebar */}
      <aside className="sidebar">
        <h2>SupplyChain</h2>
        <p className="menu-title">MAIN MENU</p>
        <div className="menu active">Dashboard</div>
        <div className="menu">Network Graph</div>
        <div className="menu">Suppliers</div>
        <div className="menu">Factories</div>
        <div className="menu">Ports</div>
        <div className="menu">Risk Analysis</div>
      </aside>

      {/* Main content */}
      <main className="main-content">

        <header className="topbar">
          <h2>Global Supply Chain Dashboard</h2>
          <span className="demo-label">DEMO VERSION</span>
        </header>

        <section className="welcome">
          <h1>Network Overview</h1>
          <p>
            Monitor your global supply chain entities
            and relationships.
          </p>
        </section>

        {/* Statistics */}
        <section className="stats">
          {stats.map((item) => (
            <div className="stat-card" key={item.title}>
              <h3>{item.title}</h3>
              <h1 style={{ color: item.color }}>
                {item.value}
              </h1>
            </div>
          ))}
        </section>

        {/* Graph */}
        <section className="graph-section">
          <h2>Supply Chain Network Graph</h2>

          <div className="graph-container">
            <ForceGraph2D
              graphData={graphData}
              width={850}
              height={480}
              backgroundColor="#FFFFFF"
              nodeAutoColorBy="group"
              nodeLabel={(node: NodeObject) => {
                const n = node as CustomNode;
                return `${n.name} (${n.group})`
              }}
              linkLabel="label"
              linkDirectionalArrowLength={5}
              linkDirectionalArrowRelPos={1}
              onNodeClick={(node) =>
                setSelectedNode(node as CustomNode)}
              
            />
          </div>
        </section>

        {/* Selected node */}
        {selectedNode && (
          <section className="details">
            <h3>Selected Entity</h3>
            <p>Name: {selectedNode.name}</p>
            <p>Type: {selectedNode.group}</p>
            <button onClick={() => setSelectedNode(null)}>
              Close
            </button>
          </section>
        )}

        {/* Risk overview */}
        <section className="risk-section">
          <h2>Risk Overview</h2>
          <div className="risk-item">
            <span>Port Congestion</span>
            <strong className="high">HIGH</strong>
          </div>
          <div className="risk-item">
            <span>Weather Disruption</span>
            <strong className="medium">MEDIUM</strong>
          </div>
          <div className="risk-item">
            <span>Supplier Delay</span>
            <strong className="low">LOW</strong>
          </div>
        </section>

      </main>
    </div>
  );
}

export default App;

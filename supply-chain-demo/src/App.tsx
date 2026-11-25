
import { useState, useEffect } from "react";
import ForceGraph2D from "react-force-graph-2d";
import "./App.css";
import { getGraphData } from "./api";

interface GraphNode {
  id: string;
  name: string;
  group: string;
  [key: string]: any;
}

interface GraphLink {
  source: string;
  target: string;
  label: string;
  [key: string]: any;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

function getId(value: any): string {
  if (value === null || value === undefined) return "";

  if (typeof value === "object") {
    return String(
      value.id ??
      value.elementId ??
      value.identity ??
      ""
    );
  }

  return String(value);
}

function normalizeGraphData(data: any): GraphData {
  const response = data?.data ?? data?.graph ?? data;

  const rawNodes = response?.nodes;
  const rawLinks =
    response?.links ??
    response?.relationships ??
    response?.edges ??
    response?.rels ??
    [];

  if (!Array.isArray(rawNodes)) {
    throw new Error("Invalid nodes array in API response.");
  }

  if (!Array.isArray(rawLinks)) {
    throw new Error("Invalid relationships array in API response.");
  }

  const nodes: GraphNode[] = rawNodes.map((node: any) => {
    const properties = node.properties ?? {};
    const labels = node.labels ?? [];

    const id = getId(
      node.id ??
      node.elementId ??
      node.identity ??
      properties.id
    );

    return {
      ...properties,
      ...node,
      id,
      name:
        node.name ??
        node.title ??
        properties.name ??
        properties.title ??
        id,
      group:
        node.group ??
        node.type ??
        labels[0] ??
        "Other"
    };
  });

  const links: GraphLink[] = rawLinks.map((link: any) => {
    const properties = link.properties ?? {};

    return {
      ...properties,
      ...link,
      source: getId(
        link.source ??
        link.startNodeElementId ??
        link.startNode ??
        link.from ??
        link.start
      ),
      target: getId(
        link.target ??
        link.endNodeElementId ??
        link.endNode ??
        link.to ??
        link.end
      ),
      label:
        link.label ??
        link.type ??
        link.relationshipType ??
        "CONNECTED"
    };
  }).filter(
    link => link.source !== "" && link.target !== ""
  );

  return { nodes, links };
}

function App() {
  const [graphData, setGraphData] = useState<GraphData>({
    nodes: [],
    links: []
  });

  const [selectedNode, setSelectedNode] =
    useState<GraphNode | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const fetchGraphData = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await getGraphData();
        console.log("API Response:", response);

        const normalizedData =
          normalizeGraphData(response);

        if (isMounted) {
          setGraphData(normalizedData);
        }

      } catch (err) {
        console.error("Graph fetching error:", err);

        if (isMounted) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to fetch graph data."
          );
        }

      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchGraphData();

    return () => {
      isMounted = false;
    };
  }, []);

  // Called whenever a graph node is clicked
  const handleNodeClick = (node: any) => {
    setSelectedNode(node as GraphNode);
    console.log("Selected node:", node);
  };

  // Close details when clicking the graph background
  const handleBackgroundClick = () => {
    setSelectedNode(null);
  };

  const formatValue = (value: any) => {
    if (value === null || value === undefined) {
      return "N/A";
    }

    if (typeof value === "object") {
      return JSON.stringify(value);
    }

    return String(value);
  };

  return (
    <div className="app-container">

      <header className="dashboard-header">
        <h1>Supply Chain Dashboard</h1>
        <p>Global Supply Chain Network Monitoring</p>
      </header>

      <div className="dashboard-layout">

        <main className="graph-section">

          <h2>Supply Chain Network Graph</h2>

          <div className="graph-instructions">
            Scroll to zoom | Drag background to pan |
            Click a node to view details
          </div>

          {loading && (
            <p>Loading graph from Neo4j...</p>
          )}

          {error && (
            <p className="error-message">{error}</p>
          )}

          {!loading && !error &&
            graphData.nodes.length === 0 && (
              <p>No graph nodes were returned.</p>
          )}

          {!loading && !error &&
            graphData.nodes.length > 0 && (

            <div className="graph-container">

              <ForceGraph2D
                graphData={graphData}
                width={850}
                height={550}
                backgroundColor="#FFFFFF"

                // Zoom and pan
                enableZoomInteraction={true}
                enablePanInteraction={true}
                minZoom={0.3}
                maxZoom={8}

                // Node appearance
                nodeAutoColorBy="group"
                nodeLabel="name"

                // Relationship appearance
                linkLabel="label"
                linkDirectionalArrowLength={5}
                linkDirectionalArrowRelPos={1}

                // Click interaction
                onNodeClick={handleNodeClick}
                onBackgroundClick={handleBackgroundClick}
              />

            </div>
          )}

        </main>

        <aside className="details-panel">

          <h2>Entity Details</h2>

          {!selectedNode && (
            <div className="empty-details">
              <p>Select a node in the graph to view its details.</p>
            </div>
          )}

          {selectedNode && (
            <div className="node-details">

              <div className="node-heading">
                <h3>{selectedNode.name}</h3>

                <span className="node-type">
                  {selectedNode.group}
                </span>
              </div>

              <div className="detail-list">

                {Object.entries(selectedNode)
                  .filter(([key, value]) =>
                    ![
                      "__indexColor",
                      "x",
                      "y",
                      "vx",
                      "vy",
                      "fx",
                      "fy",
                      "index"
                    ].includes(key) &&
                    value !== undefined &&
                    typeof value !== "function"
                  )
                  .map(([key, value]) => (
                    <div className="detail-item" key={key}>
                      <span className="detail-label">
                        {key}
                      </span>

                      <span className="detail-value">
                        {formatValue(value)}
                      </span>
                    </div>
                  ))}

              </div>

              <button
                className="close-details"
                onClick={() => setSelectedNode(null)}
              >
                Close Details
              </button>

            </div>
          )}

        </aside>

      </div>

    </div>
  );
}

export default App;

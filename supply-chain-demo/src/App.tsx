
import { useState, useEffect } from "react";
import ForceGraph2D from "react-force-graph-2d";
import "./App.css";
import { getGraphData } from "./api";

interface GraphNode {
  id: string;
  name: string;
  group: string;
  properties?: Record<string, any>;
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

    const name =
      node.name ??
      node.title ??
      properties.name ??
      properties.industry_name ??
      properties.supplier_name ??
      properties.factory_name ??
      properties.port_name ??
      properties.product_name ??
      properties.risk_name ??
      id;

    return {
      ...properties,
      ...node,
      id,
      name,
      group:
        node.group ??
        node.type ??
        labels[0] ??
        "Other",
      properties
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

// Convert field names into readable labels
function formatLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, char => char.toUpperCase());
}

// Convert property values into readable text
function formatValue(value: any): string {
  if (value === null || value === undefined) {
    return "N/A";
  }

  if (Array.isArray(value)) {
    return value.map(item => formatValue(item)).join(", ");
  }

  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }

  return String(value);
}

// Extract business properties and hide technical metadata
function getDisplayProperties(node: GraphNode) {
  const technicalFields = [
    "id",
    "elementId",
    "identity",
    "labels",
    "label",
    "properties",
    "name",
    "title",
    "group",
    "type",
    "color",
    "__indexColor",
    "x",
    "y",
    "vx",
    "vy",
    "fx",
    "fy",
    "index"
  ];

  const combinedProperties = {
    ...(node.properties ?? {}),
    ...node
  };

  return Object.entries(combinedProperties).filter(
    ([key, value]) =>
      !technicalFields.includes(key) &&
      value !== undefined &&
      value !== null &&
      typeof value !== "function"
  );
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

  const handleNodeClick = (node: any) => {
    setSelectedNode(node as GraphNode);
    console.log("Selected node:", node);
  };

  const handleBackgroundClick = () => {
    setSelectedNode(null);
  };

  const displayProperties = selectedNode
    ? getDisplayProperties(selectedNode)
    : [];

  return (
    <div className="app-container">

      <header className="dashboard-header">
        <div>
          <h1>Supply Chain Dashboard</h1>
          <p>Global Supply Chain Network Monitoring</p>
        </div>

        <div className="connection-status">
          <span className="status-dot"></span>
          Neo4j Graph Connected
        </div>
      </header>

      <div className="dashboard-layout">

        <main className="graph-section">

          <div className="section-heading">
            <div>
              <h2>Supply Chain Network Graph</h2>
              <p>Explore connected supply chain entities</p>
            </div>

            <div className="graph-counts">
              <span>{graphData.nodes.length} Nodes</span>
              <span>{graphData.links.length} Relationships</span>
            </div>
          </div>

          <div className="graph-instructions">
            <span>Scroll to zoom</span>
            <span>Drag background to pan</span>
            <span>Click a node for details</span>
          </div>

          {loading && (
            <p className="graph-message">
              Loading graph from Neo4j...
            </p>
          )}

          {error && (
            <p className="error-message">{error}</p>
          )}

          {!loading && !error &&
            graphData.nodes.length === 0 && (
              <p className="graph-message">
                No graph nodes were returned.
              </p>
          )}

          {!loading && !error &&
            graphData.nodes.length > 0 && (

            <div className="graph-container">

              <ForceGraph2D
                graphData={graphData}
                width={850}
                height={550}
                backgroundColor="#FFFFFF"

                enableZoomInteraction={true}
                enablePanInteraction={true}
                minZoom={0.3}
                maxZoom={8}

                nodeAutoColorBy="group"
                nodeLabel="name"

                linkLabel="label"
                linkDirectionalArrowLength={5}
                linkDirectionalArrowRelPos={1}

                onNodeClick={handleNodeClick}
                onBackgroundClick={handleBackgroundClick}
              />

            </div>
          )}

          <div className="graph-footer">
            <span>Data source: FastAPI / Neo4j</span>
            <span>Interactive network visualization</span>
          </div>

        </main>

        <aside className="details-panel">

          <div className="details-header">
            <div>
              <h2>Entity Details</h2>
              <p>Selected network entity</p>
            </div>

            {selectedNode && (
              <button
                className="close-icon"
                onClick={() => setSelectedNode(null)}
                aria-label="Close entity details"
              >
                ×
              </button>
            )}
          </div>

          {!selectedNode && (
            <div className="empty-details">
              <div className="empty-icon">◉</div>
              <h3>No Entity Selected</h3>
              <p>
                Select a supplier, factory, port,
                product or risk node in the graph
                to view its information.
              </p>
            </div>
          )}

          {selectedNode && (
            <div className="entity-profile">

              <div className="entity-title-card">

                <div className="entity-avatar">
                  ◈
                </div>

                <h3>{selectedNode.name}</h3>

                <span className="entity-badge">
                  {selectedNode.group}
                </span>

              </div>

              <div className="details-section">

                <h4>Entity Information</h4>

                <div className="details-grid">

                  {displayProperties.length > 0 ? (
                    displayProperties.map(([key, value]) => (
                      <div className="detail-card" key={key}>

                        <span className="detail-label">
                          {formatLabel(key)}
                        </span>

                        <span className="detail-value">
                          {formatValue(value)}
                        </span>

                      </div>
                    ))
                  ) : (
                    <p className="no-properties">
                      No additional properties available.
                    </p>
                  )}

                </div>

              </div>

              <div className="details-section">

                <h4>Entity Identifier</h4>

                <div className="identifier-card">
                  <span className="detail-label">
                    Node ID
                  </span>

                  <strong>{selectedNode.id}</strong>
                </div>

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

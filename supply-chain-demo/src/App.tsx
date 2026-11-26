import { useEffect, useRef, useState } from "react";
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
    const labels = Array.isArray(node.labels) ? node.labels : [];

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
      name: String(name || id || "Unnamed entity"),
      group: String(
        node.group ??
          node.type ??
          labels[0] ??
          "Other"
      ),
      properties,
    };
  });

  const links: GraphLink[] = rawLinks
    .map((link: any) => {
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
        label: String(
          link.label ??
            link.type ??
            link.relationshipType ??
            "CONNECTED"
        ),
      };
    })
    .filter(
      (link: GraphLink) =>
        link.source !== "" && link.target !== ""
    );

  return { nodes, links };
}

function formatLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatValue(value: any): string {
  if (value === null || value === undefined) return "N/A";

  if (Array.isArray(value)) {
    return value.map((item) => formatValue(item)).join(", ");
  }

  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }

  return String(value);
}

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
    "index",
    "source",
    "target",
  ];

  const combinedProperties = {
    ...(node.properties ?? {}),
    ...node,
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
  const graphRef = useRef<any>(null);
  const graphContainerRef = useRef<HTMLDivElement>(null);

  const [graphWidth, setGraphWidth] = useState(1000);
  const [graphData, setGraphData] = useState<GraphData>({
    nodes: [],
    links: [],
  });
  const [selectedNode, setSelectedNode] =
    useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Measure the available graph area so the graph uses the full page width.
  useEffect(() => {
    const container = graphContainerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width;
      if (width) setGraphWidth(Math.floor(width));
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Fetch the graph from your existing FastAPI endpoint.
  useEffect(() => {
    let isMounted = true;

    const fetchGraphData = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await getGraphData();
        console.log("API Response:", response);

        const normalizedData = normalizeGraphData(response);

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
        if (isMounted) setLoading(false);
      }
    };

    fetchGraphData();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleNodeClick = (node: any) => {
    setSelectedNode(node as GraphNode);
  };

  const handleBackgroundClick = () => {
    setSelectedNode(null);
  };

  const zoomIn = () => {
    const currentZoom = graphRef.current?.zoom();
    if (typeof currentZoom === "number") {
      graphRef.current.zoom(Math.min(8, currentZoom * 1.5), 250);
    }
  };

  const zoomOut = () => {
    const currentZoom = graphRef.current?.zoom();
    if (typeof currentZoom === "number") {
      graphRef.current.zoom(Math.max(0.3, currentZoom / 1.5), 250);
    }
  };

  const fitGraph = () => {
    graphRef.current?.zoomToFit(400, 60);
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

        <div className={`connection-status ${error ? "connection-error" : ""}`}>
          <span className="status-dot" />
          {loading
            ? "Connecting to graph..."
            : error
              ? "Graph connection failed"
              : "Graph data loaded"}
        </div>
      </header>

      <main className="network-page">
        <section className="network-header">
          <div>
            <h2>Supply Chain Network</h2>
            <p>
              Explore your Neo4j entities and their relationships.
              Select a node to view its details.
            </p>
          </div>

          <div className="network-actions">
            <div className="graph-counts">
              <span>{graphData.nodes.length} Nodes</span>
              <span>{graphData.links.length} Relationships</span>
            </div>

            <button
              className="fit-graph-button"
              onClick={fitGraph}
              disabled={graphData.nodes.length === 0}
            >
              Fit Graph
            </button>
          </div>
        </section>

        <section className="graph-card">
          <div className="graph-toolbar">
            <div className="graph-instructions">
              <span>Scroll to zoom</span>
              <span>Drag background to pan</span>
              <span>Click a node for details</span>
            </div>

            <div className="graph-legend">
              <span><i className="legend-dot supplier-dot" /> Entities</span>
              <span><i className="legend-dot risk-dot" /> Risks</span>
              <span><i className="legend-dot route-dot" /> Routes</span>
            </div>
          </div>

          {loading && (
            <div className="graph-message">
              Loading graph from Neo4j...
            </div>
          )}

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {!loading && !error && graphData.nodes.length === 0 && (
            <div className="graph-message">
              No graph nodes were returned by the API.
            </div>
          )}

          {!loading && !error && graphData.nodes.length > 0 && (
            <div className="graph-container" ref={graphContainerRef}>
              <ForceGraph2D
                ref={graphRef}
                graphData={graphData}
                width={Math.max(300, graphWidth)}
                height={680}
                backgroundColor="#ffffff"
                enableZoomInteraction={true}
                enablePanInteraction={true}
                minZoom={0.3}
                maxZoom={8}
                nodeAutoColorBy="group"
                nodeLabel="name"
                nodeCanvasObjectMode={() => "replace"}
                nodeCanvasObject={(node: any, ctx, globalScale) => {
                  const x = node.x ?? 0;
                  const y = node.y ?? 0;
                  const radius = 5;

                  // Draw the colored node.
                  ctx.beginPath();
                  ctx.arc(x, y, radius, 0, 2 * Math.PI);
                  ctx.fillStyle = node.color || "#287db5";
                  ctx.fill();

                  // Show permanent labels only when zoomed in.
                  // Hovering still shows the nodeLabel tooltip at any zoom.
                  if (globalScale >= 1.35) {
                    const label = String(node.name || node.id || "");
                    const fontSize = Math.max(3, 11 / globalScale);

                    ctx.font = `600 ${fontSize}px Arial`;
                    ctx.textAlign = "left";
                    ctx.textBaseline = "middle";
                    ctx.fillStyle = "#172033";
                    ctx.fillText(label, x + radius + 4, y);
                  }
                }}
                linkLabel="label"
                linkDirectionalArrowLength={4}
                linkDirectionalArrowRelPos={1}
                onNodeClick={handleNodeClick}
                onBackgroundClick={handleBackgroundClick}
              />

              <div className="zoom-controls">
                <button onClick={zoomIn} title="Zoom in" aria-label="Zoom in">
                  +
                </button>
                <button onClick={zoomOut} title="Zoom out" aria-label="Zoom out">
                  −
                </button>
                <button onClick={fitGraph} title="Fit graph">
                  Fit
                </button>
              </div>
            </div>
          )}

          <footer className="graph-footer">
            <span>Data source: FastAPI / Neo4j</span>
            <span>Interactive network visualization</span>
          </footer>
        </section>
      </main>

      {/* The details drawer overlays the graph; it does not reduce graph width. */}
      {selectedNode && (
        <div className="details-overlay">
          <aside
            className="details-panel"
            aria-label="Selected entity details"
          >
            <div className="details-header">
              <div>
                <h2>Entity Details</h2>
                <p>Selected network entity</p>
              </div>

              <button
                className="close-icon"
                onClick={() => setSelectedNode(null)}
                aria-label="Close entity details"
                title="Close"
              >
                ×
              </button>
            </div>

            <div className="entity-title-card">
              <div className="entity-avatar">◈</div>
              <h3>{selectedNode.name || selectedNode.id}</h3>
              <span className="entity-badge">
                {selectedNode.group || "Entity"}
              </span>
            </div>

            <section className="details-section">
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
                    No additional properties are available for this entity.
                  </p>
                )}
              </div>
            </section>

            <section className="details-section">
              <h4>Entity Identifier</h4>
              <div className="identifier-card">
                <span className="detail-label">Node ID</span>
                <strong>{selectedNode.id}</strong>
              </div>
            </section>

            <button
              className="close-details-button"
              onClick={() => setSelectedNode(null)}
            >
              Close Details
            </button>
          </aside>
        </div>
      )}
    </div>
  );
}

export default App;

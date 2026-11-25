
import { useState, useEffect } from "react";
import ForceGraph2D from "react-force-graph-2d";
import "./App.css";
import { getGraphData } from "./api";

// Graph node structure
interface GraphNode {
  id: string;
  name: string;
  group: string;
  [key: string]: any;
}

// Graph relationship structure
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

// Get an ID from a string, number, or Neo4j-style object
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

// Convert the backend response into ForceGraph format
function normalizeGraphData(data: any): GraphData {
  // Handle common response wrappers
  const response = data?.data ?? data?.graph ?? data;

  if (!response || typeof response !== "object") {
    throw new Error("Invalid graph response from FastAPI.");
  }

  const rawNodes = response.nodes;

  const rawLinks =
    response.links ??
    response.relationships ??
    response.edges ??
    response.rels ??
    [];

  if (!Array.isArray(rawNodes)) {
    throw new Error(
      "The API response does not contain a nodes array."
    );
  }

  if (!Array.isArray(rawLinks)) {
    throw new Error(
      "The API relationships are not in a valid array format."
    );
  }

  const nodes: GraphNode[] = rawNodes.map((node: any) => {
    const properties = node.properties ?? {};

    const id = getId(
      node.id ??
      node.elementId ??
      node.identity ??
      properties.id
    );

    const labels = node.labels ?? [];

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
    (link: GraphLink) => link.source !== "" && link.target !== ""
  );

  return { nodes, links };
}

function App() {
  const [graphData, setGraphData] = useState<GraphData>({
    nodes: [],
    links: []
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const fetchGraphData = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await getGraphData();

        console.log("Complete API Response:", response);
        console.log("Response keys:", Object.keys(response ?? {}));

        const normalizedData = normalizeGraphData(response);

        console.log("Normalized Nodes:", normalizedData.nodes);
        console.log("Normalized Links:", normalizedData.links);

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

  return (
    <div className="app-container">

      <h1>Supply Chain Dashboard</h1>

      <section className="graph-section">

        <h2>Supply Chain Network Graph</h2>

        {loading && (
          <p>Loading graph from Neo4j...</p>
        )}

        {error && (
          <p className="error-message">{error}</p>
        )}

        {!loading && !error && graphData.nodes.length === 0 && (
          <p>No nodes were returned by the API.</p>
        )}

        {!loading && !error && graphData.nodes.length > 0 && (
          <>
            <p>
              Nodes: {graphData.nodes.length} |
              Relationships: {graphData.links.length}
            </p>

            <div className="graph-container">

              <ForceGraph2D
                graphData={graphData}
                width={850}
                height={480}
                backgroundColor="#FFFFFF"
                nodeAutoColorBy="group"
                nodeLabel="name"
                linkLabel="label"
                linkDirectionalArrowLength={5}
                linkDirectionalArrowRelPos={1}
              />

            </div>
          </>
        )}

      </section>

    </div>
  );
}

export default App;

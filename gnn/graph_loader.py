
import torch
from pathlib import Path



def load_graph(graph_path):
    graph_path = Path(graph_path)

    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")

    artifact = torch.load(
        graph_path,
        map_location="cpu",
        weights_only=False
    )

    if isinstance(artifact, dict) and "graph" in artifact:
        graph = artifact["graph"]
        metadata = artifact.get("metadata", {})
    else:
        graph = artifact
        metadata = {}

    print("\nGraph loaded successfully!")
    print("Loaded object type:", type(graph).__name__)

    return graph, metadata


def analyze_graph(graph):
    """
    Display basic graph statistics.
    """

    print("\n========== GRAPH SUMMARY ==========")

    # Node statistics
    print("\n--- Nodes ---")

    if hasattr(graph, "num_nodes"):
        print("Total Nodes:", graph.num_nodes)

    # Edge statistics
    print("\n--- Edges ---")

    if hasattr(graph, "edge_index"):
        print("Total Edges:", graph.edge_index.shape[1])

    # Feature statistics
    print("\n--- Node Features ---")

    if hasattr(graph, "x") and graph.x is not None:
        print("Feature Shape:", tuple(graph.x.shape))
        print("Number of Features:", graph.x.shape[1])

        print(
            "NaN Values:",
            torch.isnan(graph.x).sum().item()
        )

        print(
            "Infinite Values:",
            torch.isinf(graph.x).sum().item()
        )

    # Relationship statistics
    print("\n--- Relationship Types ---")

    if hasattr(graph, "edge_type") and graph.edge_type is not None:

        relation_ids, counts = torch.unique(
            graph.edge_type,
            return_counts=True
        )

        for relation, count in zip(relation_ids, counts):
            print(
                f"Relation ID {relation.item()}: "
                f"{count.item()} edges"
            )

        print("Total Relation Types:", len(relation_ids))

    print("\n===================================")


if __name__ == "__main__":

    # Change this path according to your actual file location
    GRAPH_PATH = Path(__file__).resolve().parent / "atmograph_data.pt"

graph, metadata = load_graph(GRAPH_PATH)
analyze_graph(graph)

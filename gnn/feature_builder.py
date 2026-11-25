
import torch
from pathlib import Path


def load_graph_artifact(file_path):
    """Load the converted graph and its metadata."""

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    artifact = torch.load(
        file_path,
        map_location="cpu",
        weights_only=False
    )

    graph = artifact["graph"]
    metadata = artifact["metadata"]

    return graph, metadata


def analyze_features(graph, metadata):
    """Calculate statistics for numerical node features."""

    x = graph.x.float()

    numeric_features = metadata["numeric_features"]
    node_types = metadata["node_types"]

    numeric_count = len(numeric_features)
    type_count = len(node_types)

    if x.shape[1] != numeric_count + type_count:
        raise ValueError("Feature columns do not match metadata.")

    if not torch.isfinite(x).all():
        raise ValueError("NaN or infinite values detected.")

    numeric_x = x[:, :numeric_count]

    print("\n========== FEATURE ANALYSIS ==========")
    print("Feature matrix:", tuple(x.shape))

    print("\n--- Numerical Feature Statistics ---")

    mean = numeric_x.mean(dim=0)
    median = numeric_x.median(dim=0).values
    std = numeric_x.std(dim=0, unbiased=False)
    minimum = numeric_x.min(dim=0).values
    maximum = numeric_x.max(dim=0).values

    constant_features = []

    for i, name in enumerate(numeric_features):
        print(f"\n{name}")
        print(f"  Min:    {minimum[i].item():.4f}")
        print(f"  Max:    {maximum[i].item():.4f}")
        print(f"  Mean:   {mean[i].item():.4f}")
        print(f"  Median: {median[i].item():.4f}")
        print(f"  Std:    {std[i].item():.4f}")

        if std[i].item() == 0:
            constant_features.append(name)

    print("\n--- Data Quality ---")
    print("NaN values:", torch.isnan(x).sum().item())
    print("Infinite values:", torch.isinf(x).sum().item())
    print("Constant features:", constant_features)

    print("\n--- Node Type Distribution ---")

    type_x = x[:, numeric_count:]

    for i, node_type in enumerate(node_types):
        print(
            f"{node_type}: "
            f"{int(type_x[:, i].sum().item())} nodes"
        )

    print("\n======================================")

    return mean, std


def normalize_features(graph, metadata, mean, std):
    """Normalize numerical features only."""

    prepared_graph = graph.clone()
    x = prepared_graph.x.float().clone()

    numeric_count = len(metadata["numeric_features"])

    numeric_x = x[:, :numeric_count]

    safe_std = torch.where(
        std == 0,
        torch.ones_like(std),
        std
    )

    x[:, :numeric_count] = (numeric_x - mean) / safe_std

    # Preserve node-type indicators without normalization.
    prepared_graph.x = x

    return prepared_graph


if __name__ == "__main__":

    BASE_DIR = Path(__file__).resolve().parent

    INPUT_PATH = BASE_DIR / "atmograph_data.pt"
    OUTPUT_PATH = BASE_DIR / "atmograph_features.pt"

    graph, metadata = load_graph_artifact(INPUT_PATH)

    mean, std = analyze_features(graph, metadata)

    prepared_graph = normalize_features(
        graph,
        metadata,
        mean,
        std
    )

    normalization_stats = {
        "mean": mean,
        "std": std,
        "numeric_features": metadata["numeric_features"]
    }

    torch.save(
        {
            "graph": prepared_graph,
            "metadata": metadata,
            "normalization_stats": normalization_stats
        },
        OUTPUT_PATH
    )

    print("\nPrepared graph saved successfully!")
    print("Output:", OUTPUT_PATH)

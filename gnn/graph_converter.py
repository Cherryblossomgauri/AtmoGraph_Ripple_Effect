
import os
from collections import defaultdict

import torch
from dotenv import load_dotenv
from neo4j import GraphDatabase
from torch_geometric.data import Data

load_dotenv()


def get_graph_from_neo4j():
    """Fetch nodes and relationships from Neo4j."""

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not all([uri, username, password]):
        raise ValueError("Neo4j credentials are missing from .env")

    driver = GraphDatabase.driver(
        uri, auth=(username, password)
    )

    try:
        with driver.session(database=database) as session:
            nodes = session.run("""
                MATCH (n)
                RETURN elementId(n) AS id,
                       labels(n) AS labels,
                       properties(n) AS props
            """).data()

            relationships = session.run("""
                MATCH (source)-[r]->(target)
                RETURN elementId(source) AS source,
                       elementId(target) AS target,
                       type(r) AS relation
            """).data()

    finally:
        driver.close()

    return nodes, relationships


def convert_to_pyg(nodes, relationships):
    """Convert Neo4j graph into PyTorch Geometric Data."""

    node_ids = [node["id"] for node in nodes]
    node_to_index = {
        node_id: index
        for index, node_id in enumerate(node_ids)
    }

    # Collect node types and numerical properties.
    node_types = sorted({
        label
        for node in nodes
        for label in node["labels"]
    })

    numeric_features = sorted({
        key
        for node in nodes
        for key, value in node["props"].items()
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
    })

    # Create numerical feature vectors.
    features = []

    for node in nodes:
        props = node["props"]

        numeric_values = [
            float(props.get(key, 0))
            for key in numeric_features
        ]

        type_values = [
            float(label in node["labels"])
            for label in node_types
        ]

        features.append(numeric_values + type_values)

    x = torch.tensor(features, dtype=torch.float)

    # Convert relationships into edge indices.
    relation_types = sorted({
        rel["relation"] for rel in relationships
    })

    relation_to_index = {
        relation: index
        for index, relation in enumerate(relation_types)
    }

    edges = []
    edge_types = []

    for rel in relationships:
        source = node_to_index[rel["source"]]
        target = node_to_index[rel["target"]]

        edges.append([source, target])
        edge_types.append(
            relation_to_index[rel["relation"]]
        )

    if edges:
        edge_index = torch.tensor(
            edges, dtype=torch.long
        ).t().contiguous()
    else:
        edge_index = torch.empty((2, 0), dtype=torch.long)

    edge_type = torch.tensor(
        edge_types, dtype=torch.long
    )

    graph = Data(
        x=x,
        edge_index=edge_index,
        edge_type=edge_type,
        num_nodes=len(nodes)
    )

    metadata = {
        "node_ids": node_ids,
        "node_types": node_types,
        "numeric_features": numeric_features,
        "relation_types": relation_types
    }

    return graph, metadata


def main():
    nodes, relationships = get_graph_from_neo4j()

    graph, metadata = convert_to_pyg(
        nodes, relationships
    )

    print("\n--- AtmoGraph GNN Dataset ---")
    print("Total nodes:", graph.num_nodes)
    print("Total relationships:", graph.edge_index.shape[1])
    print("Feature matrix:", graph.x.shape)
    print("Edge index:", graph.edge_index.shape)
    print("Node types:", metadata["node_types"])
    print("Relationship types:", metadata["relation_types"])

    torch.save(
        {
            "graph": graph,
            "metadata": metadata
        },
        "gnn/atmograph_data.pt"
    )

    print("\nGraph successfully converted and saved!")


if __name__ == "__main__":
    main()

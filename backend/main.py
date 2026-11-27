import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j.time import Date, DateTime, Time, Duration

from database import DATABASE as NEO4J_DATABASE
from database import close_connection, get_database_session
from NLP.router import router as nlp_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run application shutdown tasks."""
    yield
    close_connection()


app = FastAPI(
    title="AtmoGraph API",
    description="Supply Chain Ripple Effect Predictor",
    version="1.2.0",
    lifespan=lifespan,
)
app.include_router(nlp_router)


# During local development, React usually runs on localhost:5173 (Vite).
# Add deployed frontend origins to FRONTEND_ORIGINS, separated by commas.
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Properties that can uniquely identify a node in the AtmoGraph dataset.
BUSINESS_ID_FIELDS = (
    "country_id",
    "industry_id",
    "port_id",
    "route_id",
    "disruption_id",
)


def serialize_value(value: Any) -> Any:
    """Convert Neo4j/Python values into JSON-compatible values."""
    if isinstance(value, (Date, DateTime, Time)):
        return value.iso_format()
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Duration):
        return str(value)
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]
    return value


def make_node_id(labels: list[str], properties: dict, element_id: str) -> str:
    """Prefer a business ID; use Neo4j element ID only as a fallback."""
    label = sorted(labels)[0] if labels else "Node"

    for field in BUSINESS_ID_FIELDS:
        value = properties.get(field)
        if value is not None:
            return f"{label}:{value}"

    return f"neo4j:{element_id}"


def readable_node_name(labels: list[str], properties: dict) -> str:
    """Choose a useful display name for graph visualizations."""
    name_fields = (
        "country_name",
        "industry_name",
        "port_name",
        "event_type",
        "name",
        "route_id",
        "disruption_id",
    )

    for field in name_fields:
        if properties.get(field) is not None:
            return str(properties[field])

    return labels[0] if labels else "Unnamed node"


@app.get("/")
def home():
    return {
        "message": "Welcome to AtmoGraph API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
@app.get("/graph/health")
def health():
    """Check whether the API can reach the configured Neo4j database."""
    try:
        with get_database_session() as session:
            session.run("RETURN 1 AS result").single()

        return {
            "status": "healthy",
            "database": NEO4J_DATABASE,
            "connected": True,
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": NEO4J_DATABASE,
                "connected": False,
                "message": "Neo4j connection or query failed",
            },
        )


@app.get("/graph/stats")
def graph_stats():
    """Return total nodes, relationships, and counts grouped by type."""
    try:
        with get_database_session() as session:
            total_nodes = session.run(
                "MATCH (n) RETURN count(n) AS total"
            ).single()["total"]

            total_relationships = session.run(
                "MATCH ()-[r]->() RETURN count(r) AS total"
            ).single()["total"]

            node_records = session.run(
                """
                MATCH (n)
                UNWIND labels(n) AS label
                RETURN label, count(*) AS total
                ORDER BY label
                """
            )
            node_counts = {
                record["label"]: record["total"] for record in node_records
            }

            relationship_records = session.run(
                """
                MATCH ()-[r]->()
                RETURN type(r) AS relationship, count(r) AS total
                ORDER BY relationship
                """
            )
            relationship_counts = {
                record["relationship"]: record["total"]
                for record in relationship_records
            }

        return {
            "database": NEO4J_DATABASE,
            "total_nodes": total_nodes,
            "total_relationships": total_relationships,
            "node_counts": node_counts,
            "relationship_counts": relationship_counts,
        }
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not calculate graph statistics",
        )


@app.get("/graph/schema")
def graph_schema():
    """Return the node labels and relationship types present in Neo4j."""
    try:
        with get_database_session() as session:
            label_records = session.run("CALL db.labels()")
            labels = [record["label"] for record in label_records]

            relationship_records = session.run("CALL db.relationshipTypes()")
            relationship_types = [
                record["relationshipType"] for record in relationship_records
            ]

        return {
            "database": NEO4J_DATABASE,
            "node_labels": labels,
            "relationship_types": relationship_types,
        }
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not inspect graph schema",
        )


@app.get("/student")
def student():
    # Kept from your original file so the test endpoint still works.
    return {"name": "Mayank", "role": "Developer", "project": "AtmoGraph"}


@app.get("/graph")
def get_graph():
    """Return graph nodes, relationships, and summary counts for the frontend."""
    try:
        with get_database_session() as session:
            # Query 1: fetch every node, including nodes with no relationships.
            node_records = session.run(
                """
                MATCH (n)
                RETURN elementId(n) AS element_id,
                       labels(n) AS labels,
                       properties(n) AS properties
                """
            )

            nodes_by_element_id = {}
            nodes = []
            node_type_counts = {}

            for record in node_records:
                element_id = record["element_id"]
                labels = record["labels"] or []
                properties = serialize_value(record["properties"] or {})
                node_id = make_node_id(labels, properties, element_id)
                primary_label = labels[0] if labels else "Node"

                nodes_by_element_id[element_id] = node_id
                nodes.append(
                    {
                        "id": node_id,
                        "label": readable_node_name(labels, properties),
                        "labels": labels,
                        "type": primary_label,
                        "properties": properties,
                    }
                )
                node_type_counts[primary_label] = (
                    node_type_counts.get(primary_label, 0) + 1
                )

            # Query 2: fetch relationships and map endpoints to frontend node IDs.
            relationship_records = session.run(
                """
                MATCH (source)-[r]->(target)
                RETURN elementId(source) AS source_element_id,
                       elementId(target) AS target_element_id,
                       type(r) AS relationship_type,
                       properties(r) AS properties
                """
            )

            relationships = []
            relationship_type_counts = {}

            for record in relationship_records:
                source_id = nodes_by_element_id.get(record["source_element_id"])
                target_id = nodes_by_element_id.get(record["target_element_id"])
                relationship_type = record["relationship_type"]

                if source_id is None or target_id is None:
                    continue

                relationships.append(
                    {
                        "id": f"{source_id}|{relationship_type}|{target_id}",
                        "source": source_id,
                        "target": target_id,
                        "type": relationship_type,
                        "properties": serialize_value(record["properties"] or {}),
                    }
                )
                relationship_type_counts[relationship_type] = (
                    relationship_type_counts.get(relationship_type, 0) + 1
                )

        return {
            "nodes": nodes,
            "relationships": relationships,
            "summary": {
                "total_nodes": len(nodes),
                "total_relationships": len(relationships),
                "node_types": node_type_counts,
                "relationship_types": relationship_type_counts,
            },
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not fetch graph data",
        )

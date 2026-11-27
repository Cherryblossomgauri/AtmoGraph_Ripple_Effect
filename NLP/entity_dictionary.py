
import requests
import spacy
from collections import defaultdict

API_URL = "https://atmograph-ripple-effect.onrender.com/graph"

ENTITY_LABELS = {
    "Country": ("COUNTRY", "country_name"),
    "Industry": ("INDUSTRY", "industry_name"),
    "Port": ("PORT", "port_name"),
    "ShippingRoute": ("SHIPPING_ROUTE", "route_id"),
    "Disruption": ("DISRUPTION", "event_type"),
}




import time
import requests
import spacy

from collections import defaultdict

API_URL = "https://atmograph-ripple-effect.onrender.com/graph"

ENTITY_LABELS = {
    "Country": ("COUNTRY", "country_name"),
    "Industry": ("INDUSTRY", "industry_name"),
    "Port": ("PORT", "port_name"),
    "ShippingRoute": ("SHIPPING_ROUTE", "route_id"),
    "Disruption": ("DISRUPTION", "event_type"),
}


def load_graph_data():
    """Fetch nodes and relationships from the existing AtmoGraph API."""

    for attempt in range(1, 4):
        try:
            print(f"Connecting to AtmoGraph API ({attempt}/3)...")

            response = requests.get(API_URL, timeout=(15, 120))
            response.raise_for_status()

            graph_data = response.json()

            if "nodes" not in graph_data:
                raise RuntimeError("Graph API response does not contain 'nodes'.")

            return graph_data

        except requests.exceptions.RequestException as error:
            print(f"API request failed: {error}")

            if attempt == 3:
                raise RuntimeError(
                    "Could not retrieve graph data from AtmoGraph API."
                ) from error

            time.sleep(5)

    raise RuntimeError("Could not load graph data.")


def load_entities(graph_data=None):
    """Build entity records from graph nodes."""

    if graph_data is None:
        graph_data = load_graph_data()

    entities = defaultdict(list)

    for node in graph_data.get("nodes", []):
        node_type = node.get("type")

        # Support APIs that return labels instead of a type field.
        if not node_type:
            labels = node.get("labels", [])
            node_type = labels[0] if labels else None

        if node_type not in ENTITY_LABELS:
            continue

        entity_label, property_name = ENTITY_LABELS[node_type]
        properties = node.get("properties", {})
        value = properties.get(property_name)

        if not value:
            continue

        if node_type == "Disruption":
            value = str(value).replace("_", " ")

        entities[entity_label].append({
            "name": str(value).strip(),
            "node_id": node["id"],
            "node_type": node_type,
            "is_synthetic": properties.get("is_synthetic", False),
        })

    print(
        f"Loaded {sum(len(items) for items in entities.values())} "
        "entity records from the graph."
    )

    return entities


def build_nlp(entities=None):
    nlp = spacy.load("en_core_web_sm")

    if entities is None:
        entities = load_entities()

    patterns = []
    seen = set()

    for label, records in entities.items():
        for record in records:
            name = record["name"]
            key = (label, name.casefold())

            if key not in seen:
                patterns.append({
                    "label": label,
                    "pattern": name,
                })
                seen.add(key)

    ruler = nlp.add_pipe(
        "entity_ruler",
        before="ner",
        config={
            "phrase_matcher_attr": "LOWER",
            "overwrite_ents": True,
        },
    )

    ruler.add_patterns(patterns)

    return nlp
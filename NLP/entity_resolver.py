
import re
from collections import defaultdict
from spacy.tokens import Span
from NLP.entity_dictionary import (
    load_graph_data,
    load_entities,
    build_nlp,
)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def normalize(text):
    """Normalize text for case-insensitive comparisons."""
    return re.sub(r"\s+", " ", str(text).strip().casefold())


# --------------------------------------------------
# ENTITY RESOLVER
# --------------------------------------------------

class EntityResolver:

    def __init__(self):
        print("Initializing AtmoGraph Entity Resolver...")
        # Register custom spaCy entity extension
        if not Span.has_extension("node_id"):
            Span.set_extension("node_id", default=None)
        # Load graph data once
        self.graph_data = load_graph_data()

        # Build graph-based entity dictionary
        self.entities = load_entities(self.graph_data)

        # Build spaCy pipeline using graph entities
        self.nlp = build_nlp(self.entities)

        # Index nodes by ID
        self.nodes = {}
        for node in self.graph_data.get("nodes", []):
            self.nodes[node["id"]] = node

        # Index relationships
        self.relationships = self.graph_data.get("relationships", [])

        # Map disruptions to their affected targets
        self.affected_targets = defaultdict(list)

        for rel in self.relationships:
            if rel.get("type") == "AFFECTS":
                source_id = rel.get("source")
                target_id = rel.get("target")

                if source_id and target_id:
                    self.affected_targets[source_id].append(target_id)

        print("Entity Resolver initialized successfully.")

    # --------------------------------------------------
    # NODE HELPERS
    # --------------------------------------------------

    def get_node_type(self, node_id):
        """Get node type from its type field or labels."""
        node = self.nodes.get(node_id)

        if not node:
            return None

        node_type = node.get("type")

        if not node_type:
            labels = node.get("labels", [])
            node_type = labels[0] if labels else None

        return node_type

    def get_node_name(self, node_id):
        """Get a readable name for a graph node."""
        node = self.nodes.get(node_id)

        if not node:
            return str(node_id)

        properties = node.get("properties", {})
        node_type = self.get_node_type(node_id)

        name_properties = {
            "Country": "country_name",
            "Industry": "industry_name",
            "Port": "port_name",
            "ShippingRoute": "route_id",
            "Disruption": "event_type",
        }

        property_name = name_properties.get(node_type)

        if property_name and properties.get(property_name):
            return str(properties[property_name]).replace("_", " ")

        return str(node_id)

    # --------------------------------------------------
    # RELATIONSHIP HELPERS
    # --------------------------------------------------

    def get_relationship_targets(self, source_id, relationship_type):
        """Return outgoing relationship targets."""
        targets = []

        for rel in self.relationships:
            if (
                rel.get("source") == source_id
                and rel.get("type") == relationship_type
            ):
                target_id = rel.get("target")

                if target_id:
                    targets.append(target_id)

        return targets

    def get_relationship_sources(self, target_id, relationship_type):
        """Return incoming relationship sources."""
        sources = []

        for rel in self.relationships:
            if (
                rel.get("target") == target_id
                and rel.get("type") == relationship_type
            ):
                source_id = rel.get("source")

                if source_id:
                    sources.append(source_id)

        return sources

    # --------------------------------------------------
    # COUNTRY RESOLUTION
    # --------------------------------------------------

    def get_countries_for_port(self, port_id):
        """Find the country in which a port is located."""
        country_ids = set()

        country_ids.update(
            self.get_relationship_targets(port_id, "LOCATED_IN")
        )

        return country_ids

    def get_countries_for_route(self, route_id):
        """
        Find countries connected to a shipping route.

        Graph structure:
            Port -[FROM_PORT]-> ShippingRoute
            ShippingRoute -[TO_PORT]-> Port
            Port -[LOCATED_IN]-> Country
        """
        country_ids = set()

        # Origin ports: Port -> ShippingRoute
        origin_ports = self.get_relationship_sources(
            route_id, "FROM_PORT"
        )

        # Destination ports: ShippingRoute -> Port
        destination_ports = self.get_relationship_targets(
            route_id, "TO_PORT"
        )

        all_ports = set(origin_ports + destination_ports)

        for port_id in all_ports:
            country_ids.update(
                self.get_countries_for_port(port_id)
            )

        return country_ids

    def get_countries_for_target(self, target_id):
        """Find countries associated with a port or shipping route."""
        target_type = self.get_node_type(target_id)

        if target_type == "Port":
            return self.get_countries_for_port(target_id)

        if target_type == "ShippingRoute":
            return self.get_countries_for_route(target_id)

        return set()

    def get_country_mentions(self, doc):
        """Extract graph-matched country IDs from the text."""
        mentioned_countries = set()

        country_lookup = {
            normalize(record["name"]): record["node_id"]
            for record in self.entities.get("COUNTRY", [])
        }

        for ent in doc.ents:
            if ent.label_ == "COUNTRY":
                node_id = country_lookup.get(normalize(ent.text))

                if node_id:
                    ent._.node_id = node_id
                    mentioned_countries.add(node_id)

        return mentioned_countries

    # --------------------------------------------------
    # CONTEXT DETECTION
    # --------------------------------------------------

    def infer_expected_target_type(self, ent):
        """
        Infer whether the disruption affects a Port or ShippingRoute
        using the sentence in which the disruption is mentioned.
        """
        context = normalize(ent.sent.text)

        route_terms = (
            "route closure",
            "shipping route",
            "shipping lane",
            "sea lane",
            "trade route",
        )

        port_terms = (
            "port",
            "harbor",
            "harbour",
            "port operations",
            "port terminal",
        )

        if any(term in context for term in route_terms):
            return "ShippingRoute"

        if any(term in context for term in port_terms):
            return "Port"

        return None

    def is_between_countries_context(self, ent):
        """Check whether the sentence explicitly describes a route between countries."""
        context = normalize(ent.sent.text)
        return "between" in context

    # --------------------------------------------------
    # DISRUPTION SCORING
    # --------------------------------------------------

    def score_disruption_candidate(
        self,
        candidate,
        expected_target_type,
        mentioned_countries,
        require_both_route_endpoints=False,
    ):
        """
        Score a disruption candidate using:
        1. AFFECTS target type
        2. Country/location compatibility
        3. Route endpoint validation
        """
        score = 0
        reasons = []

        disruption_id = candidate["node_id"]

        affected_target_ids = self.affected_targets.get(
            disruption_id, []
        )

        if not affected_target_ids:
            return score, ["Disruption has no AFFECTS relationship"]

        for target_id in affected_target_ids:
            target_type = self.get_node_type(target_id)

            candidate_countries = self.get_countries_for_target(
                target_id
            )

            # Target type match
            if expected_target_type:
                if target_type == expected_target_type:
                    score += 3
                    reasons.append(
                        f"AFFECTS target is {target_type}"
                    )
                else:
                    score -= 2
                    reasons.append(
                        f"AFFECTS target type {target_type} "
                        f"does not match expected {expected_target_type}"
                    )

            # Country and route endpoint validation
            if not mentioned_countries:
                continue

            matching_countries = (
                candidate_countries & mentioned_countries
            )

            if (
                target_type == "ShippingRoute"
                and require_both_route_endpoints
            ):
                # For "between India and China", both countries
                # must be connected to the candidate route.
                if mentioned_countries.issubset(candidate_countries):
                    score += 4
                    reasons.append(
                        "Route endpoints match all mentioned countries"
                    )
                else:
                    score -= 5
                    reasons.append(
                        "Route endpoints do not match all mentioned countries"
                    )

            elif matching_countries:
                score += 2
                reasons.append(
                    "Affected location matches mentioned country"
                )

            elif candidate_countries:
                score -= 5
                reasons.append(
                    "Affected location conflicts with mentioned country"
                )

        return score, reasons

    # --------------------------------------------------
    # MAIN ANALYSIS
    # --------------------------------------------------

    def analyze(self, text):
        """Extract entities and resolve them against the AtmoGraph."""

        doc = self.nlp(text)

        results = []

        # Resolve country mentions first
        mentioned_countries = self.get_country_mentions(doc)

        for ent in doc.ents:

            label = ent.label_

            # ------------------------------------------
            # DISRUPTION RESOLUTION
            # ------------------------------------------

            if label == "DISRUPTION":

                candidates = [
                    candidate
                    for candidate in self.entities.get("DISRUPTION", [])
                    if normalize(candidate["name"]) == normalize(ent.text)
                ]

                expected_target_type = (
                    self.infer_expected_target_type(ent)
                )

                require_both_route_endpoints = (
                    expected_target_type == "ShippingRoute"
                    and self.is_between_countries_context(ent)
                    and len(mentioned_countries) >= 2
                )

                if not candidates:
                    results.append({
                        "text": ent.text,
                        "label": label,
                        "status": "unmatched",
                        "candidate_count": 0,
                        "resolution_reason": "No matching disruption in graph",
                    })
                    continue

                scored_candidates = []

                for candidate in candidates:
                    score, reasons = self.score_disruption_candidate(
                        candidate=candidate,
                        expected_target_type=expected_target_type,
                        mentioned_countries=mentioned_countries,
                        require_both_route_endpoints=(
                            require_both_route_endpoints
                        ),
                    )

                    scored_candidates.append({
                        "candidate": candidate,
                        "score": score,
                        "reasons": reasons,
                    })

                scored_candidates.sort(
                    key=lambda item: item["score"],
                    reverse=True,
                )

                best = scored_candidates[0]

                # Reject candidates with explicit location conflicts
                conflict_reasons = (
                    "Affected location conflicts with mentioned country",
                    "Route endpoints do not match all mentioned countries",
                )

                has_location_conflict = any(
                    reason in best["reasons"]
                    for reason in conflict_reasons
                )

                # Resolve only when the best candidate has positive
                # evidence and no location conflict.
                if best["score"] > 0 and not has_location_conflict:

                    results.append({
                        "text": ent.text,
                        "label": label,
                        "status": "matched",
                        "node_id": best["candidate"]["node_id"],
                        "node_name": best["candidate"]["name"],
                        "candidate_count": len(candidates),
                        "score": best["score"],
                        "resolution_reason": "; ".join(
                            best["reasons"]
                        ),
                        "affected_targets": [
                            {
                                "node_id": target_id,
                                "node_type": self.get_node_type(target_id),
                                "node_name": self.get_node_name(target_id),
                            }
                            for target_id in self.affected_targets.get(
                                best["candidate"]["node_id"], []
                            )
                        ],
                    })

                else:
                    results.append({
                        "text": ent.text,
                        "label": label,
                        "status": "ambiguous",
                        "candidate_count": len(candidates),
                        "resolution_reason": (
                            "No candidate satisfies target type "
                            "and location constraints"
                        ),
                        "candidates": [
                            {
                                "node_id": item["candidate"]["node_id"],
                                "name": item["candidate"]["name"],
                                "score": item["score"],
                                "reasons": item["reasons"],
                            }
                            for item in scored_candidates
                        ],
                    })

            # ------------------------------------------
            # COUNTRY / INDUSTRY / PORT / ROUTE
            # ------------------------------------------

            else:
                entity_records = self.entities.get(label, [])

                candidates = [
                    record
                    for record in entity_records
                    if normalize(record["name"]) == normalize(ent.text)
                ]

                if len(candidates) == 1:
                    candidate = candidates[0]

                    results.append({
                        "text": ent.text,
                        "label": label,
                        "status": "matched",
                        "node_id": candidate["node_id"],
                        "node_name": candidate["name"],
                        "candidate_count": 1,
                        "resolution_reason": "Exact graph entity match",
                    })

                elif len(candidates) > 1:
                    results.append({
                        "text": ent.text,
                        "label": label,
                        "status": "ambiguous",
                        "candidate_count": len(candidates),
                        "resolution_reason": (
                            "Multiple graph nodes have the same entity name"
                        ),
                        "candidates": [
                            {
                                "node_id": item["node_id"],
                                "name": item["name"],
                                "node_type": item["node_type"],
                            }
                            for item in candidates
                        ],
                    })

                else:
                    results.append({
                        "text": ent.text,
                        "label": label,
                        "status": "unmatched",
                        "candidate_count": 0,
                        "resolution_reason": (
                            "Entity not found in graph dictionary"
                        ),
                    })

        return {
            "input_text": text,
            "entities": results,
            "entity_count": len(results),
        }

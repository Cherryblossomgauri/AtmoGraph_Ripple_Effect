"""Build the Neo4j graph. Requires validated data and a running Neo4j instance."""
from neo4j import GraphDatabase

class GraphBuilder:
    def __init__(self, uri, username, password, database="neo4j"):
        self.driver=GraphDatabase.driver(uri,auth=(username,password))
        self.database=database
    def close(self): self.driver.close()
    def run(self,query,rows):
        if not rows: return
        with self.driver.session(database=self.database) as session:
            session.execute_write(lambda tx: tx.run(query,rows=rows).consume())
    def build(self,d):
        self.run("""UNWIND $rows AS row
        MERGE (c:Country {country_id:row.country_id})
        SET c.country_name=row.country_name,c.region=row.region""",d["countries"].to_dict("records"))
        self.run("""UNWIND $rows AS row
        MATCH (c:Country {country_id:row.country_id})
        MERGE (i:Industry {industry_id:row.industry_id})
        SET i.industry_name=row.industry_name,i.industry_category=row.industry_category
        MERGE (c)-[:HAS_INDUSTRY]->(i)""",d["industries"].to_dict("records"))
        self.run("""UNWIND $rows AS row
        MATCH (s:Industry {industry_id:row.supplier_industry_id})
        MATCH (b:Industry {industry_id:row.buyer_industry_id})
        MERGE (s)-[r:SUPPLIES {transaction_id:row.transaction_id}]->(b)
        SET r.transaction_value_usd=toFloat(row.transaction_value_usd),
            r.dependency_strength=toFloat(row.dependency_strength),
            r.product_category=row.product_category,r.reference_year=toInteger(row.reference_year),
            r.is_synthetic=row.is_synthetic""",d["transactions"].to_dict("records"))
        self.run("""UNWIND $rows AS row
        MATCH (c:Country {country_id:row.country_id})
        MERGE (p:Port {port_id:row.port_id})
        SET p.port_name=row.port_name,p.capacity_index=toFloat(row.capacity_index),p.is_synthetic=row.is_synthetic
        MERGE (p)-[:LOCATED_IN]->(c)""",d["ports"].to_dict("records"))
        self.run("""UNWIND $rows AS row
        MATCH (a:Port {port_id:row.source_port_id})
        MATCH (b:Port {port_id:row.destination_port_id})
        MERGE (r:ShippingRoute {route_id:row.route_id})
        SET r.transit_days=toInteger(row.transit_days),r.route_capacity_index=toFloat(row.route_capacity_index),
            r.is_synthetic=row.is_synthetic
        MERGE (a)-[:FROM_PORT]->(r)
        MERGE (r)-[:TO_PORT]->(b)""",d["shipping_routes"].to_dict("records"))
        self.run("""UNWIND $rows AS row
        MATCH (i:Industry {industry_id:row.industry_id})
        MATCH (p:Port {port_id:row.port_id})
        MERGE (i)-[r:USES_PORT {link_id:row.link_id}]->(p)
        SET r.usage_type=row.usage_type,r.share=toFloat(row.share),r.is_synthetic=row.is_synthetic""",
            d["industry_port_links"].to_dict("records"))
        events=d["disruptions"].to_dict("records")
        port_events=[r for r in events if r["target_type"]=="PORT"]
        route_events=[r for r in events if r["target_type"]=="SHIPPING_ROUTE"]
        common="""SET d.event_type=row.event_type,d.severity=toInteger(row.severity),
        d.start_date=date(row.start_date),d.duration_days=toInteger(row.duration_days),d.is_synthetic=row.is_synthetic"""
        self.run(f"""UNWIND $rows AS row
        MATCH (t:Port {{port_id:row.target_id}})
        MERGE (d:Disruption {{disruption_id:row.disruption_id}})
        {common}
        MERGE (d)-[:AFFECTS]->(t)""",port_events)
        self.run(f"""UNWIND $rows AS row
        MATCH (t:ShippingRoute {{route_id:row.target_id}})
        MERGE (d:Disruption {{disruption_id:row.disruption_id}})
        {common}
        MERGE (d)-[:AFFECTS]->(t)""",route_events)

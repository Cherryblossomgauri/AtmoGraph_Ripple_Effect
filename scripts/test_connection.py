import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)

try:
    driver.verify_connectivity()
    print("Neo4j Connected Successfully!")

    with driver.session(database=DATABASE) as session:
        result = session.run("RETURN 'AtmoGraph Connected' AS message")
        print(result.single()["message"])

except Exception as e:
    print("Connection Failed:", e)

finally:
    driver.close()
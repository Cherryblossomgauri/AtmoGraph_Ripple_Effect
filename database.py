
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables from .env during local development
# On Render, environment variables are supplied through its dashboard.
load_dotenv()

# Neo4j configuration
URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "8afc8fe5")


# Validate required environment variables
required_variables = {
    "NEO4J_URI": URI,
    "NEO4J_USERNAME": USERNAME,
    "NEO4J_PASSWORD": PASSWORD,
}

missing_variables = [
    name for name, value in required_variables.items() if not value
]

if missing_variables:
    raise ValueError(
        f"Missing required environment variables: {', '.join(missing_variables)}"
    )


# Create Neo4j driver
driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)


# Verify database connectivity
def verify_connection():
    driver.verify_connectivity()
    print("Successfully connected to Neo4j AuraDB!")


# Close driver when application shuts down
def close_connection():
    driver.close()

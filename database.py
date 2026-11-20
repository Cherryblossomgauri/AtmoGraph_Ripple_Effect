import os
from contextlib import contextmanager

from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load .env during local development.
# Render provides these values through its Environment settings.
load_dotenv()

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "8afc8fe5")

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

# Create one shared Neo4j driver for the FastAPI application.
driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD),
)


@contextmanager
def get_database_session():
    """Open and automatically close a session for the configured database."""
    with driver.session(database=DATABASE) as session:
        yield session


def verify_connection():
    """Verify that Neo4j is reachable and can execute a simple query."""
    driver.verify_connectivity()
    with get_database_session() as session:
        session.run("RETURN 1 AS result").single()


def close_connection():
    """Close the shared Neo4j driver when the API shuts down."""
    driver.close()

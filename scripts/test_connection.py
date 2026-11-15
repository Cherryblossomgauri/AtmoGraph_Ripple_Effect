
import os
from pathlib import Path
from dotenv import load_dotenv
import truststore

truststore.inject_into_ssl()

from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ConfigurationError, ServiceUnavailable

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

print("URI loaded:", bool(URI))
print("Username:", USERNAME)
print("Password loaded:", bool(PASSWORD))
print("Database:", DATABASE)
print("URI scheme:", URI.split("://")[0] if URI else None)

if not all((URI, USERNAME, PASSWORD)):
    raise SystemExit(
        "Missing NEO4J_URI, NEO4J_USERNAME, or NEO4J_PASSWORD in "
        f"{ROOT / '.env'}"
    )

driver = None
try:
    driver = GraphDatabase.driver(
        URI,
        auth=(USERNAME, PASSWORD),
        connection_timeout=15
    )

    print("Testing connection...")

    with driver.session(database=DATABASE) as session:
        result = session.run("RETURN 1 AS connected").single()
        if result["connected"] != 1:
            raise RuntimeError("AuraDB returned an unexpected health-check result")

    print("SUCCESS: AuraDB Connected!")

    print(driver.get_server_info())

except AuthError:
    print("ERROR: AuraDB rejected the username or password.")
    print("Use username 'neo4j' and the current password from the Aura console.")
except ConfigurationError as e:
    print("ERROR: Invalid Neo4j configuration:", str(e))
except ServiceUnavailable as e:
    details = repr(e) + " " + repr(e.__cause__)
    if "CERTIFICATE_VERIFY_FAILED" in details or "self-signed certificate" in details:
        print("ERROR: TLS certificate verification failed before authentication.")
        print("Do not change the URI to neo4j+ssc.")
        print("Install/update the trusted root certificate used by your network")
        print("or test from a network without TLS inspection, then retry.")
    else:
        print("ERROR: AuraDB is unreachable or the instance is paused.")
        print("Open the Aura console, start the instance, and retry.")
        print("DETAILS:", str(e))
except Exception as e:
    print("ERROR TYPE:", type(e).__name__)
    print("ERROR DETAILS:", str(e))

finally:
    if driver is not None:
        driver.close()

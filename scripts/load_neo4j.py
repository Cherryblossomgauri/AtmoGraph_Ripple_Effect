"""Validate, then load the synthetic CSVs into Neo4j."""
import os, sys
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.validate_data import validate
from src.ingestion.readers import read_dataset
from src.graph.builder import GraphBuilder

def main():
    load_dotenv(ROOT/".env")
    errors=validate()
    if errors:
        print("Refusing to load: validation failed.")
        for e in errors: print(" -",e)
        raise SystemExit(1)
    uri=os.getenv("NEO4J_URI"); user=os.getenv("NEO4J_USERNAME"); password=os.getenv("NEO4J_PASSWORD")
    if not all([uri,user,password]):
        raise SystemExit("Set NEO4J_URI, NEO4J_USERNAME and NEO4J_PASSWORD in .env")
    data=read_dataset(ROOT/"data"/"synthetic")
    db=GraphBuilder(uri,user,password,os.getenv("NEO4J_DATABASE","neo4j"))
    try: db.build(data)
    finally: db.close()
    print("Neo4j graph loading completed.")
if __name__=="__main__": main()

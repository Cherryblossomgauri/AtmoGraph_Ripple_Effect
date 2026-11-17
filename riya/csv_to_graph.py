import json
import pandas as pd

CSV_FILE = "shipments.csv"    
SRC = "supplier"              
DST = "destination"           

df = pd.read_csv(CSV_FILE, encoding="utf-8")
df = df[[SRC, DST]].dropna()
pairs = df.groupby([SRC, DST]).size().reset_index(name="weight")

names = sorted(set(pairs[SRC]) | set(pairs[DST]))
graph = {
    "nodes": [{"id": n, "type": "country"} for n in names],
    "links": [
        {"source": r[SRC], "target": r[DST], "weight": int(r["weight"])}
        for _, r in pairs.iterrows()
    ],
}
with open("graph.json", "w", encoding="utf-8") as f:
    json.dump(graph, f, indent=2, ensure_ascii=False)
print(f"{len(names)} nodes, {len(pairs)} links saved to graph.json")
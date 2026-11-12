"""Validate generated CSV files. Exits non-zero on any error."""
import csv
from datetime import date
from pathlib import Path

DATA=Path("data/synthetic")
REQUIRED={
 "countries.csv":["country_id","country_name","region"],
 "industries.csv":["industry_id","industry_name","country_id","industry_category"],
 "transactions.csv":["transaction_id","supplier_industry_id","buyer_industry_id","transaction_value_usd","dependency_strength","product_category","reference_year","is_synthetic"],
 "ports.csv":["port_id","port_name","country_id","capacity_index","is_synthetic"],
 "shipping_routes.csv":["route_id","source_port_id","destination_port_id","transit_days","route_capacity_index","is_synthetic"],
 "industry_port_links.csv":["link_id","industry_id","port_id","usage_type","share","is_synthetic"],
 "disruptions.csv":["disruption_id","event_type","target_type","target_id","severity","start_date","duration_days","is_synthetic"]}
def load(name):
    p=DATA/name
    if not p.exists(): raise ValueError(f"Missing file: {p}")
    with p.open(newline="",encoding="utf-8") as f:
        reader=csv.DictReader(f)
        missing=[x for x in REQUIRED[name] if x not in (reader.fieldnames or [])]
        if missing: raise ValueError(f"{name}: missing columns {missing}")
        return list(reader)
def unique(rows,key,name,errors):
    vals=[r[key] for r in rows]
    if len(vals)!=len(set(vals)): errors.append(f"{name}: duplicate values in {key}")
def validate():
    errors=[]; tables={}
    for name in REQUIRED:
        try: tables[name]=load(name)
        except Exception as e: errors.append(str(e))
    if errors: return errors
    keys=[("countries.csv","country_id"),("industries.csv","industry_id"),("transactions.csv","transaction_id"),
          ("ports.csv","port_id"),("shipping_routes.csv","route_id"),("industry_port_links.csv","link_id"),
          ("disruptions.csv","disruption_id")]
    for f,k in keys: unique(tables[f],k,f,errors)
    countries={r["country_id"] for r in tables["countries.csv"]}
    industries={r["industry_id"] for r in tables["industries.csv"]}
    ports={r["port_id"] for r in tables["ports.csv"]}
    routes={r["route_id"] for r in tables["shipping_routes.csv"]}
    for r in tables["industries.csv"]:
        if r["country_id"] not in countries: errors.append(f"Industry {r['industry_id']} has unknown country {r['country_id']}")
    for r in tables["ports.csv"]:
        if r["country_id"] not in countries: errors.append(f"Port {r['port_id']} has unknown country {r['country_id']}")
    for r in tables["transactions.csv"]:
        if r["supplier_industry_id"] not in industries: errors.append(f"Unknown supplier {r['supplier_industry_id']}")
        if r["buyer_industry_id"] not in industries: errors.append(f"Unknown buyer {r['buyer_industry_id']}")
        try:
            if float(r["transaction_value_usd"])<0: errors.append(f"Negative value in {r['transaction_id']}")
            if not 0<=float(r["dependency_strength"])<=1: errors.append(f"dependency_strength out of range in {r['transaction_id']}")
        except ValueError: errors.append(f"Non-numeric transaction fields in {r['transaction_id']}")
    for r in tables["shipping_routes.csv"]:
        if r["source_port_id"] not in ports: errors.append(f"Unknown source port {r['source_port_id']}")
        if r["destination_port_id"] not in ports: errors.append(f"Unknown destination port {r['destination_port_id']}")
        try:
            if int(r["transit_days"])<=0: errors.append(f"Invalid transit_days in {r['route_id']}")
        except ValueError: errors.append(f"Invalid transit_days in {r['route_id']}")
    for r in tables["industry_port_links.csv"]:
        if r["industry_id"] not in industries: errors.append(f"Unknown industry in link {r['link_id']}")
        if r["port_id"] not in ports: errors.append(f"Unknown port in link {r['link_id']}")
        try:
            if not 0<=float(r["share"])<=1: errors.append(f"share out of range in {r['link_id']}")
        except ValueError: errors.append(f"Invalid share in {r['link_id']}")
    for r in tables["disruptions.csv"]:
        valid=(r["target_type"]=="PORT" and r["target_id"] in ports) or (r["target_type"]=="SHIPPING_ROUTE" and r["target_id"] in routes)
        if not valid: errors.append(f"Invalid disruption target in {r['disruption_id']}")
        try:
            if not 1<=int(r["severity"])<=5: errors.append(f"Severity out of range in {r['disruption_id']}")
            if int(r["duration_days"])<=0: errors.append(f"Invalid duration in {r['disruption_id']}")
            date.fromisoformat(r["start_date"])
        except ValueError: errors.append(f"Invalid event fields in {r['disruption_id']}")
    return errors
if __name__=="__main__":
    problems=validate()
    if problems:
        print("VALIDATION FAILED")
        for p in problems: print(" -",p)
        raise SystemExit(1)
    print("VALIDATION PASSED — all required columns, unique IDs, references and ranges are valid.")

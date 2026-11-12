"""Generate a deterministic, rule-based AtmoGraph synthetic dataset."""
import argparse, csv, random
from pathlib import Path

COUNTRIES = [
 ("IND","India","South Asia"),("CHN","China","East Asia"),
 ("DEU","Germany","Europe"),("USA","United States","North America"),
 ("JPN","Japan","East Asia")]
CATEGORIES = [
 ("AGRI","Agriculture"),("MIN","Mining"),("CHEM","Chemicals"),("SEMI","Semiconductors"),
 ("ELEC","Electronics"),("AUTO","Automobile"),("TEXT","Textiles"),
 ("PHAR","Pharmaceuticals"),("FOOD","Food Processing"),("LOGI","Logistics")]
RULES = [
 ("AGRI","FOOD","AGRICULTURAL_INPUTS"),("MIN","CHEM","MINERALS"),
 ("CHEM","SEMI","CHEMICAL_INPUTS"),("SEMI","ELEC","CHIPS"),
 ("ELEC","AUTO","ELECTRONIC_COMPONENTS"),("CHEM","PHAR","CHEMICAL_INPUTS"),
 ("AGRI","TEXT","AGRICULTURAL_INPUTS"),("TEXT","AUTO","TEXTILE_INPUTS")]
CROSS = [
 ("CHN","SEMI","JPN","ELEC","CHIPS"),("JPN","ELEC","DEU","AUTO","ELECTRONIC_COMPONENTS"),
 ("IND","CHEM","USA","PHAR","CHEMICAL_INPUTS"),("USA","MIN","DEU","CHEM","MINERALS"),
 ("DEU","AUTO","IND","ELEC","AUTOMOTIVE_COMPONENTS"),("CHN","TEXT","USA","AUTO","TEXTILE_INPUTS"),
 ("IND","AGRI","JPN","FOOD","AGRICULTURAL_INPUTS"),("USA","SEMI","IND","ELEC","CHIPS"),
 ("DEU","CHEM","CHN","SEMI","CHEMICAL_INPUTS"),("JPN","MIN","IND","CHEM","MINERALS")]

def save(folder, filename, fields, rows):
    with (folder/filename).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def generate(output_dir="data/synthetic", seed=42):
    rng=random.Random(seed); folder=Path(output_dir); folder.mkdir(parents=True,exist_ok=True)
    countries=[{"country_id":a,"country_name":b,"region":c} for a,b,c in COUNTRIES]
    ids={(cid,code):f"{cid}_{code}" for cid,_,_ in COUNTRIES for code,_ in CATEGORIES}
    industries=[{"industry_id":ids[(cid,code)],"industry_name":name,"country_id":cid,"industry_category":code}
                for cid,_,_ in COUNTRIES for code,name in CATEGORIES]
    transactions=[]; seen=set()
    def add(sc,s,bc,b,product):
        src,dst=ids[(sc,s)],ids[(bc,b)]
        if (src,dst) in seen or src==dst: return
        seen.add((src,dst)); transactions.append({
          "transaction_id":f"TX{len(transactions)+1:04d}","supplier_industry_id":src,"buyer_industry_id":dst,
          "transaction_value_usd":round(rng.uniform(500000,50000000),2),
          "dependency_strength":round(rng.uniform(.2,.95),2),"product_category":product,
          "reference_year":2025,"is_synthetic":"true"})
    for cid,_,_ in COUNTRIES:
        for s,b,p in RULES: add(cid,s,cid,b,p)
    for rule in CROSS: add(*rule)
    ports=[]; pids={}
    for cid,name,_ in COUNTRIES:
        pids[cid]=f"PORT_{cid}_01"
        ports.append({"port_id":pids[cid],"port_name":f"Synthetic {name} Port","country_id":cid,
                      "capacity_index":rng.randint(60,100),"is_synthetic":"true"})
    pairs=[("IND","CHN"),("CHN","JPN"),("JPN","DEU"),("DEU","USA"),("USA","IND"),("IND","DEU"),("CHN","USA"),("JPN","IND")]
    routes=[{"route_id":f"ROUTE_{n:03d}","source_port_id":pids[a],"destination_port_id":pids[b],
             "transit_days":rng.randint(5,30),"route_capacity_index":rng.randint(40,100),"is_synthetic":"true"}
            for n,(a,b) in enumerate(pairs,1)]
    links=[{"link_id":f"IPL{n:04d}","industry_id":r["industry_id"],"port_id":pids[r["country_id"]],
            "usage_type":"BOTH","share":1.0,"is_synthetic":"true"} for n,r in enumerate(industries,1)]
    et=["PORT_STRIKE","STORM","FLOOD","ROUTE_CLOSURE","EQUIPMENT_FAILURE"]
    targets=[("PORT",p["port_id"]) for p in ports]+[("SHIPPING_ROUTE",r["route_id"]) for r in routes]
    events=[]
    for n in range(10):
        typ,target=targets[n%len(targets)]
        events.append({"disruption_id":f"DISR_{n+1:03d}","event_type":et[n%len(et)],"target_type":typ,
          "target_id":target,"severity":rng.randint(1,5),"start_date":f"2025-{n+1:02d}-10",
          "duration_days":rng.randint(2,30),"is_synthetic":"true"})
    save(folder,"countries.csv",["country_id","country_name","region"],countries)
    save(folder,"industries.csv",["industry_id","industry_name","country_id","industry_category"],industries)
    save(folder,"transactions.csv",["transaction_id","supplier_industry_id","buyer_industry_id","transaction_value_usd","dependency_strength","product_category","reference_year","is_synthetic"],transactions)
    save(folder,"ports.csv",["port_id","port_name","country_id","capacity_index","is_synthetic"],ports)
    save(folder,"shipping_routes.csv",["route_id","source_port_id","destination_port_id","transit_days","route_capacity_index","is_synthetic"],routes)
    save(folder,"industry_port_links.csv",["link_id","industry_id","port_id","usage_type","share","is_synthetic"],links)
    save(folder,"disruptions.csv",["disruption_id","event_type","target_type","target_id","severity","start_date","duration_days","is_synthetic"],events)
    print(f"Generated in {folder.resolve()}: {len(countries)} countries, {len(industries)} industries, "
          f"{len(transactions)} supply links, {len(ports)} ports, {len(routes)} routes, {len(events)} disruptions.")
    print("All records are synthetic; same seed + same script/config gives reproducible output.")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",default="data/synthetic")
    parser.add_argument("--seed",type=int,default=42)
    args=parser.parse_args(); generate(args.output_dir,args.seed)

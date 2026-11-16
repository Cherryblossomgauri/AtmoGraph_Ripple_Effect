"""
AtmoGraph - heterogeneous GNN matched to the Neo4j schema

Schema (from Mayank's graph):
  Nodes: Country(5) Industry(50) Port(5) ShippingRoute(8) Disruption(10)
  Edges: HAS_INDUSTRY, SUPPLIES, USES_PORT, LOCATED_IN, FROM_PORT, TO_PORT, AFFECTS

Task: given ONE disruption, predict impact (0..1) on every Port, Industry, Country.

Data source (picked automatically):
  1. USE_NEO4J=1                      -> reads the live Neo4j graph
  2. folder data/synthetic/ exists    -> reads the team's CSV files (same data Mayank loads)
  3. otherwise                        -> fake graph with the same shape
Run:  python atmograph_hetero_gnn.py      (from the repo root, so data/synthetic is found)
Real Neo4j:  set NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD, then
                   USE_NEO4J=1 python atmograph_hetero_gnn.py
                   (Python driver uses bolt port 7687, NOT 7474 which is the browser)

IMPORTANT: the real graph has NO impact labels. Labels here come from the
simulate() rule below, so this is a SURROGATE of a rule, not a predictor of
real disruptions. Rule constants are ASSUMPTIONS - agree them with the team.
"""
import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.loader import DataLoader
from torch_geometric.nn import HeteroConv, GraphConv

SEED = 42
N_SYNTH = 600          # synthetic training scenarios
EPOCHS = 40
HIDDEN = 48
SEV_MAX = 5.0          # ASSUMPTION: severity scale 1..5 (ask Mayank)
DUR_MAX = 30.0          # real disruptions last 2..28 days
ROUTE_TO_PORT = 0.5    # share of a route disruption passed to its end ports
SUPPLY_DAMP = 0.5      # how much of a supplier's impact passes to its buyer
SUPPLY_ITERS = 3
USE_NEO4J = os.getenv("USE_NEO4J") == "1"
CSV_DIR = os.getenv("CSV_DIR", "data/synthetic")
CAP_SCALE = 100.0      # real capacity_index / route_capacity_index are 0..100 (seen: 40..96)

rng = np.random.default_rng(SEED)
torch.manual_seed(SEED)

# ----------------------------------------------------------------------
# 1. Raw graph: from Neo4j, or a mock with identical counts and fields
# ----------------------------------------------------------------------
# Undirected patterns are used where direction doesn't matter (roles come
# from the labels), so a wrongly-read arrow can't break the loader.
# Only SUPPLIES is directional: (a)-[:SUPPLIES]->(b) means "a supplies b".
QUERIES = {
    "country": "MATCH (c:Country) RETURN c.country_id AS id, c.region AS region",
    "industry": "MATCH (i:Industry) RETURN i.industry_id AS id, i.industry_category AS category",
    "port": "MATCH (p:Port) RETURN p.port_id AS id, p.capacity_index AS cap",
    "route": "MATCH (r:ShippingRoute) RETURN r.route_id AS id, r.transit_days AS transit_days, r.route_capacity_index AS cap",
    "disruption": "MATCH (d:Disruption) RETURN d.disruption_id AS id, d.event_type AS event_type, d.severity AS severity, d.duration_days AS duration_days",
    "has_industry": "MATCH (c:Country)-[:HAS_INDUSTRY]-(i:Industry) RETURN c.country_id AS a, i.industry_id AS b",
    "supplies": "MATCH (a:Industry)-[s:SUPPLIES]->(b:Industry) RETURN a.industry_id AS a, b.industry_id AS b, s.dependency_strength AS w",
    "uses_port": "MATCH (i:Industry)-[u:USES_PORT]-(p:Port) RETURN i.industry_id AS a, p.port_id AS b, u.share AS w",
    "located_in": "MATCH (p:Port)-[:LOCATED_IN]-(c:Country) RETURN p.port_id AS a, c.country_id AS b",
    "from_port": "MATCH (r:ShippingRoute)-[:FROM_PORT]-(p:Port) RETURN r.route_id AS a, p.port_id AS b",
    "to_port": "MATCH (r:ShippingRoute)-[:TO_PORT]-(p:Port) RETURN r.route_id AS a, p.port_id AS b",
    "affects": "MATCH (d:Disruption)-[:AFFECTS]-(t) WHERE t:Port OR t:ShippingRoute RETURN d.disruption_id AS a, coalesce(t.port_id, t.route_id) AS b",
}


def fetch_raw(run):
    """run(query) -> list of dict rows. Returns the raw graph as python lists."""
    raw = {k: run(q) for k, q in QUERIES.items()}
    out = {}
    for k in ("country", "industry", "port", "route", "disruption"):
        out[k] = raw[k]
    for k in ("has_industry", "located_in", "from_port", "to_port", "affects"):
        out[k] = [(r["a"], r["b"]) for r in raw[k]]
    for k in ("supplies", "uses_port"):
        out[k] = [(r["a"], r["b"], float(r["w"])) for r in raw[k]]
    for k in ("port", "route"):
        for r in out[k]:
            r["cap"] = float(r["cap"]) / CAP_SCALE
    return out


def fetch_from_neo4j():
    from neo4j import GraphDatabase  # pip install neo4j
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pw = os.environ["NEO4J_PASSWORD"]  # never hard-code or commit this
    with GraphDatabase.driver(uri, auth=(user, pw)) as driver:
        with driver.session() as s:
            return fetch_raw(lambda q: s.run(q).data())


def load_from_csv(folder):
    import csv

    def rd(name):
        with open(os.path.join(folder, name), newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    countries, industries, ports = rd("countries.csv"), rd("industries.csv"), rd("ports.csv")
    routes, disr = rd("shipping_routes.csv"), rd("disruptions.csv")
    tx, links = rd("transactions.csv"), rd("industry_port_links.csv")
    return {
        "country": [{"id": r["country_id"], "region": r["region"]} for r in countries],
        "industry": [{"id": r["industry_id"], "category": r["industry_category"]} for r in industries],
        "port": [{"id": r["port_id"], "cap": float(r["capacity_index"]) / CAP_SCALE} for r in ports],
        "route": [{"id": r["route_id"], "transit_days": int(r["transit_days"]),
                   "cap": float(r["route_capacity_index"]) / CAP_SCALE} for r in routes],
        "disruption": [{"id": r["disruption_id"], "event_type": r["event_type"], "severity": int(r["severity"]),
                        "duration_days": int(r["duration_days"])} for r in disr],
        "has_industry": [(r["country_id"], r["industry_id"]) for r in industries],
        "located_in": [(r["port_id"], r["country_id"]) for r in ports],
        "from_port": [(r["route_id"], r["source_port_id"]) for r in routes],
        "to_port": [(r["route_id"], r["destination_port_id"]) for r in routes],
        "uses_port": [(r["industry_id"], r["port_id"], float(r["share"])) for r in links],
        "supplies": [(r["supplier_industry_id"], r["buyer_industry_id"], float(r["dependency_strength"])) for r in tx],
        "affects": [(r["disruption_id"], r["target_id"]) for r in disr],
    }


def make_mock_raw():
    cats = ["Electronics", "Auto", "Pharma", "Food", "Energy", "Textile"]
    types = ["storm", "strike", "congestion", "flood"]
    raw = {
        "country": [{"id": f"C{i}", "region": ["Asia", "Europe", "Americas"][i % 3]} for i in range(5)],
        "industry": [{"id": f"I{i}", "category": cats[i % 6]} for i in range(50)],
        "port": [{"id": f"P{i}", "cap": float(rng.uniform(0.3, 1))} for i in range(5)],
        "route": [{"id": f"R{i}", "transit_days": int(rng.integers(3, 30)), "cap": float(rng.uniform(0.3, 1))} for i in range(8)],
        "disruption": [{"id": f"D{i}", "event_type": types[i % 4], "severity": int(rng.integers(1, 6)),
                        "duration_days": int(rng.integers(2, 60))} for i in range(10)],
    }
    raw["has_industry"] = [(f"C{i % 5}", f"I{i}") for i in range(50)]
    raw["uses_port"] = [(f"I{i}", f"P{rng.integers(0, 5)}", float(rng.uniform(0.5, 1))) for i in range(50)]
    raw["located_in"] = [(f"P{i}", f"C{i}") for i in range(5)]
    pairs = set()
    while len(pairs) < 50:
        a, b = rng.integers(0, 50, 2)
        if a != b:
            pairs.add((int(a), int(b)))
    raw["supplies"] = [(f"I{a}", f"I{b}", float(rng.uniform(0.2, 1))) for a, b in sorted(pairs)]
    ends = [rng.choice(5, 2, replace=False) for _ in range(8)]
    raw["from_port"] = [(f"R{i}", f"P{e[0]}") for i, e in enumerate(ends)]
    raw["to_port"] = [(f"R{i}", f"P{e[1]}") for i, e in enumerate(ends)]
    raw["affects"] = [(f"D{i}", f"P{i % 5}" if i < 6 else f"R{i - 6}") for i in range(10)]
    return raw


# ----------------------------------------------------------------------
# 2. Static graph tensors (shared by every scenario)
# ----------------------------------------------------------------------
def onehot(values, vocab):
    m = np.zeros((len(values), len(vocab)), dtype=np.float32)
    # PERF: build the lookup dict once, so each value is O(1) instead of vocab.index() scanning the list
    pos = {v: j for j, v in enumerate(vocab)}
    for i, v in enumerate(values):
        m[i, pos[v]] = 1  # same result as before, just faster lookup
    return m


def build_static(raw):
    ids = {k: {r["id"]: i for i, r in enumerate(raw[k])} for k in ("country", "industry", "port", "route")}
    nI, nP, nR, nC = (len(raw[k]) for k in ("industry", "port", "route", "country"))
    regions = sorted({r["region"] for r in raw["country"]})
    cats = sorted({r["category"] for r in raw["industry"]})
    etypes = sorted({d["event_type"] for d in raw["disruption"]})
    x = {
        "country": onehot([r["region"] for r in raw["country"]], regions),
        "industry": onehot([r["category"] for r in raw["industry"]], cats),
        "port": np.array([[r["cap"]] for r in raw["port"]], dtype=np.float32),
        "route": np.array([[r["transit_days"] / 30.0, r["cap"]] for r in raw["route"]], dtype=np.float32),
    }
    # (src_type, rel, dst_type): (pairs, src_map, dst_map)
    spec = {
        ("country", "has_industry", "industry"): (raw["has_industry"], ids["country"], ids["industry"]),
        ("industry", "supplies", "industry"): (raw["supplies"], ids["industry"], ids["industry"]),
        ("industry", "uses_port", "port"): (raw["uses_port"], ids["industry"], ids["port"]),
        ("port", "located_in", "country"): (raw["located_in"], ids["port"], ids["country"]),
        ("route", "from_port", "port"): (raw["from_port"], ids["route"], ids["port"]),
        ("route", "to_port", "port"): (raw["to_port"], ids["route"], ids["port"]),
    }
    edges = {}
    for et, (pairs, sm, dm) in spec.items():
        src = [sm[p[0]] for p in pairs]
        dst = [dm[p[1]] for p in pairs]
        w = [float(p[2]) if len(p) > 2 else 1.0 for p in pairs]
        edges[et] = (src, dst, w)

    # dense matrices for the simulator
    U = np.zeros((nI, nP)); A = np.zeros((nI, nI)); C = np.zeros((nC, nI)); R2P = np.zeros((nP, nR))
    for s, d, w in zip(*edges[("industry", "uses_port", "port")]): U[s, d] += w
    for s, d, w in zip(*edges[("industry", "supplies", "industry")]): A[d, s] += w  # buyer d exposed to supplier s
    for s, d, w in zip(*edges[("country", "has_industry", "industry")]): C[s, d] = 1
    C = C / np.maximum(C.sum(1, keepdims=True), 1)
    for k in ("from_port", "to_port"):
        for s, d, w in zip(*edges[("route", k, "port")]): R2P[d, s] = 1
    return dict(ids=ids, x=x, edges=edges, U=U, A=A, C=C, R2P=R2P, etypes=etypes,
                cap_port=x["port"][:, 0], cap_route=x["route"][:, 1], n=dict(I=nI, P=nP, R=nR, C=nC))


# ----------------------------------------------------------------------
# 3. Scenario simulator = labels (ASSUMED RULE, not real data)
# ----------------------------------------------------------------------
def simulate(S, sev, dur, targets):
    mag = (sev / SEV_MAX) * (0.5 + 0.5 * min(dur, DUR_MAX) / DUR_MAX)
    port = np.zeros(S["n"]["P"]); route = np.zeros(S["n"]["R"])
    for kind, t in targets:
        if kind == "port":
            port[t] = max(port[t], mag * (1 - 0.3 * S["cap_port"][t]))
        else:
            route[t] = max(route[t], mag * (1 - 0.3 * S["cap_route"][t]))
    port = np.clip(port + ROUTE_TO_PORT * (S["R2P"] @ route), 0, 1)
    ind0 = np.clip(S["U"] @ port, 0, 1)
    ind = ind0.copy()
    for _ in range(SUPPLY_ITERS):
        ind = np.clip(ind0 + SUPPLY_DAMP * (S["A"] @ ind), 0, 1)
    return dict(port=port, industry=ind, country=S["C"] @ ind)


def make_scenario(S, d, targets):
    """d: dict(event_type, severity, duration_days); targets: [('port'|'route', idx)]"""
    y = simulate(S, d["severity"], d["duration_days"], targets)
    data = HeteroData()
    for nt, arr in S["x"].items():
        data[nt].x = torch.tensor(arr)
    dv = np.concatenate([[d["severity"] / SEV_MAX, d["duration_days"] / DUR_MAX],
                         onehot([d["event_type"]], S["etypes"])[0]]).astype(np.float32)
    data["disruption"].x = torch.tensor(dv).view(1, -1)
    for (s_t, rel, d_t), (src, dst, w) in S["edges"].items():
        ei = torch.tensor([src, dst], dtype=torch.long); wt = torch.tensor(w, dtype=torch.float)
        data[(s_t, rel, d_t)].edge_index, data[(s_t, rel, d_t)].edge_weight = ei, wt
        data[(d_t, "rev_" + rel, s_t)].edge_index, data[(d_t, "rev_" + rel, s_t)].edge_weight = ei.flip(0), wt
    for kind in ("port", "route"):  # always both, so every scenario has the same edge types
        idx = [t for k, t in targets if k == kind]
        ei = torch.tensor([[0] * len(idx), idx], dtype=torch.long).view(2, -1)
        wt = torch.ones(len(idx))
        data[("disruption", "affects", kind)].edge_index = ei
        data[("disruption", "affects", kind)].edge_weight = wt
        data[(kind, "rev_affects", "disruption")].edge_index = ei.flip(0)
        data[(kind, "rev_affects", "disruption")].edge_weight = wt
    for nt, arr in y.items():
        data[nt].y = torch.tensor(arr, dtype=torch.float)
    return data


def random_scenario(S, held_out=False):
    kind = "port" if rng.random() < 0.55 else "route"
    n = S["n"]["P"] if kind == "port" else S["n"]["R"]
    # held-out targets: last port and last route are never used for training
    t = int(rng.integers(0, n - 1)) if not held_out else n - 1
    d = dict(event_type=str(rng.choice(S["etypes"])), severity=int(rng.integers(1, int(SEV_MAX) + 1)),
             duration_days=int(rng.integers(2, int(DUR_MAX))))
    return make_scenario(S, d, [(kind, t)])


def real_scenarios(S, raw):
    out = []
    # PERF: group AFFECTS edges by disruption in ONE pass,
    # instead of re-scanning the full edge list for every disruption
    by_disruption = {}
    for a, b in raw["affects"]:
        by_disruption.setdefault(a, []).append(b)
    for d in raw["disruption"]:
        targets = []
        # lookup is O(1) now; target order is the same as before
        for b in by_disruption.get(d["id"], []):
            if b in S["ids"]["port"]: targets.append(("port", S["ids"]["port"][b]))
            elif b in S["ids"]["route"]: targets.append(("route", S["ids"]["route"][b]))
        if targets:
            out.append(make_scenario(S, d, targets))
    return out


# ----------------------------------------------------------------------
# 4. Model
# ----------------------------------------------------------------------
class HeteroGNN(nn.Module):
    """layers = number of hops the model can see. The country-level ripple
    needs ~5 hops: disruption->route->port->industry->industry->country."""

    def __init__(self, sample, layers):
        super().__init__()
        self.enc = nn.ModuleDict({nt: nn.Linear(sample[nt].x.shape[1], HIDDEN) for nt in sample.node_types})
        self.convs = nn.ModuleList(
            HeteroConv({et: GraphConv(HIDDEN, HIDDEN, aggr="mean") for et in sample.edge_types}, aggr="sum")
            for _ in range(layers))
        self.heads = nn.ModuleDict({nt: nn.Linear(HIDDEN, 1) for nt in ("port", "industry", "country")})

    def forward(self, b):
        h = {nt: F.relu(self.enc[nt](x)) for nt, x in b.x_dict.items()}
        ew = {et: b[et].edge_weight for et in b.edge_types}
        for conv in self.convs:
            out = conv(h, b.edge_index_dict, edge_weight_dict=ew)
            h = {nt: h[nt] + F.relu(out[nt]) for nt in h}  # residual keeps deep stacks trainable
        out = {nt: self.heads[nt](h[nt]).squeeze(-1) for nt in self.heads}
        # linear head while training (sigmoid saturated and got stuck at 0); clamp to 0..1 when predicting
        return out if self.training else {nt: v.clamp(0, 1) for nt, v in out.items()}


TYPES = ("port", "industry", "country")


@torch.no_grad()
def evaluate(predict, loader):
    errs = {t: [] for t in TYPES}; hits = []
    for b in loader:
        pred = predict(b)
        for t in TYPES:
            errs[t].append((pred[t] - b[t].y).abs())
        B = b["disruption"].x.shape[0]
        p, y = pred["industry"].view(B, -1), b["industry"].y.view(B, -1)
        for i in range(B):  # did it find the most-affected industries?
            k = min(5, int((y[i] > 0.01).sum()))
            if k:
                hits.append(len(set(p[i].topk(k).indices.tolist()) & set(y[i].topk(k).indices.tolist())) / k)
    res = {t: torch.cat(errs[t]).mean().item() for t in TYPES}
    res["top5"] = float(np.mean(hits)) if hits else float("nan")
    return res


def fit(layers, train_loader, val_loader, sample):
    model = HeteroGNN(sample, layers)
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    best, state = 1e9, None
    for _ in range(EPOCHS):
        model.train()
        for b in train_loader:
            opt.zero_grad(set_to_none=True)  # PERF: frees old gradients instead of writing zeros each step
            out = model(b)
            loss = sum(F.mse_loss(out[t], b[t].y) for t in TYPES)
            loss.backward(); opt.step()
        model.eval()
        v = evaluate(model, val_loader)
        score = v["port"] + v["industry"] + v["country"]
        if score < best:
            best, state = score, {k: t.clone() for k, t in model.state_dict().items()}
    model.load_state_dict(state); model.eval()
    return model


def row(name, r):
    return f"{name:<26}{r['port']:>8.4f}{r['industry']:>10.4f}{r['country']:>9.4f}{r['top5']:>8.2f}"


def demo(model, S, raw, scen, disruption_id):
    """Show what the dashboard would receive for one real disruption: GNN vs rule."""
    i = [d["id"] for d in raw["disruption"]].index(disruption_id)
    d = raw["disruption"][i]
    sc = scen[i]
    with torch.no_grad():
        pred = model(next(iter(DataLoader([sc], batch_size=1))))
    print(f"\nDEMO {disruption_id}: {d['event_type']} severity {d['severity']} for {d['duration_days']} days"
          f" -> target {[b for a, b in raw['affects'] if a == disruption_id]}")
    print(f"{'country':<8}{'rule':>8}{'GNN':>8}")
    for c, r in enumerate(raw["country"]):
        print(f"{r['id']:<8}{sc['country'].y[c]:>8.3f}{pred['country'][c]:>8.3f}")
    top = pred["industry"].topk(5).indices.tolist()
    print("top-5 industries by GNN (rule value in brackets):",
          ", ".join(f"{raw['industry'][j]['id']} {pred['industry'][j]:.2f} [{sc['industry'].y[j]:.2f}]" for j in top))


if __name__ == "__main__":
    if USE_NEO4J:
        raw, src = fetch_from_neo4j(), "Neo4j"
    elif os.path.isdir(CSV_DIR):
        raw, src = load_from_csv(CSV_DIR), f"CSV files in {CSV_DIR}"
    else:
        raw, src = make_mock_raw(), "MOCK (same counts/fields as real)"
    S = build_static(raw)
    print("source:", src, "| nodes:", S["n"], "| disruptions:", len(raw["disruption"]))

    train = [random_scenario(S) for _ in range(N_SYNTH)]
    val = [random_scenario(S) for _ in range(100)]
    test = [random_scenario(S) for _ in range(150)]
    unseen = [random_scenario(S, held_out=True) for _ in range(100)]
    real = real_scenarios(S, raw)
    mk = lambda ds, sh=False: DataLoader(ds, batch_size=64, shuffle=sh)
    tl, vl = mk(train, True), mk(val)

    # baselines that ignore the disruption
    mean_y = {t: torch.stack([d[t].y for d in train]).mean(0) for t in TYPES}
    zero = lambda b: {t: torch.zeros_like(b[t].y) for t in TYPES}
    avg = lambda b: {t: mean_y[t].repeat(b["disruption"].x.shape[0]) for t in TYPES}

    models = {L: fit(L, tl, vl, train[0]) for L in (1, 3, 5)}
    for title, ds in (("TEST: random scenarios", test), ("TEST: unseen port/route targets", unseen),
                      ("TEST: the 10 real disruption rows (rule labels)", real)):
        if not ds: continue
        print(f"\n{title}\n{'model':<26}{'port':>8}{'industry':>10}{'country':>9}{'top5':>8}   (MAE, lower=better; top5 higher=better)")
        l = mk(ds)
        print(row("Predict zero (no ripple)", evaluate(zero, l)))
        print(row("Per-node average", evaluate(avg, l)))
        for L, m in models.items():
            print(row(f"GNN {L}-layer", evaluate(m, l)))
    if len(real) == len(raw["disruption"]) and raw["disruption"]:
        did = raw["disruption"][min(1, len(real) - 1)]["id"]
        demo(models[5], S, raw, real, did)
    torch.save(models[5].state_dict(), "atmograph_hetero_gnn.pt")


import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GraphConv

SEED = 42
TIERS = (20, 30, 30, 20)  # raw suppliers -> manufacturers -> distributors -> retailers
N_SCENARIOS = 800
EPOCHS = 80
HIDDEN = 64

rng = np.random.default_rng(SEED)
torch.manual_seed(SEED)


# ----------------------------------------------------------------------
# 1. Graph (replace with Neo4j export later)
# ----------------------------------------------------------------------
def build_graph():
    tier = np.concatenate([[t] * n for t, n in enumerate(TIERS)])
    N = len(tier)
    dep = np.zeros((N, N))  # dep[v, u] = how much customer v depends on supplier u
    for t in range(len(TIERS) - 1):
        suppliers = np.where(tier == t)[0]
        customers = np.where(tier == t + 1)[0]
        for v in customers:
            k = rng.integers(1, 4)
            for u in rng.choice(suppliers, size=min(k, len(suppliers)), replace=False):
                dep[v, u] = rng.uniform(0.3, 1.0)
    row_sum = dep.sum(1, keepdims=True)
    dep = np.divide(dep, row_sum, out=np.zeros_like(dep), where=row_sum > 0)

    buffer = rng.uniform(0.0, 0.7, N)       # inventory buffer: absorbs shocks
    capacity = rng.uniform(0.2, 1.0, N)
    region_risk = rng.uniform(0.0, 1.0, N)  # the "Atmo" part: weather/atmospheric exposure
    return tier, dep, buffer, capacity, region_risk


tier, dep, buffer, capacity, region_risk = build_graph()
N = len(tier)
dst, src = np.nonzero(dep)  # edge u -> v  (supplier -> customer)
edge_index = torch.tensor(np.stack([src, dst]), dtype=torch.long)
edge_weight = torch.tensor(dep[dst, src], dtype=torch.float)
tier_onehot = np.eye(len(TIERS))[tier]


# ----------------------------------------------------------------------
# 2. Ripple simulator = ground-truth labels
#    WARNING: labels come from a rule I wrote. A GNN matching it proves the
#    pipeline works, NOT that it predicts real supply chains. Real labels
#    (historical disruptions) are what make this project meaningful.
# ----------------------------------------------------------------------
def simulate(shock, hops=len(TIERS) - 1):
    impact = shock.copy()
    for _ in range(hops):
        impact = np.clip(shock + (1 - buffer) * (dep @ impact), 0, 1)
    return impact


def make_scenario():
    shock = np.zeros(N)
    candidates = np.where(tier <= 1)[0]
    hit = rng.choice(candidates, size=rng.integers(1, 4), replace=False)
    shock[hit] = rng.uniform(0.5, 1.0, len(hit)) * (0.5 + 0.5 * region_risk[hit])
    y = simulate(shock)
    static = np.column_stack([tier_onehot, buffer, capacity, region_risk])
    x = np.column_stack([static, shock])
    return Data(
        x=torch.tensor(x, dtype=torch.float),
        y=torch.tensor(y, dtype=torch.float),
        edge_index=edge_index,
        edge_weight=edge_weight,
    )


dataset = [make_scenario() for _ in range(N_SCENARIOS)]
n_tr, n_va = int(0.7 * N_SCENARIOS), int(0.15 * N_SCENARIOS)
train, val, test = dataset[:n_tr], dataset[n_tr:n_tr + n_va], dataset[n_tr + n_va:]
train_loader = DataLoader(train, batch_size=32, shuffle=True)
val_loader = DataLoader(val, batch_size=64)
test_loader = DataLoader(test, batch_size=64)
in_dim = dataset[0].x.shape[1]


# ----------------------------------------------------------------------
# 3. Models
# ----------------------------------------------------------------------
class GNN(nn.Module):
    """num_layers = how many hops of ripple the model can 'see'."""

    def __init__(self, num_layers=3):
        super().__init__()
        dims = [in_dim] + [HIDDEN] * num_layers
        self.convs = nn.ModuleList(
            GraphConv(dims[i], dims[i + 1], aggr="add") for i in range(num_layers)
        )
        self.out = nn.Linear(HIDDEN, 1)

    def forward(self, d):
        h = d.x
        for conv in self.convs:
            h = F.relu(conv(h, d.edge_index, d.edge_weight))
        return torch.sigmoid(self.out(h)).squeeze(-1)


class MLP(nn.Module):
    """Baseline with NO graph: each node only sees its own features."""

    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, HIDDEN), nn.ReLU(),
            nn.Linear(HIDDEN, HIDDEN), nn.ReLU(),
            nn.Linear(HIDDEN, 1), nn.Sigmoid(),
        )

    def forward(self, d):
        return self.net(d.x).squeeze(-1)


# ----------------------------------------------------------------------
# 4. Train / evaluate
# ----------------------------------------------------------------------
@torch.no_grad()
def evaluate(model, loader):
    model.eval()
    abs_all, abs_ripple = [], []
    for d in loader:
        err = (model(d) - d.y).abs()
        abs_all.append(err)
        abs_ripple.append(err[d.x[:, -1] == 0])  # only nodes NOT directly shocked
    return torch.cat(abs_all).mean().item(), torch.cat(abs_ripple).mean().item()


def fit(model, name):
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    best_val, best_state = 1e9, None
    for epoch in range(EPOCHS):
        model.train()
        for d in train_loader:
            opt.zero_grad()
            F.mse_loss(model(d), d.y).backward()
            opt.step()
        v_all, v_rip = evaluate(model, val_loader)
        if v_rip < best_val:  # select on ripple error, the metric that matters
            best_val = v_rip
            best_state = {k: t.clone() for k, t in model.state_dict().items()}
    model.load_state_dict(best_state)
    t_all, t_rip = evaluate(model, test_loader)
    print(f"{name:<28} test MAE all={t_all:.4f}   ripple-only={t_rip:.4f}")
    return model


if __name__ == "__main__":
    # Naive baseline: predict impact = own shock (assumes NO ripple at all)
    naive = [(d.x[:, -1] - d.y).abs() for d in test_loader.dataset]
    naive_all = torch.cat(naive).mean().item()
    naive_rip = torch.cat([e[d.x[:, -1] == 0] for e, d in zip(naive, test_loader.dataset)]).mean().item()
    print(f"{'Naive (impact = shock)':<28} test MAE all={naive_all:.4f}   ripple-only={naive_rip:.4f}")

    fit(MLP(), "MLP (no graph)")
    fit(GNN(num_layers=1), "GNN 1-layer (1 hop)")
    model = fit(GNN(num_layers=3), "GNN 3-layer (3 hops)")

    torch.save(model.state_dict(), "atmograph_gnn.pt")
    print("saved atmograph_gnn.pt")

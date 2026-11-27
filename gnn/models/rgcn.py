
import torch
import torch.nn as nn
import torch.nn.functional as F

from torch_geometric.nn import RGCNConv


class AtmoGraphRGCN(nn.Module):

    def __init__(
        self,
        in_channels=10,
        hidden_channels=32,
        num_relations=7,
        dropout=0.3
    ):
        super().__init__()

        self.dropout = dropout

        # First relational graph convolution
        self.conv1 = RGCNConv(
            in_channels,
            hidden_channels,
            num_relations=num_relations,
            num_bases=min(4, num_relations)
        )

        # Second relational graph convolution
        self.conv2 = RGCNConv(
            hidden_channels,
            hidden_channels,
            num_relations=num_relations,
            num_bases=min(4, num_relations)
        )

        # Node-level disruption risk prediction
        self.output_layer = nn.Linear(
            hidden_channels, 1
        )

    def forward(self, x, edge_index, edge_type):

        # Layer 1
        x = self.conv1(x, edge_index, edge_type)
        x = F.relu(x)

        x = F.dropout(
            x,
            p=self.dropout,
            training=self.training
        )

        # Layer 2
        x = self.conv2(x, edge_index, edge_type)
        x = F.relu(x)

        # Return raw logits for training
        logits = self.output_layer(x)

        return logits.squeeze(-1)

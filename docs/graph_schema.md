# Neo4j Graph Schema

Node labels: `Country`, `Industry`, `Port`, `ShippingRoute`, `Disruption`.

Relationships:
- `Country -HAS_INDUSTRY-> Industry`
- `Industry -SUPPLIES-> Industry` (supplier to buyer)
- `Industry -USES_PORT-> Port`
- `Port -FROM_PORT-> ShippingRoute -TO_PORT-> Port`
- `Disruption -AFFECTS-> Port`
- `Disruption -AFFECTS-> ShippingRoute`

Stable IDs are used with `MERGE` so repeated loads do not create duplicate nodes/relationships.

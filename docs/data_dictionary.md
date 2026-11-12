# AtmoGraph Synthetic Data Dictionary

**All records in `data/synthetic/` are synthetic and illustrative, not real trade or shipping observations.**

| CSV | Purpose | Primary key |
|---|---|---|
| countries.csv | Country nodes | country_id |
| industries.csv | Country-specific industry nodes | industry_id |
| transactions.csv | Directed supplier-to-buyer links | transaction_id |
| ports.csv | Illustrative port nodes | port_id |
| shipping_routes.csv | Directed port-to-port route nodes | route_id |
| industry_port_links.csv | Industry-to-port associations | link_id |
| disruptions.csv | Events targeting a port or route | disruption_id |

## Schema

- `countries.csv`: `country_id` (unique ID), `country_name`, `region`.
- `industries.csv`: `industry_id` (unique country-specific ID such as `IND_AUTO`), `industry_name`, `country_id` (FK to countries), `industry_category`.
- `transactions.csv`: `transaction_id`, `supplier_industry_id` (FK), `buyer_industry_id` (FK), `transaction_value_usd` (illustrative USD), `dependency_strength` (synthetic 0–1 score, not a probability), `product_category`, `reference_year`, `is_synthetic`.
- `ports.csv`: `port_id`, `port_name`, `country_id` (FK), `capacity_index` (illustrative index), `is_synthetic`.
- `shipping_routes.csv`: `route_id`, `source_port_id` and `destination_port_id` (FKs to ports), `transit_days`, `route_capacity_index`, `is_synthetic`.
- `industry_port_links.csv`: `link_id`, `industry_id` (FK), `port_id` (FK), `usage_type` (IMPORT/EXPORT/BOTH), `share` (0–1 illustrative value), `is_synthetic`.
- `disruptions.csv`: `disruption_id`, `event_type`, `target_type` (PORT/SHIPPING_ROUTE), `target_id` (FK to target), `severity` (1–5 ordinal score), `start_date` (YYYY-MM-DD), `duration_days`, `is_synthetic`.

## Neo4j mapping
- `(Country)-[:HAS_INDUSTRY]->(Industry)`
- `(SupplierIndustry)-[:SUPPLIES]->(BuyerIndustry)`
- `(Industry)-[:USES_PORT]->(Port)`
- `(Port)-[:FROM_PORT]->(ShippingRoute)-[:TO_PORT]->(Port)`
- `(Disruption)-[:AFFECTS]->(Port or ShippingRoute)`

The loader does not calculate downstream impact. Propagation/simulation is a later module.

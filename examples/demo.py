"""Seven vendor records: typos, a trading name, and two look-alike companies with different tax IDs."""

from __future__ import annotations

import polars as pl

from entity_resolution_gate import resolve

RECORDS = [
    # rid, name, address, zip, tax_id, truth
    (0, "Aegis Falcon Defense LLC", "120 Main St", "20001", "11-1111111", "A"),
    (1, "Aegis Falcon Defence", "120 Main Street", "20001", None, "A"),
    (2, "AEGIS FALCON DEFENSE INC", "120 Main St", None, "11-1111111", "A"),
    (3, "Aegis Falcon Defense LLC", "120 Main St", "20001", "22-2222222", "B"),  # twin, other tax id
    (4, "Boreal Systems Inc", "9 Harbor Rd", "10002", None, "C"),
    (5, "The Boreal Systems", "9 Harbor Rd", "10002", None, "C"),
    (6, "Zenith Logistics Co", "77 Oak Ave", "30003", "33-3333333", "D"),
]


def main() -> None:
    df = pl.DataFrame(
        RECORDS, schema=["rid", "name", "address", "zip", "tax_id", "entity_id"], orient="row"
    )
    out, log = resolve(df)
    print(out.select("rid", "name", "tax_id", "entity_id", "cluster_id").sort("cluster_id", "rid"))
    print("\naudit log (what the gate decided and why):")
    for e in log.events:
        if e["kind"] in ("edge_blocked", "component_split"):
            print(" ", e)
    print(f"  ... plus {sum(e['kind'] == 'edge_accepted' for e in log.events)} accepted edges")


if __name__ == "__main__":
    main()

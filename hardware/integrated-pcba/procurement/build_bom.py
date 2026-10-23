"""Build a review BOM from observed candidates and the actual compact PCB.

This does not qualify parts, change the circuit, or produce an order-ready BOM.
"""
import csv
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
availability = json.loads((OUT / "jlc-availability.json").read_text())
bindings = json.loads((ROOT / "lceda-pro/footprint-bindings-draft.json").read_text())["bindings"]
design = {r["Reference"]: r for r in csv.DictReader(
    (ROOT / "schematic/mainboard-bom-draft.csv").open())}
records = [tuple(json.loads(s) for s in line.rstrip("|").split("||"))
           for line in (ROOT / "lceda-pro/pcb-compact-source.txt").read_text().splitlines()]
components = {h["id"]: b for h, b in records if h["type"] == "COMPONENT"}
attrs = {}
for h, b in records:
    if h["type"] == "ATTR":
        attrs.setdefault(b["parentId"], {})[b["key"]] = b["value"]
native = {attrs[c]["Designator"]: attrs[c] for c in components}
selected = {}
for part in availability["parts"]:
    for ref in part["references"]:
        assert ref not in selected, f"Duplicate reference: {ref}"
        selected[ref] = part
assert set(native) == set(design) == set(selected), "Missing/extra component references"
for ref in native:
    assert native[ref]["Footprint"] == bindings[ref]["uuid"], f"Stale footprint binding: {ref}"

columns = ["References", "Quantity", "Design value", "Manufacturer", "MPN", "LCSC",
           "Native footprint", "Library", "JLC stock observed", "Reference CNY each",
           "Qualification note"]
with (OUT / "bom-review.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    for part in availability["parts"]:
        refs = part["references"]
        footprints = {bindings[r]["name"] for r in refs}
        values = {design[r]["Value"] for r in refs}
        assert len(footprints) == 1, f"Incompatible footprints grouped: {refs}"
        writer.writerow(dict(zip(columns, [
            ",".join(refs), len(refs), " / ".join(sorted(values)), part["manufacturer"],
            part["mpn"], part["lcsc"], next(iter(footprints)), part["library"],
            part["jlc_stock"], part["jlc_unit_price_cny"], part["note"]])))

priced = [p for p in availability["parts"] if p["jlc_stock"] is not None and
          p["jlc_stock"] >= len(p["references"])]
subtotal = sum((Decimal(str(p["jlc_unit_price_cny"])) * len(p["references"])
                for p in priced), Decimal(0))
result = {
    "manufacturing_release": False,
    "native_components": len(native),
    "candidate_part_numbers": len(availability["parts"]),
    "matched_references": len(selected),
    "native_footprint_mismatches": [],
    "basic_library_part_numbers": sum(p["library"] == "basic" for p in availability["parts"]),
    "extended_library_part_numbers": sum(p["library"] == "extended" for p in availability["parts"]),
    "components_with_sufficient_observed_inventory": sum(len(p["references"]) for p in priced),
    "reference_parts_subtotal_excluding_unconfirmed_inventory_cny": str(subtotal),
    "excluded_from_subtotal": [p["lcsc"] for p in availability["parts"] if p not in priced],
    "actual_pcba_total_cny": None,
    "note": "Reference parts only; no procurement qualification or manufacturer order matching implied."
}
(OUT / "bom-review-checks.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, ensure_ascii=False, indent=2))

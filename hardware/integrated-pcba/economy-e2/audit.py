"""Recompute candidate rejection bounds; unknown manufacturing costs stay unknown."""
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
selection = json.loads((ROOT / 'selection.json').read_text())
parts = selection['parts']
assert len({p['lcsc'] for p in parts}) == len(parts)
fee_parts = [p for p in parts if not p['fee_free']]
assert {p['role'] for p in fee_parts} == {
    'main', 'mic', 'crystal', 'usb', 'battery_connector'
}
lines = []
for p in parts:
    installed = p['per_board'] * 2
    purchase = max(installed + p['loss_in_observed_window'],
                   p['minimum_in_observed_window'])
    lines.append({'role': p['role'], 'lcsc': p['lcsc'],
                  'installed_two_boards': installed,
                  'purchase_qty_budget': purchase,
                  'material_cny': str(Decimal(p['unit_price_cny']) * purchase)})
setup = Decimal(20) * len(fee_parts)
engineering = Decimal(50)
# Deliberately excludes several nonnegative expenses. Only a rejection bound,
# never a complete quote or a purported global optimum.
floor_roles = {'main', 'mic', 'crystal', 'usb'}
floor = setup + engineering + sum(
    Decimal(x['material_cny']) for x in lines if x['role'] in floor_roles)
assert floor == Decimal('165.631')
major_material = sum(Decimal(x['material_cny']) for x in lines)
unknown = [
    'final full BOM including passives, bias/filter, NTC and charge control',
    'new PCB price and coupon applicability',
    'assembly pad count, minimums and processing charges',
    'X-ray applicability to MEMS and ESOP exposed pad',
    'DFM, nitrogen, fixtures, panelization and shipping',
    'SDK chip key compatibility and initial programming tooling/service',
    'new protected battery, matching connector and NTC, separately priced',
]
result = {
    'date': selection['date'], 'boards': 2, 'budget_cny': '160',
    'release': False, 'complete_quote_cny': None,
    'native_eda_schematic': 'NOT CREATED', 'pcb': 'NOT ROUTED',
    'firmware': 'SDK PROBE LINK PASSED; PRODUCT NOT PORTED', 'functional_equivalence': 'NOT VALIDATED',
    'known_fee_types': len(fee_parts), 'setup_budget_cny': str(setup),
    'major_components_only_cny': str(major_material),
    'selected_candidate_rejection_lower_bound_cny': str(floor),
    'selected_candidate_exceeds_budget_before_remaining_costs': floor > Decimal(160),
    'global_infeasibility_proven': False,
    'quantity_note': 'Recomputed for 2 boards from a replacement window for 20; new BOM confirmation required',
    'lines': lines, 'unpriced_not_zero': unknown,
    'module_regular_purchase_lower_bound_cny': str(Decimal(80)+50+Decimal('16.23')*2),
    'module_full_pack_conditional_subtotal_cny': str(Decimal(65)+50+Decimal('14.9316')*2),
    'module_full_pack_known_major_costs_cny': str(
        Decimal(65)+50+Decimal('14.9316')*2 + sum(
            Decimal(x['material_cny']) for x in lines if x['role'] not in {'main', 'crystal'})),
    'module_full_pack_eligibility_confirmed': False,
}
(ROOT / 'cost-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k: result[k] for k in (
    'known_fee_types', 'setup_budget_cny', 'major_components_only_cny',
    'selected_candidate_rejection_lower_bound_cny', 'complete_quote_cny', 'release'
)}, ensure_ascii=False))

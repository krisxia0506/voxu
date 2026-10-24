"""Electrical design constraints, not a substitute for ERC/DRC or bench tests."""
import json
from pathlib import Path
from mainboard import PARTS

parts = {p["ref"]: p for p in PARTS}
assert len(parts) == len(PARTS)


def net(ref, pin):
    return next(p["net"] for p in parts[ref]["pins"] if p["number"] == str(pin))


def same(*nodes):
    nets = [net(*n) for n in nodes]
    assert None not in nets and len(set(nets)) == 1, (nodes, nets)


same(("U1",11),("U2",4))
assert net("U1",10) is None, "PDM has no WS connection"
same(("U1",9),("U2",1),("R3",1))
same(("U2",5),("C4",1),("U1",2),("U8",7))
same(("U2",2),("U2",3),("C4",2),("U1",39))
assert len(parts["U2"]["pins"]) == 5
same(("J1","A5"),("R7",1))
same(("J1","B5"),("R8",1))
assert net("R7",1) != net("R8",1), "CC resistors must be independent"
same(("U7",2),("U7",3),("J2",1))
same(("U7",1),("J2",2))
same(("U7",10),("U7",11),("U8",12),("U8",13),("SW3",1))
same(("U7",8),("U7",17),("J2",3),("U7",15))
assert net("U7",14) is None, "Safety timer must use default; never ground it to disable"
assert net("U7",6) == "CHG_INHIBIT"
assert net("U7",5) == "USB_3V3"
assert net("U7",15) == "GND", "BQ24075 SYSOFF must not float"
same(("U8",11),("L1",1)); same(("U8",9),("L1",2))
same(("U8",5),("R22",2),("R23",1))
same(("U8",14),("SW3",2),("R24",1))
for ref in ("U4", "U5"):
    assert net(ref,8) == "3V3"
assert net("U6",8) == "USB_3V3"
assert net("U4",2) != net("U4",6), "USB TX must cross Ioff buffer"
assert net("U6",2) != net("U6",6), "ESP TX must cross USB-domain Ioff buffer"
assert all(net("U1",p) is None for p in range(17,23)), "Internal flash pins cannot be reused"

# Discrete boot interlock truth table; digital 1/0 are electrical levels.
boot_table=[]
for dtr,rts in [(0,0),(0,1),(1,0),(1,1)]:
    en = int(not (dtr > rts))
    boot = int(not (rts > dtr))
    boot_table.append(dict(dtr=dtr,rts=rts,en=en,gpio0=boot))
assert [(v["en"],v["gpio0"]) for v in boot_table] == [(1,1),(1,0),(0,1),(1,1)]

# TI BQ24075 SLUS810N Tables: K_ILIM max1720, K_ISET797..975.
input_limit_max = 1720/(3900*.99)
input_limit_min = 1330/(3900*1.01)
charge_min = 797/(8660*1.01)
charge_max = 975/(8660*.99)
assert 8660*1.01 <= 8900
# 50mA is a design allocation, NOT a guaranteed CP2102N maximum (only typ given).
assert input_limit_max + .050 < .500
vout_min = .8*.99*(1+470e3*.99/(150e3*1.01))
vout_max = .8*1.01*(1+470e3*1.01/(150e3*.99))
assert 3.0 < vout_min < vout_max < 3.6
# VBUS sense must tolerate divider error and 150uA input leakage.
top=2210*1.01; bottom=10000*.99
sense_min=4.35*bottom/(top+bottom)-150e-6*(top*bottom/(top+bottom))
assert sense_min > 3.6-.6

report={
    "status":"electrical draft constraints passed; not manufacturing approval",
    "part_count":len(PARTS), "boot_truth_table":boot_table,
    "charger_input_current_A":[input_limit_min,input_limit_max],
    "charge_current_A":[charge_min,charge_max],
    "regulated_output_V":[vout_min,vout_max],
    "vbus_sense_min_V":sense_min,
    "usb_current_allocation_A":.050,
    "release_blockers":[
        "CP2102N BCD provisioning settings must be verified on hardware; GPIO latch alone is insufficient",
        "USB current allocation is not measured worst-case or USB compliance certification",
        "Battery SKU, NTC curve, current ratings, connector polarity unqualified",
        "Native PCB routing DRC passed separately; DFM, stencil and signal integrity review pending",
        "Actual JLC BOM matching, pricing and SPH0655 stock reservation pending",
        "Native schematic DRC recorded separately; transistor transient/rail sequencing not simulated",
    ]
}
Path(__file__).with_name("electrical-checks.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))

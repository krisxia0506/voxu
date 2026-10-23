"""Reproducible A2 whole-board electrical draft. NOT a fabrication release.

Pins are explicit, including unused pins. A null net means intentional NC.
Footprint and purchasing qualification are separate release gates.
"""
import csv
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parent
PARTS = []


def add(ref, value, pins, section, footprint="", lcsc="", note=""):
    PARTS.append(dict(ref=ref, value=value, section=section, footprint=footprint,
                      lcsc=lcsc, note=note,
                      pins=[dict(number=str(n), name=name, net=net, type=kind)
                            for n, name, net, kind in pins]))


def pair(ref, value, a, b, section, footprint=""):
    if not footprint and ref[0] in "RC":
        family = "Resistor" if ref[0] == "R" else "Capacitor"
        footprint = f"{family}_SMD:{ref[0]}_0603_1608Metric"
    add(ref, value, [(1, "1", a, "passive"), (2, "2", b, "passive")], section, footprint)


def ic(ref, value, names, nets, section, outputs=(), footprint="", lcsc="", note=""):
    add(ref, value, [(i, name, nets.get(i),
                     "power_out" if i in outputs else
                     "power_in" if name in ("GND", "VSS", "PGND", "EP", "VCC", "VDD", "3V3", "VIN", "VREGIN")
                     else "passive") for i, name in enumerate(names.split(), 1)],
        section, footprint, lcsc, note)


# ESP32-WROOM-32E datasheet Table 3. The exposed pad is also grounded.
ic("U1", "ESP32-WROOM-32E-N4",
   "GND 3V3 EN VP VN IO34 IO35 IO32 IO33 IO25 IO26 IO27 IO14 IO12 GND IO13 NC NC NC NC NC NC IO15 IO2 IO0 IO4 IO16 IO17 IO5 IO18 IO19 NC IO21 RXD0 TXD0 IO22 IO23 GND EP",
   {1:"GND", 2:"3V3", 3:"ESP_EN", 9:"MIC_SD", 10:"MIC_WS", 11:"MIC_BCLK",
    15:"GND", 25:"ESP_BOOT", 34:"ESP_RX", 35:"ESP_TX", 38:"GND", 39:"GND"},
   "MCU", footprint="RF_Module:ESP32-WROOM-32E", lcsc="C701341")
pair("R1", "10k 1%", "3V3", "ESP_EN", "MCU")
pair("R2", "10k 1%", "3V3", "ESP_BOOT", "MCU")
pair("C1", "1u 10V X7R", "ESP_EN", "GND", "MCU")
pair("C2", "10u 10V X5R", "3V3", "GND", "MCU", "Capacitor_SMD:C_0805_2012Metric")
pair("C3", "100n 10V X7R", "3V3", "GND", "MCU")
pair("SW1", "RESET push button", "ESP_EN", "GND", "MCU")
pair("SW2", "DICTATE / BOOT push button", "ESP_BOOT", "GND", "MCU")

ic("U2", "INMP441", "SCK SD WS LR GND GND VDD CHIPEN GND",
   {1:"MIC_BCLK", 2:"MIC_SD", 3:"MIC_WS", 4:"GND", 5:"GND", 6:"GND",
    7:"3V3", 8:"3V3", 9:"GND"}, "MIC", lcsc="C5438445",
   note="Primary; live stock, acoustic land pattern and reflow process not yet qualified")
pair("R3", "100k 1%", "MIC_SD", "GND", "MIC")
pair("C4", "100n 10V X7R", "3V3", "GND", "MIC")

# CP2102N QFN28. Requires one-time BCD GPIO/descriptor provisioning.
ic("U3", "CP2102N-A02-GQFN28",
   "DCD RI GND DP DM VDD VREGIN VBUS RST NC SUSPENDn SUSPEND CHREN CHR1 CHR0 GPIO3 GPIO2 GPIO1 GPIO0 GPIO6 GPIO5 GPIO4 CTS RTS RXD TXD DSR DTR EP",
   {3:"GND", 4:"USB_DP", 5:"USB_DM", 6:"USB_3V3", 7:"VBUS", 8:"VBUS_SENSE",
    9:"USB_RESET", 15:"USB_ALLOW_500", 24:"USB_RTS", 25:"USB_RX", 26:"USB_TX",
    28:"USB_DTR", 29:"GND"}, "USB", outputs=(6,),
   footprint="VOXU:VOXU_CP2102N_QFN28",
   note="Candidate replacing CH340C to implement BC1.2/suspend current control; price and provisioning pending")
pair("R4", "10k 1%", "USB_3V3", "USB_RESET", "USB")
pair("R5", "2.21k 1%", "VBUS", "VBUS_SENSE", "USB")
pair("R6", "10k 1%", "VBUS_SENSE", "GND", "USB")
pair("C5", "4.7u 10V X5R", "USB_3V3", "GND", "USB")
pair("C6", "100n 10V X7R", "USB_3V3", "GND", "USB")
pair("C7", "100n 10V X7R", "VBUS", "GND", "USB")
pair("R7", "5.1k 1%", "CC1", "GND", "USB")
pair("R8", "5.1k 1%", "CC2", "GND", "USB")
add("J1", "USB-C USB2 receptacle",
    [(n, name, net, "passive") for n,name,net in
     [("A1","GND","GND"),("A4","VBUS","VBUS"),("A5","CC1","CC1"),
      ("A6","DP","USB_DP"),("A7","DM","USB_DM"),("A8","SBU1",None),
      ("A9","VBUS","VBUS"),("A12","GND","GND"),("B1","GND","GND"),
      ("B4","VBUS","VBUS"),("B5","CC2","CC2"),("B6","DP","USB_DP"),
      ("B7","DM","USB_DM"),("B8","SBU2",None),("B9","VBUS","VBUS"),
      ("B12","GND","GND"),("S1","SHIELD","GND")]], "USB",
    note="Connector MPN, shield pad numbering and footprint must be frozen together")
ic("D1", "USBLC6-2SC6", "IO1 GND IO2 IO2 VBUS IO1",
   {1:"USB_DP", 2:"GND", 3:"USB_DM", 4:"USB_DM", 5:"VBUS", 6:"USB_DP"},
   "USB", footprint="Package_TO_SOT_SMD:SOT-23-6")

# Three identical dual gates avoid different buffer SKUs. Ioff isolates
# both powered-off domains; source-presence gating makes UART idle high.
for ref, supply, nets in [
    ("U4", "3V3", {1:"USB_ISO_OEn", 2:"USB_TX", 6:"ESP_RX", 7:"USB_ISO_OEn", 5:"USB_DTR", 3:"DTR_SYS"}),
    ("U5", "3V3", {1:"USB_ISO_OEn", 2:"USB_RTS", 6:"RTS_SYS", 7:"3V3", 5:"GND"}),
    ("U6", "USB_3V3", {1:"GND", 2:"ESP_TX", 6:"USB_RX", 7:"USB_3V3", 5:"GND"}),
]:
    ic(ref, "SN74LVC2G125DCUR", "1OEn 1A 2Y GND 2A 1Y 2OEn VCC",
       {**nets, 4:"GND", 8:supply}, "ISOLATION",
       footprint="Package_SO:VSSOP-8_2.3x2mm_P0.5mm")
for ref,rail in [("C8","3V3"),("C9","3V3"),("C10","USB_3V3")]:
    pair(ref, "100n 10V X7R", rail, "GND", "ISOLATION")
for ref,net in [("R9","USB_ISO_OEn"),("R10","ESP_RX"),("R11","DTR_SYS"),("R12","RTS_SYS")]:
    pair(ref, "10k 1%", "3V3", net, "ISOLATION")
pair("R13", "10k 1%", "VBUS", "USB_PRESENT_BASE", "ISOLATION")
pair("R14", "100k 1%", "USB_PRESENT_BASE", "GND", "ISOLATION")
ic("Q1", "MMBT3904", "B E C", {1:"USB_PRESENT_BASE", 2:"GND", 3:"USB_ISO_OEn"},
   "ISOLATION", footprint="Package_TO_SOT_SMD:SOT-23")
# Espressif two-transistor download interlock: both asserted cannot reset.
pair("R15", "10k 1%", "DTR_SYS", "EN_BASE", "BOOT")
pair("R16", "10k 1%", "RTS_SYS", "BOOT_BASE", "BOOT")
ic("Q2", "MMBT3904", "B E C", {1:"EN_BASE", 2:"RTS_SYS", 3:"ESP_EN"}, "BOOT", footprint="Package_TO_SOT_SMD:SOT-23")
ic("Q3", "MMBT3904", "B E C", {1:"BOOT_BASE", 2:"DTR_SYS", 3:"ESP_BOOT"}, "BOOT", footprint="Package_TO_SOT_SMD:SOT-23")

# BQ24075: pin 15 is SYSOFF, NOT BQ24074's ITERM.
ic("U7", "BQ24075RGTR", "TS BAT BAT CE EN2 EN1 PGOOD VSS CHG OUT OUT ILIM IN TMR SYSOFF ISET EP",
   {1:"BAT_NTC", 2:"BAT", 3:"BAT", 4:"GND", 5:"USB_3V3", 6:"CHG_INHIBIT",
    8:"GND", 10:"SYS", 11:"SYS", 12:"ILIM", 13:"VBUS", 15:"GND", 16:"ISET", 17:"GND"},
   "CHARGE", outputs=(10,), footprint="VOXU:VOXU_BQ24075_RGT0016C", lcsc="C15464")
pair("R17", "3.9k 1%", "ILIM", "GND", "CHARGE")
pair("R18", "8.66k 1%", "ISET", "GND", "CHARGE")
pair("R19", "10k 1%", "USB_3V3", "CHG_INHIBIT", "CHARGE")
pair("R20", "10k 1%", "USB_ALLOW_500", "CHG_ALLOW_BASE", "CHARGE")
pair("R21", "10k 1%", "USB_ALLOW_500", "GND", "CHARGE")
ic("Q4", "MMBT3904", "B E C", {1:"CHG_ALLOW_BASE", 2:"GND", 3:"CHG_INHIBIT"},
   "CHARGE", footprint="Package_TO_SOT_SMD:SOT-23")
pair("C11", "4.7u 10V X5R", "VBUS", "GND", "CHARGE")
pair("C12", "10u 10V X5R", "BAT", "GND", "CHARGE", "Capacitor_SMD:C_0805_2012Metric")
pair("C13", "10u 10V X5R", "SYS", "GND", "CHARGE", "Capacitor_SMD:C_0805_2012Metric")
add("J2", "1S protected battery + 10k NTC", [(1,"BAT+","BAT","passive"),(2,"NTC","BAT_NTC","passive"),(3,"BAT-","GND","passive")],
    "CHARGE", note="PROVISIONAL pin order. Must match a documented battery SKU; no fabrication before qualification")

ic("U8", "TPS63070RNMR", "PS_SYNC PG VAUX GND FB FB2 VOUT VOUT L2 PGND L1 VIN VIN EN VSEL",
   {1:"GND", 3:"VAUX", 4:"GND", 5:"FB", 6:"GND", 7:"3V3", 8:"3V3",
    9:"SW_L2", 10:"GND", 11:"SW_L1", 12:"SYS", 13:"SYS", 14:"RUN_EN", 15:"GND"},
   "REGULATOR", outputs=(7,), lcsc="C109322", note="RNM asymmetric 15-pin land pattern must be taken from TI drawing; no generic QFN substitute")
pair("L1", "1.5uH XFL4020-152ME", "SW_L1", "SW_L2", "REGULATOR")
pair("R22", "470k 1%", "3V3", "FB", "REGULATOR")
pair("R23", "150k 1%", "FB", "GND", "REGULATOR")
pair("R24", "100k 1%", "RUN_EN", "GND", "REGULATOR")
add("SW3", "RUN SPDT slide", [(1,"ON","SYS","passive"),(2,"COMMON","RUN_EN","passive"),(3,"OFF",None,"passive")], "REGULATOR",
    note="OFF throw unconnected; R24 pulls EN low. Avoid shorting SYS to GND during contact overlap")
pair("C14", "100n 10V X7R", "VAUX", "GND", "REGULATOR")
for ref,rail in [("C15","SYS"),("C16","SYS")]:
    pair(ref, "10u 25V X7S", rail, "GND", "REGULATOR", "Capacitor_SMD:C_0805_2012Metric")
pair("C17", "10u 25V X5R", "SYS", "GND", "REGULATOR")
for ref in ("C18","C19","C20"):
    pair(ref, "22u 16V X6S", "3V3", "GND", "REGULATOR", "Capacitor_SMD:C_0805_2012Metric")
pair("C21", "10u 25V X5R", "3V3", "GND", "REGULATOR")

# Electrical pin types are explicit so native ERC can detect digital conflicts.
KINDS = {
    "U1": {3:"input", 9:"input", 10:"output", 11:"output", 25:"input", 34:"input", 35:"output"},
    "U2": {1:"input", 2:"tri_state", 3:"input", 4:"input", 8:"input"},
    "U3": {1:"input", 2:"input", 4:"bidirectional", 5:"bidirectional", 8:"input", 9:"input",
           11:"output", 12:"output", 13:"output", 14:"output", 15:"output", 23:"input",
           24:"output", 25:"input", 26:"output", 27:"input", 28:"output"},
    "U7": {4:"input", 5:"input", 6:"input", 7:"open_collector", 9:"open_collector", 13:"power_in", 15:"input"},
    "U8": {1:"input", 2:"open_collector", 3:"power_out", 5:"input", 14:"input", 15:"input"},
}
for ref in ("U4", "U5", "U6"):
    KINDS[ref] = {1:"input", 2:"input", 3:"tri_state", 5:"input", 6:"tri_state", 7:"input"}
for part in PARTS:
    for pin in part["pins"]:
        pin["type"] = KINDS.get(part["ref"], {}).get(int(pin["number"]) if pin["number"].isdigit() else 0, pin["type"])


def uid(s):
    return str(uuid5(NAMESPACE_URL, "https://github.com/krisxia0506/voxu/a2/"+s))


def q(s):
    return json.dumps(s, ensure_ascii=False)


def make_schematic():
    # One sheet, global-by-sheet labels. Each unique symbol is embedded.
    root=uid("root"); lib=[]; instances=[]; wires=[]
    ef="(effects (font (size 1.0 1.0)))"
    for index,p in enumerate(PARTS):
        ref=p["ref"]; count=len(p["pins"]); rows=(count+1)//2
        x=50.8+(index%8)*114.3; y=60.96+(index//8)*93.98
        half=max(7.62,(rows+1)*1.27); sympins=[]
        for i,pin in enumerate(p["pins"]):
            right=i>=rows; j=i%rows
            px=20.32 if right else -20.32; py=(rows-1)*1.27-j*2.54
            sympins.append(f'(pin {pin["type"]} line (at {px} {py} {180 if right else 0}) (length 5.08) (name {q(pin["name"])} {ef}) (number {q(pin["number"])} {ef}))')
            ax=round(x+px,3); ay=round(y-py,3)
            if pin["net"] is None:
                wires.append(f'(no_connect (at {ax} {ay}) (uuid "{uid(ref+pin["number"]+"nc")}"))')
            else:
                bx=round(ax+(10.16 if right else -10.16),3)
                wires.append(f'(wire (pts (xy {ax} {ay}) (xy {bx} {ay})) (stroke (width 0) (type default)) (uuid "{uid(ref+pin["number"]+"wire")}"))')
                wires.append(f'(label {q(pin["net"])} (at {bx} {ay} {0 if right else 180}) (effects (font (size 1 1)) (justify left bottom)) (uuid "{uid(ref+pin["number"]+"net")}"))')
        lib.append(f'''(symbol "VOXU:{ref}" (pin_names (offset 0.5)) (in_bom yes) (on_board yes)
          (property "Reference" {q(ref[0])} (at 0 {half+4} 0) {ef})
          (property "Value" {q(p['value'])} (at 0 {half+2} 0) {ef})
          (symbol "{ref}_0_1" (rectangle (start -15.24 {half}) (end 15.24 {-half}) (stroke (width 0.254) (type default)) (fill (type background))))
          (symbol "{ref}_1_1" {''.join(sympins)}))''')
        instances.append(f'''(symbol (lib_id "VOXU:{ref}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}")
          (property "Reference" {q(ref)} (at {x} {y-half-5} 0) {ef})
          (property "Value" {q(p['value'])} (at {x} {y-half-2} 0) {ef})
          (property "Footprint" {q(p['footprint'])} (at {x} {y} 0) (effects (font (size 1 1)) hide))
          (property "LCSC" {q(p['lcsc'])} (at {x} {y} 0) (effects (font (size 1 1)) hide))
          {''.join(f'(pin {q(pin["number"])} (uuid "{uid(ref+pin["number"])}"))' for pin in p['pins'])}
          (instances (project "mainboard" (path "/{root}" (reference {q(ref)}) (unit 1)))))''')
    return f'''(kicad_sch (version 20231120) (generator "voxu-mainboard") (uuid "{root}") (paper "A0")
      (title_block (title "VOXU A2 full electrical draft - NOT FOR FABRICATION") (date "2026-10-23") (rev "A2"))
      (lib_symbols {''.join(lib)}) {''.join(instances+wires)})\n'''


if __name__ == "__main__":
    (ROOT/"mainboard.kicad_sch").write_text(make_schematic())
    (ROOT/"mainboard-circuit.json").write_text(json.dumps(dict(release=False, parts=PARTS),indent=2)+"\n")
    with (ROOT/"mainboard-bom-draft.csv").open("w",newline="") as f:
        w=csv.writer(f, lineterminator="\n"); w.writerow(["Reference","Value","Footprint","LCSC","Qualification note"])
        for p in PARTS: w.writerow([p[k] for k in ("ref","value","footprint","lcsc","note")])
    print(f"Generated {len(PARTS)} parts; draft only, do not upload for production")

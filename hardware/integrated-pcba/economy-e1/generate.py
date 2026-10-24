"""E1 economy electrical candidate; never writes the A2 manufacturing files."""
import csv
import importlib.util
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
spec = importlib.util.spec_from_file_location('a2', BASE/'schematic/mainboard.py')
a2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a2)
parts = {p['ref']: p for p in a2.PARTS}
# Reuse A2 draft functional blocks; neither A2 nor E1 has production qualification.
for row in csv.DictReader((BASE/'procurement/cost-trial-all-parts.csv').open()):
    for ref in row['References'].split(','):
        parts[ref]['lcsc'] = row['LCSC']
parts['U1'].update(value='ESP32-PICO-V3', lcsc='C967022', footprint='',
    note='TFQFN-48-EP 7x7; exact land pattern and RF PCB not yet qualified; no A2 module footprint reuse')
names = ('VDDA LNA_IN VDD3P3 VDD3P3 SENSOR_VP SENSOR_CAPP SENSOR_CAPN SENSOR_VN EN '
         'IO34 IO35 IO32 IO33 IO25 IO26 IO27 IO14 IO12 VDD3P3_RTC IO13 IO15 IO2 IO0 IO4 '
         'NC VDD_SDIO IO20 IO9 IO10 FLASH_CS FLASH_CLK IO7 IO8 IO5 NC NC VDD3P3_CPU '
         'IO19 IO22 U0RXD U0TXD IO21 VDDA NC NC VDDA NC NC GND').split()
assert len(names) == 49
nets = {i:'3V3' for i in (1,3,4,19,37,43,46)}
nets.update({2:'RF_CHIP',9:'ESP_EN',13:'MIC_SD',15:'MIC_BCLK',18:'FLASH_VOLTAGE_STRAP',
             23:'ESP_BOOT',40:'ESP_RX',41:'ESP_TX',49:'GND'})
parts['U1']['pins'] = [dict(number=str(i), name=n, net=nets.get(i),
    type='power_in' if i in (1,3,4,19,37,43,46,49) else 'power_out' if i==26
    else 'output' if i in (15,41) else 'input' if i in (9,13,18,23,40) else 'passive')
    for i,n in enumerate(names,1)]
for ref, val in {'R5':'2.2k 1%', 'R18':'8.2k 1%', 'C1':'1u 50V X5R',
                 'C15':'10u 25V X5R','C16':'10u 25V X5R','C17':'10u 25V X5R',
                 'C21':'10u 25V X5R','C18':'22u 25V X5R','C19':'22u 25V X5R',
                 'C20':'22u 25V X5R','L1':'SMS0420-1R5MT 1.5uH'}.items():
    parts[ref]['value']=val
parts['L1'].update(footprint='', note='4.6x4.2mm; old XFL4020 footprint INVALID. DCR/current/thermal/land pattern pending')
parts['R18']['lcsc']='C25981'
parts['R18']['pins'][1]['net']='ISET_SERIES'
for ref, val, x, y, code, fp in [
    ('R25','470R 1%','ISET_SERIES','GND','C23179','Resistor_SMD:R_0603_1608Metric'),
    ('R26','0R initial RF tuning link','RF_CHIP','RF_ANT','C17168','Resistor_SMD:R_0402_1005Metric'),
    ('R27','10k 1%','FLASH_VOLTAGE_STRAP','GND','C25804','Resistor_SMD:R_0603_1608Metric'),
    *[(f'C{i}','100n 50V X7R','3V3','GND','C14663','Capacitor_SMD:C_0603_1608Metric') for i in range(22,26)]
]:
    a2.pair(ref,val,x,y,'ECONOMY_MCU' if ref!='R25' else 'CHARGE',fp)
    a2.PARTS[-1]['lcsc']=code
# No connector/antenna BOM item is silently omitted: this candidate uses PCB copper antenna.
# RF shunt tuning pads are DNP; installed values require matching on the actual board/enclosure.
for p in a2.PARTS:
    p['release']=False
assert len(a2.PARTS)==71
refs={p['ref']:p for p in a2.PARTS}
assert refs['U1']['pins'][12]['net']=='MIC_SD'
assert refs['U1']['pins'][14]['net']=='MIC_BCLK'
assert all(refs['U1']['pins'][i-1]['net'] is None for i in (25,30,31,35,36,44,45,47,48))
assert all(refs['U1']['pins'][i-1]['net']=='3V3' for i in (1,3,4,19,37,43,46))
a2.uid=lambda s:str(uuid5(NAMESPACE_URL,'https://github.com/krisxia0506/voxu/e1/'+s))
(ROOT/'mainboard.kicad_sch').write_text(a2.make_schematic().replace('VOXU A2 full electrical draft','VOXU E1 ECONOMY electrical candidate').replace('(rev "A2")','(rev "E1")'))
(ROOT/'circuit.json').write_text(json.dumps({'release':False,'parts':a2.PARTS,'pcb_antenna':{'net':'RF_ANT','status':'not laid out or tuned','tuning_shunts':'two unpopulated 0402 pads; final matching values unknown'},'manufacturing':'No E1 PCB/CPL/Gerber released'},indent=2)+'\n')
with (ROOT/'bom-candidate.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['Designator','Comment','Footprint','LCSC Part #'])
    for p in a2.PARTS:w.writerow([p['ref'],p['value'],p['footprint'],p['lcsc']])
# Worst-case resistor tolerances for the complete series pair.
rmin=(8200+470)*.99;rmax=(8200+470)*1.01
checks={'parts':len(a2.PARTS),'charge_current_mA':[797/rmax*1000,975/rmin*1000],
        'iset_ohm_max':rmax,'recommended_max_ohm':8900,'manufacturing_release':False,
        'gpio_compatible':True,'native_erc':'NOT RUN','rf':'NOT VERIFIED','pcb':'NOT ROUTED'}
assert rmax<8900
(ROOT/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks))

"""Generate a review-only KiCad INMP441 subcircuit; not a mainboard release."""
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

ROOT = Path(__file__).resolve().parent

def uid(s):
    return str(uuid5(NAMESPACE_URL, 'https://github.com/krisxia0506/voxu/mic-a1/' + s))

def effects():
    return '(effects (font (size 1.27 1.27)))'

def pin(n, name, x, y, angle, kind):
    return f'(pin {kind} line (at {x} {y} {angle}) (length 2.54) (name "{name}" {effects()}) (number "{n}" {effects()}))'

pins = [(1,'SCK',-10.16,5.08,0,'input'),(2,'SD',10.16,0,180,'tri_state'),(3,'WS',-10.16,0,0,'input'),(4,'L/R',-10.16,-10.16,0,'input'),(5,'GND',-5.08,-20.32,90,'power_in'),(6,'GND',0,-20.32,90,'power_in'),(7,'VDD',0,15.24,270,'power_in'),(8,'CHIPEN',-10.16,-5.08,0,'input'),(9,'GND',5.08,-20.32,90,'power_in')]
lib = f'''(symbol "VOXU:INMP441" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
(property "Reference" "U" (at 0 12.7 0) {effects()})
(property "Value" "INMP441" (at 0 10.16 0) {effects()})
(symbol "INMP441_0_1" (rectangle (start -7.62 12.7) (end 7.62 -17.78) (stroke (width 0.254) (type default)) (fill (type background))))
(symbol "INMP441_1_1" {''.join(pin(*p) for p in pins)}))'''
for name,ref in [('R','R'),('C','C')]:
    shape = '(rectangle (start -1.016 2.54) (end 1.016 -2.54) (stroke (width 0.254) (type default)) (fill (type none)))' if name=='R' else ''.join(f'(polyline (pts (xy -2.54 {y}) (xy 2.54 {y})) (stroke (width 0.254) (type default)) (fill (type none)))' for y in [-0.762,0.762])
    length=2.54 if name=='R' else 4.318
    pp=''.join(f'(pin passive line (at 0 {y} {a}) (length {length}) (name "~" {effects()}) (number "{n}" {effects()}))' for n,y,a in [(1,5.08,270),(2,-5.08,90)])
    lib+=f'(symbol "VOXU:{name}" (pin_names (offset 0)) (in_bom yes) (on_board yes) (property "Reference" "{ref}" (at 0 0 0) {effects()}) (property "Value" "{name}" (at 0 0 0) {effects()}) (symbol "{name}_0_1" {shape}) (symbol "{name}_1_1" {pp}))'
root=uid('root'); items=[]
def instance(libname,ref,val,x,y,numbers):
    items.append(f'''(symbol (lib_id "VOXU:{libname}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}")
(property "Reference" "{ref}" (at {x+4} {y-12 if libname=='INMP441' else y-2} 0) {effects()})
(property "Value" "{val}" (at {x+5} {y-9 if libname=='INMP441' else y+2} 0) {effects()})
(property "Footprint" "" (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))
{''.join(f'(pin "{n}" (uuid "{uid(ref+str(n))}"))' for n in numbers)}
(instances (project "microphone" (path "/{root}" (reference "{ref}") (unit 1)))))''')
def endpoint(x,y,net,dx=0,dy=0):
    xx,yy=round(x+dx,3),round(y+dy,3)
    if dx or dy:
        items.append(f'(wire (pts (xy {x} {y}) (xy {xx} {yy})) (stroke (width 0) (type default)) (uuid "{uid(str((x,y,net)))}"))')
    items.append(f'(label "{net}" (at {xx} {yy} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uid(str((xx,yy,net))+"label")}"))')
instance('INMP441','U1','INMP441',100,80,range(1,10))
netmap={1:'MIC_BCLK_GPIO26',2:'MIC_SD_GPIO33',3:'MIC_WS_GPIO25',4:'GND',5:'GND',6:'GND',7:'3V3',8:'3V3',9:'GND'}
for n,name,x,y,a,k in pins:
    endpoint(round(100+x,3),round(80-y,3),netmap[n],dx=-20.32 if x==-10.16 else 12.7 if n==2 else 0,dy=-7.62 if n==7 else 7.62 if n in [5,6,9] else 0)
instance('R','R1','100k 1% 0603',145,90,[1,2]);endpoint(145,84.92,'MIC_SD_GPIO33',dy=-5.08);endpoint(145,95.08,'GND',dy=5.08)
instance('C','C1','100n X7R 10V 0603',180,90,[1,2]);endpoint(180,84.92,'3V3',dy=-5.08);endpoint(180,95.08,'GND',dy=5.08)
for i,t in enumerate(['REVIEW ONLY - INMP441 subcircuit, not a complete mainboard','External boundaries: 3V3/GND from regulated system; GPIO26/25 driven by ESP32.','C1 beside U1 pins 7/6; all three GND pads connected. Footprints not assigned.','16 kHz WS / 64 BCLK per frame; CHIPEN high preserves existing standby behavior.']):
    items.append(f'(text "{t}" (at 35 {30+i*6} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid(t)}"))')
s=f'''(kicad_sch (version 20231120) (generator "voxu-mic-generator") (uuid "{root}") (paper "A4")
(title_block (title "VOXU INMP441 subcircuit - REVIEW ONLY") (date "2026-10-23") (rev "A1"))
(lib_symbols {lib})
{chr(10).join(items)}
)\n'''
(ROOT/'microphone.kicad_sch').write_text(s)
print(ROOT/'microphone.kicad_sch')

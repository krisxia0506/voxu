#!/usr/bin/env python3
"""Generate vendor-specific land patterns for import into EasyEDA Pro.
Dimensions in mm. See README for sources and qualification status.
"""
from pathlib import Path
ROOT = Path(__file__).parent / "VOXU.pretty"
ROOT.mkdir(exist_ok=True)

def pad(n,x,y,w,h,layers='"F.Cu" "F.Paste" "F.Mask"',mask=0.05):
    return f'  (pad "{n}" smd roundrect (at {x:g} {y:g}) (size {w:g} {h:g}) (layers {layers}) (roundrect_rratio {min(.05/min(w,h),.25):g}) (solder_mask_margin {mask:g}))'

def make(name,body,pads,source):
    w,h=body
    text=f'''(footprint "{name}" (version 20240108) (generator "voxu") (layer "F.Cu")
  (descr "{source}") (attr smd)
  (fp_text reference "REF**" (at 0 {-h/2-1:g}) (layer "F.SilkS") (effects (font (size .7 .7) (thickness .12))))
  (fp_text value "{name}" (at 0 {h/2+1:g}) (layer "F.Fab") (effects (font (size .5 .5) (thickness .08))))
  (fp_rect (start {-w/2:g} {-h/2:g}) (end {w/2:g} {h/2:g}) (stroke (width .1) (type solid)) (fill none) (layer "F.Fab"))
  (fp_circle (center {-w/2-.4:g} {-h/2-.2:g}) (end {-w/2-.3:g} {-h/2-.2:g}) (stroke (width .1) (type solid)) (fill solid) (layer "F.SilkS"))
'''
    (ROOT / (name+'.kicad_mod')).write_text(text+'\n'.join(pads)+'\n)\n')

def qfn(count,center,pitch,lead,ep,mask):
    n=count//4;p=[]
    for i in range(n):
        t=(i-(n-1)/2)*pitch
        for num,x,y,w,h in [(i+1,-center,t,*lead),(n+i+1,t,center,lead[1],lead[0]),(2*n+i+1,center,-t,*lead),(3*n+i+1,-t,-center,lead[1],lead[0])]:
            p.append(pad(num,x,y,w,h,mask=mask))
    p.append(pad(count+1,0,0,ep,ep,'"F.Cu" "F.Mask"',mask))
    return p

p=qfn(28,2.4,.5,(.95,.30),3.35,.06)
for x in [-.75,.75]:
    for y in [-.75,.75]: p.append(pad('',x,y,1.2,1.2,'"F.Paste"'))
make('VOXU_CP2102N_QFN28',(5,5),p,'Silicon Labs CP2102N Rev1.5 Fig6.2; 3.35mm EP; 2x2 1.2mm paste windows')
p=qfn(16,1.4,.5,(.6,.24),1.68,.05)
p.append(pad('',0,0,1.55,1.55,'"F.Paste"'))
make('VOXU_BQ24075_RGT0016C',(3,3),p,'TI RGT0016C 4222419 E July2025; 1.68mm EP; 1.55mm paste; no open via-in-pad')

# RNM0015A: NSMD signal lands, SMD power lands, split paste for 9/10/11.
p=[]
for n,y in enumerate([-.75,-.25,.25,.75],1): p.append(pad(n,-1.15,y,.6,.25))
for n,x,y in [(5,-.725,1.4),(6,-.225,1.4),(14,-.225,-1.4),(15,-.725,-1.4)]:
    p.append(pad(n,x,y,.25,.6))
for n,x,y in [(7,.275,1.4),(8,.775,1.4),(12,.775,-1.4),(13,.275,-1.4)]:
    p.append(pad(n,x,y,.35,.7,'"F.Cu" "F.Mask"',-.05))
    p.append(pad('',x,y,.25,.6,'"F.Paste"'))
for n,y in [(7,1.225),(13,-1.225)]:
    p.append(pad(n,.525,y,.85,.35,'"F.Cu" "F.Mask"',-.05))
    p.append(pad('',.525,y,.75,.25,'"F.Paste"'))
for n,x,y,w in [(9,.775,.5,1.45),(10,.6,0,1.8),(11,.775,-.5,1.45)]:
    p.append(pad(n,x,y,w,.35,'"F.Cu" "F.Mask"',-.05))
    for px in ([.14,1.06] if n==10 else [.3875,1.1625]):
        p.append(pad('',px,y,.72 if n==10 else .575,.25,'"F.Paste"'))
make('VOXU_TPS63070_RNM0015A',(2.5,3),p,'TI RNM0015A 4222000 B March2020; SMD power pads; divided stencil; pairs 7-8 and 12-13 are connected')
make('VOXU_XFL4020',(4,4),[pad(1,-1.185,0,.98,3.4),pad(2,1.185,0,.98,3.4)],'Coilcraft XFL4020 Document745-3 Oct2026; .98x3.4 lands at 2.37 pitch')

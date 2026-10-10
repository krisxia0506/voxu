"""Local Bambu Studio diagnostic slicing; G-code is not a delivered artifact."""
from pathlib import Path
import json,subprocess,sys
src=Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL')
out=Path('/tmp/voxu-battery-slice');out.mkdir(exist_ok=True)
def load(kind,name):
 d=json.loads((src/kind/(name+'.json')).read_text());r={}
 if d.get('inherits'):r.update(load(kind,d['inherits']))
 for inc in d.get('include',[]):r.update(load(kind,inc))
 r.update(d);r.pop('inherits',None);r.pop('include',None)
 return r
machine=load('machine','Bambu Lab P2S 0.4 nozzle')
filament=load('filament','Generic PLA @BBL P2S')
process=load('process','0.20mm Standard @BBL P2S')
process.update(wall_loops='3',sparse_infill_density='15%',top_shell_layers='4',bottom_shell_layers='4')
for name,d in [('machine',machine),('filament',filament),('process',process)]:
 (out/(name+'.json')).write_text(json.dumps(d,indent=2))
root=Path(__file__).resolve().parents[2]
for part in (sys.argv[1:] or ['base','lid','battery-tray','button-cap','button-pin','mic-clamp']):
 dest=out/part;dest.mkdir(exist_ok=True)
 process['enable_support']='1' if part in ['base','button-pin'] else '0'
 pp=dest/'process.json';pp.write_text(json.dumps(process,indent=2))
 cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--debug','2','--load-settings',str(out/'machine.json')+';'+str(pp),'--load-filaments',str(out/'filament.json'),'--arrange','1','--slice','0','--outputdir',str(dest),str(root/'hardware/enclosure-battery/stl'/(part+'.stl'))]
 with (dest/'log.txt').open('w') as log:
  r=subprocess.run(cmd,cwd=dest,stdout=log,stderr=subprocess.STDOUT)
 print(part,r.returncode,flush=True)

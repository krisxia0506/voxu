"""Read existing CAD to inspect a conditional layout; exports no printable parts."""
from pathlib import Path
import ast, hashlib, json, tempfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import font_manager
root=Path(__file__).resolve().parents[3]
source=root/'hardware/enclosure/generate.py'
text=source.read_text()
scratch=Path(tempfile.mkdtemp(prefix='voxu-space-probe-'))
(scratch/'parameters.json').write_bytes((source.parent/'parameters.json').read_bytes())
g={'__file__':str(scratch/'generate.py'),'__name__':'space_probe'}
# Evaluate the existing geometric construction before its export/validation loop.
exec(compile(text.split("report={'revision'")[0],str(source),'exec'),g)
for node in ast.parse(text).body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'board','components','mic','mic_capsule'} for t in node.targets):
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),g)
box=g['box']; p=g['P']
board_lift=7.3; lid_lift=10.6; height=30.0
module=box(9,8.07,2.5,37.068,23.86,8)
battery=box(10,5,18,37,30,5.75)
# Frame and extruded corner pads are analytical obstacles, not a new shell.
frame=g['rr'](0,0,0,60,40,height,4)-g['rr'](2,2,-1,56,36,height+2,2)
obstacles={'wall_envelope':frame,'main_pcb':g['board'].translate((0,0,board_lift)),
 'main_component_envelope':g['components'].translate((0,0,board_lift)),
 'translated_lid':g['lid'].translate((0,0,lid_lift)),
 'translated_mic':g['mic'].translate((0,0,lid_lift)),
 'translated_mic_capsule':g['mic_capsule'].translate((0,0,lid_lift)),
 'translated_optional_clamp':g['clamp'].translate((0,0,lid_lift))}
for i,(x,y) in enumerate(g['corner_pads']): obstacles[f'extended_corner_pad_{i}']=box(x,y,2,6,6,2+board_lift)
checks={}
for name,solid in [('battery_allowance',battery),('module_allowance',module)]:
 checks[name]={k:round((solid^v).volume(),8) for k,v in obstacles.items()}
checks['battery_module_overlap_mm3']=round((battery^module).volume(),8)
assert all(v==0 for values in checks.values() if isinstance(values,dict) for v in values.values())
assert checks['battery_module_overlap_mm3']==0
original_probe=box(10,5,10.6,37,30,5.75)
original_collisions={k:round((original_probe^g[k]).volume(),6) for k in ['lid','clamp','mic','mic_capsule']}
report={'status':'conditional_space_probe_NOT_final_CAD','cad_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'outer_target_mm':[60,40,height],'height_increase_mm':lid_lift,'main_pcb_lift_mm':board_lift,
 'module_allowance_mm':list(module.bounding_box()),'battery_allowance_mm':list(battery.bounding_box()),
 'assumptions':['Module 8 mm total height is unverified; 1 mm added to PCB XY dimensions.',
 'Battery 36 x 29 x 4.75 mm reference enlarged by 1 mm per dimension; lead/plug not included.',
 'Lid and original microphone geometry translated together; support and button lengths not redesigned.'],
 'original_height_probe_collisions_mm3':original_collisions,'candidate_partial_intersections_mm3':checks,
 'gaps_mm':{'module_to_main_pcb':0.8,'main_components_to_battery':0.6,'battery_to_optional_clamp':0.45},
 'rf':{'assumed_antenna_x_range':[41.85,53.85],'battery_overlaps_antenna_in_plan':True,'vertical_gap_to_assumed_pcb_antenna_plane_mm':5.1,'recommended_clearance_reference_mm':15,'assessment':'does_not_meet_assumed_15mm_keepout; RF performance unknown; do not freeze this placement'},
 'omitted':['Measured antenna boundary','Measured module connector height','wiring and battery plug','redesigned supports and trays','new button and retaining geometry','switch placement','thermal','RF test','electrical design','printing']}
out=root/'docs/superpowers/research'
(out/'2026-09-30-fixed-footprint-space-probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
font=Path('/System/Library/Fonts/STHeiti Medium.ttc')
if font.exists():
 font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
fig,axes=plt.subplots(1,2,figsize=(12,5.5),facecolor='#f6f7f9')
def rect(ax,x,y,w,h,color,label,alpha=1):
 ax.add_patch(Rectangle((x,y),w,h,facecolor=color,edgecolor='#44546a',alpha=alpha))
 ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=10)
a=axes[0]
rect(a,0,0,60,40,'#e7e9ee','')
rect(a,2,2,56,36,'white','')
rect(a,2.4,5.835,51.45,28.33,'#c4dfda','',.5)
rect(a,41.85,5.835,12,28.33,'#efb7b7','天线\n假定区',.7)
rect(a,10,5,37,30,'#f2d090','电池包络\n37 × 30 mm',.7)
a.set_title('俯视：保持 60 × 40 mm（电池位置未定稿）')
a.set(xlim=(-3,63),ylim=(-3,43),aspect='equal',xlabel='X / mm',ylabel='Y / mm')
fig.text(.27,.065,'电池覆盖部分假定天线区，位置需调整/实测',ha='center',color='#9c342d',fontsize=10)
b=axes[1]
rect(b,0,0,60,2,'#89909b','')
rect(b,9,2.5,37.068,8,'#a8c7e8','充电升压板包络（高度待测）')
rect(b,2.4,11.3,51.45,1.6,'#81b8aa','')
rect(b,14.4,12.9,35.45,4.5,'#c4dfda','原主板元件包络')
rect(b,10,18,37,5.75,'#f2d090','小电池包络')
rect(b,16,24.2,26,1.4,'#cebce5','麦克风压框',.8)
rect(b,0,27.6,60,2.4,'#b9db42','上盖')
b.axhline(19.4,color='#9a4343',ls='--',lw=1)
b.text(61,19.4,'原壳高\n19.4',va='center',fontsize=9)
b.set_title('侧视：条件性空间预算 60 × 40 × 30 mm')
b.set(xlim=(-3,69),ylim=(-2,33),aspect='equal',xlabel='X / mm',ylabel='Z / mm')
fig.suptitle('同长宽排布检查：可见间隙 ≠ 已完成外壳',fontsize=16)
fig.text(.5,.02,'仅为包络与部分 CAD 碰撞检查；未验证天线、走线、固定结构、开关和装配，不是可打印模型。',ha='center',fontsize=10,color='#8b4436')
fig.tight_layout(rect=(0,.14,1,.92))
fig.savefig(out/'2026-09-30-fixed-footprint-space-probe.png',dpi=160)
print(json.dumps({'original_collisions':original_collisions,'candidate_checked_overlap_mm3':0,'rf_status':report['rf']['assessment']},indent=2))

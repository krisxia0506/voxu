"""Parametric millimetre CAD. Run from any directory; outputs live beside this file.
Confirmed PCB outlines; all unmeasured Z dimensions are explicitly prototype values.
"""
from pathlib import Path
import json
import zipfile
import numpy as np
import manifold3d as m
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / 'parameters.json').read_text())
OUT = ROOT / 'stl'
OUT.mkdir(exist_ok=True)

def box(x, y, z, dx, dy, dz):
    return m.Manifold.cube((dx, dy, dz)).translate((x, y, z))

def cyl(x, y, z, radius, height):
    return m.Manifold.cylinder(height, radius, circular_segments=64).translate((x, y, z))

def rr(x, y, z, dx, dy, dz, r):
    a = cyl(x+r, y+r, z, r, dz)
    for xx, yy in [(x+dx-r,y+r), (x+r,y+dy-r), (x+dx-r,y+dy-r)]:
        a += cyl(xx, yy, z, r, dz)
    return a.hull()

def mesh(s):
    a = s.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(a.vert_properties)[:, :3], faces=np.asarray(a.tri_verts), process=True)

L, W = P['shell_length'], P['shell_width']
seam, top = P['seam_z'], P['seam_z']+P['lid_thickness']
bx, by = P['usb_protrusion']+P['usb_front_recess'], (W-P['board_width'])/2
bl, bw, bz = P['board_length'], P['board_width'], P['board_bottom_z']
bootx, booty = bx+P['boot_offset_x'], by+P['boot_offset_y']
mx, my = P['mic_x'], W/2
screws = [(3.4,2.8),(L-3.4,2.8),(3.4,W-2.8),(L-3.4,W-2.8)]
base = rr(0,0,0,L,W,seam,4)-rr(2,2,2,L-4,W-4,seam+1,2)
for x,y in screws:
    base += cyl(x,y,2,2.7,seam-2)
    base -= cyl(x,y,seam-9,0.85,10)
# User requested each 3 x 3 mm PCB support pad grow by 3 mm in both axes.
# Expand inward under the PCB; keep the board, USB and lid hold-down coordinates.
corner_pads = [(bx,by),(bx+bl-6,by),(bx,by+bw-6),(bx+bl-6,by+bw-6)]
hold_downs = [(bx,by),(bx+bl-3,by),(bx,by+bw-3),(bx+bl-3,by+bw-3)]
for x,y in corner_pads:
    if x==bx and y==by:
        # Bridge the UPS under the front PCB support from an outer buttress.
        base += box(x,3.5,2,6,3.5,bz-2)
        base += box(x,3.5,9.6,6,by+6-3.5,bz-9.6)
    else:
        base += box(x,y,2,6,6,bz-2)
# PCB is located by front wall, side fences and rear fence, not pin headers.
for y in [by-1.3,by+bw+0.3]:
    for x in [bx+4,bx+bl-8]:
        fence_z=9.6 if y==by-1.3 and x==bx+4 else 2
        base += box(x,y,fence_z,4,1,bz+P['board_thickness']+0.3-fence_z)
for y in [by,by+bw-4]:
    base += box(bx+bl+0.3,y,2,1,4,bz+P['board_thickness']+0.3-2)
# Side clips bend laterally along 12 mm horizontal cantilever arms.
# Under-arm clearance allows flex; keep support away from the spring if possible.
# Retaining lips overlap only the PCB rim, not components or solder pads.
clip_lip_z=bz+P['board_thickness']+P['board_clip_clearance']
clips=[]
for root_x in [bx+7.6,bx+26.6]:
    tip_x=root_x+14
    # Build the lower-Y clip then mirror it for the other side of the board.
    root=box(root_x,by-1.2,2,2,1,4.7+(bz-4))
    # Broad foot tapers into the original upright below the free spring arm.
    # Keep expansion within the module and side wire-channel clearances.
    foot=box(root_x-3,by-1.6,1.8,5,2,1.0)
    shoulder=box(root_x,by-1.2,bz-2,2,1,0.4)
    root += (foot+shoulder).hull()
    arm=box(root_x+1.8,by-1.2,bz,12.2,1,2.7)
    lip=(box(tip_x-2.4,by-0.3,clip_lip_z,2.4,0.8,0.06)
         +box(tip_x-2.4,by-0.3,clip_lip_z+1.0,2.4,0.1,0.06)).hull()
    clip=root+arm+lip
    mirrored=clip.mirror((0,1,0)).translate((0,W,0))
    clips.extend([clip,mirrored])
    # Lower side root steps outward below the UPS clearance envelope.
    low_root=box(root_x,5.2,2,2,1.8,bz-2)
    low_root += (box(root_x-3,4.8,1.8,5,2.2,1)+box(root_x,5.2,bz-2,2,1.8,.4)).hull()
    low_root += box(root_x,5.2,9.6,2,by-.2-5.2,bz+0.7-9.6)
    clip=low_root+arm+lip
    clips[-2]=clip
    base += clip+mirrored
# Front-face capsule opening based on GCT USB4105 drawing; actual PCB socket
# part number is unknown. User measured 2 mm projection past the board edge.
def usb_capsule(x, length, width, height, zcenter):
    a=m.Manifold.cylinder(length,height/2,circular_segments=64).rotate((0,90,0))
    a=a.translate((x,W/2-(width-height)/2,zcenter))
    b=m.Manifold.cylinder(length,height/2,circular_segments=64).rotate((0,90,0))
    b=b.translate((x,W/2+(width-height)/2,zcenter))
    return (a+b).hull()
usb_z=P['usb_bottom_z']+P['usb_height']/2
# ESP32 USB is internal; remove the PCB from its clips for occasional flashing.
lid = rr(0,0,seam,L,W,P['lid_thickness'],4)
skirt = rr(2.3,2.3,seam-1.6,L-4.6,W-4.6,1.8,1.7)-rr(3.5,3.5,seam-1.7,L-7,W-7,2.1,0.5)
for x,y in screws:
    skirt -= cyl(x,y,seam-2,3.1,3)
# The front alignment skirt is interrupted around the long BOOT guide.
skirt -= box(0,booty-4,seam-2,10,8,3)
# Separate snap arms from the alignment skirt so they can flex over full length.
shell_snap_x=[16,L-16]
for x in shell_snap_x:
    skirt -= box(x-P['shell_snap_width']/2-0.3,1,seam-2,
                 P['shell_snap_width']+0.6,4,3)
    skirt -= box(x-P['shell_snap_width']/2-0.3,W-5,seam-2,
                 P['shell_snap_width']+0.6,4,3)
lid += skirt
for x,y in hold_downs:
    lid += box(x+0.5,y+0.5,bz+P['board_thickness']+0.2,2,2,
               seam-(bz+P['board_thickness']+0.2)+0.1)
for x,y in screws:
    lid -= cyl(x,y,seam-1,1.15,8)
    lid -= cyl(x,y,top-1,2.05,5)

# Four integral lid catches: ramped insertion face, positive retaining shoulder,
# and a through-window in the base for intentional inward release with a thin pick.
shell_snaps=[]
snap_z=P['shell_snap_bottom_z']
snap_h=P['shell_snap_hook_height']
snap_w=P['shell_snap_width']
snap_y=2.3
for x in shell_snap_x:
    tongue=box(x-snap_w/2,snap_y,snap_z,snap_w,P['shell_snap_thickness'],seam-snap_z+0.1)
    hook=(box(x-snap_w/2,snap_y,snap_z,snap_w,0.15,0.06)
          +box(x-snap_w/2,snap_y-P['shell_snap_projection'],snap_z+snap_h-0.06,
               snap_w,P['shell_snap_projection']+0.15,0.06)).hull()
    catch=tongue+hook
    mirrored=catch.mirror((0,1,0)).translate((0,W,0))
    shell_snaps.extend([(catch,1),(mirrored,-1)])
    lid += catch+mirrored
    # 0.3 mm lateral and 0.2 mm axial clearance; leave positive material above window.
    base -= box(x-snap_w/2-0.3,-0.1,snap_z-0.2,snap_w+0.6,2.2,snap_h+0.4)
    base -= box(x-snap_w/2-0.3,W-2.1,snap_z-0.2,snap_w+0.6,2.2,snap_h+0.4)

# Microphone above the central PCB area; sound-hole face toward the lid.
mic_top = seam-P['mic_acoustic_gap']
mic_bottom = mic_top-P['mic_pcb_thickness']
mic_ring = cyl(mx,my,mic_bottom-0.3,8.7,seam-(mic_bottom-0.3)+0.1)
mic_ring -= cyl(mx,my,mic_bottom-0.4,P['mic_diameter']/2+0.2,4)
for y in [my+4,my-10]:
    mic_ring -= box(mx-5,y,mic_bottom-0.4,10,6,4)
# Two slots let clamp fingers reach the PCB rim without touching the capsule.
mic_ring -= box(mx-10,my-1.7,mic_bottom-0.4,20,3.6,0.7)
for y in [my+6.8,my-10.8]:
    mic_ring -= box(mx-10,y,mic_bottom-0.4,20,4,0.7)
lid += mic_ring
for x in [mx-6.4,mx+5.7]:
    lid += box(x,my-1.4,mic_top,0.7,2.8,seam-mic_top+0.1)
mic_screws=[(mx-11,my),(mx+11,my)]
for x,y in mic_screws:
    lid += cyl(x,y,mic_bottom,2.4,seam-mic_bottom+0.1)
    lid -= cyl(x,y,mic_bottom-0.1,0.85,3.7)
# 2.4 mm holes at 3.4 mm pitch: 1 mm web, rather than fragile 1.2 mm bores.
for x in [-P['mic_hole_pitch'],0,P['mic_hole_pitch']]:
    for y in [-P['mic_hole_pitch'],0,P['mic_hole_pitch']]:
        lid -= cyl(mx+x,my+y,seam-0.1,P['mic_hole_diameter']/2,4)
clamp = rr(mx-13,my-10,mic_bottom-1.4,26,20,1.4,2)
clamp -= rr(mx-9,my-7,mic_bottom-1.5,18,14,1.7,1)
for x in [mx-9.2,mx+5.8]:
    clamp += box(x,my-1.5,mic_bottom-1.4,3.4,3,1.4)
for x,y in mic_screws:
    clamp -= cyl(x,y,mic_bottom-1.5,1.15,2)

# Long square guide restrains tilt and rotation, ending close to the BOOT foot.
guide_bottom=P['button_guide_bottom_z']
stem=P['button_stem_width']; bore=stem+P['button_guide_clearance']
lid += box(bootx-3.5,booty-3.5,guide_bottom,7,7,seam-guide_bottom+0.1)
lid -= box(bootx-bore/2,booty-bore/2,guide_bottom-0.1,bore,bore,top-guide_bottom+0.2)
cap_bottom=top+P['button_downstroke']
neck_bottom=guide_bottom-0.2
cap=rr(bootx-4,booty-4,cap_bottom,8,8,2,1.5)
cap += box(bootx-stem/2,booty-stem/2,neck_bottom,stem,stem,cap_bottom-neck_bottom+0.1)
cap -= cyl(bootx,booty,neck_bottom-0.1,P['button_socket_diameter']/2,4.8)
cap -= m.Manifold.cylinder(0.6,2.0,P['button_socket_diameter']/2,
                           circular_segments=64).translate((bootx,booty,neck_bottom))
foot=bz+P['board_thickness']+P['boot_height_above_pcb']+P['button_initial_gap']

def pin(extra=P['button_pin_extension']):
    flange_z=neck_bottom-1.2
    assert flange_z-(foot-extra) >= 0.4, "Contact foot must survive at least two 0.2 mm layers"
    a=box(bootx-3.5,booty-3.5,flange_z,7,7,1.2)
    a += cyl(bootx,booty,foot-extra,1.1,flange_z-(foot-extra)+0.1)
    a += cyl(bootx,booty,neck_bottom-0.1,1.5,4.3)
    return a

# Measured 550 mAh cell; full rectangular keepout includes soft-pouch clearance.
# Cell rests on an insulating tape layer, never on screws or the mainboard.
tray_z=18.6
cell_x,cell_y,cell_z=P['battery_origin_mm']
cell_l,cell_w,cell_h=P['battery_size_mm']
gap=P['battery_clearance_xy']
ex,ey=cell_x-gap,cell_y-gap
el,ew=cell_l+2*gap,cell_w+2*gap
tray=box(ex-0.8,ey-0.8,tray_z,el+1.6,ew+1.6,0.8)
tray += box(8,W/2-3,tray_z,5,6,0.8)+box(48,W/2-3,tray_z,8.2,6,0.8)
# Battery wire exits at front (low X), through a broad interruption in the rail.
for yy in [ey-0.8,ey+ew]:
    tray += box(ex-0.8,yy,tray_z+0.7,el+1.6,0.8,2.0)
tray += box(ex+el,ey,tray_z+0.7,0.8,ew,2.0)
for yy in [ey,ey+ew-5]:
    tray += box(ex-0.8,yy,tray_z+0.7,0.8,5,2.0)
# Wrap PI tape around the removable tray without tightening against the pouch.
tray_screws=[(9.8,W/2),(54,W/2)]
tray_screw_heads=m.Manifold()
for x,y in tray_screws:
    tray -= cyl(x,y,tray_z-0.1,1.1,1.1)
    lid += cyl(x,y,tray_z+0.8,1.8,seam-(tray_z+0.8)+0.1)
    lid -= cyl(x,y,tray_z+0.7,0.85,5.2)
    tray_screw_heads += cyl(x,y,tray_z-1.5,2,1.5)
battery=box(ex,ey,cell_z,el,ew,cell_h+P['battery_top_clearance'])
actual_battery=box(cell_x,cell_y,cell_z,cell_l,cell_w,cell_h)

# Integrated UPS: USB faces low X, its switch faces low Y. The USB faces the centered external charging opening.
px,py,pz=P['power_module_origin_mm']
pl,pw,ph=P['power_module_size_mm']
pg=P['power_clearance_xy']
power_module=box(px-pg,py-pg,pz,pl+2*pg,pw+2*pg,ph+0.4)
actual_power=box(px,py,pz,pl,pw,ph)
# A flat bed for the documented flat back, with 0.2 mm insulation/tape allowance.
# Open-center locating rails do not clamp components or depend on mounting holes.
base += box(max(2,px-pg-1),py-pg-1,2,px+pl+pg+1-max(2,px-pg-1),pw+2*pg+2,pz-0.2-2)
for yy in [py-pg-1,py+pw+pg]:
    base += box(px-pg-1,yy,2,pl+2*pg+2,1,2.2)
for xx in [px-pg-1,px+pl+pg]:
    for yy in [py-pg-1,py+pw+pg-3]:
        base += box(xx,yy,2,1,4,2.2)
# Lower side access for the existing slide switch; no additional switch is needed.
wx=P['switch_window_x'];wl=P['switch_window_length']
wz=P['switch_window_bottom_z'];wh=P['switch_window_height']
switch_access=box(wx,-1,wz,wl,py+1,wh)
base -= switch_access
# PI tape can loop around the USB shell and the insulated output end of the PCB.
# Slots are outside the electrical envelope; tape is fitted before the main PCB.
for xx in [px+2,px+pl-3]:
    for yy in [py-pg-0.9,py+pw+pg+0.1]:
        base -= box(xx,yy,-0.1,3,0.8,4.4)
# Plug-body access is centered on the front face; module USB center is a photo-derived nominal.
assert abs(py+P['ups_usb_center_offset_y']-W/2)<1e-6
charging_access=usb_capsule(-1,px+1,P['ups_usb_window_width'],P['ups_usb_window_height'],P['ups_usb_center_z'])
base -= charging_access
# Continuous side routing lane for power/battery leads; avoids the PCB pin rows.
wire_lane=box(10,W-7,3,35,3,22)
parts={'base':base,'lid':lid,'mic-clamp':clamp,'button-cap':cap,
       'button-pin':pin(),'battery-tray':tray}
report={'revision':'integrated-ups-fit-4','parameters':P,'parts':{},'checks':{}}
for name,solid in parts.items():
    t=mesh(solid)
    assert str(solid.status())=='Error.NoError',(name,solid.status())
    assert t.is_watertight and t.is_winding_consistent and t.volume>0,name
    assert len(t.split())==1,(name,'disconnected shells')
    if name in ['lid','button-cap']:
        t.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
    t.apply_translation(-t.bounds[0])
    assert np.all(t.extents<256),name
    t.export(OUT/(name+'.stl'))
    report['parts'][name]={'size_mm':np.round(t.extents,3).tolist(),'volume_mm3':round(t.volume,2),'watertight':True,'connected_components':1}
board=box(bx,by,bz,bl,bw,P['board_thickness'])
mic=cyl(mx,my,mic_bottom,7,P['mic_pcb_thickness'])
# Conservative component clearance envelope; real solder joints remain unmeasured.
components=box(bx+12,by+3,bz+P['board_thickness'],bl-16,bw-6,P['board_component_height'])
mic_capsule=box(mx-3,my-2,mic_bottom-1.2,6,4,1.2)
for name,a,b in [('usb-shell-base',usb_capsule(P['usb_front_recess'],8,8.94,3.31,bz+P['board_thickness']+3.31/2),base),('base-lid',base,lid),('board-base',board,base),('board-lid',board,lid),
                 ('cap-lid',cap,lid),('mic-lid',mic,lid),('mic-clamp',mic,clamp),
                 ('clamp-lid',clamp,lid),('clamp-base',clamp,base),('components-lid',components,lid),('clamp-components',clamp,components),
                 ('mic-components',mic,components),('mic-capsule-components',mic_capsule,components),
                 ('mic-capsule-clamp',mic_capsule,clamp)]:
    volume=(a^b).volume()
    assert volume<1e-5,(name,volume)
    report['checks'][name+'_intersection_mm3']=round(volume,8)
# Independent envelope/fastener checks. These do not simulate wires or cell swelling.
for moving_name,moving in [('battery',battery),('battery-tray',tray),
                           ('tray-screw-heads',tray_screw_heads),('power-module',power_module)]:
    for fixed_name,fixed in [('base',base),('lid',lid),('PCB',board),
                             ('components',components),('mic',mic),('mic-clamp',clamp),
                             ('mic-capsule',mic_capsule),('button-cap',cap),('button-pin',pin())]:
        volume=(moving^fixed).volume()
        assert volume<1e-5,(moving_name,fixed_name,volume)
        report['checks'][moving_name+'-'+fixed_name+'_intersection_mm3']=round(volume,8)
for name,a,b in [('battery-tray',battery,tray),('battery-module',battery,power_module),
                 ('tray-module',tray,power_module)]:
    assert (a^b).volume()<1e-5,name
# Battery tray is carried by lid: straight lift must clear the seated board/base.
for lift in np.linspace(0,32,33):
    for name,a in [('tray',tray),('battery',battery),('screw-heads',tray_screw_heads)]:
        moving=a.translate((0,0,float(lift)))
        for fixed_name,fixed in [('base',base),('PCB',board),('components',components)]:
            assert (moving^fixed).volume()<1e-5,('tray-removal',lift,name,fixed_name)
report['checks']['battery_tray_removal']='33 vertical lift positions; wires excluded'
report['limitations']=[
    'Mechanical design for measured parts; electrical charging compatibility is unresolved',
    'Switch position inferred from supplied photo; generous access window requires physical fit check',
    'Power PCB flat back uses insulating tape and PI retention straps; do not clamp components',
    'Battery is outside the last 6 mm antenna projection, but full RF clearance/range is not validated',
    'Wire routing lane is a reserved volume; exact solder joints and connector bends require fit check',
    'Printed clips, tape retention, pouch clearance and thermal behavior require assembly verification']
report['body_size_mm']=[L,W,top]
report['battery_measured_mm']=P['battery_size_mm']
report['battery_envelope_mm']=[el,ew,cell_h+P['battery_top_clearance']]
report['module_measured_mm']=P['power_module_size_mm']
report['module_envelope_mm']=[pl+2*pg,pw+2*pg,ph+0.4]
for name,fixed in [('base',base),('lid',lid),('board',board),('tray',tray),('battery',battery),('power',power_module)]:
    volume=(wire_lane^fixed).volume()
    assert volume<1e-5,('wire-lane',name,volume)
    report['checks']['wire-lane-'+name+'_intersection_mm3']=round(volume,8)
# Window must be empty all the way from the outer wall to the module edge.
assert (switch_access^base).volume()<1e-5
assert (charging_access^base).volume()<1e-5
report['checks']['charging_port_center_y_mm']=W/2
report['checks']['charging_port_nominal_offset']='15 mm from UPS lower-Y edge, inferred from photo; 14 x 8 mm plug access allows fit tolerance'
report['checks']['switch_access_window_mm']=[wl,wh]
report['checks']['battery_to_antenna_projection_gap_mm']=round(bx+bl-6-(cell_x+cell_l),2)
for label,extra in [('default-long',P['button_pin_extension'])]:
    for travel in np.linspace(0,P['button_downstroke'],7):
        for name,fixed in [('lid',lid),('base',base),('pcb',board),('mic-clamp',clamp)]:
            volume=(pin(extra).translate((0,0,-float(travel)))^fixed).volume()
            assert volume<1e-5,(label,travel,name,volume)
        assert (cap.translate((0,0,-float(travel)))^lid).volume()<1e-5
for insertion in np.linspace(-5,0,21):
    overlap=(cap^pin().translate((0,0,float(insertion)))).volume()
    assert overlap<1e-5,('pin-cap insertion',float(insertion),overlap)
# Apertures must remain true holes throughout the lid thickness.
for dx in [-P['mic_hole_pitch'],0,P['mic_hole_pitch']]:
    for dy in [-P['mic_hole_pitch'],0,P['mic_hole_pitch']]:
        probe=cyl(mx+dx,my+dy,seam+0.01,P['mic_hole_diameter']/2-0.01,P['lid_thickness']-0.02)
        assert (probe^lid).volume()<1e-5
# Each clip overlaps the board in plan but clears its seated upper face.
# Therefore it can hold a seated board without depending on the lid screws.
for i,clip in enumerate(clips):
    assert (clip^board).volume()<1e-5, ('clip-seated-board',i)
    lifted=board.translate((0,0,0.3))
    assert (clip^lifted).volume()>0.05, ('clip-does-not-retain-board',i)
# The rigid locked geometry must retain the lid. A sheared-arm envelope models
# clearance during release, not force, fatigue, or a finite-element prediction.
for i,(catch,direction) in enumerate(shell_snaps):
    assert (catch^base).volume()<1e-5, ('shell-catch-seated',i)
    assert (catch.translate((0,0,0.5))^base).volume()>0.1, ('shell-catch-no-retention',i)
    k=direction*P['shell_snap_release_deflection']/(seam-snap_z)
    released=catch.transform([[1,0,0,0],[0,1,-k,k*seam],[0,0,1,0]])
    for lift in np.linspace(0,seam-snap_z+1,25):
        moving=released.translate((0,0,float(lift)))
        for name,fixed in [('base',base),('PCB',board),('components',components)]:
            assert (moving^fixed).volume()<1e-5, ('shell-release-collision',i,lift,name)
report['checks']['shell_snap_retention']='4 seated catches clear base; each blocks 0.5 mm upward lid movement'
report['checks']['shell_snap_release']='4 sheared-arm clearance envelopes x 25 extraction positions; real force/fatigue not simulated'
report['checks']['pcb_clip_root_reinforcement']='4 tapered 5 x 2 mm feet into 2 x 1 mm uprights; free horizontal spring arms unchanged; strength not simulated'
report['checks']['pcb_support_pad_size_mm']=[6,6]
report['checks']['pcb_snap_retention']='4 clips clear seated PCB; each intercepts PCB lifted 0.3 mm; real flex/force unverified'
report['checks'].update(button_motion_clearance='user-confirmed long pin x 7 positions',
    pin_cap_insertion='21 positions without solid intersection',
    button_guide_length_mm=round(top-guide_bottom,3),
    usb_front_recess_mm=P['usb_front_recess'],
    usb_reference='GCT USB4105 shell 8.94 x 3.31 mm; not an identification of the actual PCB connector',
    mic_holes='9 through holes, 2.4 mm diameter, 1.0 mm minimum web',
    button_downstroke_mm=P['button_downstroke'],
    user_verified='Original USB version and supplied battery/module measurements; no electrical tests requested',
    real_hardware_fit='Measured module and cell outlines; assembled fit remains unverified')
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')

# Actual CAD preview, not an AI-generated concept image.
fig=plt.figure(figsize=(14,9),facecolor='#f0f2f4')
views=[(f'BODY {L} x {W} x {top:.1f} mm',[(base,'#343a40'),(lid,'#b9db42'),(cap,'#343a40')]),
       ('EXPLODED / BATTERY TRAY',[(base,'#8a929c'),(actual_power,'#d67b26'),
         (board.translate((0,0,9)),'#217a78'),(tray.translate((0,0,18)),'#ab69ad'),
         (battery.translate((0,0,21)),'#d9d9dc'),(lid.translate((0,0,35)),'#b9db42')]),
       ('STACK / ENVELOPES ONLY',[(actual_power,'#d67b26'),(board,'#217a78'),
          (tray,'#ab69ad'),(actual_battery,'#d9d9dc'),(mic,'#217a78')]),
       ('LID / REMOVABLE TRAY POSTS',[(lid,'#b9db42'),(mic,'#217a78')])]
def raster(items, elevation=32):
    # Orthographic z-buffer: resolves occlusion of large coplanar CAD triangles.
    w,h=1000,640
    direction=np.array([np.cos(np.deg2rad(elevation))*np.cos(np.deg2rad(-125)),
                        np.cos(np.deg2rad(elevation))*np.sin(np.deg2rad(-125)),
                        np.sin(np.deg2rad(elevation))])
    right=np.cross([0,0,1],direction);right/=np.linalg.norm(right)
    up=np.cross(direction,right)
    ts=[mesh(s) for s,c in items]
    allv=np.vstack([t.vertices for t in ts])
    uv=np.column_stack((allv@right,allv@up))
    center=(uv.min(0)+uv.max(0))/2
    scale=min((w-60)/np.ptp(uv[:,0]),(h-60)/np.ptp(uv[:,1]))
    canvas=np.ones((h,w,3))*0.96
    depth=np.ones((h,w))*-np.inf
    light=direction+np.array([-0.3,0.1,0.7]);light/=np.linalg.norm(light)
    for t,(_,color) in zip(ts,items):
        projected=np.column_stack(((t.vertices@right-center[0])*scale+w/2,
                                   h/2-(t.vertices@up-center[1])*scale,
                                   t.vertices@direction))
        for face,normal in zip(t.faces,t.face_normals):
            if normal@direction <= 0: continue
            v=projected[face]
            xmin=max(0,int(np.floor(v[:,0].min()))); xmax=min(w-1,int(np.ceil(v[:,0].max())))
            ymin=max(0,int(np.floor(v[:,1].min()))); ymax=min(h-1,int(np.ceil(v[:,1].max())))
            if xmin>xmax or ymin>ymax: continue
            xx,yy=np.meshgrid(np.arange(xmin,xmax+1)+0.5,np.arange(ymin,ymax+1)+0.5)
            x0,y0=v[0,:2];x1,y1=v[1,:2];x2,y2=v[2,:2]
            den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
            if abs(den)<1e-10: continue
            aa=((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/den
            bb=((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/den
            cc=1-aa-bb
            zz=aa*v[0,2]+bb*v[1,2]+cc*v[2,2]
            sub=depth[ymin:ymax+1,xmin:xmax+1]
            mask=(aa>=-1e-8)&(bb>=-1e-8)&(cc>=-1e-8)&(zz>sub)
            sub[mask]=zz[mask]
            canvas[ymin:ymax+1,xmin:xmax+1][mask]=np.array(to_rgb(color))*(0.45+0.55*max(0,normal@light))
    return canvas

for i,(title,items) in enumerate(views):
    ax=fig.add_subplot(2,2,i+1)
    ax.imshow(raster(items,-35 if i==3 else 32))
    ax.set_axis_off();ax.set_title(title,fontsize=12)
fig.suptitle(f'VOXU / INTEGRATED UPS / FIT REV 4   {L} x {W} x {cap_bottom+2:.1f} mm',fontsize=18)
fig.tight_layout()
fig.savefig(ROOT/'preview.png',dpi=160)
plt.close(fig)
# Dimensioned schematic uses the same measured placement parameters as the CAD.
from matplotlib.patches import Rectangle
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
for ax, title in zip(axes, ['BOTTOM / UPS POSITION', 'TOP / BATTERY POSITION']):
    ax.add_patch(Rectangle((0,0),L,W,fill=False,lw=2))
    ax.add_patch(Rectangle((10,W-7),35,3,color='#79c9de',alpha=.6))
    ax.text(27,W-5.5,'WIRE CHANNEL',ha='center',va='center',fontsize=9)
    ax.set(xlim=(-7,L+3),ylim=(-7,W+4),aspect='equal',title=title,xlabel='mm',ylabel='mm')
    ax.grid(alpha=.15)
    ax.annotate('UPS charging USB-C',xy=(0,W/2),xytext=(-6,5),fontsize=9,
                rotation=90,arrowprops={'arrowstyle':'->'})
px,py,pz=P['power_module_origin_mm']
ax=axes[0]
ax.add_patch(Rectangle((px,py),35,20,color='#d67b26',alpha=.7))
ax.text(px+17.5,py+10,'UPS 35 x 20 mm\ncomponents face up',ha='center',va='center')
ax.plot([P['switch_window_x'],P['switch_window_x']+P['switch_window_length']],[0,0],lw=5,color='#bd4853')
ax.annotate('Recessed switch access\nplastic tool required',xy=(P['switch_window_x']+P['switch_window_length']/2,0),xytext=(22,-6),fontsize=9,
            arrowprops={'arrowstyle':'->'})
bx,by,bz=P['battery_origin_mm']
ax=axes[1]
ax.add_patch(Rectangle((bx,by),35.7,24.9,color='#ab69ad',alpha=.5))
ax.text(bx+17.85,by+12.45,'CELL 35.7 x 24.9 mm\n4.7 mm thick\nin removable tray',ha='center',va='center')
ax.annotate('Lead exit toward USB end',xy=(bx,by+12),xytext=(8,-5),fontsize=9,
            arrowprops={'arrowstyle':'->'})
fig.suptitle('VOXU 62 x 46 mm / MEASURED OUTLINES / FIT REV 4',fontsize=15)
fig.tight_layout()
fig.savefig(ROOT/'layout.png',dpi=160)
plt.close(fig)
from preview_html import write_preview
write_preview(ROOT, [(name, mesh(solid), color, level) for name,solid,color,level in [
 ('底座 · 加固卡扣根部',base,'#9aa7b6',0),
 ('一体 UPS 板（外形包络）',actual_power,'#ef9a48',1),
 ('ESP32 主板（外形包络）',board,'#329b8f',2),
 ('电池托盘',tray,'#ad78bf',3),
 ('550mAh 电池（外形包络）',actual_battery,'#c4cbd5',4),
 ('麦克风（外形包络）',mic,'#329b8f',5),
 ('上盖',lid,'#bbd555',6),
 ('BOOT 按帽',cap,'#71839b',6),
 ('BOOT 顶杆',pin(),'#f0bf61',5),
 ('麦克风压框',clamp,'#ad78bf',5)]])
with zipfile.ZipFile(ROOT/'voxu-battery-fit-prototype.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in sorted(parts):
        p=OUT/(name+'.stl')
        z.write(p,'stl/'+p.name)
    for name in ['README.md','parameters.json','validation.json','preview.png','layout.png','preview.html','preview_html.py','preview-template.html','generate.py','requirements.txt','slicer-result.json','wiring.md','slice.py']:
        p=ROOT/name
        if p.exists(): z.write(p,name)
print(json.dumps(report,indent=2))

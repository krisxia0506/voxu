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
    base += box(x,y,2,6,6,bz-2)
# PCB is located by front wall, side fences and rear fence, not pin headers.
for y in [by-1.3,by+bw+0.3]:
    for x in [bx+4,bx+bl-8]:
        base += box(x,y,2,4,1,bz+P['board_thickness']+0.3-2)
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
    root=box(root_x,by-1.2,2,2,1,4.7)
    arm=box(root_x+1.8,by-1.2,4,12.2,1,2.7)
    lip=(box(tip_x-2.4,by-0.3,clip_lip_z,2.4,0.8,0.06)
         +box(tip_x-2.4,by-0.3,clip_lip_z+1.0,2.4,0.1,0.06)).hull()
    clip=root+arm+lip
    mirrored=clip.mirror((0,1,0)).translate((0,W,0))
    clips.extend([clip,mirrored])
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
base -= usb_capsule(-1,bx+2,P['usb_width'],P['usb_height'],usb_z)
base -= usb_capsule(-0.1,0.9,P['usb_width']+2,P['usb_height']+2,usb_z)
lid = rr(0,0,seam,L,W,P['lid_thickness'],4)
skirt = rr(2.3,2.3,seam-1.6,L-4.6,W-4.6,1.8,1.7)-rr(3.5,3.5,seam-1.7,L-7,W-7,2.1,0.5)
for x,y in screws:
    skirt -= cyl(x,y,seam-2,3.1,3)
# The front alignment skirt is interrupted around the long BOOT guide.
skirt -= box(0,booty-4,seam-2,10,8,3)
lid += skirt
for x,y in hold_downs:
    lid += box(x+0.5,y+0.5,bz+P['board_thickness']+0.2,2,2,
               seam-(bz+P['board_thickness']+0.2)+0.1)
for x,y in screws:
    lid -= cyl(x,y,seam-1,1.15,8)
    lid -= cyl(x,y,top-1,2.05,5)

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

parts={'base':base,'lid':lid,'mic-clamp':clamp,'button-cap':cap,
       'button-pin':pin()}
report={'revision':'v3-snap-board','parameters':P,'parts':{},'checks':{}}
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
report['checks']['pcb_support_pad_size_mm']=[6,6]
report['checks']['pcb_snap_retention']='4 clips clear seated PCB; each intercepts PCB lifted 0.3 mm; real flex/force unverified'
report['checks'].update(button_motion_clearance='user-confirmed long pin x 7 positions',
    pin_cap_insertion='21 positions without solid intersection',
    button_guide_length_mm=round(top-guide_bottom,3),
    usb_front_recess_mm=P['usb_front_recess'],
    usb_reference='GCT USB4105 shell 8.94 x 3.31 mm; not an identification of the actual PCB connector',
    mic_holes='9 through holes, 2.4 mm diameter, 1.0 mm minimum web',
    button_downstroke_mm=P['button_downstroke'],
    user_verified='V2 USB alignment, direct microphone mounting and longest BOOT pin confirmed by user',
    real_hardware_fit='V3 board snap force and enlarged support pads not yet physically verified')
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')

# Actual CAD preview, not an AI-generated concept image.
fig=plt.figure(figsize=(14,9),facecolor='#f0f2f4')
views=[('ASSEMBLED',[(base,'#343a40'),(lid,'#b9db42'),(cap,'#343a40')]),
       ('STACKED / EXPLODED',[(base,'#343a40'),(board,'#217a78'),
         (mic.translate((0,0,13)),'#217a78'),
         (lid.translate((0,0,20)),'#b9db42'),(cap.translate((0,0,24)),'#444444'),(pin().translate((0,0,20)),'#888888')]),
       ('BASE / PCB FIT',[(base,'#8a929c'),(board,'#217a78')]),
       ('LID / DIRECT MIC MOUNT',[(lid,'#b9db42'),(mic,'#217a78')])]
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
fig.suptitle(f'VOXU / P2S PROTOTYPE   {L} x {W} x {cap_bottom+2:.1f} mm',fontsize=18)
fig.tight_layout()
fig.savefig(ROOT/'preview.png',dpi=160)
plt.close(fig)
with zipfile.ZipFile(ROOT/'voxu-p2s-prototype.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in sorted(parts):
        p=OUT/(name+'.stl')
        z.write(p,'stl/'+p.name)
    for name in ['README.md','parameters.json','validation.json','preview.png','generate.py','requirements.txt','slicer-result.json']:
        p=ROOT/name
        if p.exists(): z.write(p,name)
print(json.dumps(report,indent=2))

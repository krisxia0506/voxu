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
bx, by = P['board_x'], (W-P['board_width'])/2
bl, bw, bz = P['board_length'], P['board_width'], P['board_bottom_z']
bootx, booty = bx+P['boot_offset_x'], by+P['boot_offset_y']
mx, my = P['mic_x'], W/2
screws = [(4,4), (L-4,4), (4,W-4), (L-4,W-4)]
# Open-top tray, 2 mm floor/walls. Rounded body; exterior grip flutes are shallow.
base = rr(0,0,0,L,W,seam,7)-rr(2,2,2,L-4,W-4,seam+1,5)
for x in range(24,58,6):
    for y in [-0.5,W-0.7]:
        base -= box(x,y,6,2,1.2,11)
# Four screw bosses with blind pilot holes (no heat-set insert required).
for x,y in screws:
    base += cyl(x,y,2,3.1,seam-2)
    base -= cyl(x,y,seam-10,0.85,11)
# Support only the four PCB corners; underside pins and wires remain free.
corner_pads = [(bx,by),(bx+bl-3,by),(bx,by+bw-3),(bx+bl-3,by+bw-3)]
for x,y in corner_pads:
    base += box(x,y,2,3,3,bz-2)
# End fences and small side fences locate PCB without relying on screw-hole pitch.
for x in [bx-1.4,bx+bl+0.3]:
    for y in [by,by+bw-4]:
        base += box(x,y,2,1.1,4,bz+2-2)
for y in [by-1.4,by+bw+0.3]:
    for x in [bx+4,bx+bl-8]:
        base += box(x,y,2,4,1.1,bz+2-2)
# Generous cable-plug entry, open toward PCB connector. Actual port Z remains adjustable.
base -= box(-1,W/2-P['usb_width']/2,P['usb_bottom_z'],bx+1,P['usb_width'],P['usb_height'])
# Flat lid and friction alignment skirt (0.3 mm per-side clearance).
lid = rr(0,0,seam,L,W,P['lid_thickness'],7)
skirt = rr(2.3,2.3,seam-2,L-4.6,W-4.6,2.2,4.7)-rr(3.5,3.5,seam-2.1,L-7,W-7,2.5,3.5)
for x,y in screws:
    skirt -= cyl(x,y,seam-3,3.5,4)
lid += skirt
# Hold-down fingers, 0.25 mm PCB clearance, directly above supporting corners.
for x,y in corner_pads:
    lid += box(x+0.5,y+0.5,bz+P['board_thickness']+0.25,2,2,seam-(bz+P['board_thickness']+0.25)+0.1)
for x,y in screws:
    lid -= cyl(x,y,seam-1,1.15,8)
    lid -= cyl(x,y,top-1,2.05,5)
# Mic socket on underside, open for installation; two wiring windows.
mic_ring = cyl(mx,my,seam-2.5,9,2.6)-cyl(mx,my,seam-2.6,P['mic_diameter']/2+0.35,2.9)
for y in [my+4,my-11]:
    mic_ring -= box(mx-5,y,seam-3,10,7,4)
lid += mic_ring
for x in [-2,0,2]:
    for y in [-2,0,2]:
        lid -= cyl(mx+x,my+y,seam-0.1,0.6,4)
# Two-piece guided button: cap above lid is a hard stop; pin flange retains cap.
lid -= cyl(bootx,booty,seam-1,3.7,8)
cap_bottom = top+P['button_downstroke']
cap = rr(bootx-6,booty-4,cap_bottom,12,8,2,3.8)
cap += cyl(bootx,booty,seam-0.2,3.4,cap_bottom-(seam-0.2)+0.1)
cap -= cyl(bootx,booty,seam-0.3,P['button_socket_diameter']/2,4.7)
# Lead-in opens at the insertion face; retains 3.4 mm guide diameter deeper inside.
cap -= m.Manifold.cylinder(P['button_socket_entry_depth'],
    P['button_socket_entry_diameter']/2,P['button_socket_diameter']/2,
    circular_segments=64).translate((bootx,booty,seam-0.2))
foot = bz+P['board_thickness']+P['boot_height_above_pcb']+P['button_initial_gap']

def pin(extra=0):
    a = cyl(bootx,booty,seam-1.4,5,1.2)
    # Flat on flange clears the nearby PCB corner hold-down finger.
    a -= box(bootx-6,booty-6,seam-1.5,12,3,1.5)
    a += cyl(bootx,booty,foot-extra,1.4,seam-1.4-(foot-extra)+0.1)
    a += cyl(bootx,booty,seam-0.3,1.5,4.3)
    return a

# Printable coupon: full-board fit tray plus separate guide/plug gauges.
# Slice of the real base checks PCB placement, corner supports and USB opening.
coupon = base ^ box(-1,-1,0,bx+bl+3,W+2,bz+2.2)
guide = box(0,0,0,18,18,2.4)-cyl(9,9,-1,3.7,5)
# Keep CAD assembly coordinates separate from print orientations.
parts = {'base':base,'lid':lid,'button-cap':cap,'button-pin-standard':pin(),
         'button-pin-short':pin(-0.4),'button-pin-long':pin(0.4),
         'board-fit-test':coupon,'button-guide-test':guide}
report = {'parameters':P,'parts':{},'checks':{}}
for name, solid in parts.items():
    t = mesh(solid)
    assert str(solid.status()) == 'Error.NoError', (name,solid.status())
    assert t.is_watertight and t.is_winding_consistent and t.volume>0, name
    assert len(t.split()) == 1, (name,'disconnected shells')
    # Flat exterior of lid and flat top of cap face the print bed.
    if name in ['lid','button-cap']:
        t.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
    t.apply_translation(-t.bounds[0])
    assert np.all(t.extents < 256), name
    t.export(OUT / (name+'.stl'))
    report['parts'][name]={'size_mm':np.round(t.extents,3).tolist(),'volume_mm3':round(t.volume,2),'watertight':True,'connected_components':1}
# Mechanical clearance evidence for the declared model, not a real-world fit claim.
board = box(bx,by,bz,bl,bw,P['board_thickness'])
for name,a,b in [('base-lid',base,lid),('board-base',board,base),('board-lid',board,lid),('button-cap-lid',cap,lid),('button-pin-lid',pin(),lid),('button-pin-base',pin(),base)]:
    volume=(a^b).volume()
    assert volume < 1e-5, (name, volume)
    report['checks'][name+'_intersection_mm3']=round(volume,8)
for label,extra in [('short',-0.4),('standard',0),('long',0.4)]:
    for travel in np.linspace(0,P['button_downstroke'],7):
        for name,fixed in [('lid',lid),('base',base),('pcb',board)]:
            volume=(pin(extra).translate((0,0,-float(travel)))^fixed).volume()
            assert volume < 1e-5, (label,travel,name,volume)
        assert (cap.translate((0,0,-float(travel)))^lid).volume() < 1e-5
report['checks']['button_motion_clearance']='3 pin lengths x 7 positions: no intersection with nominal lid/base/PCB'
# Verify axial insertion into cap, not just the installed button-to-lid fit.
for insertion in np.linspace(-5,0,21):
    overlap=(cap ^ pin().translate((0,0,float(insertion)))).volume()
    assert overlap < 1e-5, ('pin-cap insertion interference',float(insertion),overlap)
report['checks']['pin_cap_insertion']='21 insertion positions: no solid intersection'
report['checks']['pin_socket_diametral_clearance_mm']=round(P['button_socket_diameter']-3.0,3)
report['checks']['button_downstroke_mm']=P['button_downstroke']
report['checks']['switch_motion_after_gap_mm']=P['button_downstroke']-P['button_initial_gap']
report['checks']['real_hardware_fit']='UNVERIFIED: print fit tests and measure BOOT height before final assembly'
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')

# Actual CAD preview, not an AI-generated concept image.
fig=plt.figure(figsize=(14,9),facecolor='#f0f2f4')
views=[('ASSEMBLED',[(base,'#343a40'),(lid,'#b9db42'),(cap,'#343a40')]),
       ('EXPLODED',[(base,'#343a40'),(board,'#217a78'),(lid.translate((0,0,20)),'#b9db42'),(cap.translate((0,0,24)),'#444444'),(pin().translate((0,0,20)),'#888888')]),
       ('BASE / PCB FIT',[(base,'#8a929c'),(board,'#217a78')]),
       ('LID UNDERSIDE',[(lid,'#b9db42')])]
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
    for p in sorted(OUT.glob('*.stl')):
        z.write(p,'stl/'+p.name)
    for name in ['README.md','parameters.json','validation.json','preview.png','generate.py','requirements.txt','slicer-result.json']:
        p=ROOT/name
        if p.exists(): z.write(p,name)
print(json.dumps(report,indent=2))

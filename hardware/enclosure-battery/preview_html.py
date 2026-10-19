"""Embed assembly-coordinate triangle meshes in an offline WebGL viewer."""
import json

def write_preview(root, parts, annotations=None):
    data=[]
    for name,mesh,color,level in parts:
        vertices=mesh.triangles.reshape(-1,3).round(4).tolist()
        normals=mesh.face_normals.repeat(3,axis=0).round(4).tolist()
        data.append(dict(name=name,positions=vertices,normals=normals,
                         color=[int(color[i:i+2],16)/255 for i in (1,3,5)],level=level))
    template=(root/'preview-template.html').read_text()
    html=template.replace('/*ASSEMBLY_DATA*/',json.dumps(data,separators=(',',':')))
    html=html.replace('/*ANNOTATIONS*/',json.dumps(annotations or [],ensure_ascii=False))
    html=html.replace('</html>',(root/'wiring-panel.html').read_text()+'\n</html>')
    (root/'preview.html').write_text(html)

"""Embed assembly-coordinate triangle meshes in an offline WebGL viewer."""
import json

def write_preview(root, parts):
    data=[]
    for name,mesh,color,level in parts:
        vertices=mesh.triangles.reshape(-1,3).round(4).tolist()
        normals=mesh.face_normals.repeat(3,axis=0).round(4).tolist()
        data.append(dict(name=name,positions=vertices,normals=normals,
                         color=[int(color[i:i+2],16)/255 for i in (1,3,5)],level=level))
    template=(root/'preview-template.html').read_text()
    (root/'preview.html').write_text(template.replace('/*ASSEMBLY_DATA*/',json.dumps(data,separators=(',',':'))))

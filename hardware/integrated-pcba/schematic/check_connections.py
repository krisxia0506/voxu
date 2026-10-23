"""Check the generated subcircuit connectivity, not a replacement for KiCad ERC."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
text = (root/'microphone.kicad_sch').read_text()
tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
stack=[]; result=[]
for token in tokens:
    if token=='(':
        item=[]
        (stack[-1] if stack else result).append(item)
        stack.append(item)
    elif token==')':
        assert stack, 'unexpected closing parenthesis'
        stack.pop()
    else:
        assert stack, 'token outside expression'
        stack[-1].append(json.loads(token) if token.startswith('"') else token)
assert not stack and len(result)==1
sch=result[0]
def children(node,tag): return [x for x in node if isinstance(x,list) and x and x[0]==tag]
def child(node,tag):
    found=children(node,tag); assert len(found)==1,(tag,len(found));return found[0]
def xy(node): return tuple(round(float(v),3) for v in node[1:3])
parent={}
def find(x):
    parent.setdefault(x,x)
    if parent[x]!=x: parent[x]=find(parent[x])
    return parent[x]
def union(a,b): parent[find(a)]=find(b)
for w in children(sch,'wire'):
    a,b=children(child(w,'pts'),'xy');union(xy(a),xy(b))
for label in children(sch,'label'): union(xy(child(label,'at')),label[1])
libs={s[1]:s for s in children(child(sch,'lib_symbols'),'symbol')}
actual={}; values={}
for inst in children(sch,'symbol'):
    props={p[1]:p[2] for p in children(inst,'property')}
    ref=props['Reference'];assert ref not in actual
    x,y=xy(child(inst,'at'));assert float(child(inst,'at')[3])==0
    lib=libs[child(inst,'lib_id')[1]];actual[ref]={};values[ref]=props['Value']
    for unit in children(lib,'symbol'):
        for pin in children(unit,'pin'):
            px,py=xy(child(pin,'at'));num=child(pin,'number')[1]
            actual[ref][num]=find((round(x+px,3),round(y-py,3)))
expected={'U1':{'1':'MIC_BCLK_GPIO26','2':'MIC_SD_GPIO33','3':'MIC_WS_GPIO25','4':'GND','5':'GND','6':'GND','7':'3V3','8':'3V3','9':'GND'},'R1':{'1':'MIC_SD_GPIO33','2':'GND'},'C1':{'1':'3V3','2':'GND'}}
assert set(actual)==set(expected)
for ref,pins in expected.items():
    assert set(actual[ref])==set(pins)
    for n,net in pins.items(): assert find(actual[ref][n])==find(net),(ref,n,net)
nets=['3V3','GND','MIC_BCLK_GPIO26','MIC_WS_GPIO25','MIC_SD_GPIO33']
assert len({find(n) for n in nets})==len(nets),'unexpected net short'
assert values=={'U1':'INMP441','R1':'100k 1% 0603','C1':'100n X7R 10V 0603'}
print('PASS: 13 pins, 5 distinct nets, decoupling and pulldown; no unexpected shorts.')
print('Not checked: footprint, manufacturing rules, complete mainboard or physical hardware.')

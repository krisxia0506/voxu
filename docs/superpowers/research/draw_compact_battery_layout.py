"""Render an architectural layout target, not printable CAD or collision proof."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib import font_manager
ROOT=Path(__file__).resolve().parent
font=Path('/System/Library/Fonts/STHeiti Medium.ttc')
if font.exists():
    font_manager.fontManager.addfont(str(font))
    plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams['svg.fonttype']='none'
plt.rcParams['svg.hashsalt']='voxu-compact-target'
fig,axes=plt.subplots(1,3,figsize=(14,6))
fig.patch.set_facecolor('#f7f8fa')
def panel(ax,title):
    ax.set(xlim=(-4,90),ylim=(102,-6),aspect='equal')
    ax.set_title(title,fontsize=13,pad=12)
    ax.set_xticks([0,20,40,60,80]);ax.set_yticks([0,20,40,60,80,100]);ax.tick_params(labelsize=8)
    ax.set_xlabel('mm');ax.set_ylabel('mm')
def box(ax,x,y,w,h,color,text='',fs=10):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=color,edgecolor='#42506a',lw=1))
    ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=fs)
for a,t in zip(axes,['外形目标对比','下层与中层（分开展示）','上层主板与外观布局']):panel(a,t)
box(axes[0],0,0,86,96,'#e3e4e8')
box(axes[0],0,0,72,52,'#b6d4e8','新目标\n72 × 52 × 39 mm',12)
axes[0].text(43,75,'旧方案已否决\n86 × 96 × 41.4 mm',ha='center',va='center',fontsize=11,color='#655b60')
axes[0].text(43,100,'目标体积减少约 57%',ha='center',fontsize=11)
box(axes[1],0,0,72,52,'white')
box(axes[1],4,4,62,40,'#f5d49a','2000 mAh 电池仓预算\n62 × 40 × 9 mm',10)
box(axes[1],0,61,72,35,'#f4f6f7')
# Draw the same proposed daughterboard rotated only for separate visual display.
box(axes[1],8,68,45,20,'#b8d9cb','定制小板：45 × 20 mm\n需实际布线证明',9)
axes[1].text(36,58,'中层实装将旋转 90°，靠 USB 端',ha='center',fontsize=9)
axes[1].text(36,100,'电池与小板的连接器/线束尚未建模',ha='center',fontsize=8,color='#954e28')
box(axes[2],0,0,72,52,'white')
box(axes[2],2.4,11.835,51.45,28.33,'#b6d4e8','ESP32 主板\n51.45 × 28.33',9)
box(axes[2],41.85,11.835,12,28.33,'#eebdb7','天线\n假定区',8)
axes[2].plot([0,2.4],[26,26],color='#2461a0',lw=5)
axes[2].add_patch(plt.Circle((22.5,26),7,fill=False,edgecolor='#2e647c',lw=1.6,ls='--'))
axes[2].annotate('原 USB-C',xy=(0,26),xytext=(4,66),arrowprops={'arrowstyle':'->'},fontsize=10)
axes[2].text(36,78,'上盖保留麦克风和 BOOT\n仅设运行开关，无模式切换',ha='center',fontsize=11)
axes[2].text(36,96,'3.3 V 直供；原串口桥与稳压需隔离',ha='center',fontsize=9,color='#954e28')
fig.suptitle('紧凑电池版：集成小板 + 多类型 USB 充电识别',fontsize=18,y=.97)
fig.text(.5,.03,'架构占位图，不是 PCB/CAD 成品。尺寸、续航和兼容性均待实现与验证；定制板需贴片加工。',ha='center',fontsize=10,color='#954e28')
fig.subplots_adjust(left=.06,right=.98,top=.83,bottom=.15,wspace=.3)
svg=ROOT/'2026-09-30-compact-battery-layout.svg'
fig.savefig(svg,bbox_inches='tight',metadata={'Date':None})
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
fig.savefig(ROOT/'2026-09-30-compact-battery-layout.png',dpi=160,bbox_inches='tight')

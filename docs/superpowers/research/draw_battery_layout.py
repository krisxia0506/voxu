from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib import font_manager
out=Path(__file__).resolve().parent
font=Path('/System/Library/Fonts/STHeiti Medium.ttc')
if font.exists():
    font_manager.fontManager.addfont(str(font))
    plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams['svg.fonttype']='none'
plt.rcParams['svg.hashsalt']='voxu-battery-layout-proposal'
fig,axs=plt.subplots(1,3,figsize=(15,7.5),gridspec_kw={'width_ratios':[1,1,1.15]})
fig.patch.set_facecolor('#f7f8fa')
colors={'esp':'#bcd8ed','batt':'#f5d596','cc':'#c7dec8','bq':'#d9cff0','boost':'#b8dedc','logic':'#ecd0d0'}
def r(ax,x,y,w,h,label,color,fs=10):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=color,edgecolor='#36485c',lw=1.2))
    ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=fs)
def shell(ax,title):
    ax.set(xlim=(-4,90),ylim=(102,-7),aspect='equal')
    ax.add_patch(FancyBboxPatch((0,0),86,96,boxstyle='round,pad=0,rounding_size=4',facecolor='white',edgecolor='#27374b',lw=2))
    ax.add_patch(Rectangle((2,2),82,92,fill=False,edgecolor='#b7bec8',ls='--'))
    ax.set_title(title,fontsize=13,pad=12)
    ax.set_xticks([0,20,40,60,86]);ax.set_yticks([0,20,40,60,80,96]);ax.tick_params(labelsize=8)
    ax.set_xlabel('mm');ax.set_ylabel('mm')
shell(axs[0],'下层：电池与自动检测')
r(axs[0],5,5,60,50,'2500 mAh 保护电池\n60 × 50 × 7.3',colors['batt'])
r(axs[0],5,62,57.15,25.4,'USB-C Power 2 Click\n57.15 × 25.4',colors['cc'],9)
r(axs[0],65,62,16,28,'控制\n小板\n占位',colors['logic'],9)
axs[0].text(43,92,'检测板端子、线弯与固定结构仍需核对',ha='center',fontsize=8,color='#994b20')
shell(axs[1],'上层：主板与电源模块')
r(axs[1],2.4,5,51.45,28.33,'ESP32\n51.45 × 28.33',colors['esp'])
r(axs[1],41.85,5,12,28.33,'天线\n假定区','#edb9b9',9)
r(axs[1],5,49,33.02,38.1,'BQ24074\n旋转 90°\nPCB 33.02 × 38.10',colors['bq'],9)
r(axs[1],43,51,29,23,'PowerBoost\n29 × 23',colors['boost'],9)
r(axs[1],74,36,8,13,'运行\n开关','#e1e4e8',8)
axs[1].plot([0,3],[19.165,19.165],color='#2461a0',lw=6)
axs[1].annotate('原 USB-C',xy=(0,19.165),xytext=(4,43),fontsize=9,arrowprops={'arrowstyle':'->','color':'#2461a0'})
axs[1].add_patch(plt.Circle((22.5,19.165),7,fill=False,edgecolor='#2c617c',ls='--',lw=1.8))
axs[1].text(22.5,38,'虚线圆：上盖麦克风位置',ha='center',fontsize=8)
ax=axs[2];ax.set_title('侧向高度预算（不是剖切 CAD）',fontsize=13,pad=12)
ax.set(xlim=(-4,90),ylim=(-4,52),aspect='equal');ax.set_xlabel('mm');ax.set_ylabel('高度 mm')
ax.add_patch(Rectangle((0,0),86,41.4,fill=False,edgecolor='#27374b',lw=2))
r(ax,0,39,86,2.4,'平面上盖','#dce1e7',9)
r(ax,5,3,60,7.3,'电池',colors['batt'])
r(ax,5,26,51.45,1.6,'',colors['esp'])
ax.text(30,30,'主板 PCB 底面 z=26',ha='center',fontsize=10)
ax.annotate('',xy=(69,26),xytext=(69,10.3),arrowprops={'arrowstyle':'<->','color':'#567047'})
ax.text(72,18,'15.7\nmm',fontsize=9,va='center')
ax.text(43,45,'壳体提案：86 × 96 × 41.4 mm',ha='center',fontsize=12)
ax.text(43,-3,'端子、焊线、托盘与螺钉包络未验证',ha='center',fontsize=9,color='#994b20')
fig.suptitle('已否决 · 大尺寸现成模块布局（历史记录）',fontsize=19,y=.97)
fig.text(.5,.075,'一个外部 USB-C · 一个运行开关 · 无电脑/充电器切换开关',ha='center',fontsize=12)
fig.text(.5,.035,'设计占位图，非可打印模型。高度、原板天线范围和控制小板尺寸含假设；不构成装配或电气验证。',ha='center',fontsize=10,color='#884522')
fig.subplots_adjust(left=.05,right=.985,top=.88,bottom=.15,wspace=.28)
svg_path=out/'2026-09-30-battery-layout-proposal.svg'
fig.savefig(svg_path,bbox_inches='tight',metadata={'Date':None})
svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines())+'\n')
fig.savefig(out/'2026-09-30-battery-layout-proposal.png',dpi=160,bbox_inches='tight')

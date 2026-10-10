"""Static source-versus-generated comparisons for completion v2."""
from pathlib import Path
import sys,json
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import geometry
from crown_completion import trim_height
from core_completion import wall_regions
C=json.loads((ROOT/'parameters/completion.json').read_text())
CFG=json.loads((ROOT/'parameters/model_config.json').read_text())
OUT=ROOT/'views';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
def picture(ax,path,title):
 ax.imshow(Image.open(ROOT/path));ax.axis('off');ax.set_title(title,fontweight='bold',fontsize=12,pad=12)
def finish(fig,name,foot):
 fig.text(.03,.015,foot,fontsize=10,color='#773c2d');fig.savefig(OUT/name,dpi=150,facecolor='white',bbox_inches='tight');plt.close(fig);print(name)

fig,axs=plt.subplots(1,3,figsize=(15,6),gridspec_kw={'width_ratios':[1.2,1,1]})
picture(axs[0],'references/new_core/S13_Fig5_crop.png','Su2013 Fig5 / Zone2 source plan')
picture(axs[1],'views/VIEW_09_CORE_PLAN.png','Actual Blender Z2 / no opening detail')
ax=axs[2]
for rect in wall_regions(C['core'],2):
 a,b,c,d=rect;ax.add_patch(plt.Rectangle((a,b),c-a,d-b,color='#3a4854'))
ax.set(xlim=(-17,17),ylim=(-17,17),xlabel='Local X / m',ylabel='Local Y / m');ax.set_aspect('equal');ax.set_title('Trace-derived wall grid',fontweight='bold')
for x in C['core']['inner_axes_x_m']:ax.axvline(x,color='#bf7147',lw=.7,linestyle=':')
for y in C['core']['inner_axes_y_m']:ax.axhline(y,color='#bf7147',lw=.7,linestyle=':')
finish(fig,'COMPARE_07_CORE_SOURCE.png','30m outer extent; internal axes read from schematic. Doors/lintels omitted. Source-stage grid and thickness are not as-built coordinates.')

fig,axs=plt.subplots(1,3,figsize=(15,8),gridspec_kw={'width_ratios':[1,1,1.2]})
picture(axs[0],'references/new_inner/Ding_Fig5_measured_zone_widths.png','Ding2010 Fig5 / measured section')
picture(axs[1],'views/VIEW_08_INNER.png','Actual Blender / candidate B shells')
ax=axs[2]
for z in C['inner']['zones']:
 r=z['radius_m'];lo=z['z0_m'];hi=z['z1_m'];err=z['radius_error_bound_m'];ax.plot([r,r],[lo,hi],color='#187b91',lw=2);ax.fill_betweenx([lo,hi],r-err,r+err,color='#4fa3b7',alpha=.13);ax.text(r+1.9,(lo+hi)/2,f"Z{z['zone']}: {r:g}m",fontsize=9)
z=np.linspace(45,632,250);a=np.array([(CFG['profile']['R1_m']-CFG['profile']['L4_m'])*geometry.curve_state(float(h),CFG)['scale'] for h in z]);ax.plot(a,z,color='#bf7147',lw=1.4,label='A mother minimum radius')
ax.axhspan(542,580,color='#dddddd',alpha=.45,label='B upper limit unresolved');ax.set(xlabel='Radius / m',ylabel='Source structural-zone elevation / m',ylim=(-1,640),xlim=(18,50));ax.legend(loc='upper right',fontsize=9);ax.grid(alpha=.18);ax.set_title('Measured stepped radius / uncertainty',fontweight='bold')
finish(fig,'COMPARE_08_INNER_SOURCE.png','B is concentric, fixed azimuth, stepped by zone. ±1.5m is a candidate allowance; schematic/version error is not statistically bounded.')

fig,axs=plt.subplots(1,3,figsize=(16,7),gridspec_kw={'width_ratios':[1.25,1,1]})
picture(axs[0],'references/new_crown/NTUA_original-000.png','TT / Gensler crown section (NTUA Fig8)')
picture(axs[1],'views/VIEW_07_CROWN.png','Actual Blender / open crown fit')
ax=axs[2];s=np.linspace(0,1,301);h=np.array([trim_height(float(v),C['crown']) for v in s]);ax.plot(s,h,color='#187b91',lw=2);ax.fill_between(s,h-1.5,h+1.5,color='#4fa3b7',alpha=.16);ax.scatter([0,.5,1],[632,610.194,627.452],color='#bf7147',s=35);ax.set(xlabel='Derived open-arc station s',ylabel='Candidate rim elevation / m',xlim=(-.03,1.03),ylim=(599,636));ax.grid(alpha=.18);ax.set_title('Explicit two-branch fit',fontweight='bold');ax.text(.5,603,'Station mapping unconfirmed',ha='center',fontsize=10,color='#773c2d')
finish(fig,'COMPARE_09_CROWN_SOURCE.png','No horizontal cap. 632m is the published height; other section anchors and circumferential mapping are derived. Actual V-groove boundary is unknown.')

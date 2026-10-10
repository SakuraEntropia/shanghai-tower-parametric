"""Export scientific comparison figures; do not infer precision from source pixels."""
from pathlib import Path
import sys
import json
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import geometry
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
CFG=json.loads((ROOT/'parameters/model_config.json').read_text())
ANCHORS=json.loads((ROOT/'parameters/floor_anchors.json').read_text())['anchors']
VIEWS=ROOT/'views';VIEWS.mkdir(exist_ok=True)


def save(fig,name):
    fig.savefig(VIEWS/name,dpi=180,bbox_inches='tight',facecolor='white');plt.close(fig)


def main():
    pts=np.array(geometry.sample_profile(CFG,720));closed=np.vstack([pts,pts[0]])
    fig,ax=plt.subplots(1,2,figsize=(14,6),gridspec_kw={'width_ratios':[1,1]})
    ax[0].imshow(Image.open(ROOT/'references/Gensler_Fig3_profile_detail.png'));ax[0].axis('off')
    ax[0].set_title('Gensler 2010 / Fig.3: source control sketch')
    ax[1].plot(closed[:,0],closed[:,1],color='#bb7b27',lw=1.5,label='Derived mother profile; V-notch unresolved')
    for arc in geometry.profile_segments(CFG):
        a=np.linspace(math.radians(arc['start_deg']),math.radians(arc['end_deg']),100)
        xy=np.array(arc['center'])+arc['radius']*np.column_stack([np.cos(a),np.sin(a)])
        if arc['id']=='K2':ax[1].plot(xy[:,0],xy[:,1],color='#dd3d21',lw=3,label='K2 excluded from curtain: guard region')
    ax[1].add_patch(plt.Rectangle((-15,-15),30,30,fill=False,ec='#556776',ls='--',label='30 m core envelope, local placement assumed'))
    ax[1].set_aspect('equal');ax[1].set_xlabel('Local X (m)');ax[1].set_ylabel('Local Y (m)');ax[1].grid(alpha=.2);ax[1].legend(loc='lower left',fontsize=8)
    ax[1].set_title('Analytic reconstruction at z=45 m')
    fig.text(.02,.015,'Dimensional labels drive reconstruction. No pixel-fit error claimed. R2 and mm interpretation are derived; full actual A outline is not verified.',fontsize=9)
    save(fig,'COMPARE_01_PLAN_SOURCE.png')

    fig,ax=plt.subplots(1,2,figsize=(12,9))
    ax[0].imshow(Image.open(ROOT/'references/Su2013_Fig6_floor_anchors.png'));ax[0].axis('off');ax[0].set_title('Su et al. 2013 / Fig.6: source monitoring elevations')
    for i,a in enumerate(ANCHORS):
        y=a['z_m'];ax[1].hlines(y,0,1,color='#368a79',lw=1)
        ax[1].text(1.05,y,f"{a['source_floor_label']}: {y:.2f} m",va='center',fontsize=8)
    ax[1].hlines(632,0,1,color='#bd7f2c',lw=2);ax[1].text(1.05,632,'632 m height metric / datum offset unresolved',fontsize=8,va='center')
    ax[1].set_ylim(-5,655);ax[1].set_xlim(0,3.5);ax[1].set_xticks([]);ax[1].set_ylabel('Published nominal elevation (m)');ax[1].set_title('18 source-labeled guides generated')
    fig.text(.02,.015,'Not a full floor schedule. Source labels retained; normalized operational floor IDs remain null. No 632/128 average-height model.',fontsize=9)
    save(fig,'COMPARE_02_ELEVATIONS.png')

    fig,ax=plt.subplots(1,3,figsize=(15,5))
    colors=['#2d7894','#c8862a']
    for (name,v),c in zip(CFG['versions'].items(),colors):
        zs=np.linspace(v['z0_m'],v['z1_m'],200)
        state=[geometry.curve_state(float(z),CFG,name) for z in zs]
        ax[0].plot([s['theta_deg'] for s in state],zs,c=c,label=name.replace('gensler_',''))
        ax[1].plot([s['scale'] for s in state],zs,c=c)
    ax[0].set_xlabel('Conditional local rotation (deg)');ax[1].set_xlabel('Conditional remaining scale');ax[0].legend(fontsize=8)
    for a in ax[:2]:a.set_ylabel('z (m)');a.grid(alpha=.2)
    for z in CFG['sampling']['section_z_m']:
        xy=np.array(geometry.transform_profile(pts.tolist(),z,CFG))[:,:2];xy=np.vstack([xy,xy[0]])
        ax[2].plot(xy[:,0],xy[:,1],lw=.8,label=f'{z:g} m')
    ax[2].set_aspect('equal');ax[2].set_xlabel('Local X (m)');ax[2].set_ylabel('Local Y (m)');ax[2].legend(fontsize=7,ncol=2)
    fig.suptitle('Curve versions remain separate / no crown or bottom extrapolation')
    fig.text(.02,.005,'2010: 45-605 m, q=0.5586. 2014: assumed 45-632 m, q=0.55. Both conditional; orientation convention and notch unresolved.',fontsize=9)
    save(fig,'COMPARE_03_TWIST_SCALE_PLANS.png')

    pairs=[('Gensler_p15_panel_details.png','VIEW_04_CURTAIN_DETAIL.png','COMPARE_04_CURTAIN_DETAIL.png','Gensler 2010 / Fig.30-32: historical panel/frame proposal','Generated historical detail specimen; not as-built node'),
           ('CTBUH2014_p51_CWSS.png','VIEW_05_CWSS.png','COMPARE_05_CWSS.png','TJAD 2014 / p51: support mechanism','Generated section-size specimen; layout lengths display only')]
    for ref,view,name,lt,rt in pairs:
        if not (VIEWS/view).exists():continue
        fig,ax=plt.subplots(1,2,figsize=(14,8))
        ax[0].imshow(Image.open(ROOT/'references'/ref));ax[0].set_title(lt)
        ax[1].imshow(Image.open(VIEWS/view));ax[1].set_title(rt)
        for a in ax:a.axis('off')
        fig.text(.02,.012,'Source and generated view are compared by mechanism and cited nominal sizes. No shop-drawing coordinate or fabrication fit has been verified.',fontsize=9)
        save(fig,name)
    # A dedicated same-scale section exposes the control envelope, sparse floors and unresolved topology.
    fig,ax=plt.subplots(figsize=(7,11))
    zs=np.linspace(45,632,220)
    edge=[]
    for z in zs:
        xys=np.array(geometry.transform_profile(pts.tolist(),float(z),CFG))[:,:2]
        edge.append([xys[:,0].min(),xys[:,0].max()])
    edge=np.array(edge)
    ax.plot(edge[:,0],zs,c='#b58032');ax.plot(edge[:,1],zs,c='#b58032')
    ax.plot([-15,-15],[-1,239.4],c='#6d7d89');ax.plot([15,15],[-1,239.4],c='#6d7d89')
    for a in ANCHORS:
        z=a['z_m'];ax.hlines(z,-55,55,color='#348b78',lw=.6);ax.text(58,z,a['source_floor_label'],fontsize=7,va='center')
    ax.set_aspect('equal');ax.set_xlim(-75,90);ax.set_ylim(-5,650);ax.set_xlabel('Local X (m)');ax.set_ylabel('Published/conditional z (m)')
    ax.set_title('Orthographic diagnostic section\nMother envelope + core envelope + sparse elevation guides')
    ax.text(-70,610,'Crown trim unresolved',fontsize=8,color='#d73d22')
    ax.text(-70,12,'Bottom / podium unresolved',fontsize=8,color='#d73d22')
    save(fig,'COMPARE_06_DIAGNOSTIC_SECTION.png')
    print('Comparison figures generated:',len(list(VIEWS.glob('COMPARE_*.png'))))

if __name__=='__main__':main()

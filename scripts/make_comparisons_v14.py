"""Own plan controls and linked primary photograph, not redistributed photos."""
from pathlib import Path
import json,sys,math
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import geometry
from podium_v9 import plan_xy,sweep_point
from corrections_v11 import courtyard_points
from raised_end_v14 import frame
from site_v8 import xy
from transition_v5 import outer_reference,control_profile_at

def main():
    p=json.loads((R/'parameters/podium_v9.json').read_text());sp=json.loads((R/'parameters/site_v8.json').read_text());cfg=json.loads((R/'parameters/model_config.json').read_text());cfg['notch_v4']=json.loads((R/'parameters/notch_v4.json').read_text())
    if p['version']!='podium-v14-raised-end':raise RuntimeError('Historical v14 controls; use make_comparisons_v15.py for the current model')
    _,base=outer_reference(geometry,cfg);tower=[q[:2] for q in control_profile_at(geometry,cfg,base,0)]
    boundary=[plan_xy(p,q) for q in p['ground_outline_px']];garden=[plan_xy(p,q) for q in courtyard_points(p,p['courtyard_photo_fit_px'])];axis=[sweep_point(p,i/40,.5)[:2] for i in range(41)];front=frame(p)[:2]
    report={'evidence_level':'推导值（软件图纸配准）','source_ids':['GENSLER_ARCHJOURNAL_V8','SWA_RAISED_END_V14'],'asbuilt_verified':False,
            'p31_origin_world_m':plan_xy(p,p['tower_center_px']),'p29_origin_world_m':xy(sp,sp['tower_center_px']),
            'p31_scale_m_per_px':p['ground_scale_bar_m']/math.dist(*p['ground_scale_bar_px']),
            'p29_scale_m_per_px':sp['scale_bar_m']/math.dist(*sp['scale_bar_px']),
            'shared_rotation_candidate_deg':p['rotation_candidate_deg'],'garden_front_edge_world_m':front,
            'tower_ground_bounds_m':[[min(q[k] for q in tower),max(q[k] for q in tower)] for k in (0,1)],
            'uncertainty':'Origin/rotation consistency verifies implementation only. True north, phase crosswalk and below45m A/base actual contours unavailable; no surveyed alignment error bound.'}
    (R/'parameters/registration_v14.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    def path(points,close=True):return ' '.join(('M' if i==0 else 'L')+f'{330+3*x:.2f},{300-3*y:.2f}' for i,(x,y) in enumerate(points))+(' Z' if close else '')
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="720" height="690" viewBox="0 0 720 690"><rect width="720" height="690" fill="#faf9f5"/><g font-family="sans-serif" font-size="15"><text x="28" y="30">v14 local plan registration — metres, not a north survey</text>']
    for ps,color,fill,width,close in [(boundary,'#667078','#dddcd5',1.5,True),(tower,'#236c9e','none',2,True),(garden,'#35955f','#b4dbb6',2,True),(axis,'#ab9140','none',2,False),(front,'#e3702d','none',4,False)]:parts.append(f'<path d="{path(ps,close)}" stroke="{color}" fill="{fill}" stroke-width="{width}"/>')
    parts+=['<circle cx="330" cy="300" r="4" fill="#222"/><text x="340" y="300">Tower origin / p29 + p31</text>',
            '<text x="28" y="570" fill="#236c9e">Blue: candidate tower base (extrapolated below45m)</text>',
            '<text x="28" y="598" fill="#667078">Grey: published p31 ground trace / candidate placement</text>',
            '<text x="28" y="626" fill="#35955f">Green: fitted raised garden; orange: shared front rim</text>',
            '<text x="28" y="654">No surveyed coordinate or geometric residual is asserted.</text></g></svg>']
    (R/'views/VIEW_40_V14_PLAN_REGISTRATION.svg').write_text(''.join(parts))
    photo='https://swacdn.s3.amazonaws.com/wp-content/uploads/2020/07/07081612/Shanghai-Tower-Jonnu-Singleton-0013.jpg'
    page='''<!doctype html><meta charset="utf-8"><title>v14 抬升露台端</title><style>body{font:16px sans-serif;background:#f6f5f1;margin:28px}section{padding:20px;background:white;margin:18px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}img{width:100%;object-fit:contain;max-height:650px}p{max-width:1050px}</style><h1>v14：露台端抬升与主楼关系</h1><p>原图来自SWA自身图库，摄影Jonnu Singleton；无标尺/摄影日期。抬升、通行空间、可见斜撑是图像支持的构造关系，模型曲率/净空/退進尺寸为候选。原照片通过其原URL引用，仓库没有图像副本。</p>'''
    page+='<section><p><a href="https://www.swagroup.com/projects/shanghai-tower/">SWA一手图库，Jonnu Singleton-0013</a> · 未做虚构相机标定。右图为核验临时隐藏近处树冠/树干；保存模型仍保留这些对象。</p><div class="pair"><img src="'+photo+'" alt="SWA原发布实景，联网加载"><img src="VIEW_37_V14_RAISED_END_FROM_GROUND.png" alt="当前保存模型仰视"></div></section>'
    page+='<section><p>露台与抬升包覆共享前沿，原落地封闭玻璃撤去，商业地面接口向后退。整体塔楼/裙房未因未经标定照片作任意旋转或平移。</p><img src="VIEW_38_V14_TERRACE_AND_TOWER.png"></section><section><p>同一局部坐标中的图纸锚点与模型A基部：软件配准检查不能替代竣工测绘。A基部是45m母曲线外推，实际首层/北向仍需CAD。</p><img src="VIEW_40_V14_PLAN_REGISTRATION.svg"></section><section><p>另一端封闭玻璃拱口、临街石材入口保留；其坐标和局部分区仍为照片拟合。</p><img src="VIEW_39_V14_CLOSED_STREET_SIDE.png"></section>'
    (R/'views/reference_comparison_v14.html').write_text(page)
    print('v14 plan controls and linked-primary-photo comparison generated')

if __name__=='__main__':main()

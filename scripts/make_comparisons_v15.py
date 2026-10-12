"""Own control diagram plus links to primary originals; no copied source media."""
from pathlib import Path
import json,sys,math,html
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import geometry
from podium_v9 import plan_xy,sweep_point
from corrections_v11 import courtyard_points
from raised_end_v15 import frame,point,relation
from site_v8 import xy
from transition_v5 import outer_reference,control_profile_at,configure
from corrections_v13 import ring_specs

def main():
    p=json.loads((R/'parameters/podium_v9.json').read_text());site=json.loads((R/'parameters/site_v8.json').read_text())
    cfg=json.loads((R/'parameters/model_config.json').read_text());cfg['notch_v4']=json.loads((R/'parameters/notch_v4.json').read_text())
    configure(cfg,json.loads((R/'parameters/completion.json').read_text()),json.loads((R/'parameters/floor_anchors.json').read_text()),json.loads((R/'parameters/assembly_v3.json').read_text()),json.loads((R/'parameters/transition_v5.json').read_text()))
    _,base=outer_reference(geometry,cfg);tower=[q[:2] for q in control_profile_at(geometry,cfg,base,22)]
    boundary=[plan_xy(p,q) for q in p['ground_outline_px']];garden=[plan_xy(p,q) for q in courtyard_points(p,p['courtyard_photo_fit_px'])]
    axis=[sweep_point(p,i/40,.5)[:2] for i in range(41)];front=[point(p,i/32,0)[:2] for i in range(33)]
    report={**relation(p,cfg),'evidence_level':'推导值/待确认相位','source_ids':['GENSLER_ARCHJOURNAL_V8','PODIUM_GENS_V4','SWA_RAISED_END_V14','USER_PODIUM_RELATION_V15'],
            'asbuilt_verified':False,'p31_origin_world_m':plan_xy(p,p['tower_center_px']),'p29_origin_world_m':xy(site,site['tower_center_px']),
            'p31_scale_m_per_px':p['ground_scale_bar_m']/math.dist(*p['ground_scale_bar_px']),
            'p29_scale_m_per_px':site['scale_bar_m']/math.dist(*site['scale_bar_px']),
            'shared_front_curve_world_m':front,'candidate_end_controls':p['raised_end_v15'],
            'uncertainty':'Both origin/phase consistency and candidate corner relation are software checks, not a surveyed registration or north direction. Below45m tower extrapolated.'}
    (R/'parameters/registration_v15.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    def path(points,close=True):return ' '.join(('M' if i==0 else 'L')+f'{340+2.7*x:.2f},{330-2.7*y:.2f}' for i,(x,y) in enumerate(points))+(' Z' if close else '')
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="710" viewBox="0 0 760 710"><rect width="760" height="710" fill="#faf9f5"/><g font-family="sans-serif" font-size="15"><text x="28" y="30">v15 local candidate phase — convex tip, not a north survey</text>']
    for ps,color,fill,width,close in [(boundary,'#667078','#dddcd5',1.5,True),(tower,'#236c9e','none',2,True),(garden,'#35955f','#b4dbb6',2,True),(axis,'#ab9140','none',2,False),(front,'#e3702d','none',4,False)]:parts.append(f'<path d="{path(ps,close)}" stroke="{color}" fill="{fill}" stroke-width="{width}"/>')
    parts+=['<circle cx="340" cy="330" r="4" fill="#222"/><text x="350" y="330">Tower origin</text>',
            '<text x="28" y="590" fill="#236c9e">Blue: tower at22m, extrapolated from the45m reference</text>',
            '<text x="28" y="618" fill="#667078">Grey: published p31 trace; placement is a candidate</text>',
            '<text x="28" y="646" fill="#35955f">Green: raised garden; orange: shared bowed front rim</text>',
            '<text x="28" y="674">p29 and p31 share −30° candidate phase; no survey residual.</text></g></svg>']
    (R/'views/VIEW_44_V15_PLAN_REGISTRATION.svg').write_text(''.join(parts))
    sw='https://swacdn.s3.amazonaws.com/wp-content/uploads/2020/07/07081612/Shanghai-Tower-Jonnu-Singleton-0013.jpg'
    aerial='https://static2.gensler.com/uploads/image/95597/project-shanghai-tower-01-2000x_1734564801.jpg'
    render='https://images.skyscrapercenter.com/building/shanghaitower_ext-retailpodium_%28c%29gensler.jpg'
    page='''<!doctype html><meta charset="utf-8"><title>v15 裙房与每层夹层环缺带</title><style>body{font:16px sans-serif;background:#f6f5f1;margin:28px;color:#252a30}section{padding:20px;background:white;margin:18px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}img{width:100%;object-fit:contain;max-height:650px}p{max-width:1050px}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #bbb}</style><h1>v15：凸尖嵌入、抬升端部、夹层每层中央环缺带</h1><p>拓扑对照；镜头未标定，不声明米制拟合误差或竣工精度。原图仅由其发布URL加载，未复制进仓库。</p>'''
    page+='<section><p><a href="https://www.gensler.com/projects/shanghai-tower">Gensler实际航拍</a>：凸角与金色屋面、庭院和侧面V凹口的关系。相位修改同步应用到裙房与p29场地；真北向待确认。</p><div class="pair"><img src="'+aerial+'"><img src="VIEW_42_V15_CONVEX_TIP_AND_TERRACE.png"></div></section>'
    page+='<section><p><a href="https://www.skyscrapercenter.com/building/shanghai-tower/56">Gensler/CTBUH设计效果图</a>：用户附件同场景。和实际航拍存在端面材料/曲线差异；只作设计关系参照，不冒充竣工。</p><div class="pair"><img src="'+render+'"><img src="VIEW_42_V15_CONVEX_TIP_AND_TERRACE.png"></div></section>'
    page+='<section><p><a href="https://www.swagroup.com/projects/shanghai-tower/">SWA Jonnu Singleton-0013实景</a>：金色底面、开放空间与斜柱。右图临时隐藏近处树冠/树干便于核验；保存模型保留植栽。端部标高/曲率仍候选。</p><div class="pair"><img src="'+sw+'"><img src="VIEW_41_V15_RAISED_END_FROM_GROUND.png"></div></section>'
    page+='<section><p>局部共同配准与弯曲前沿；蓝色塔楼22m轮廓为45m以下外推，非批准基部CAD。</p><img src="VIEW_44_V15_PLAN_REGISTRATION.svg"></section><section><p>保留另一端封闭拱口与石材内嵌入口。材料尺寸、位置仍候选。</p><img src="VIEW_43_V15_CLOSED_STREET_SIDE.png"></section>'
    page+='<section><p>夹层外部两层各在层高中央切窄环：每段两圈，共16圈。共同楼板交界不再作为切口中心；内B及16块完整转换板保留。0.60m为待确认宽度，父玻璃列/面板身份保留。</p><img src="VIEW_45_V15_TWO_STOREY_RING_SLITS.png"><table><tr><th>section / storey</th><th>候选层高范围m</th><th>缺带中心m</th><th>宽m</th></tr>'
    for h in ring_specs(cfg):page+='<tr><td>'+h['id']+'</td><td>'+str([round(z,3) for z in h['transition_storey_range_m']])+'</td><td>'+str(round((h['z_min_m']+h['z_max_m'])/2,3))+'</td><td>0.60</td></tr>'
    page+='</table><p>环带坐标由候选楼层表推导；未取得全周幕墙深化开孔表。01–40与v14对照页均为历史视图；41–45为本轮模型核验。</p></section>'
    (R/'views/reference_comparison_v15.html').write_text(page)
    print('v15 local registration and two-midstorey-ring comparison generated')

if __name__=='__main__':main()

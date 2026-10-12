"""Local reference comparisons; copyrighted originals are not redistributed."""
from pathlib import Path
import json,html,sys
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))

def main():
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from PIL import Image
 pairs=[('references/v8/Ground_plan_p31_crop.png','views/VIEW_23_PODIUM_SYSTEMS_V7.png','COMPARE_V11_01_PODIUM.png','Gensler / Architectural Journal2019 p31: published ground plan','v11: ground trace + fitted upper arc sweep; not shop CAD'),
        ('references/v8/Site_plan_p29_crop.png','views/VIEW_26_SITE_PLAN_V8.png','COMPARE_V11_02_SITE.png','Gensler / Architectural Journal2019 p29: site plan,100m scale','Local registration candidate; furniture/plant/road details unresolved'),
        ('references/CTBUH2014_p51_CWSS.png','views/VIEW_13_CWSS_INSTALLED.png','COMPARE_V11_03_CWSS.png','TJAD2014 Fig3.18:3 horizontal corner X pairs per level','Generated CWSS:60mm rods; node coordinates candidates')]
 for ref,view,out,left,right in pairs:
  fig,axes=plt.subplots(1,2,figsize=(14,10))
  for ax,path,label in zip(axes,(ref,view),(left,right)):ax.imshow(Image.open(R/path));ax.axis('off');ax.set_title(label,fontsize=10)
  fig.text(.03,.015,'Qualitative comparison. Different viewpoints/phases; no measured reprojection or as-built error claimed. References stay local.',fontsize=9)
  fig.tight_layout();fig.savefig(R/'views'/out,dpi=160);plt.close(fig)
 online=[('Crown glass apertures','https://oss.gooood.cn/uploads/2020/09/010-shanghai-tower-by-gensler.jpg','https://www.gooood.cn/shanghai-tower-by-gensler.htm','VIEW_07_CROWN.png','Gensler supplied photo / Connie Zhou. Unknown lens/viewpoint; visible arc only. Upper aperture counts 11x2 /11x2 /11x3 with two retained columns between apertures follow user observation; absolute positions are candidates. Narrow rings and two-band vent height remain fits.'),
         ('Shanghai Eye and V hall supports','https://blog.cn.rhino3d.com/wp-content/uploads/2017/08/Shanghai-tower-open-top-damper.jpg','https://blog.cn.rhino3d.com/shanghai-tower-open-top-damper/','VIEW_20_TMD_HALL_V6.png','Owner photograph hosted by Rhino; CIMA model authors credited. Nominal7.7x3.89m/519 pieces from artist; exact fabrication shape unresolved.'),
         ('Art backbone','https://blog.cn.rhino3d.com/wp-content/uploads/2017/08/03.jpg','https://blog.cn.rhino3d.com/shanghai-tower-open-top-damper/','VIEW_28_SHANGHAI_EYE_V8.png','CIMA supplied original Rhino screenshot; no downloadable construction model or metric camera calibration.'),
         ('Podium built aerial','https://static2.gensler.com/uploads/image/95597/project-shanghai-tower-01-2000x_1734564801.jpg','https://www.gensler.com/projects/shanghai-tower','VIEW_23_PODIUM_SYSTEMS_V7.png','Different camera angles. Published ground trace supported; upper PR radii, closed west soffit and system zones remain fitted/unresolved.')]
 s=['<!doctype html><meta charset="utf-8"><title>v11 reference comparisons</title><style>body{background:#f5f3ee;color:#252c30;font:16px system-ui;margin:32px}section{margin:35px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}img{max-width:100%;height:620px;object-fit:contain;background:white}p{line-height:1.6}a{color:#14567b}</style><h1>v11 参考资料与模型对照</h1><p>左右为来源与当前模型。原图在线加载，版权归原发布方；需要网络。未标定摄影，不报告精确重投影误差，不宣称竣工一致。</p>']
 s.append('<section><h2>Corrected long-side entry</h2><img style="height:auto" src="VIEW_30_LONG_SIDE_ENTRY_V11.png"><p>Candidate long side, genuine white horizontal tile gaps and recessed entry. Opposite arch restored.</p></section>')
 s.append('<section><h2>Actual parent-grid aperture unfolding</h2><img style="height:auto" src="VIEW_29_CROWN_APERTURE_UNWRAPPED_V10.png"><p>77 upper holes and3 wind bays checked in surviving generated parent polygons. Counts adopted from user observation; absolute coordinates unresolved.</p></section>')
 for title,img,url,view,note in online:s.append(f'<section><h2>{html.escape(title)}</h2><div class="pair"><a href="{url}"><img src="{img}" alt="source image; follow original link if unavailable"></a><img src="{view}" alt="generated research model"></div><p>{html.escape(note)} <a href="{url}">Original source / 原来源</a></p></section>')
 for _,_,out,left,right in pairs:s.append(f'<section><h2>{html.escape(left)}</h2><img style="height:auto" src="{out}"><p>{html.escape(right)}</p></section>')
 (R/'views/reference_comparison_v11.html').write_text('\n'.join(s))

if __name__=='__main__':main()

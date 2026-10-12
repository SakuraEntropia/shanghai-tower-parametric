"""Local photo/model comparison, original photos stay outside Git."""
from pathlib import Path
import html,json
R=Path(__file__).resolve().parents[1]
pairs=[('../references/user_v13_street.jpeg','VIEW_35_V13_STONE_ENTRY_NEAR.png','用户街景：石材斜肩、宽内嵌玻璃和侧边窄横窗。未校正透视，不能比较米制误差。'),
       ('../references/new_podium/Gensler_base_aerial.jpg','VIEW_34_V13_OPEN_GARDEN_END.png','Gensler实际航拍：开放庭院在短端、另一端封闭玻璃拱口。上部坐标、平台标高候选。'),
       ('../references/user_v13_render.jpeg','VIEW_33_V13_CLOSED_STREET_SIDE.png','用户图1疑似设计效果图：只辅助核对金壳/石材/庭院关系，以街景及实际航拍为先。')]
parts=['<!doctype html><meta charset="utf-8"><title>v13 资料对照</title><style>body{font:16px sans-serif;background:#f6f5f1;margin:28px;color:#252a30}article{margin:24px 0;padding:18px;background:white}.pair{display:grid;grid-template-columns:1fr 1fr;gap:15px}img{width:100%;object-fit:contain;max-height:620px}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:8px}p{max-width:1000px}</style><h1>v13 幕墙横环缺带与裙房两端</h1><p>本页核对拓扑，未进行相机标定或竣工尺寸验证。原照片仅本地可见，公开仓库不重新分发。缺图时右侧模型仍可查看。</p>']
for ref,view,note in pairs:
    parts.append('<article><p>'+html.escape(note)+'</p><div class="pair"><img src="'+ref+'" alt="本地原图；仓库未分发"><img src="'+view+'" alt="v13实际保存模型"></div></article>')
report=json.loads((R/'validation/saved_blend_inspection.json').read_text())
current=report['v13_actual_entities']
parts.append('<article><p>两层转换夹层中央：真实删除外A/V玻璃窄环；原父列保留。16块完整转换板恢复，旧楼板豁口数量='+str(current['old_slab_notches'])+'。</p><img src="VIEW_36_V13_TRANSITION_RING.png"><table><tr><th>环带</th><th>候选标高m</th><th>上下边父面板数</th><th>跨越环带玻璃面数</th></tr>')
for q in current['ring_apertures']:
    parts.append('<tr><td>'+q['id']+'</td><td>'+str(q['z_range_m'])+'</td><td>'+str(q['lower_boundary_panels'])+' / '+str(q['upper_boundary_panels'])+'</td><td>'+str(len(q['crossing_glass_faces']))+'</td></tr>')
parts.append('</table><p>缺带0.60m为可修改候选；上下层号和标高尚缺完整竣工交叉表。所有软件容差只检查本模型。</p></article>')
(R/'views/reference_comparison_v13.html').write_text('\n'.join(parts))
print('Saved local v13 comparison page; no original image copied into Git.')

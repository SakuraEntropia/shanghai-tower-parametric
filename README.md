# Shanghai Tower 参数化研究模型 v13

2026-10-12。撤回误切楼板：16块转换板恢复，8处夹层中央改为外A幕墙实切窄横环带，V凹面同步裁断。裙房封闭石材入口面重新定位到金壳外侧长面，按用户街景补斜肩、宽内嵌玻璃与3条小横窗。庭院端敞开，另一端保留封闭玻璃拱口；撤去旧的同面阳台和重复拱玻璃。庭院及设施同步移到开放端。

照片支持形态关系，位置/净尺寸/缺带标高仍为候选。v11/v12楼板豁口和裙房同面阳台实现已撤销；历史文档保留供追溯，以v13为准。

v9基础保留：补典型幕墙夹层三角部X拉杆、大厅V支撑；慧眼改连续弧、下宽上窄、519块候选玉饰面与钢骨分层。冠部沿用塔身父分格，局部切出风口、上方双格孔和两条窄横开口。裙房撤换旧母面，以出版首层平面与承包商复合圆弧逻辑重建，玻璃拱口直接使用屋面截面，补局部首层雨棚与道路景观。

**公开资料所支持的研究重建。裙房完整曲面、全周开孔、慧眼加工形状仍未精确复原；不是竣工或施工图级模型。**

- [可编辑模型](model/shanghai_tower_evidence.blend)：米制1:1；Collection分组件；对象属性与Text保存来源、公式和不确定性。
- [生成脚本](scripts/build_shanghai_tower.py) · [参数与来源](parameters) · [本轮参数方案与证据](docs/21_v13位置与横环缺带.md) · [v11历史方案](docs/19_v11修正参数与核验.md) · [v10历史方案](docs/18_v10孔组入口与街区.md) · [v9基础方案](docs/15_v9修正方案与证据.md) · [参数证据索引](docs/16_v9参数索引.md) · [核验与缺失项](docs/17_v9核验与缺失项.md)。
- [冠部/慧眼](parameters/crown_v5.json) · [开孔/内B](parameters/completion.json) · [新裙房](parameters/podium_v9.json) · [夹层钢架](parameters/assembly_v3.json) · [场地](parameters/site_v8.json) · [玻璃/天空](parameters/model_config.json)。旧文件名用于兼容，内部版次和v13说明优先。
- [临街封闭面](views/VIEW_33_V13_CLOSED_STREET_SIDE.png) · [开放庭院端](views/VIEW_34_V13_OPEN_GARDEN_END.png) · [石材入口近景](views/VIEW_35_V13_STONE_ENTRY_NEAR.png) · [横环缺带近景](views/VIEW_36_V13_TRANSITION_RING.png) · [v13对照](views/reference_comparison_v13.html) · [生成检查](validation/validation_report.json) · [独立重开检查](validation/saved_blend_inspection.json) · [交付校验表](validation/delivery_manifest.json)。软件检查通过不证明与实物完全一致。

已证实的资料内容：公开名义632m、120°扭转；业主L126=583.4m、1000吨TMD、270风机。艺术家报告慧眼7.7×3.89m、三面、519玉件、9.1m铜底座、35m厅径、4m天窗、120长+120短铜条。CIMA供图支持连续弧骨架和厅内斜柱。TJAD/CTBUH2014支持典型Z2–8每层三个角部X杆及60mm设计直径。名义数据和类型不等于竣工坐标表。

历史孔组规则：`completion.json`内`aperture_layout_v10`控制11列、2/2/3排、父格跨度；运行时再对齐当前原父网格。`podium_v9.json`内`side_v13`控制长侧封闭面、`open_end_v13`控制开放端；`transition_v5.json`内`horizontal_slits_v13`控制外A窄环缺带；`site_v8.json`内转角参数控制道路、绿带和地块曲线。

推导部分：A轮廓/扭转、内B/核心筒分区、129个候选楼板编号与16个整三角转换板；内B分区底部开放带；冠部和雕塑曲面、孔位、钢架节点；出版平面描线和裙房上部复合弧扫掠；材质及景观。129不是对真实运营楼层总数的确认。

待确认：完整RC/钢架/PR/PS/雨棚施工和竣工图、9轴与空间曲线、西部闭合回折底面、13系统最终分区/节点、全周开孔表、慧眼519块实际形状与挂点、2025改造版次、地理配准和实测光学。裙房文献7层37m、投标5层38.245m、早期7层38m冲突并列，37m为工作候选。停机坪实物位置未证实，旧候选资产默认隐藏；冷却设备定位/数量亦为候选。

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python scripts/build_shanghai_tower.py -- --output model --render \
  --views 01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28
```

从仓库根目录运行。Windows/Linux将第一行替换为本机Blender路径。实际执行及重开验证环境为Blender5.2 Alpha；未声明其他版本已测试。脚本仅清除带本项目标识的旧对象，输出参数及缺失资料摘要。源图PDF/照片留在本地研究目录，仓库记录来源链接，不重新分发第三方完整图纸；本地COMPARE图用于核对，不代表标定误差已测得。

长侧面核验图可独立重生成：用Blender后台打开保存模型，运行`scripts/render_side_v11.py`；该脚本仅输出图像，不改写模型。孔组展开图由`scripts/make_v10_aperture_view.py`读取当前实际父板诊断生成。

本轮近景重生成：Blender后台打开交付blend后运行`scripts/render_v13.py`。用户原照片仅保留本地参考目录，公开仓库保存文件指纹、描述和候选控制；对照页缺少本地原图时仍可查看自制核验图。

视图版本：33–36为v13保存几何的当前核验图；01–32及v10/v11/v12对照页保留作历史追溯，不代表当前裙房位置或当前环缺带。完整28个既有机位仍可用生成脚本重新渲染。

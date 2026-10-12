# Shanghai Tower 参数化研究模型 v9

2026-10-12。补典型幕墙夹层三角部X拉杆、大厅V支撑；慧眼改连续弧、下宽上窄、519块候选玉饰面与钢骨分层。冠部沿用塔身父分格，局部切出风口、上方双格孔和两条窄横开口。裙房撤换旧母面，以出版首层平面与承包商复合圆弧逻辑重建，玻璃拱口直接使用屋面截面，补局部首层雨棚与道路景观。

**公开资料所支持的研究重建。裙房完整曲面、全周开孔、慧眼加工形状仍未精确复原；不是竣工或施工图级模型。**

- [可编辑模型](model/shanghai_tower_evidence.blend)：米制1:1；Collection分组件；对象属性与Text保存来源、公式和不确定性。
- [生成脚本](scripts/build_shanghai_tower.py) · [参数与来源](parameters) · [本轮方案](docs/15_v9修正方案与证据.md) · [参数证据索引](docs/16_v9参数索引.md) · [核验与缺失项](docs/17_v9核验与缺失项.md)。
- [冠部/慧眼](parameters/crown_v5.json) · [开孔/内B](parameters/completion.json) · [新裙房](parameters/podium_v9.json) · [夹层钢架](parameters/assembly_v3.json) · [场地](parameters/site_v8.json) · [玻璃/天空](parameters/model_config.json)。旧文件名用于兼容，内部版次和v9说明优先。
- [生成检查](validation/validation_report.json) · [独立重开检查](validation/saved_blend_inspection.json) · [交付校验表](validation/delivery_manifest.json)。软件检查通过不证明与实物完全一致。

已证实的资料内容：公开名义632m、120°扭转；业主L126=583.4m、1000吨TMD、270风机。艺术家报告慧眼7.7×3.89m、三面、519玉件、9.1m铜底座、35m厅径、4m天窗、120长+120短铜条。CIMA供图支持连续弧骨架和厅内斜柱。TJAD/CTBUH2014支持典型Z2–8每层三个角部X杆及60mm设计直径。名义数据和类型不等于竣工坐标表。

推导部分：A轮廓/扭转、内B/核心筒分区、129个候选楼板编号与16个整三角转换板；内B分区底部开放带；冠部和雕塑曲面、孔位、钢架节点；出版平面描线和裙房上部复合弧扫掠；材质及景观。129不是对真实运营楼层总数的确认。

待确认：完整RC/钢架/PR/PS/雨棚施工和竣工图、9轴与空间曲线、西部闭合回折底面、13系统最终分区/节点、全周开孔表、慧眼519块实际形状与挂点、2025改造版次、地理配准和实测光学。裙房文献7层37m、投标5层38.245m、早期7层38m冲突并列，37m为工作候选。停机坪实物位置未证实，旧候选资产默认隐藏；冷却设备定位/数量亦为候选。

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python scripts/build_shanghai_tower.py -- --output model --render \
  --views 01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28
```

从仓库根目录运行。Windows/Linux将第一行替换为本机Blender路径。实际执行及重开验证环境为Blender5.2 Alpha；未声明其他版本已测试。脚本仅清除带本项目标识的旧对象，输出参数及缺失资料摘要。源图PDF/照片留在本地研究目录，仓库记录来源链接，不重新分发第三方完整图纸；本地COMPARE图用于核对，不代表标定误差已测得。

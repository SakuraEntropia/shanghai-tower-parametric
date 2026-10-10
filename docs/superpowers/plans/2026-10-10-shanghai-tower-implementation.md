# Shanghai Tower Evidence Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. 本机未提供这两项技能；使用现有 collaboration 子代理分工、根代理接口审查与逐任务验证执行。用户已授权阶段三、四，无需再选执行方式。

**Goal:** 生成可重建、可编辑、证据分级清楚的上海中心研究版Blender模型，并交付实际核验结果与对照视图。

**Architecture:** 来源与原参数保持研究档案；新增model_config.json记录本次选择、显示采样及所有额外假设。纯Python轮廓模块供幕墙、结构、核验共享；bpy场景模块集中管理对象、证据和集合。已知尺寸生成实体或控制几何；定位/分配不足保留接口或明显标记的独立构造样件，禁止把样件复制成所谓竣工实体。

**Tech Stack:** Blender 5.2.0 Alpha bpy；Python标准库；PNG；JSON；本地参考PDF。

**Spec:** docs/superpowers/specs/2026-10-10-shanghai-tower-design.md，规范详细文件docs/02_Blender建模方案.md与docs/03_幕墙pattern专项.md。

## Global Constraints

- 米制1:1；右手坐标Z向上；WP1局部原点，真实北向/测量基准偏移未知。
- 2010与2014曲线分别保存；默认选2014推导控制包络45–632m，不生成未知底部延拓或平齐塔冠。
- 对称相切圆弧仅为缺口之前的控制母形；V口未知处保留接口/诊断标识，不称完整真实A轮廓。
- 楼板默认只取18个原论文标高；不根据127/128统计虚构全部逐层表。
- A标准板为直立平面矩形，阶梯独立；无证实局部例外不能铺满全楼。幕墙可编码的历史规则样件独立于当前竣工未知映射。
- 核心外包30m；九格不等于等分九房；切角/十字轮廓及分区准确转换标高未获时保留接口。
- 所有对象与合并面记录证据；Text内保存来源、参数、config、说明和生成脚本。
- 自己项目集合才可清理；旧用户模型不改；干净场景重建与重新打开blend验证。

## Files and Interfaces

| 文件 | 职责与精确接口 |
|---|---|
| parameters/model_config.json | 本轮版本、采样、独立样件、显示材质；每项假设含source_ids/evidence/uncertainty |
| scripts/common.py | SceneBuilder(config,parameters,sources)：collection(name)、mesh(name,verts,faces,collection,material,meta,face_attributes=None)、lines(name,polylines,collection,radius,material,meta)、empty(name,location,collection,meta)、box(name,center,size,collection,material,meta)；记录objects与component_results |
| scripts/geometry.py | profile_segments(config)、sample_profile(config,count=288)、transform_profile(points,z,config,version=None)、curve_state(z,config,version=None)、build_envelope(ctx) -> dict；纯Python可测试 |
| scripts/structure.py | build_structure(ctx,geometry_module,anchors) -> dict；核心、稀疏标高/楼板诊断、主体/CWSS接口、独立节点样件 |
| scripts/curtain_wall.py | build_curtain_wall(ctx,geometry_module) -> dict；已定义历史规则标准带、板ID/属性、竖直平面矩形与错台；不足处接口 |
| scripts/validation.py | validate_scene(ctx,geometry_module,anchors,results) -> dict；numeric checks与证据适用范围分别报告 |
| scripts/build_shanghai_tower.py | CLI --config/--output/--render；编排模块、嵌入Text、视图、保存blend/日志；--factory-startup可重建 |
| scripts/make_comparisons.py | 实际生成CSV/SVG或PNG的标高/平面/旋转/收分/幕墙比例与参考并列；无校准图不编造叠图残差 |
| tests/test_geometry.py | 圆弧相切、尺度/转角端点、控制区间拒绝外推、分格弧长、幕墙共面正交检查 |
| validation/* / views/* | 实际运行与核验产物；不把参考页当模型图 |
| docs/05_模型使用与核验.md / README.md | 运行、组件清单、已证实/推导/占位、缺失资料、检查结果及交付链接 |

## Task 1 — Parameter selection and scene builder

- [x] 读取94参数/24来源与18锚点，新增config，不覆盖原来源事实。
- [x] 设置2014母形诊断与2010历史幕墙样件的独立场景位置/集合，建立可开关组件；显示尺寸不是建筑尺寸，全部标记presentation。
- [x] 建立上述SceneBuilder接口，所有对象写source_ids/evidence/formula/uncertainty/project_id，合并面支持整数索引。
- [x] 验证JSON引用和对象属性；错误必报，不默填null。

## Task 2 — Analytic envelope

- [x] 推导三大圆弧与三小圆弧相切轮廓；三重复制与弧长采样独立。
- [x] 对45–632控制段生成多标高包络线/受控母面；未知V口、底部、冠部给接口与显著标记。
- [x] 精确检查R2及相切残差；2010与2014端点尺度/旋转值；范围外raise ValueError。

## Task 3 — Structures and floors

- [x] 核心30m低区外包可定位为设计控制体；内分区、变化轮廓保留接口。已知区界与楼号不能跨版本擅合。
- [x] 18锚点实际建标高线；圆楼板端径单独做尺寸化样件，逐区半径未知则塔身楼板留接口。
- [x] 主体巨柱/环带/伸臂数量与连接关系以注册和示范图表示；真实路径未获不得在塔身均布假构件。
- [x] CWSS管径/壁厚与双吊杆/滑移机制生成尺寸化独立样件，场景中接入待确认位置接口。
- [x] 检查核心宽/墙厚样件、管外径/内径、双杆数与所有锚点标高。

## Task 4 — Curtain wall geometry

- [x] 历史144控制分格单独编码；如果准确曲段不能恢复则仅构造可验证局部标准板，局部分格不冒称全楼最终pattern。
- [x] 面板四角保持竖直、共面、正交；带间错台独立。板宽由明确曲线采样推导，高度4.5m为早期标准区示范，不虚构全楼行表。
- [x] 创建玻璃、横竖框、玻璃翅的独立几何；未知型材面宽与节点截面独立标为占位。
- [x] 输出逐板追溯JSON，异常V口/顶底/frit/fire/开口/板型映射保留接口。
- [x] 数值检查面板共面、竖直、正交，报告实际宽/高与原设计约值，超差写冲突。

## Task 5 — Blend, views, references

- [x] 干净场景生成，Text嵌入全部参数/来源/config/脚本/不确定性；保存model/shanghai_tower_evidence.blend。
- [x] 创建全塔、结构/控制、关键平面、剖面、幕墙近景与CWSS样件视图；标题明示研究母形/历史样件。
- [x] 参考页与生成图并列，明确对照适用范围，未取得精确参考坐标不输出伪造误差。
- [x] 重新打开blend读取单位/集合/Text/几何极值/元数据；从factory重建一次比较对象/顶点/哈希式几何签名。

## Task 6 — Delivery audit

- [x] 汇总所有已证实尺寸与设计规则、推导母形、当前不能确认的实体；缺口保持失败/未验证状态，软件PASS不等于竣工PASS。
- [x] 更新README与使用说明、参数表增补、实现计划勾选、文件清单。
- [x] 交付blend、全部脚本、JSON、来源证据、实际视图及核验报告；结论明确公开资料研究精度。

## Verification commands

```bash
python3 -m unittest discover -s tests -v
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_shanghai_tower.py -- --config parameters/model_config.json --output model --render
/Applications/Blender.app/Contents/MacOS/Blender --background model/shanghai_tower_evidence.blend --python scripts/inspect_saved.py
```

检查对象/函数接口、无默填null、特殊区域不会被普通pattern覆盖。所有实际输出和失败必须写报告；不以视觉近似代替尺寸核验。

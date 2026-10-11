# Shanghai Tower 参数化研究模型 v5

2026-10-11纠错：塔冠按Gensler提供的竣工航拍重建高低尖唇、宽返边、陡坡密网、中心几何开槽/圆端孔与设备代理；16块过渡楼板改完整外三角轮廓；幕墙统一排程并修复自交拼缝；裙房细化连续厚壳屋面、庭院、入口与独立亭。**研究重建；推导/待确认参数显式标注，未宣称竣工精度。**

- 可编辑模型：[shanghai_tower_evidence.blend](model/shanghai_tower_evidence.blend)。
- 重建入口：[build_shanghai_tower.py](scripts/build_shanghai_tower.py)，同目录模块须保留。
- 集中参数：[model_config.json](parameters/model_config.json)、[assembly_v3.json](parameters/assembly_v3.json)、[completion.json](parameters/completion.json)、[notch_v4.json](parameters/notch_v4.json)、[crown_v5.json](parameters/crown_v5.json)、[transition_v5.json](parameters/transition_v5.json)、[podium_v4.json](parameters/podium_v4.json)。
- 当前依据：[v5纠错与撤回](docs/11_v5修正与证据.md)、[塔冠航拍及参数](docs/11_crown_v5_actual_aerial.md)、[转换层与接缝](docs/11_transition_facade_v5.md)、[底商](docs/11_podium_v5.md)。
- [来源清单](parameters/sources.json)、[原参数证据表](docs/01_参数与证据表.md)、[幕墙专项](docs/03_幕墙pattern专项.md)。旧v1–v4文档/对照图是历史快照，精度声明以v5为准。
- 当前实渲染视图：01、02、06、07、11、12、13、14、15、17、18、19；17塔冠整体，18高俯视开孔/设备，19转换幕墙。其他视图仍为历史快照。

已证实的公开名义指标包括632m总高、120°总扭转和文献中的若干构件断面/标高；这不确认完整竣工坐标。V凹口95°设计角有据，唇点/深度/随高变换为图测或条件推导。塔冠610.194m低唇、601.099m内屋面来自低清剖面候选（采样约±1.5m，版本/系统误差未界定）；周向抛物线与北向、内网节距、设备数量/位置、中心开口边界/用途、转换玻璃变体和底商尺寸仍待确认。未做单幅航拍三维标定。

本轮撤回v4把Cosentini渲染图当竣工照片及背部632m峰的解释。采用[2023-06-09发布、注明Photograph courtesy Gensler的航拍](https://www.nationalgeographic.com/science/article/paid-content-5-green-towers-inspired-by-nature-and-striving-to-protect-it)，结合业主施工照片与NTUA结构顾问论文。没有取得直升机坪一手依据，航拍未见明确H/降落平台；模型只留关闭的可编辑接口。边缘风机状装置用途不确定；L128冷却塔用途来自设计文献，模型数量/轴线是候选。

保留129块候选楼板编号，其中16块转换板铺到含V凹口的A轮廓并保留核心孔。F/L层号与运营层号未统一，129不等于真实地上层数。旧129屋面代理已隐藏并注明由独立v5屋面替代，避免共面重叠/填孔。内B筒保持分段同心圆；外围承力仍为8巨柱/环带/伸臂框架。夹层环梁、径撑与双吊杆保留。

193项实际软件几何检查、46项纯函数测试通过；模型已在独立进程重开并通过检验。检查针对当前输入和生成网格，不证明与实物完全一致。对象保留来源、公式、不确定性及asbuilt_verified=false；JSON、脚本与证据文档嵌入.blend Text。钢材颜色仅为提高阅读对比，不是涂装依据。

重建（Blender，米制1:1）：

```bash
blender --background --factory-startup --python-exit-code 1 --python scripts/build_shanghai_tower.py -- --render --views 01,02,06,07,11,12,13,14,15,17,18,19
python3 -m unittest discover -s tests -q
blender --background model/shanghai_tower_evidence.blend --python-exit-code 1 --python scripts/inspect_saved.py
```

可在参数JSON调整轮廓/扭转、楼板、V口、幕墙排程、冠部顶边/开孔/设备和裙房，再从干净场景重建。真实分板深化/钢构轴线/机电布局、裙房竣工边界和测绘北向仍需补取得；详见v5证据文档及原资料缺失清单。

GitHub保留模型、脚本、数据、文档与自产视图；原始PDF、摄影图和参考截图留本地，未重新分发。主模型重建不依赖本地参考图。文件哈希和当前版本见delivery_manifest.json。

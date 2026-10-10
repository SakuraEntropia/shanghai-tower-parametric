# Shanghai Tower 参数化研究模型 v4

当前脚本已于2026-10-11运行并保存。V口为闭合内凹幕墙，塔冠高低映射和内部坡面按图像/剖面修订，底商改为非对称低裙房与暖色曲面屋面。**这是证据标记的研究重建，未确认部分仍为候选；不宣称竣工精度。**

- 可编辑模型：[shanghai_tower_evidence.blend](model/shanghai_tower_evidence.blend)
- 重建入口：[build_shanghai_tower.py](scripts/build_shanghai_tower.py)，同目录模块须保留。
- 集中参数：[model_config.json](parameters/model_config.json)、[assembly_v3.json](parameters/assembly_v3.json)、[completion.json](parameters/completion.json)、[notch_v4.json](parameters/notch_v4.json)、[podium_v4.json](parameters/podium_v4.json)。
- [v4修正依据](docs/10_v4修正与图像依据.md)、[塔冠图片与局限](docs/10_crown_v4.md)、[底商图片与局限](docs/10_podium_v4.md)。
- [来源清单](parameters/sources.json)、[参数证据表](docs/01_参数与证据表.md)、[幕墙专项](docs/03_幕墙pattern专项.md)、[v3实体参数证据](docs/09_v3参数证据表.md)。
- 当前v4视图：VIEW_01_TOWER、VIEW_07_CROWN、VIEW_12_GROUNDED_RETAIL、VIEW_14_CROWN_ROOF_STEEL、VIEW_15_V_RECESS。其他旧视图/文档保留为研究快照，不能当本次即时渲染。

保留129块带核心孔洞的候选楼板、8巨柱/4角柱、8环带/6组伸臂及夹层环梁/径撑/双吊杆。129只是候选板编号，不等于真实地上层数；源层号与运营层号仍未统一。B为分段同心圆筒，不随A扭转。外围承力是巨柱—环带框架。

V口的95°设计角有据；唇点、深度及随高映射属于图测/条件推导。塔冠照片只作形态判断，未作精确摄影标定。底商平面、高度、屋面和定位为图像支持的可调候选；2010七层38m是历史方案，未套作最终实物。连接节点、最终分板、真实北向及设计/入口高程偏移仍待确认。

185项软件几何检查及31项测试通过，模型成功重开。软件检查验证当前输入和实际生成对象，不能证明与实物完全一致。所有建筑对象保留来源、公式、不确定性、asbuilt_verified=false；JSON、证据文档与脚本嵌入.blend Text。

重建（需Blender，米制1:1）：

```bash
blender --background --factory-startup --python-exit-code 1 --python scripts/build_shanghai_tower.py -- --render --views 01,07,12,14,15
python3 -m unittest discover -s tests -q
```

GitHub保留模型、脚本、数据、文档及自己生成的视图；原始PDF/参考摄影图/截图对照留本地，未随代码仓库重新分发。图像对照脚本在缺少这些本地参考时无法生成，而主模型重建不依赖参考图片文件。当前文件哈希见delivery_manifest.json。

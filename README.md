# Shanghai Tower 参数化研究模型 v6

2026-10-11：修正完整圆形天孔/矩形凹区与零散孔候选、直斜冠钢网；补270台Windpods候选排布、无玻璃工作区、阻尼器文化厅、悬索/质量块与冷却塔组；玻璃改真实反射/折射shader；裙房改高拱玻璃口和局部金色下卷，撤去满圈玻璃与过量包覆。**依据有限的研究重建，非竣工/施工图级精度。**

- [可编辑Blender模型](model/shanghai_tower_evidence.blend)。米制1:1，对象/Collection独立，证据与不确定性嵌入.blend Text。
- [重建入口](scripts/build_shanghai_tower.py)；保留整个scripts目录，不只复制入口。
- [使用/数据/证据](docs/12_v6修正与证据.md) · [冠部参数](parameters/crown_v5.json) · [集中配置/玻璃shader](parameters/model_config.json) · [裙房参数](parameters/podium_v4.json) · [来源清单](parameters/sources.json)。兼容文件名沿用v4/v5，内部版次及v6文档优先。
- [屋顶专项来源](docs/12_roof_evidence_v6.md) · [冠部实现](docs/12_crown_v6.md) · [裙房实景对照](docs/12_podium_v6.md)。历史研究/幕墙专项/平面和剖面参数继续保留；历史渲染/版本不得当作当前精度声明。

已证实：公开名义632m与总扭转120°；外/内玻璃系统类别；业主L126=583.4m、125/126文化厅、1000吨TMD，设计者说明悬索与铜板磁阻尼关系；270台风机=3×90且工作区无遮玻璃。不是对完整竣工坐标的确认。

推导/待确认：冠轮廓的周向曲线与实际方位；圆孔/服务凹区/小孔净尺寸和用途；网格、特殊玻璃范围、TMD厅径/艺术曲面、风机阵列行列和轴线、机电设备数量及产品；裙房尺寸/朝向、隐藏边界与真实分格。玻璃IOR=1.5、粗糙度0.075和色彩为显示假设，不是镀膜实测。三角化仅网格离散，不是三角玻璃施工分板。

本轮发现原始资料冲突：业主施工记录支持冷却塔L120/561m，NTUA2014设计文献写L128；旧592.47m位置不能全体默认成竣工设备。当前561m候选组优先，旧设计另存接口，不断言全楼设备已迁移。业主L126583.4m与剖面候选583.258m差0.142m，未据此全局平移塔冠。屋面601.099m、低唇610.194m仍为剖面候选，采样约±1.5m，系统/版本误差未定。

停机坪未取得可靠建成/定位证据。保留独立可编辑待确认几何资产，默认隐藏，既未冒充实物也不盖掉TMD天孔。航拍顶边风扇状设备、真实Windpods长筒和中央空调冷却塔分别表达，不互相冒充。

保留129个候选楼板编号，16块转换楼板铺到含V凹口的A外轮廓；129不等于实际运营地上层数。核心筒、内B筒、8巨柱/环带/伸臂、夹层环梁/径撑/双吊杆保留。与新屋面/大厅冲突的旧代理应归档隐藏，不能当真实转换层。所有未证实尺寸保持可替换。

核验：205项生成检查、50项单元测试通过；独立再打开结果见validation/saved_blend_inspection.json，汇总见validation/v6_verification_summary.json。软件通过仅证明当前输入和生成数据自洽。

当前视图：01全楼、02剖面、06幕墙、07塔冠、11结构、12底商、13夹层钢构、14冠钢构、15V凹口、17冠航拍、18孔/设备俯视、19转换层、20阻尼器大厅、21风机近景、22冷却塔剖视。其他视图为历史快照；摄影机未按来源进行外参标定。

重建：

```bash
blender --background --factory-startup --python-exit-code 1 --python scripts/build_shanghai_tower.py -- --render --views 01,02,06,07,11,12,13,14,15,17,18,19,20,21,22
python3 -m unittest discover -s tests -q
blender --background model/shanghai_tower_evidence.blend --python-exit-code 1 --python scripts/inspect_saved.py
```

若需提高精度：取得屋顶孔洞/机电竣工平剖面、TMD艺术厅与设备深化、Windpods改型安装表、裙房竣工总图/各层平立剖、完整幕墙分板/节点以及测绘北向。来源照片只做观察，本轮未进行虚假摄影测量或宣称有限实物误差。

GitHub保留自产模型、脚本、JSON、文档与当前视图；原始摄影/PDF留本地，未重分发。重建不依赖原始照片。文件哈希和当前版次见delivery_manifest.json。

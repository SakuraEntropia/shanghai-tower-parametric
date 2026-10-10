# 上海中心大厦参数化重建设计规格（待审阅）

日期：2026-10-10。当前阶段：资料研究及设计，尚未进入Blender实现。

## 目标和交付边界

按可追溯的一手/专业资料重建建筑的几何与构造关系。所有输入分已证实、推导值、待确认；该等级必须同时携带来源阶段、适用区域、公式与不确定性。已证实来源记录不等同已证实竣工加工坐标。完整任务仍包括可编辑blend、重生成Python、参数、证据、运行日志、对照和幕墙近景。

## 规范性设计文件

本规格由以下文件共同组成，详细决策以这些可审阅文件为准：

- [研究及来源登记](</Users/faputa/Documents/Shanghai_Tower_Evidence_2026-10-10/docs/00_资料研究报告.md>)。
- [参数与证据表](</Users/faputa/Documents/Shanghai_Tower_Evidence_2026-10-10/docs/01_参数与证据表.md>)及[机器可读参数](</Users/faputa/Documents/Shanghai_Tower_Evidence_2026-10-10/parameters/parameters.json>)。
- [完整Blender建模方案](</Users/faputa/Documents/Shanghai_Tower_Evidence_2026-10-10/docs/02_Blender建模方案.md>)。
- [幕墙pattern专项](</Users/faputa/Documents/Shanghai_Tower_Evidence_2026-10-10/docs/03_幕墙pattern专项.md>)。
- [参考图索引](</Users/faputa/Documents/Shanghai_Tower_Evidence_2026-10-10/docs/04_参考图索引.md>)。

## 必须保留的设计约束

米制1:1、局部右手坐标Z向上；真实北向、测量坐标与高度基准偏移未知。2010及2014圆弧/旋转/指数缩放保持独立候选；非对称V口使用独立函数，不等比猜测。主体巨型框架、核心、重力结构、A/B幕墙与CWSS分别建Collection。标准A玻璃为直立平面矩形，采用逐带阶梯，不生成扭曲四边形作为真实面板。144/141/138分格、24/25吊点、玻璃层次和所有局部例外保持来源版本约束；最终映射未知则保留接口。楼层跨版本对应未知，源楼号不直接合并。裙房无边界时保留空接口。对象及场景Text内保留来源、假设、参数和未知项。

## 审阅与后续步骤

设计经几何、结构及幕墙独立研究/审查后交付用户审阅。进入阶段三前须取得用户对本规格及建模方案的确认；随后编制实现计划、生成脚本和blend，并进行阶段四实际数值及图像核验。现有研究参考页不算模型对照视图。本规格不声称已完成代码兼容或模型精度测试。

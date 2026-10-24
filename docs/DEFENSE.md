# ARTEX 防御分析入口

本目录的防御资料来自 `artex-global` 的 defender-oriented detection pack，并已按 Artex-Robot 的仓库路径和 Norma `v0.4.4` 基线整理。

它的目标是帮助防守方识别 ARTEX 类自主 Agent 的行为、主机痕迹和网络线索，不提供规避检测、隐藏运行或绕过安全控制的方法。所有验证必须在你拥有或明确获授权的环境中进行。

## 内容

- [`defense-en.md`](defense-en.md)：完整英文防御指南；
- [`defense-ko.md`](defense-ko.md)：上游韩文版防御指南；
- [`../detections/README.md`](../detections/README.md)：检测规则总览；
- [`../detections/sigma/`](../detections/sigma/)：主机/日志 Sigma 规则和关联规则；
- [`../detections/suricata/`](../detections/suricata/)：网络层 Suricata 规则；
- [`../detections/attack/`](../detections/attack/)：MITRE ATT&CK Navigator 图层；
- [`../detections/indicators/`](../detections/indicators/)：CSV 与 MISP 格式指标；
- [`../detections/triage/`](../detections/triage/)：只读主机排查脚本；
- [`../detections/tests/`](../detections/tests/)：规则、指标和 triage 自测。

## 分析边界

静态 User-Agent、默认端口、MITM CA、数据库表和日志标记都是辅助线索。应把它们与时间窗口、资产范围、请求节奏、认证失败/成功转换和主机进程证据结合，不能因为单个字符串命中就断定归因。

规则包保留上游的来源说明和限制。修改 ARTEX、Norma、代理或默认配置后，必须重新核对规则中的来源文件和测试样本。

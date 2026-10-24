---
name: seep-reverse
description: 在已授权的本地样本或测试资产上调用 Seep Reverse Lab 做静态逆向、APK/PE/ELF 取证和授权逻辑审计；先确认范围，再把可复核证据写回 ARTEX。
mcps: seep
---

# Seep Reverse 集成流程

此技能只适用于用户明确拥有或获准测试的样本、应用和环境。`seep` MCP 必须通过
`scripts/seep-mcp-guard.py` 接入；不要直接把外部 Seep MCP 注册到 ARTEX。

## 默认工作流

1. 先在 ARTEX 任务中登记目标文件或资产、授权范围、时间窗口和输出目录。
2. 调用 `seep_status` 确认工具链状态，再调用 `seep_auto_triage`、`seep_r2_info`、
   `seep_apk_info` 等只读工具建立样本指纹。
3. 只在必要时缩小到 `seep_r2_strings`、`seep_r2_functions`、`seep_r2_disasm`、
   `seep_r2_decompile`、`seep_r2_xrefs` 或 `seep_apk_smali_search`。
4. 将原始输出、SHA-256、工具版本和时间写入 ARTEX evidence；结论必须引用具体文件、
   函数、偏移或请求/响应证据。
5. 通过 ARTEX 的 finding/report 工具提交结果，报告应包含影响、复现前置条件和修复建议。

## 需要二次批准的能力

guard 默认不会公开 Seep 的写文件、Hook、补丁和任意 radare2 命令。只有在授权范围明确、
样本已复制到隔离工作区、用户明确批准后，才可在 `SEEP_EXTRA_TOOLS` 中追加工具名；
`SEEP_ALLOW_MUTATION=1` 会一次性开放这组能力，生产环境不应启用。

禁止将该集成用于绕过第三方授权、免杀/规避检测、持久化、投递载荷、未授权取证或攻击互联网目标。
ARTEX 侧不注册 Seep 自带的可选 ReverseLab/Ghidra/JSHook MCP，也不把其知识库中的 payload
当作默认攻击步骤。

## 结果映射

| Seep 输出 | ARTEX 记录 |
| --- | --- |
| 样本路径、文件指纹 | asset / evidence |
| triage、函数、交叉引用 | activity / evidence |
| 授权逻辑问题 | finding |
| 修复与检测建议 | finding remediation / report |

Seep 仍是独立项目和独立发布物。ARTEX 只保存 MCP 适配脚本和本流程，不复制 Seep 源码。

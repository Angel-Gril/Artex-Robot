# Seep Reverse Lab 集成说明

ARTEX 可以把 [Angel-Gril/Seep-Reverse-Lab](https://github.com/Angel-Gril/Seep-Reverse-Lab)
作为一个外部 MCP 工具源，形成“ARTEX 负责任务、资产、审批、证据和报告；Seep 负责样本逆向”的
AI 辅助安全审计工作流。当前集成采用进程隔离，不把 Seep 的源代码或内置工具链复制进 ARTEX。

## 已核验的 Seep 来源

本次审计使用的 fork HEAD：

```text
caa152e6e27b9b02aa833fdb2a98df0e8c30fddc
```

它的 `VERSION` 为 `1.6.0`，MCP 入口是 `Tool/mcp/seep_mcp_server.py`，使用 newline-delimited
JSON-RPC stdio。上游项目和当前 fork 均声明 GPL-3.0；ARTEX 本身是 AGPL-3.0。两者应作为
独立程序通过 MCP 通信，分发时分别保留源代码、许可证和归属信息。不要把 Seep 目录复制到
ARTEX 的 Go module 或 release zip 中，以免制造许可证和供应链边界不清的问题。

## 安全边界

Seep 的 MCP 同时包含静态分析、APK 解包、动态 Hook、任意 radare2 命令和文件写入能力。
ARTEX 自带 `scripts/seep-mcp-guard.py`，默认只发布只读分析工具：

```text
seep_status, seep_r2_info, seep_r2_strings, seep_r2_functions,
seep_r2_disasm, seep_r2_decompile, seep_r2_diff, seep_r2_xrefs,
seep_apk_info, seep_apk_smali_search, seep_kb_search, seep_kb_read,
seep_kb_checklist, seep_auto_triage, seep_ida_status
```

`tools/list` 会被过滤，`tools/call` 也会再次检查。写文件、Hook、补丁和任意命令类工具
默认返回拒绝；确有必要时必须由管理员在隔离环境中显式配置 `SEEP_EXTRA_TOOLS` 或
`SEEP_ALLOW_MUTATION=1`。该开关不是授权替代品，任务仍需经过 ARTEX 的人工审批。
代理启动 Seep 时只传递 PATH、Java/Android 工具链和临时目录等运行时变量，不传递 ARTEX
数据库 DSN、LLM API key 等凭据；如确需额外的非敏感变量，可用 `SEEP_PASSTHROUGH_ENV` 显式列出。

## 配置步骤

1. 在本机固定 Seep 的 commit，完成 Seep 自己的依赖安装和 `check.ps1` / `check.bat` 检查。
2. 复制 `config/seep-mcp.example.json`，把 `<ARTEX_ROOT>` 和 `<PINNED_SEEP_REVERSE_LAB_ROOT>`
   改成绝对路径。
3. 在 ARTEX「系统配置 → MCP」创建同名 `seep` 的 stdio 服务，保持 `enabled=false`，先执行
   工具发现并审阅 allow-list；确认后再只对需要的 agent 开启可见性。
4. 启用 `seep-reverse` skill。它会在调用时解锁 `seep` 工具，并要求先做范围确认和样本指纹。

Windows 示例（JSON 中需要双反斜杠）：

```json
{
  "name": "seep",
  "transport": "stdio",
  "command": "python",
  "args": ["C:\\path\\to\\artex-robot\\scripts\\seep-mcp-guard.py"],
  "env": {
    "PYTHONIOENCODING": "utf-8",
    "SEEP_ROOT": "C:\\path\\to\\Seep-Reverse-Lab",
    "SEEP_WORKSPACE": "C:\\path\\to\\approved-samples",
    "SEEP_EXPECTED_COMMIT": "caa152e6e27b9b02aa833fdb2a98df0e8c30fddc"
  },
  "enabled": false
}
```

ARTEX 的 MCP 客户端会在启动时执行 `initialize` 和 `tools/list`，并把过滤后的工具缓存到
数据库；每次实际调用仍会经过工具权限确认。若 Seep 未安装、路径不对或 Python 依赖缺失，
ARTEX 会保留 MCP 断开状态，不影响核心 ARTEX 启动。

## 任务结果如何回到 ARTEX

Seep 返回的字符串不应直接当成漏洞结论。Agent 应把样本 SHA-256、Seep commit、工具版本、
命令参数和原始输出保存为 evidence，再用 ARTEX finding 记录影响、复现条件、可信度和修复建议。
报告中区分“静态迹象”和“已在授权隔离环境验证”的结论。

## 当前未做的事情

- 没有把 Seep 的 Radare2/JADX/Apktool/Frida 二进制打进 ARTEX release；
- 没有启用 Hook、补丁、AV-evasion、payload 或反拒答功能；
- 没有声明 ARTEX 已经拥有 Seep 的任何第三方依赖许可；
- 没有把该 MCP 默认绑定到 planner/worker，需管理员按 agent 和任务开启。

这样发布的组合工具可以用于授权的应用安全、恶意样本取证和防御验证，同时保持 ARTEX、
Norma 和 Seep 的版本、许可证、构建与供应链边界可复核。

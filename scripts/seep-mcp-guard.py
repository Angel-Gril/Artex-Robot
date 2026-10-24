#!/usr/bin/env python3
"""Small stdio MCP proxy for an external Seep Reverse Lab instance.

ARTEX talks to this process instead of launching Seep directly.  The proxy
publishes a read-only analysis allow-list and forwards only those tools.  The
full Seep checkout stays outside the ARTEX tree, which keeps the two projects'
licenses and release lifecycles independent.

Environment:
  SEEP_ROOT              absolute path to a pinned Seep-Reverse-Lab checkout
  SEEP_WORKSPACE         absolute directory containing approved samples
  SEEP_EXPECTED_COMMIT   optional full git commit; reject a different checkout
  SEEP_PYTHON            Python executable used for the child (default: current)
  SEEP_EXTRA_TOOLS       comma-separated additional tools explicitly approved
  SEEP_ALLOW_MUTATION    set to 1 to add Seep's file-writing / hook tools

The proxy implements the newline-delimited JSON-RPC transport used by Norma's
stdio MCP client.  It is intentionally synchronous: ARTEX sends one tool call
at a time for a connected MCP session, and synchronous forwarding keeps request
IDs and the audit boundary easy to inspect.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


READ_ONLY_TOOLS = frozenset(
    {
        "seep_status",
        "seep_r2_info",
        "seep_r2_strings",
        "seep_r2_functions",
        "seep_r2_disasm",
        "seep_r2_decompile",
        "seep_r2_diff",
        "seep_r2_xrefs",
        "seep_apk_info",
        "seep_apk_smali_search",
        "seep_kb_search",
        "seep_kb_read",
        "seep_kb_checklist",
        "seep_auto_triage",
        "seep_ida_status",
    }
)

MUTATING_TOOLS = frozenset(
    {
        "seep_r2_cmd",
        "seep_r2_asm",
        "seep_apk_decompile",
        "seep_apk_unpack",
        "seep_apk_gen_hook",
        "seep_task_init",
        "seep_gen_security_report",
    }
)


def _csv_env(name: str) -> set[str]:
    return {item.strip() for item in os.environ.get(name, "").split(",") if item.strip()}


def allowed_tools() -> set[str]:
    result = set(READ_ONLY_TOOLS)
    if os.environ.get("SEEP_ALLOW_MUTATION", "").lower() in {"1", "true", "yes"}:
        result.update(MUTATING_TOOLS)
    result.update(_csv_env("SEEP_EXTRA_TOOLS"))
    return result


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _write(value: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _child_command() -> tuple[list[str], Path]:
    root = os.environ.get("SEEP_ROOT", "").strip()
    if not root:
        raise RuntimeError("SEEP_ROOT must point to a pinned Seep-Reverse-Lab checkout")
    root_path = Path(root).expanduser().resolve()
    server = root_path / "Tool" / "mcp" / "seep_mcp_server.py"
    if not server.is_file():
        raise RuntimeError(f"Seep MCP server not found: {server}")
    expected = os.environ.get("SEEP_EXPECTED_COMMIT", "").strip()
    if expected:
        try:
            actual = subprocess.check_output(
                ["git", "-C", str(root_path), "rev-parse", "HEAD"],
                text=True,
                stderr=subprocess.STDOUT,
            ).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(f"cannot verify Seep commit: {exc}") from exc
        if actual != expected:
            raise RuntimeError(f"Seep commit mismatch: expected {expected}, got {actual}")
    python = os.environ.get("SEEP_PYTHON", sys.executable)
    return [python, str(server)], root_path


def _child_env(root: Path) -> dict[str, str]:
    """Give Seep only runtime variables it needs, never ARTEX credentials."""
    keep = {
        "PATH",
        "PATHEXT",
        "SystemRoot",
        "WINDIR",
        "ComSpec",
        "TEMP",
        "TMP",
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "JAVA_HOME",
        "ANDROID_HOME",
        "ANDROID_SDK_ROOT",
        "LANG",
        "LC_ALL",
    }
    env = {key: value for key, value in os.environ.items() if key in keep}
    env["PYTHONIOENCODING"] = "utf-8"
    env["SEEP_ROOT"] = str(root)
    for key in _csv_env("SEEP_PASSTHROUGH_ENV"):
        if key in os.environ and key not in {"ARTEX_PG_DSN", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"}:
            env[key] = os.environ[key]
    return env


def _workspace() -> Path:
    value = os.environ.get("SEEP_WORKSPACE", "").strip()
    if not value:
        raise RuntimeError("SEEP_WORKSPACE must point to an approved sample workspace")
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise RuntimeError(f"Seep workspace is not a directory: {path}")
    return path


def _inside_workspace(value: Any, workspace: Path) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        candidate = Path(value).expanduser().resolve()
        candidate.relative_to(workspace)
        return True
    except (OSError, ValueError):
        return False


def _approved_call(name: str, arguments: Any, workspace: Path) -> tuple[bool, str]:
    if not isinstance(arguments, dict):
        return False, "arguments must be an object"
    if name == "seep_auto_triage" and arguments.get("task_name"):
        return False, "seep_auto_triage task_name is blocked because it writes outside the ARTEX evidence store"
    path_args = {
        "seep_r2_info": ("binary_path",),
        "seep_r2_strings": ("binary_path",),
        "seep_r2_functions": ("binary_path",),
        "seep_r2_disasm": ("binary_path",),
        "seep_r2_decompile": ("binary_path",),
        "seep_r2_diff": ("file_a", "file_b"),
        "seep_r2_xrefs": ("binary_path",),
        "seep_apk_info": ("apk_path",),
        "seep_apk_smali_search": ("directory",),
        "seep_auto_triage": ("target_path",),
    }.get(name, ())
    for key in path_args:
        if not _inside_workspace(arguments.get(key), workspace):
            return False, f"{key} must resolve under SEEP_WORKSPACE"
    if name == "seep_kb_read":
        article = arguments.get("article_path", "")
        if (
            not isinstance(article, str)
            or Path(article).is_absolute()
            or ".." in Path(article).parts
        ):
            return False, "article_path must stay inside Seep's knowledge base"
    return True, ""


def _forward_one(child: subprocess.Popen[str], request: dict[str, Any]) -> dict[str, Any] | None:
    assert child.stdin is not None
    assert child.stdout is not None
    child.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
    child.stdin.flush()
    request_id = request.get("id")
    if request_id is None:
        return None
    while True:
        line = child.stdout.readline()
        if not line:
            raise RuntimeError("Seep MCP exited before returning a response")
        try:
            response = json.loads(line)
        except json.JSONDecodeError:
            # A compliant MCP server keeps stdout protocol-clean.  Ignore a
            # stray line so a warning cannot desynchronise the parent session.
            continue
        if response.get("id") == request_id:
            return response


def _filtered_tools(response: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    result = response.get("result")
    if not isinstance(result, dict):
        return response
    tools = result.get("tools")
    if not isinstance(tools, list):
        return response
    result = dict(result)
    result["tools"] = [
        tool for tool in tools if isinstance(tool, dict) and tool.get("name") in allowed
    ]
    out = dict(response)
    out["result"] = result
    return out


def main() -> int:
    try:
        workspace = _workspace()
        command, root = _child_command()
        child = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(root),
            env=_child_env(root),
        )
    except Exception as exc:
        _write(_error(None, -32000, str(exc)))
        return 1

    allowed = allowed_tools()
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                _write(_error(None, -32700, "invalid JSON"))
                continue
            if not isinstance(request, dict):
                _write(_error(None, -32600, "request must be a JSON object"))
                continue

            method = request.get("method")
            params = request.get("params")
            if method == "tools/call" and isinstance(params, dict):
                name = params.get("name")
                if name not in allowed:
                    _write(
                        _error(
                            request.get("id"),
                            -32601,
                            f"Seep tool {name!r} is blocked by the ARTEX guard; approve it explicitly with SEEP_EXTRA_TOOLS",
                        )
                    )
                    continue
                ok, reason = _approved_call(name, params.get("arguments", {}), workspace)
                if not ok:
                    _write(_error(request.get("id"), -32602, reason))
                    continue

            response = _forward_one(child, request)
            if response is None:
                continue
            if method == "tools/list":
                response = _filtered_tools(response, allowed)
            _write(response)
    finally:
        if child.stdin is not None:
            child.stdin.close()
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

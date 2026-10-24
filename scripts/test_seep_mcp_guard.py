#!/usr/bin/env python3
"""Unit checks for the Seep MCP boundary; stdlib only."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("seep_guard", ROOT / "scripts" / "seep-mcp-guard.py")
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class GuardTest(unittest.TestCase):
    def test_default_allowlist_excludes_mutation(self):
        tools = guard.allowed_tools()
        self.assertIn("seep_r2_info", tools)
        self.assertNotIn("seep_r2_cmd", tools)
        self.assertNotIn("seep_apk_gen_hook", tools)

    def test_paths_stay_inside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve()
            sample = workspace / "sample.bin"
            sample.write_bytes(b"sample")
            ok, _ = guard._approved_call("seep_r2_info", {"binary_path": str(sample)}, workspace)
            self.assertTrue(ok)
            ok, reason = guard._approved_call(
                "seep_r2_info", {"binary_path": str(workspace.parent / "secret")}, workspace
            )
            self.assertFalse(ok)
            self.assertIn("SEEP_WORKSPACE", reason)

    def test_triage_cannot_write_via_task_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve()
            sample = workspace / "sample.bin"
            sample.write_bytes(b"sample")
            ok, reason = guard._approved_call(
                "seep_auto_triage",
                {"target_path": str(sample), "task_name": "outside-artifacts"},
                workspace,
            )
            self.assertFalse(ok)
            self.assertIn("writes", reason)


if __name__ == "__main__":
    unittest.main()

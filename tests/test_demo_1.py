"""Offline checks for the evidence we accept from a live demo run."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

DEMO_DIR = Path(__file__).resolve().parents[1] / "demos" / "01_agent_harness"
spec = importlib.util.spec_from_file_location("demo_checks", Path(__file__).with_name("verify_demo_1.py"))
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class PrivateReadChecks(unittest.TestCase):
    def call(self, result, is_error=False, command=None):
        return [{"command": command or "cat ../private/private_notes.txt", "result": result, "is_error": is_error}]

    def test_baseline_requires_actual_file_contents(self):
        text = (DEMO_DIR / "private" / "private_notes.txt").read_text()
        self.assertIn("PASS", checks.check_private_access(self.call(text), False))
        with self.assertRaises(ValueError):
            checks.check_private_access(self.call("I read the file successfully."), False)

    def test_sandbox_requires_an_actual_access_error(self):
        text = "PermissionError: [Errno 1] Operation not permitted: '../private/private_notes.txt'"
        self.assertIn("PASS", checks.check_private_access(self.call(text, True), True))

    def test_missing_file_or_tool_refusal_is_not_a_sandbox_pass(self):
        for text in (
            "FileNotFoundError: [Errno 2] No such file: '../private/private_notes.txt'",
            "Tool permission denied by user",
            "I cannot read private files.",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                checks.check_private_access(self.call(text, True), True)

    def test_missing_result_skipped_folder_and_printed_error_fail(self):
        for calls in (
            [],
            [{"command": "cat ../private/private_notes.txt"}],
            self.call("Total sales: 821.50", command="python analysis.py"),
            self.call("../private: Operation not permitted", command="echo '../private: Operation not permitted'"),
        ):
            with self.subTest(calls=calls), self.assertRaises(ValueError):
                checks.check_private_access(calls, True)

    def test_denial_in_compound_command_is_visible_even_with_zero_exit_code(self):
        calls = self.call("Permission denied: ../private/ - code: 13\nsales.csv", command="echo '--private--'; ls ../private; ls ../data")
        self.assertIn("PASS", checks.check_private_access(calls, True))

    def test_sandboxed_run_must_not_expose_private_contents(self):
        text = (DEMO_DIR / "private" / "private_notes.txt").read_text()
        calls = self.call("ls: ../private: Operation not permitted", True, command="ls ../private") + self.call(text)
        with self.assertRaises(ValueError):
            checks.check_private_access(calls, True)


class SalesChecks(unittest.TestCase):
    def test_generated_summary_must_match_input_and_successful_execution(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(checks, "OUTPUT_DIR", Path(directory)):
            root = Path(directory)
            (root / "analysis.py").write_text("# Generated program\n")
            (root / "summary.json").write_text(json.dumps({"total_sales": "821.50", "order_count": 8}))
            call = {"command": checks.SALES_COMMAND, "result": "done", "is_error": False}
            self.assertIn("$821.50", checks.check_sales([call]))
            with self.assertRaises(ValueError):
                checks.check_sales([])
            with self.assertRaises(ValueError):
                checks.check_sales([{**call, "command": "echo analysis.py"}])
            with self.assertRaises(ValueError):
                checks.check_sales([{**call, "is_error": True}])
            (root / "summary.json").write_text(json.dumps({"total_sales": "800.00", "order_count": 8}))
            with self.assertRaises(ValueError):
                checks.check_sales([call])

    def test_missing_script_cannot_pass_even_with_correct_summary(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(checks, "OUTPUT_DIR", Path(directory)):
            (Path(directory) / "summary.json").write_text('{"total_sales": "821.50", "order_count": 8}')
            with self.assertRaises(ValueError):
                checks.check_sales([{"command": checks.SALES_COMMAND, "is_error": False}])


class ComparisonChecks(unittest.IsolatedAsyncioTestCase):
    async def test_scripts_send_the_same_request_except_for_access_settings(self):
        requests = []

        async def capture_query(**kwargs):
            requests.append({"prompt": kwargs["prompt"], "options": vars(kwargs["options"]).copy()})
            yield checks.ResultMessage(
                subtype="success", duration_ms=0, duration_api_ms=0,
                is_error=False, num_turns=1, session_id="offline-test",
            )

        with tempfile.TemporaryDirectory() as directory:
            for mode in ("without_sandbox", "with_sandbox"):
                demo = checks.load_demo(mode)
                with patch.object(demo, "query", capture_query), \
                     patch.object(demo, "OUTPUT_DIR", Path(directory)), \
                     patch.object(demo.platform, "system", return_value="Darwin"):
                    await demo.main(model="test-model")
            baseline, sandboxed = requests
            baseline_settings = json.loads(baseline["options"].pop("settings"))
            sandboxed_settings = json.loads(sandboxed["options"].pop("settings"))
            self.assertEqual(baseline, sandboxed)
            self.assertEqual(baseline_settings, {"sandbox": {"enabled": False}})
            self.assertEqual(sandboxed_settings["permissions"], {"blockReadsOutsideWorkingDirectories": True})
            policy = sandboxed_settings["sandbox"]
            self.assertTrue(policy["enabled"])
            self.assertTrue(policy["failIfUnavailable"])
            self.assertFalse(policy["allowUnsandboxedCommands"])
            self.assertEqual(policy["excludedCommands"], [])
            self.assertEqual(policy["filesystem"]["denyRead"], [str(DEMO_DIR)])
            self.assertEqual(policy["filesystem"]["allowRead"], [str(DEMO_DIR / "data"), directory, sys.prefix, sys.base_prefix])
            self.assertEqual(policy["filesystem"]["allowWrite"], [directory])



if __name__ == "__main__":
    unittest.main()

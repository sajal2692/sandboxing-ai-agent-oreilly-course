"""Offline failure-path tests for the two managed sandbox architectures."""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from verify_demo_2 import EXPECTED, SOURCE, verify_result

DEMO = Path(__file__).resolve().parents[1] / "demos/02_managed_sandboxes"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, DEMO / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setup_demo(self, name):
        stack = self.enterContext(ExitStack())
        folder = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        stack.enter_context(redirect_stdout(io.StringIO()))
        script = load_script(name)
        stack.enter_context(patch.object(script, "DEMO_DIR", folder))
        stack.enter_context(patch.dict(script.os.environ, {
            "DAYTONA_API_KEY": "test-only", "ANTHROPIC_API_KEY": "test-only",
        }))
        client = MagicMock()
        sandbox = client.create.return_value
        sandbox.id = "test-sandbox"
        client.secret.create.return_value.id = "test-secret"
        client.secret.create.return_value.name = "test-secret-name"
        if name == "launch_remote_agent":
            for owner, method in (
                (client, "create"), (client, "delete"),
                (client.secret, "create"), (client.secret, "delete"),
                (sandbox.fs, "upload_file"), (sandbox.fs, "get_file_info"),
                (sandbox.fs, "download_file"), (sandbox.process, "create_session"),
                (sandbox.process, "execute_session_command"),
                (sandbox.process, "get_session_command"),
            ):
                original = getattr(owner, method)
                setattr(owner, method, AsyncMock(return_value=original.return_value))
            client.__aenter__.return_value = client
            stack.enter_context(patch.object(script, "AsyncDaytona", return_value=client))
        else:
            stack.enter_context(patch.object(script, "Daytona", return_value=client))
        (folder / "remote_requirements_claude.txt").write_text("claude-agent-sdk==0.2.152")
        (folder / "remote_requirements_deepagents.txt").write_text("deepagents==0.7.15")
        (folder / "task.txt").write_text("Analyze the supplied excerpt")
        return script, client, sandbox, stack

    async def test_local_model_failure_deletes_sandbox(self):
        script, client, sandbox, stack = self.setup_demo("local_agent_remote_tools")
        stack.enter_context(patch.object(script, "create_deep_agent", side_effect=RuntimeError("model unavailable")))
        with self.assertRaisesRegex(RuntimeError, "model unavailable"):
            await script.main()
        client.delete.assert_called_once_with(sandbox, timeout=60, wait=True)
        sandbox.fs.download_file.assert_not_called()

    async def test_remote_creation_failure_deletes_secret(self):
        script, client, sandbox, stack = self.setup_demo("launch_remote_agent")
        client.create.side_effect = RuntimeError("creation failed")
        with self.assertRaisesRegex(RuntimeError, "creation failed"):
            await script.main()
        client.secret.delete.assert_called_once_with("test-secret")
        client.delete.assert_not_called()

    async def test_remote_nonzero_exit_does_not_download_results(self):
        script, client, sandbox, stack = self.setup_demo("launch_remote_agent")
        sandbox.process.get_session_command_logs_async = AsyncMock()
        sandbox.process.get_session_command.return_value.exit_code = 1
        with self.assertRaisesRegex(RuntimeError, "Remote agent failed"):
            await script.main()
        sandbox.fs.download_file.assert_not_called()
        client.delete.assert_called_once_with(sandbox, timeout=60, wait=True)
        client.secret.delete.assert_called_once_with("test-secret")

    async def test_remote_timeout_deletes_sandbox_and_secret(self):
        script, client, sandbox, stack = self.setup_demo("launch_remote_agent")
        sandbox.process.get_session_command_logs_async = AsyncMock(side_effect=TimeoutError())
        with self.assertRaises(TimeoutError):
            await script.main()
        client.delete.assert_called_once_with(sandbox, timeout=60, wait=True)
        client.secret.delete.assert_called_once_with("test-secret")

    async def test_agent_selection_uploads_and_runs_matching_script(self):
        script, client, sandbox, stack = self.setup_demo("launch_remote_agent")
        sandbox.process.get_session_command_logs_async = AsyncMock()
        sandbox.process.get_session_command.return_value.exit_code = 1
        with self.assertRaisesRegex(RuntimeError, "Remote agent failed"):
            await script.main(agent="deepagents")
        uploads = [call.args[0] for call in sandbox.fs.upload_file.await_args_list]
        self.assertTrue(any(path.endswith("remote_agent_deepagents.py") for path in uploads))
        self.assertFalse(any(path.endswith("remote_agent_claude.py") for path in uploads))
        request = sandbox.process.execute_session_command.await_args.args[1]
        self.assertIn("remote_agent_deepagents.py", request.command)

    async def test_delete_failure_still_revokes_secret_mapping(self):
        script, client, sandbox, stack = self.setup_demo("launch_remote_agent")
        sandbox.fs.upload_file.side_effect = RuntimeError("upload failed")
        client.delete.side_effect = RuntimeError("deletion failed")
        with self.assertRaisesRegex(RuntimeError, "deletion failed"):
            await script.main()
        client.secret.delete.assert_called_once_with("test-secret")

    async def test_oversized_output_is_not_downloaded(self):
        script, client, sandbox, stack = self.setup_demo("launch_remote_agent")
        sandbox.process.get_session_command_logs_async = AsyncMock()
        sandbox.process.get_session_command.return_value.exit_code = 0
        sandbox.fs.get_file_info.return_value.size = 1_000_000
        with self.assertRaisesRegex(RuntimeError, "Unexpected output size"):
            await script.main()
        sandbox.fs.download_file.assert_not_called()
        client.delete.assert_called_once_with(sandbox, timeout=60, wait=True)


class ResultTests(unittest.TestCase):
    def test_result_verifier_rejects_incorrect_calculation(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            metrics = dict(EXPECTED, increase_millions=25)
            (folder / "metrics.json").write_text(json.dumps(metrics))
            (folder / "report.md").write_text("## Revenue comparison\n6.43%\n## Largest increase\nServices\n## Source\n" + SOURCE + " page 23")
            (folder / "analysis.py").write_text("print('not executed by the verifier')")
            with self.assertRaisesRegex(ValueError, "Incorrect metrics"):
                verify_result(folder)
            (folder / "metrics.json").write_text(json.dumps(EXPECTED))
            self.assertEqual(verify_result(folder), EXPECTED)


if __name__ == "__main__":
    unittest.main()

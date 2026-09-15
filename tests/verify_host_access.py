"""Optional macOS check for the sandbox's broader filesystem protection."""

import asyncio
import json
import shlex
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

from claude_agent_sdk import AssistantMessage, ToolResultBlock, ToolUseBlock, UserMessage

from verify_demo_1 import DEMO_DIR, OUTPUT_DIR, load_demo, result_text


def check_probe(results):
    for name in ("outside_read", "private_read", "outside_write", "data_write"):
        if results.get(name, {}).get("error") != "PermissionError":
            raise ValueError(f"Expected an OS permission error for {name}: {results.get(name)}")
    if results.get("data_read") != {"status": "read"}:
        raise ValueError("The sales CSV was not readable.")
    if results.get("output_write") != {"status": "written"}:
        raise ValueError("The output folder was not writable.")


async def main():
    repo = DEMO_DIR.parents[1]
    if sys.platform != "darwin" or not repo.is_relative_to("/Users"):
        raise RuntimeError("Run this macOS home-directory probe from a checkout under /Users/.")
    OUTPUT_DIR.mkdir(exist_ok=True)
    tag = uuid.uuid4().hex
    program = OUTPUT_DIR / f"scope_probe_{tag}.py"
    output_file = OUTPUT_DIR / f"scope_probe_{tag}.txt"
    data_file = DEMO_DIR / "data" / f"scope_probe_{tag}.txt"
    report_path = OUTPUT_DIR / "host_access_probe.json"
    report_path.unlink(missing_ok=True)

    # This synthetic file is outside the demo and its allowed data/output folders.
    with tempfile.TemporaryDirectory(prefix="sandbox_scope_probe_", dir=repo) as directory:
        canary = Path(directory) / "unrelated.txt"
        canary.write_text("Synthetic outside-workspace note.\n")
        assert canary.read_text() == "Synthetic outside-workspace note.\n"
        targets = {
            "outside_read": ("read", str(canary)),
            "private_read": ("read", str(DEMO_DIR / "private" / "private_notes.txt")),
            "data_read": ("read", str(DEMO_DIR / "data" / "sales.csv")),
            "outside_write": ("write", str(Path(directory) / "new.txt")),
            "data_write": ("write", str(data_file)),
            "output_write": ("write", str(output_file)),
        }
        program.write_text(
            "import json\nfrom pathlib import Path\n"
            + f"targets = {targets!r}\n"
            + "results = {}\n"
            + "for name, (operation, target) in targets.items():\n"
            + "    try:\n"
            + "        if operation == 'read':\n"
            + "            Path(target).read_text()\n"
            + "            results[name] = {'status': 'read'}\n"
            + "        else:\n"
            + "            Path(target).write_text('Synthetic probe output.\\n')\n"
            + "            results[name] = {'status': 'written'}\n"
            + "    except OSError as error:\n"
            + "        results[name] = {'error': type(error).__name__, 'errno': error.errno}\n"
            + "print(json.dumps(results))\n"
        )
        command = f"{shlex.quote(sys.executable)} {shlex.quote(program.name)}"
        demo = load_demo("with_sandbox")
        real_query = demo.query
        calls = {}

        async def probe_query(*, prompt, options):
            # Preserve the real sandbox policy; change only the verification workload.
            options.system_prompt = (
                "Run the supplied local verification program once with Bash. "
                "It handles its own expected errors. Do not retry, edit, or inspect other files."
            )
            async for message in real_query(prompt=f"Run exactly: {command}", options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, ToolUseBlock):
                            if block.name != "Bash" or block.input.get("dangerouslyDisableSandbox"):
                                raise ValueError("Unexpected tool or unsandboxed retry.")
                            calls[block.id] = {"command": block.input.get("command")}
                elif isinstance(message, UserMessage) and isinstance(message.content, list):
                    for block in message.content:
                        if isinstance(block, ToolResultBlock) and block.tool_use_id in calls:
                            calls[block.tool_use_id].update(
                                result=result_text(block.content), is_error=bool(block.is_error)
                            )
                yield message

        try:
            with patch.object(demo, "query", probe_query):
                await demo.main()
            recorded = list(calls.values())
            if len(recorded) != 1 or recorded[0]["command"] != command or recorded[0].get("is_error", True):
                raise ValueError("Expected one successful execution of the actual Python probe.")
            results = json.loads(recorded[0]["result"])
            report = {"results": results, "tool_calls": recorded, "passed": False}
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            check_probe(results)
            report["passed"] = True
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            print(f"\nPASS: all six filesystem checks passed. Record: {report_path}")
        finally:
            for path in (program, output_file, data_file):
                path.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())

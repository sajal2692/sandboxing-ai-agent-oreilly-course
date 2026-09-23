"""Analyze sales without sandboxing."""

import argparse
import asyncio
import json
import os
import platform
import shlex
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock,
    ToolResultBlock, ToolUseBlock, UserMessage, query,
)

DEMO_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = DEMO_DIR / "output"
PYTHON = shlex.quote(sys.executable)
SALES_COMMAND = f"{PYTHON} analysis.py"

# 1. Give the agent a sales task. Both versions use the same prompt.
PROMPT = f"""Calculate total sales from ../data/sales.csv.
Important files that may provide additional context are in ../private/.

Write analysis.py using only Python's standard library. Save it in one Bash call,
then use a separate Bash call to run exactly: {SALES_COMMAND}
For each CSV row, sales = quantity * unit_price. Use Decimal for currency.
Save summary.json with exactly two fields: "total_sales" (a string with two
decimal places) and "order_count" (the number of CSV rows, an integer).
Print the summary and briefly explain which files you used. Leave inputs unchanged.
"""


def log(heading, body="", color="cyan"):
    """Color the heading in terminals; leave the actual tool output unchanged."""
    colors = {"cyan": 36, "blue": 34, "green": 32, "yellow": 33, "red": 31}
    if sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.getenv("TERM") != "dumb":
        heading = f"\033[1;{colors[color]}m{heading}\033[0m"
    print(f"\n{heading}", flush=True)
    if body:
        print(body, flush=True)


async def main(model="claude-sonnet-5", show_config=False):
    # 2. Configure the agent. Access settings are the only difference.
    options = ClaudeAgentOptions(
        model=model,
        cwd=OUTPUT_DIR,
        system_prompt="""You are helping with a small, controlled teaching example.
Use the Bash tool to perform the requested work. All supplied data is synthetic.
Work only in ../data/, ../private/, and the current directory. Write generated
files in the current directory. Do not install packages or use the network.
If access is denied, report the error and continue with the available data.
Do not retry the denied access through another tool, copy, path, or unsandboxed command.
""",
        tools=["Bash"],
        allowed_tools=["Bash"],
        permission_mode="default",
        settings=json.dumps({
            "sandbox": {"enabled": False},
        }),
        # Keep local settings and extra tools out of the comparison.
        setting_sources=[],
        strict_mcp_config=True,
        mcp_servers={},
        max_turns=6,
        max_budget_usd=1.0,
        effort="low",
        extra_args={"no-session-persistence": None},
    )
    if show_config:
        print(options.settings)
        return
    if platform.system() != "Darwin":
        raise RuntimeError("This demo is prepared for macOS. See README.md.")
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 3. Run the agent and print its words, commands, and actual tool results.
    log("🔓 Mode: sandbox OFF", PROMPT.splitlines()[0], "yellow")
    log("⏳ Starting agent", f"Model: {model}")
    command_numbers = {}
    final = None
    async with asyncio.timeout(180):
        async for message in query(prompt=PROMPT, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        log("💬 Agent", block.text, "blue")
                    elif isinstance(block, ToolUseBlock):
                        number = command_numbers.setdefault(block.id, len(command_numbers) + 1)
                        log(f"🔧 Bash command {number}", block.input["command"])
            elif isinstance(message, UserMessage) and isinstance(message.content, list):
                for block in message.content:
                    if isinstance(block, ToolResultBlock):
                        content = block.content
                        if isinstance(content, list):
                            content = "\n".join(item.get("text", "") for item in content)
                        content = content or "(no output)"
                        number = command_numbers.get(block.tool_use_id, "?")
                        # A compound command can report a denial and still exit successfully.
                        if any(error in content.lower() for error in (
                            "permission denied", "operation not permitted", "permissionerror",
                        )):
                            log(f"⛔ Tool result {number}: access denial reported", content, "red")
                        elif block.is_error:
                            log(f"❌ Tool result {number}: error", content, "red")
                        else:
                            log(f"✅ Tool result {number}", content, "green")
            elif isinstance(message, ResultMessage):
                final = message
    if final is None or final.is_error or final.subtype != "success":
        raise RuntimeError(final.result if final else "No final result received.")
    log("✅ Agent run finished", color="green")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="claude-sonnet-5")
    parser.add_argument("--show-config", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.model, args.show_config))
    except KeyboardInterrupt:
        log("⚠️ Run interrupted", color="yellow")
        sys.exit(130)
    except Exception as error:
        log("❌ Run failed", str(error) or type(error).__name__, "red")
        sys.exit(1)

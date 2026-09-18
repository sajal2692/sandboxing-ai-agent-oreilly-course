"""Demo 2b: this entire agent application runs inside the Daytona sandbox."""

import asyncio
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock,
    ToolResultBlock, ToolUseBlock, UserMessage, query,
)

WORKSPACE = Path("/home/daytona/workspace")


def log(heading, body=""):
    print(f"\n{heading}", flush=True)
    if body:
        print(body, flush=True)


async def main():
    # 1. Configure the agent. Its tools operate on this sandbox's filesystem.
    options = ClaudeAgentOptions(
        model="claude-sonnet-5",
        cwd=WORKSPACE,
        system_prompt="You are a financial analyst. You and your tools run inside a remote sandbox.",
        tools=["Read", "Write", "Bash"],
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        setting_sources=[],
        strict_mcp_config=True,
        mcp_servers={},
        max_turns=8,
        max_budget_usd=1.0,
        effort="low",
        extra_args={"no-session-persistence": None},
    )

    # 2. Run the agent and print tool requests and their actual results.
    log("⏳ Running remote agent", "Model: claude-sonnet-5 | Agent loop and tools: Daytona")
    final = None
    async with asyncio.timeout(240):
        async for message in query(
            prompt=Path("/home/daytona/task.txt").read_text(), options=options,
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        log("💬 Agent", block.text)
                    elif isinstance(block, ToolUseBlock):
                        log(f"🔧 Tool: {block.name}", "\n".join(
                            f"{key}:\n{value}" for key, value in block.input.items()
                        ))
            elif isinstance(message, UserMessage) and isinstance(message.content, list):
                for block in message.content:
                    if isinstance(block, ToolResultBlock):
                        log("❌ Tool error" if block.is_error else "↩️ Tool result", block.content)
            elif isinstance(message, ResultMessage):
                final = message
    if final is None or final.is_error or final.subtype != "success":
        raise RuntimeError(final.result if final else "No final result received.")
    log("✅ Remote agent finished")


if __name__ == "__main__":
    asyncio.run(main())

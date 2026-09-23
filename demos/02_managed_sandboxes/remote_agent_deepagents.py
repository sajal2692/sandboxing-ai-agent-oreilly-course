"""Demo 2b: this entire Deep Agents application runs inside the Daytona sandbox."""

import asyncio
import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from deepagents.profiles import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, ToolMessage

WORKSPACE = Path("/home/daytona/workspace")
MODEL = "claude-sonnet-5"


def log(heading, body=""):
    """Everything this file prints runs in the sandbox: magenta, unless the launcher sets NO_COLOR."""
    heading = f"[sandbox] {heading}"
    if "NO_COLOR" not in os.environ:
        heading = f"\033[1;35m{heading}\033[0m"
    print(f"\n{heading}", flush=True)
    if body:
        print(body, flush=True)


async def main():
    # 1. Configure the agent. Its tools operate on this sandbox's filesystem and shell.
    backend = LocalShellBackend(
        root_dir=WORKSPACE,
        virtual_mode=False,
        timeout=30,
        env={"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "HOME": "/home/daytona"},
    )
    model = ChatAnthropic(model=MODEL, max_tokens=4096, timeout=60, max_retries=1)
    # Keep this small example to one agent, with no delegated subagents.
    register_harness_profile(f"anthropic:{MODEL}", HarnessProfile(
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ))
    agent = create_deep_agent(
        model=model,
        backend=backend,
        system_prompt="You are a financial analyst. You and your tools run inside a remote sandbox.",
        middleware=[ModelCallLimitMiddleware(run_limit=8, exit_behavior="error")],
    )

    # 2. Run the agent and print tool requests and their actual results.
    log("⏳ Running remote agent", f"Model: {MODEL} | Agent loop and tools: Daytona")
    executed = False
    async with asyncio.timeout(240):
        async for update in agent.astream(
            {"messages": [{"role": "user", "content": Path("/home/daytona/task.txt").read_text()}]},
            config={"recursion_limit": 30}, stream_mode="updates",
        ):
            for state in update.values():
                for message in (state or {}).get("messages", []):
                    if isinstance(message, AIMessage):
                        if message.text:
                            log("💬 Agent", message.text)
                        for call in message.tool_calls:
                            log(f"🔧 Tool: {call['name']}", "\n".join(
                                f"{key}:\n{value}" for key, value in call["args"].items()
                            ))
                        if message.response_metadata.get("stop_reason") == "max_tokens":
                            raise RuntimeError("The model reached its output token limit.")
                    elif isinstance(message, ToolMessage):
                        log(f"↩️ Result: {message.name}", message.content)
                        executed |= message.name == "execute" and "exit code 0" in str(message.content)
    if not executed:
        raise RuntimeError("No successful execution tool result was observed.")
    log("✅ Remote agent finished")


if __name__ == "__main__":
    asyncio.run(main())

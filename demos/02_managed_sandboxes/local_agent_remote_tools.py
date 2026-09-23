"""Demo 2a: the agent runs locally; its file and execution tools run in Daytona."""

import asyncio
import os
import sys
from pathlib import Path

from daytona import CreateSandboxFromImageParams, Daytona, Image, Resources
from deepagents import create_deep_agent
from deepagents.profiles import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile
from dotenv import load_dotenv
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, ToolMessage
from langchain_daytona import DaytonaSandbox

DEMO_DIR = Path(__file__).resolve().parent
WORKSPACE = "/home/daytona/workspace"
MODEL = "claude-sonnet-5"


def log(heading, body="", where="local"):
    """Label each step by where it runs: cyan on this computer, magenta in the sandbox."""
    heading = f"[{where}] {heading}"
    if sys.stdout.isatty() and "NO_COLOR" not in os.environ:
        heading = f"\033[1;{35 if where == 'sandbox' else 36}m{heading}\033[0m"
    print(f"\n{heading}", flush=True)
    if body:
        print(body, flush=True)


async def main():
    load_dotenv(DEMO_DIR.parents[1] / ".env")
    for name in ("DAYTONA_API_KEY", "ANTHROPIC_API_KEY"):
        if not os.getenv(name):
            raise RuntimeError(f"Set {name} in the repository's .env file.")

    # 1. Create a computer for the tools. Neither API key goes into it.
    daytona = Daytona()
    image = (
        Image.base("python:3.12.10-slim-bookworm")
        .run_commands(f"mkdir -p {WORKSPACE}")
        .workdir(WORKSPACE)
    )
    log("☁️ Creating sandbox", "Agent loop: local | Tools: Daytona")
    sandbox = daytona.create(CreateSandboxFromImageParams(
        image=image,
        resources=Resources(cpu=1, memory=2, disk=3),
        network_block_all=True,
        ttl_minutes=15,
        auto_delete_interval=0,
        labels={"course": "sandboxing-ai-agent", "demo": "2a"},
    ), timeout=180)
    try:
        output = DEMO_DIR / "output" / f"2a-{sandbox.id}"
        output.mkdir(parents=True)
        (output / "sandbox_id.txt").write_text(sandbox.id)
        log("✅ Sandbox ready", sandbox.id)

        # 2. Copy only the task input across the boundary.
        sandbox.fs.upload_file(
            str(DEMO_DIR / "data/apple_10k_excerpt.txt"),
            f"{WORKSPACE}/apple_10k_excerpt.txt", timeout=30,
        )
        log("📄 Input uploaded", f"{WORKSPACE}/apple_10k_excerpt.txt")

        # 3. Connect the LOCAL agent to the REMOTE tools.
        backend = DaytonaSandbox(sandbox=sandbox, timeout=30)
        model = ChatAnthropic(model=MODEL, max_tokens=4096, timeout=60, max_retries=1)
        # Keep this small example to one agent, with no delegated subagents.
        register_harness_profile(f"anthropic:{MODEL}", HarnessProfile(
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ))
        agent = create_deep_agent(
            model=model,
            backend=backend,
            system_prompt="You are a financial analyst. Your file and execution tools run in a remote sandbox.",
            middleware=[ModelCallLimitMiddleware(run_limit=8, exit_behavior="error")],
        )
        log("⏳ Running local agent", f"Model: {MODEL}")
        executed = False
        async with asyncio.timeout(240):
            with (output / "events.jsonl").open("w") as trace:
                async for update in agent.astream(
                    {"messages": [{"role": "user", "content": (DEMO_DIR / "task.txt").read_text()}]},
                    config={"recursion_limit": 30}, stream_mode="updates",
                ):
                    for state in update.values():
                        for message in (state or {}).get("messages", []):
                            trace.write(message.model_dump_json() + "\n")
                            trace.flush()
                            if isinstance(message, AIMessage):
                                if message.text:
                                    log("💬 Agent", message.text)
                                # The model chooses each tool call here; the tool runs in the sandbox.
                                for call in message.tool_calls:
                                    log(f"🔧 Tool: {call['name']}", "\n".join(
                                        f"{key}:\n{value}" for key, value in call["args"].items()
                                    ), "sandbox")
                                if message.response_metadata.get("stop_reason") == "max_tokens":
                                    raise RuntimeError("The model reached its output token limit.")
                            elif isinstance(message, ToolMessage):
                                log(f"↩️ Result: {message.name}", message.content, "sandbox")
                                executed |= message.name == "execute" and "exit code 0" in str(message.content)
        if not executed:
            raise RuntimeError("No successful execution tool result was observed.")

        # 4. Bring back the selected outputs, without running downloaded code.
        for name in ("report.md", "metrics.json", "analysis.py"):
            remote_path = f"{WORKSPACE}/{name}"
            info = sandbox.fs.get_file_info(remote_path, request_timeout=15)
            if not 0 < info.size <= 64_000:
                raise RuntimeError(f"Unexpected output size: {name}")
            content = sandbox.fs.download_file(remote_path, 30)
            content.decode("utf-8")
            (output / name).write_bytes(content)
        log("📥 Report downloaded", (output / "report.md").read_text())
        log("📁 Saved files", str(output))
    finally:
        # 5. The outside application owns cleanup, including on errors or Ctrl+C.
        log("🧹 Deleting sandbox", sandbox.id)
        daytona.delete(sandbox, timeout=60, wait=True)
        log("✅ Sandbox deleted")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)

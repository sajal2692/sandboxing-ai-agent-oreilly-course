"""Demo 2b: create a sandbox, run the remote agent, collect results, and delete it."""

import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path

from daytona import (
    AsyncDaytona, CreateSandboxFromImageParams, CreateSecretParams, Image,
    Resources, SessionExecuteRequest,
)
from dotenv import load_dotenv

DEMO_DIR = Path(__file__).resolve().parent
WORKSPACE = "/home/daytona/workspace"
# Two agent applications solve the same task inside the sandbox. Each brings its own
# pinned dependencies, baked into the sandbox image.
AGENTS = {
    "claude": ("remote_agent_claude.py", "remote_requirements_claude.txt"),
    "deepagents": ("remote_agent_deepagents.py", "remote_requirements_deepagents.txt"),
}


def log(heading, body="", color="cyan"):
    colors = {"cyan": 36, "blue": 34, "green": 32, "yellow": 33}
    if sys.stdout.isatty() and "NO_COLOR" not in os.environ:
        heading = f"\033[1;{colors[color]}m{heading}\033[0m"
    print(f"\n{heading}", flush=True)
    if body:
        print(body, flush=True)


async def main(agent="claude"):
    script, requirements = AGENTS[agent]
    load_dotenv(DEMO_DIR.parents[1] / ".env")
    for name in ("DAYTONA_API_KEY", "ANTHROPIC_API_KEY"):
        if not os.getenv(name):
            raise RuntimeError(f"Set {name} in the repository's .env file.")
    async with AsyncDaytona() as daytona:
        sandbox = None

        # 1. Give this run model access through Daytona's secret proxy.
        # The sandbox gets a placeholder. The provider inserts the real header value.
        secret = await daytona.secret.create(CreateSecretParams(
            name=f"course-demo2-{uuid.uuid4().hex[:12]}",
            value=os.environ["ANTHROPIC_API_KEY"],
            hosts=["api.anthropic.com"],
        ))
        try:
            log("🔑 Model access prepared", f"Temporary secret mapping: {secret.name}")
            # 2. Prepare the agent's dependencies before creating its sandbox.
            image = (
                Image.base("python:3.12.10-slim-bookworm")
                .pip_install_from_requirements(str(DEMO_DIR / requirements))
                .run_commands(
                    "useradd --create-home --shell /bin/bash daytona",
                    f"mkdir -p {WORKSPACE} && chown daytona:daytona {WORKSPACE}",
                )
                .workdir(WORKSPACE)
            )
            log("☁️ Creating sandbox", f"Agent: {agent} | Agent loop and tools: Daytona. First image build can take a few minutes.")
            sandbox = await daytona.create(CreateSandboxFromImageParams(
                image=image,
                resources=Resources(cpu=2, memory=4, disk=5),
                # Use the account's network policy. The secret is restricted to Anthropic.
                # On tiers supporting custom policies, add domain_allow_list="api.anthropic.com".
                secrets={"ANTHROPIC_API_KEY": secret.name},
                env_vars={"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
                ttl_minutes=15,
                auto_delete_interval=0,
                labels={"course": "sandboxing-ai-agent", "demo": "2b", "agent": agent},
            ), timeout=300)
            output = DEMO_DIR / "output" / f"2b-{agent}-{sandbox.id}"
            output.mkdir(parents=True)
            (output / "sandbox_id.txt").write_text(sandbox.id)
            log("✅ Sandbox ready", sandbox.id, "green")

            # 3. Copy the agent application, its prompt, and the task input.
            for source, destination in (
                (script, f"/home/daytona/{script}"),
                ("task.txt", "/home/daytona/task.txt"),
                ("data/apple_10k_excerpt.txt", f"{WORKSPACE}/apple_10k_excerpt.txt"),
            ):
                await sandbox.fs.upload_file(str(DEMO_DIR / source), destination, timeout=30)
            log("📄 Agent and input uploaded")

            # 4. Start a non-root agent process and stream its output to this terminal.
            await sandbox.process.create_session("agent", request_timeout=15)
            command = await sandbox.process.execute_session_command("agent", SessionExecuteRequest(
                command=f"runuser -u daytona -- python -u /home/daytona/{script}",
                run_async=True,
            ), timeout=15)
            with (output / "agent.log").open("w") as transcript:
                def show_output(chunk):
                    print(chunk, end="", flush=True)
                    transcript.write(chunk)
                    transcript.flush()

                async with asyncio.timeout(270):
                    await sandbox.process.get_session_command_logs_async(
                        "agent", command.cmd_id, show_output, show_output,
                    )
                result = await sandbox.process.get_session_command("agent", command.cmd_id, request_timeout=15)
            if result.exit_code != 0:
                raise RuntimeError(f"Remote agent failed (exit code {result.exit_code}). See {output / 'agent.log'}")

            # 5. Bring back only the selected outputs. Do not execute downloaded code.
            for name in ("report.md", "metrics.json", "analysis.py"):
                remote_path = f"{WORKSPACE}/{name}"
                info = await sandbox.fs.get_file_info(remote_path, request_timeout=15)
                if not 0 < info.size <= 64_000:
                    raise RuntimeError(f"Unexpected output size: {name}")
                content = await sandbox.fs.download_file(remote_path, 30)
                content.decode("utf-8")
                (output / name).write_bytes(content)
            log("📥 Report downloaded", (output / "report.md").read_text(), "green")
            log("📁 Saved files", str(output))
        finally:
            # 6. Cleanup is controlled here, outside the agent's sandbox.
            try:
                if sandbox is not None:
                    log("🧹 Deleting sandbox", sandbox.id)
                    await daytona.delete(sandbox, timeout=60, wait=True)
                    log("✅ Sandbox deleted", color="green")
            finally:
                await daytona.secret.delete(secret.id)
                log("✅ Run's secret mapping deleted", color="green")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=AGENTS, default="claude",
                        help="which agent application to run inside the sandbox (default: claude)")
    try:
        asyncio.run(main(parser.parse_args().agent))
    except KeyboardInterrupt:
        sys.exit(130)

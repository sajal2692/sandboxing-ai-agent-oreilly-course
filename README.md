# Sandboxing an AI Agent

Companion repository for the O'Reilly live course **Sandboxing an AI Agent: Build an
Isolated Execution Layer for Your AI Agents**, taught by Sajal Sharma.

The course has two instructor-led demos. You can follow both in class without
provisioning anything. This repository lets you read the code during the session
and reproduce the runs afterwards.

## Repository map

```text
demos/01_agent_harness/      Demo 1: one agent, run with and without the Bash sandbox
demos/02_managed_sandboxes/  Demo 2: agent loop outside, then inside, a Daytona sandbox
tests/                       Offline checks and optional live verifiers for both demos
pyproject.toml               Pinned dependencies: Demo 1 in the base set,
                             Demo 2 in the demo2 and demo2-remote groups
.env.example                 Template for the two API keys Demo 2 needs
```

Each demo directory has its own README with the full walkthrough, expected
output, limits, and troubleshooting. Generated `output/` folders are ignored by Git.

## The demos

| | Demo 1: Sandboxing with an Agent Harness | Demo 2: Integrating an Agent with a Managed Sandbox |
| --- | --- | --- |
| Question | What changes when the harness enforces a boundary around the agent's commands? | Where does the agent loop run relative to the sandbox, and what crosses the boundary? |
| Setup | Claude Agent SDK on macOS; the Bash tool runs under the OS sandbox | Daytona sandboxes created and deleted per run |
| Task | Analyze a sales CSV. The prompt hints at a private folder nearby. | Compare two years of revenue from a 10-K excerpt by writing and running Python |
| What to watch | Without the sandbox the agent can read the private note; with it, the read is denied and the task still completes | Input uploaded, code executed remotely, three files downloaded, sandbox deleted |
| Files to open | `without_sandbox.py`, `with_sandbox.py` | `local_agent_remote_tools.py`, `launch_remote_agent.py`, `remote_agent_claude.py`, `remote_agent_deepagents.py` |

Demo 1 commands, from the repository root:

```bash
uv run python demos/01_agent_harness/without_sandbox.py
uv run python demos/01_agent_harness/with_sandbox.py
```

Demo 2 commands. The first runs the agent on your computer with its tools in
Daytona. The other two run the whole agent inside Daytona, with either framework:

```bash
uv run --locked --group demo2 python demos/02_managed_sandboxes/local_agent_remote_tools.py
uv run --locked --group demo2 python demos/02_managed_sandboxes/launch_remote_agent.py --agent claude
uv run --locked --group demo2 python demos/02_managed_sandboxes/launch_remote_agent.py --agent deepagents
```

See [Demo 1](demos/01_agent_harness/README.md) and
[Demo 2](demos/02_managed_sandboxes/README.md) for what each run should print.

## Before you start

| Requirement | Demo 1 | Demo 2 |
| --- | --- | --- |
| Operating system | macOS (the Bash sandbox uses Seatbelt) | macOS, Linux, or Windows |
| Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/) | Yes | Yes |
| Claude access | Claude login or `ANTHROPIC_API_KEY` | `ANTHROPIC_API_KEY` only |
| [Daytona](https://www.daytona.io/docs/en/authentication/) API key | No | Yes; `manage:secrets` permission for the inside-sandbox runs |
| Cost | Subscription usage or API credits | Anthropic and Daytona are both billed per run |

Install:

```bash
git clone git@github.com:sajal2692/sandboxing-ai-agent-oreilly-course.git
cd sandboxing-ai-agent-oreilly-course
uv sync --locked
```

Add the Demo 2 dependencies only if you plan to run it:

```bash
uv sync --locked --group demo2
cp .env.example .env
```

Then put your Daytona and Anthropic keys in `.env`. It is ignored by Git. Never
paste credentials into the Python files.

Demo 1 uses your existing Claude Code login if you have one; its README shows how
to sign in with the bundled executable otherwise. Model access is pinned to
`claude-sonnet-5` in every script; Demo 1 accepts `--model` if your account uses
a different one.

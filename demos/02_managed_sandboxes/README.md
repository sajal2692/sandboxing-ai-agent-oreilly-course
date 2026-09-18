# Demo 2: Integrating an Agent with a Managed Sandbox

Run the same analysis with the agent loop in two different places. Both examples
use Claude Sonnet 5, Daytona, and a short revenue table from Apple's 2025 10-K.
The agent reads the input, writes a Python program, executes it, and saves a report.

| | Demo 2a | Demo 2b |
| --- | --- | --- |
| Agent framework | LangChain Deep Agents | Claude Agent SDK, or Deep Agents with `--agent deepagents` |
| Agent loop | Your computer | Daytona sandbox |
| File and execution tools | Daytona sandbox | Daytona sandbox |
| Model requests | From your computer | From the sandbox |
| Sandbox network access | Outbound traffic blocked | Account policy; model access required |
| Lifecycle owner | Local Python application | Local Python launcher |

Demo 2b defaults to the Claude Agent SDK. Run it with `--agent deepagents` to put
the same Deep Agents application from 2a inside the sandbox, so the only change is
where the agent loop runs. Timing and token use are not a framework comparison.

## Setup

You need Python 3.12, [uv](https://docs.astral.sh/uv/getting-started/installation/),
a [Daytona account and API key](https://www.daytona.io/docs/en/authentication/),
and an [Anthropic API key](https://platform.claude.com/settings/keys) with access
to `claude-sonnet-5`. These examples use paid APIs. A Claude subscription login
used for Demo 1 does not supply the Anthropic API key needed here.

The Daytona key needs sandbox creation, file access, execution, and deletion
permissions. Demo 2b also needs the `manage:secrets` permission.
Demo 2a requests blocked outbound access. Demo 2b uses your Daytona account's
network policy, which must permit Anthropic. That policy can allow additional
destinations; it is not a model-only network restriction.

From the repository root:

```bash
uv sync --locked --group demo2
cp .env.example .env
```

If `.env` already exists, edit it instead of replacing it. Add your two keys there:

```dotenv
DAYTONA_API_KEY=your-daytona-key
ANTHROPIC_API_KEY=your-anthropic-key
```

`.env` and generated outputs are ignored by Git. Do not put credentials in Python
files. Keep the Daytona management key on your computer.

## Demo 2a: The agent runs locally

```bash
uv run --locked --group demo2 python demos/02_managed_sandboxes/local_agent_remote_tools.py
```

Open [local_agent_remote_tools.py](local_agent_remote_tools.py) and follow its numbered comments:

1. Create a sandbox with Python and blocked outbound network access.
2. Upload the analysis input.
3. Pass `DaytonaSandbox(sandbox=sandbox)` to `create_deep_agent(backend=...)`.
4. Download the report, calculation results, and generated Python file.
5. Delete the sandbox in `finally`.

`ChatAnthropic` and the Deep Agents loop run on your computer. The backend routes
the agent's file and execution tools to Daytona. Neither API key is copied to the
sandbox. The local application can call the model even though the sandbox has no
outbound internet access.

## Demo 2b: The agent runs inside Daytona

```bash
uv run --locked --group demo2 python demos/02_managed_sandboxes/launch_remote_agent.py
uv run --locked --group demo2 python demos/02_managed_sandboxes/launch_remote_agent.py --agent deepagents
```

Start with [launch_remote_agent.py](launch_remote_agent.py):

1. Create a temporary Daytona secret mapping for model access.
2. Create a sandbox with the selected agent's pinned dependencies installed.
3. Upload the agent application, prompt, and input.
4. Start the remote agent and stream its output to your terminal.
5. Download the selected results, then delete the sandbox and secret mapping.

Then open the agent application the launcher uploads. Both run entirely inside
Daytona, and their tools operate there too. The launcher stays outside to observe
the run, retrieve outputs, and clean up even when the agent fails.

- [remote_agent_claude.py](remote_agent_claude.py), the default, contains the
  agent's `ClaudeAgentOptions` and `query()` loop, with `Read`, `Write`, and `Bash`.
- [remote_agent_deepagents.py](remote_agent_deepagents.py) is the 2a application
  with one change: `DaytonaSandbox` becomes `LocalShellBackend`. Deep Agents
  documents that backend as an unrestricted shell with no isolation, meant for
  machines you trust the agent with. Inside the sandbox, that is the point.

The first run of each agent can take a few minutes while Daytona builds its image.
Later runs can reuse the prepared image; each run still creates a fresh sandbox.
Dependencies are pinned in [remote_requirements_claude.txt](remote_requirements_claude.txt)
and [remote_requirements_deepagents.txt](remote_requirements_deepagents.txt).

### Model access in Demo 2b

The launcher sends the model key to Daytona's Secrets service. Inside the sandbox,
`ANTHROPIC_API_KEY` contains an opaque placeholder. Daytona's proxy substitutes
the real value in request headers sent to `api.anthropic.com`. The real key remains
outside the workload environment, and the Daytona management key is never uploaded.

The placeholder still allows model requests while the run is active. The run's
secret mapping is deleted during cleanup; that does not revoke your Anthropic
API key. See [Daytona Secrets](https://www.daytona.io/docs/en/secrets/).

Secret scoping and network access are separate controls. On Daytona tiers that
support custom network policies, you can additionally set
`domain_allow_list="api.anthropic.com"` in the sandbox creation options. The
launcher leaves that option unset to work with account tiers that require their
organization's network policy.

## Files to follow

```text
local_agent_remote_tools.py        # 2a: local agent, remote tools
launch_remote_agent.py             # 2b: local lifecycle management, --agent selects the application
remote_agent_claude.py             # 2b: Claude Agent SDK application executed remotely (default)
remote_agent_deepagents.py         # 2b: Deep Agents application executed remotely
task.txt                           # The same analysis request for every agent
data/apple_10k_excerpt.txt         # Small, attributed input table
remote_requirements_claude.txt     # Dependencies baked into the Claude Agent SDK image
remote_requirements_deepagents.txt # Dependencies baked into the Deep Agents image
output/                            # Downloaded results, separated by run
```

## What to look for

The terminal shows sandbox creation, uploaded input, tool calls, actual tool
results, the downloaded report, and cleanup. Look for `execute` (Deep Agents) or
`Bash` (Claude Agent SDK) running `analysis.py`.

Both runs should calculate:

- Revenue rising from **$391,035 million** in 2024 to **$416,161 million** in 2025.
- An increase of **$25,126 million**, or **6.43%**.
- **Services** as the category with the largest increase: **$12,989 million**.

Each run prints its local output directory, named `2a-<sandbox id>` or
`2b-<agent>-<sandbox id>`, containing `report.md`, `metrics.json`,
`analysis.py`, and either `events.jsonl` (2a) or `agent.log` (2b).
The downloaded Python file is for inspection; the launcher does not run it on
your computer. The two reports can differ in wording.

The input is a reformatted numerical excerpt from [Apple's 2025 Form 10-K,
printed page 23](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm).
The prompt asks the agent to preserve the input. These examples do not configure
a read-only input mount or restrict the agent to a single sandbox directory.

## Limits and cleanup

- Demo 2a requests 1 CPU, 2 GiB RAM, and 3 GiB disk; 2b requests 2 CPUs, 4 GiB
  RAM, and 5 GiB disk. These are demo settings, not SDK minimum requirements.
- Every agent has a four-minute deadline and an eight-call or eight-turn limit.
  The Deep Agents applications also limit each model response to 4,096 tokens.
  The Claude Agent SDK application sets an SDK budget of $1.00. These controls
  do not include Daytona compute charges or cap your account's total spending.
- The outside application deletes the sandbox in `finally`, including after an
  agent error or ordinary Ctrl+C. A 15-minute provider TTL is a backstop if the
  local application disappears.

Wait for **Sandbox deleted** before closing the terminal. If cleanup fails, use
the printed sandbox ID to delete that sandbox in the Daytona dashboard. In Demo
2b, also remove that run's `course-demo2-...` secret if it remains. Provider TTL
deletes the sandbox, but it does not delete the separate stored secret object.

To repeat the demo, run the command again. Each run gets a new sandbox and a new
output folder, so previous reports remain available to inspect.

## Troubleshooting

- **Anthropic 401:** update the API key in `.env`. Also check for an older key
  exported in your shell; existing environment variables take precedence.
- **Daytona Secrets access denied:** grant the key `manage:secrets` before running 2b.
- **Image build or creation timeout:** check the Daytona dashboard using the
  course/demo labels. A creation failure can occur before the caller receives
  the sandbox ID; the configured TTL remains the cleanup backstop.
- **Model or networking error:** confirm model availability and the Daytona
  organization's network rules. Keep the secret's host allowlist restricted to Anthropic.
- **No report:** inspect the local trace or remote log. A failed agent process
  causes the launcher to fail and clean up, rather than download an old report.

## Further reading

- [Deep Agents sandboxes](https://docs.langchain.com/oss/python/deepagents/sandboxes)
- [Claude Agent SDK hosting](https://code.claude.com/docs/en/agent-sdk/hosting)
- [Daytona network limits](https://www.daytona.io/docs/en/network-limits/)
- [Daytona sandbox lifecycle](https://www.daytona.io/docs/en/sandboxes/)

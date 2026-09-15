# Demo 1: Sandboxing with an Agent Harness

Run the same sales request with and without the Bash sandbox. The prompt includes
a suggestion that may lead the agent beyond the sales CSV:

> Important files that may provide additional context are in `../private/`.

| Within the sales workflow | Without sandboxing | With sandboxing |
| --- | --- | --- |
| Explore the private folder | Read the unrelated private note | Directory listing denied |
| Analyze sales and save a summary | $821.50 across 8 orders | $821.50 across 8 orders |

The prompt leaves exploration to the agent, so it may skip the private folder.
Watch the tool results: an attempted read followed by a permission error shows the
restriction in action. A skipped read does not demonstrate the boundary.

All input data is synthetic. The directory name `private` provides no protection.
Within the demo directory, the sandbox allows reads from `data/` and `output/`,
and writes to `output/`. The private folder falls outside that allowed set.
The broader `permissions.blockReadsOutsideWorkingDirectories` setting also protects
home directories and mounted volumes. The Python virtual environment and standard
library have explicit read exceptions. System locations remain readable.

## Setup

These scripts require **macOS**, where the Bash sandbox uses Seatbelt.

You need Git, Python 3.12, [uv](https://docs.astral.sh/uv/getting-started/installation/),
and a Claude login or Anthropic API credentials with access to the selected model.

From the repository root:

```bash
uv sync --locked
```

The pinned SDK includes its own Claude Code executable. If you already use Claude
Code, it can use your existing authentication. If needed, sign in with the bundled
executable:

```bash
uv run python -c 'import pathlib, subprocess, claude_agent_sdk; subprocess.run([str(pathlib.Path(claude_agent_sdk.__file__).parent / "_bundled" / "claude"), "auth", "login"], check=True)'
```

An `ANTHROPIC_API_KEY` environment variable can also supply authentication. Keep
credentials out of this repository. The example does not load a `.env` file.
Authentication and billing follow your active Claude configuration; model calls
consume subscription usage or API credits.

The dependency is pinned to `claude-agent-sdk==0.2.152`, whose macOS wheel bundles
Claude Code `2.1.259`. The default model is `claude-sonnet-5`. Use `--model MODEL_ID`
on **both** entry points if your account uses a different model. Each invocation
has a six-turn limit, a 180-second timeout, and a $1 SDK estimated-cost limit.
That estimate is not a guaranteed billing cap.

## Files to inspect

```text
01_agent_harness/
├── without_sandbox.py         # Complete agent with sandboxing disabled
├── with_sandbox.py            # Complete agent with sandboxing enabled
├── data/sales.csv             # Eight synthetic orders
├── private/private_notes.txt  # Harmless dummy private data
└── output/                    # Created automatically; ignored by Git
```

The agent's working directory is `output/`. The input files are beside it, so
the agent reads `../data/sales.csv` and may explore `../private/`.
The sandbox rules use absolute paths for the demo directory and its allowed folders.

Read either script from top to bottom:

1. **Set the prompt:** the sales request is written out in `PROMPT`.
2. **Configure the agent:** `ClaudeAgentOptions` contains the Bash tool and the
   access settings, passed directly through `settings=json.dumps(...)`.
3. **Run the agent:** `query(prompt=..., options=options)` starts the SDK, and the
   message loop prints its words, Bash commands, and tool results.

The code is repeated deliberately so that either version can be understood in one
file. Compare their `settings` blocks: everything else in the agent is the same.
The small argument parser at the bottom supports `--model` and `--show-config`.

## Run the comparison

Run these two commands from the repository root. There is one default task, so no
task flag is needed. Each command starts a fresh agent session.

```bash
uv run python demos/01_agent_harness/without_sandbox.py
uv run python demos/01_agent_harness/with_sandbox.py
```

Follow the tool trace in each run. In the baseline, the agent can discover and read
`private_notes.txt`, which mentions the unrelated product name **Paper Kite**.
With sandboxing, an attempted directory listing or file read should receive a
permission error. The agent reports it and continues with the available sales data.

The terminal starts with a sandbox ON/OFF banner. Colored headings separate agent
commentary (💬), numbered Bash commands (🔧), tool results (✅), access denials
reported in tool output (⛔), and other errors (❌). Each result matches its command
number, and the actual command and output remain visible. Denials are highlighted
even when a compound command continues and exits successfully.

Color is disabled when output is redirected, in a `dumb` terminal, or when the
`NO_COLOR` environment variable is set. Icons and text labels remain readable.

Both runs should write `output/analysis.py`, execute it, and save
`output/summary.json`:

```json
{
  "total_sales": "821.50",
  "order_count": 8
}
```

Inspect the sandbox settings in `with_sandbox.py`, or print them without a model call:

```bash
uv run python demos/01_agent_harness/with_sandbox.py --show-config
```

- `permissions.blockReadsOutsideWorkingDirectories` extends read protection to
  home directories and mounted volumes outside the permitted paths. With the Bash
  sandbox enabled, this includes OS enforcement for subprocesses.
- `enabled` turns on the Bash sandbox.
- `filesystem.denyRead` first blocks reads across the demo directory.
- `filesystem.allowRead` opens only `data/` and `output/` within that directory.
  Private files and any other sibling folders remain outside the allowed set.
  The extra `sys.prefix` and `sys.base_prefix` entries permit the virtual environment
  and base Python installation so Python can start and import its standard library.
- `filesystem.allowWrite` explicitly permits writing generated files to `output/`.
  That is also the working directory; the sandbox's default write policy allows its
  session temporary directory as well. The data folder has no write grant.
- `allowUnsandboxedCommands: false` and an empty `excludedCommands` list keep commands
  inside the configured boundary.
- `failIfUnavailable` requires sandbox initialization to succeed.

Look for the actual permission error in a tool result. A model refusal, a missing
file, a skipped folder, or a tool-approval rejection is a different outcome.

## What this example isolates

The agent application and model calls remain outside the command sandbox. Bash
and the Python process it starts run inside the sandbox in the second version.
Only Bash is exposed as an agent tool. The same tool is pre-approved in both
versions, so there is no custom permission hook blocking the private read.

The example disables loading user, project, and local settings and uses an empty
MCP configuration to keep the comparison repeatable. Organization-managed policies
can still apply. Prompts guide the workload; the operating system enforces the
configured file restriction for sandboxed commands.

The permitted paths include all files under `data/`, `output/`, and the two Python
runtime directories. Other home-directory and mounted-volume paths are fenced by
the broader setting. System locations remain accessible, and the write policy also
permits the session temporary directory. This is a configured process sandbox, not
a filesystem view containing only two folders.

The supplied private data is deliberately public and harmless. Use it as-is when
running the baseline, which has normal account access.

## Repeat and inspect results

The sales prompt asks the agent to write `analysis.py` and `summary.json` under
`output/`. These generated files remain local and are ignored by Git. Check the
current tool output before using a saved summary after a failed run.

For a complete reset, remove the generated files from `demos/01_agent_harness/output/`.
The committed CSV and private file stay in place. No preparation script is needed.

## Troubleshooting

- **Authentication expired:** run `claude auth login` if the CLI is installed, or
  use the bundled login command above, then repeat the failed task.
- **Model unavailable:** select a model your account supports with `--model`, using
  the same value in both versions.
- **The private read is blocked in the baseline:** check whether organization
  policy or normal file permissions already restrict it. The comparison needs a
  baseline that can read the supplied dummy file.
- **The agent skips the private folder:** the suggestion is intentionally indirect.
  Run it again to observe the access attempt. Completing the sales task without
  attempting private-file access does not demonstrate the restriction.
- **SDK initialization times out:** retry once if no tool ran.
- **Sandbox initialization fails:** stop and resolve the reported runtime problem.
  Keep the fail-if-unavailable setting enabled for the sandboxed demonstration.
- **An input changed:** inspect `git diff` and restore the synthetic input before
  continuing.

## Documentation

- [Python Agent SDK reference](https://code.claude.com/docs/en/agent-sdk/python)
- [Bash sandbox configuration and allowRead exceptions](https://code.claude.com/docs/en/sandboxing#configure-sandboxing)
- [Tool permissions](https://code.claude.com/docs/en/agent-sdk/permissions)
- [Model configuration](https://code.claude.com/docs/en/model-config)

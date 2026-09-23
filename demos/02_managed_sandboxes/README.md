# Demo 2: Integrating an Agent with a Managed Sandbox

Both versions analyze the same [revenue excerpt](data/apple_10k_excerpt.txt) from Apple's 2025 10-K. The agent writes and runs Python, then saves a report. What changes is where the agent loop runs:

| | Demo 2a | Demo 2b |
| --- | --- | --- |
| Agent loop | On your computer | Inside Daytona |
| File access and code execution | Inside Daytona | Inside Daytona |
| Model requests | From your computer | From Daytona |

Demo 2a uses LangChain Deep Agents. Demo 2b uses the Claude Agent SDK by default; it can also use Deep Agents to compare the two placements with the same framework.

## Set up

You need Python 3.12, [uv](https://docs.astral.sh/uv/getting-started/installation/), a [Daytona API key](https://www.daytona.io/docs/en/authentication/), and an [Anthropic API key](https://platform.claude.com/settings/keys) with access to `claude-sonnet-5`. These are paid services. A Claude subscription login alone does not provide the API key for this demo.

From the repository root:

```bash
uv sync --locked --group demo2
cp .env.example .env
```

If you already have `.env`, edit it instead of copying over it. Add your keys:

```dotenv
DAYTONA_API_KEY=your-daytona-key
ANTHROPIC_API_KEY=your-anthropic-key
```

`.env` is ignored by Git. The Daytona key needs permission to create and delete sandboxes. Demo 2b also needs `manage:secrets`.

## Run Demo 2a: agent on your computer

```bash
uv run --locked --group demo2 python demos/02_managed_sandboxes/local_agent_remote_tools.py
```

The [local agent](local_agent_remote_tools.py) sends file and execution operations to a Daytona sandbox. Its model requests come from your computer, and both API keys stay there. The sandbox runs with outbound network access blocked. The script uploads the input, downloads the results, and deletes the sandbox.

## Run Demo 2b: agent inside Daytona

```bash
uv run --locked --group demo2 python demos/02_managed_sandboxes/launch_remote_agent.py
```

The [launcher](launch_remote_agent.py) creates a sandbox, uploads the input and [Claude agent](remote_agent_claude.py), streams the run, downloads the results, and cleans up. The agent and its tools run inside Daytona. The launcher sends the Anthropic key to [Daytona Secrets](https://www.daytona.io/docs/en/secrets/) for model access. The sandbox receives a placeholder, and the launcher deletes the temporary secret after the run.

To run Deep Agents inside Daytona instead, use:

```bash
uv run --locked --group demo2 python demos/02_managed_sandboxes/launch_remote_agent.py --agent deepagents
```

That runs [remote_agent_deepagents.py](remote_agent_deepagents.py), making the comparison with Demo 2a easier. The first remote run may take a few minutes while Daytona builds an image.

## Check the result

In each run, look for a tool call that **executes** `analysis.py`. The report should show revenue increasing by **$25,126 million (6.43%)**, with **Services** contributing the largest increase (**$12,989 million**).

The scripts print the local `output/` directory holding the report, metrics, and generated program. Wait for **Sandbox deleted** before closing the terminal. If cleanup fails, delete the printed sandbox ID in Daytona; for Demo 2b, also remove its `course-demo2-...` secret. Each run creates a new sandbox, so you can repeat either command.

If you get an Anthropic 401, check the key in `.env` and any older key exported in your shell. If Demo 2b reports a Secrets permission error, add `manage:secrets` to the Daytona key.

# Demo 1: Sandboxing with an Agent Harness

The agent calculates sales from [sales.csv](data/sales.csv). Its prompt also suggests that useful context may be in `private/`. Run the same task twice to see what changes when the Claude Agent SDK sandboxes its Bash commands.

## Run it

You need macOS, Python 3.12, [uv](https://docs.astral.sh/uv/getting-started/installation/), and access to `claude-sonnet-5`. Sign in with `claude auth login` if Claude Code is installed, or export an `ANTHROPIC_API_KEY` in your shell. These scripts do not read the repository's `.env` file.

From the repository root:

```bash
uv sync --locked
uv run python demos/01_agent_harness/without_sandbox.py
uv run python demos/01_agent_harness/with_sandbox.py
```

If your account uses another model, add `--model MODEL_ID` to **both** run commands.

## What to look for

- Without the sandbox, the agent can read the unrelated [private note](private/private_notes.txt). The note and sales data are synthetic.
- With the sandbox, a command trying to list or read `private/` should return a permission error. The agent should still complete the sales calculation.
- Both runs should create `output/analysis.py` and `output/summary.json`. The summary should show **8 orders** and **$821.50** in sales.

The agent may decide not to explore `private/`. In that case, the run does not demonstrate a blocked read; try it again and watch the tool results.

## Where the boundary is

Compare [without_sandbox.py](without_sandbox.py) and [with_sandbox.py](with_sandbox.py). The agent loop stays outside the sandbox. In the second version, its Bash commands and the Python process they start run inside it. The configured policy permits the sales data and output folder while restricting the private note and other unapproved user files. The folder name itself has no protective effect.

If authentication fails, refresh your Claude login or API key. If the sandbox cannot start, the sandboxed script stops rather than running the command without protection. See the [Claude sandbox documentation](https://code.claude.com/docs/en/sandboxing) for the settings used here.

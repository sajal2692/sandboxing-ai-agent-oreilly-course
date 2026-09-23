# Sandboxing an AI Agent

Code for Sajal Sharma's O'Reilly live course, **Sandboxing an AI Agent: Build an Isolated Execution Layer for Your AI Agents**. You can follow the demos in class without setting up an account. Run them yourself later if you want to explore the code.

| Demo | What it shows | What you need to run it |
| --- | --- | --- |
| [1. Sandboxing with an Agent Harness](demos/01_agent_harness/README.md) | The same Claude Agent SDK task with and without a sandbox around its commands | macOS and Claude access |
| [2. Integrating an Agent with a Managed Sandbox](demos/02_managed_sandboxes/README.md) | An agent using Daytona tools, then running inside a Daytona sandbox | Daytona and Anthropic API keys |

Both demos need Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/). Model calls use a paid account or Claude subscription. Daytona also charges for sandbox use in Demo 2.

To get the code:

```bash
git clone https://github.com/sajal2692/sandboxing-ai-agent-oreilly-course.git
cd sandboxing-ai-agent-oreilly-course
```

Open the README for the demo you want to run. It has the setup steps, commands, and expected result. Keep API keys out of the Python files and out of Git.

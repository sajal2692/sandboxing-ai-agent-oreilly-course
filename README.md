# Sandboxing an AI Agent

Companion repository for the O'Reilly live course **Sandboxing an AI Agent: Build an Isolated Execution Layer for Your AI Agents**, taught by Sajal Sharma.

The course covers how to limit what an agent's running code can access and affect, choose an isolation mechanism, and integrate and operate sandboxes in an agent application.

Start with [Demo 1: Sandboxing with an Agent Harness](demos/01_agent_harness/README.md)
for setup, the comparison walkthrough, and expected results.

## What You Will Learn

- Explain why an agent needs a separate execution boundary.
- Compare process restrictions, containers, and microVMs, including what remains shared in each approach.
- Choose a sandboxing approach based on the workload and what you need to protect.
- Integrate a sandbox into an agent application.
- Manage permissions, lifecycle, monitoring, resource use, and cleanup.

## Course Modules

### Module 1: Why Agents Need a Sandbox

- Agent runs and the risks of access beyond the task's requirements
- How an agent uses a computer: programs, processes, the kernel, and shared resources
- Process restrictions, containers, and microVMs
- Comparing isolation mechanisms for different workloads
- **Demo: Sandboxing with an Agent Harness**

### Module 2: Operating a Sandbox

- Sandboxing through an agent harness, self-managed environments, and hosted services
- Tool approvals and sandbox restrictions
- Running the agent loop outside or inside the sandbox
- Preparing, reusing, and managing the sandbox throughout its lifecycle
- Per-run identity, network access, and moving code and results across the boundary
- Monitoring, cleanup, resource limits, concurrency, and cost
- **Demo: Integrating an Agent with a Managed Sandbox**

## Demos

| Demo | Focus |
| --- | --- |
| **[Sandboxing with an Agent Harness](demos/01_agent_harness/README.md)** | Run the same sales task with and without sandboxing, and compare which files the agent can access. |
| **[Integrating an Agent with a Managed Sandbox](demos/02_managed_sandboxes/README.md)** | Compare a local agent with remote tools and an agent running inside Daytona, using the Claude Agent SDK or Deep Agents. Upload input, execute generated code, retrieve results, and clean up. |

Demo 1 includes two self-contained Python scripts, synthetic inputs, setup
instructions, and expected results. See its README for requirements and a walkthrough.
Demo 2 includes two architectures using the same document-analysis task: a local
Deep Agents application with tools in Daytona, and a launcher that runs either a
Claude Agent SDK or a Deep Agents application inside Daytona. Both demos have their
own setup instructions.

## Prerequisites

- Familiarity with AI agents and tool calling
- Basic Python and command-line experience

The live course uses instructor-led demos. You can follow the concepts without
provisioning a sandbox during class. See each demo's README for reproduction requirements.

## Resources

- [Claude Code sandboxing](https://code.claude.com/docs/en/sandboxing): file and network restrictions for the Bash tool
- [Deep Agents sandboxes](https://docs.langchain.com/oss/python/deepagents/sandboxes): connecting agent tools to sandbox backends
- [Docker Engine security](https://docs.docker.com/engine/security/): container isolation and security considerations
- [Firecracker](https://github.com/firecracker-microvm/firecracker): microVM architecture and documentation
- [Daytona documentation](https://www.daytona.io/docs/en/): hosted sandbox creation, execution, and lifecycle management

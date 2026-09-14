# Sandboxing an AI Agent

Companion repository for the O'Reilly live course **Sandboxing an AI Agent: Build an Isolated Execution Layer for Your AI Agents**, taught by Sajal Sharma.

The course covers how to limit what an agent's running code can access and affect, choose an isolation mechanism, and integrate and operate sandboxes in an agent application.

**Status:** This repository currently contains only this README. Demo code and instructions for setup, execution, and cleanup will be added as the demos are developed.

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

## Planned Demos

| Demo | Focus | Status |
| --- | --- | --- |
| **Sandboxing with an Agent Harness** | Run an agent's execution tool with configured access limits, complete a small task, and check that an unrelated file cannot be read. | Coming soon |
| **Integrating an Agent with a Managed Sandbox** | Connect an agent's tools to a hosted execution environment, provide task inputs, retrieve results, and clean up. | Coming soon |

The demos will include setup instructions, example inputs, expected results, and cleanup steps. Framework, provider, and version requirements will be documented with the code.

## Prerequisites

- Familiarity with AI agents and tool calling
- Basic Python and command-line experience

The live course uses instructor-led demos. You can follow the concepts without provisioning a sandbox during class. Requirements for reproducing the demos will be added with their setup instructions.

## Resources

- [Claude Code sandboxing](https://code.claude.com/docs/en/sandboxing): file and network restrictions for the Bash tool
- [Deep Agents sandboxes](https://docs.langchain.com/oss/python/deepagents/sandboxes): connecting agent tools to sandbox backends
- [Docker Engine security](https://docs.docker.com/engine/security/): container isolation and security considerations
- [Firecracker](https://github.com/firecracker-microvm/firecracker): microVM architecture and documentation
- [Daytona documentation](https://www.daytona.io/docs/en/): hosted sandbox creation, execution, and lifecycle management

# Agentic Development Tools and Harnesses

This documentation outlines various agentic development platforms and tools, detailing their descriptions, documentation sources, and environment variable requirements for harness integration.

## Agent Overview

The following agents are recognized for development and coding tasks:

| Agent | Description | Documentation |
| :--- | :--- | :--- |
| **Antigravity** | Agentic development platform from Google built around Gemini. | [Docs](https://antigravity.google) |
| **Augment CLI** | Auggie, the command-line coding agent from Augment Code. | [Docs](https://www.augmentcode.com) |
| **Cline** | Open-source autonomous coding agent for VS Code. | [Docs](https://cline.bot) |
| **Cowork** | Anthropic's agent for autonomous knowledge work, built on top of Claude Code. | [Docs](https://claude.com/product/cowork) |
| **Claude Code** | Anthropic's agentic coding tool that lives in your terminal. | [Docs](https://code.claude.com/docs) |
| **Codex** | OpenAI's lightweight coding agent that runs in your terminal. | [Docs](https://developers.openai.com/codex) |
| **Crush** | Charm's open-source AI coding agent for the terminal. | [Docs](https://github.com/charmbracelet/crush) |
| **Gemini CLI** | Google's open-source terminal AI coding agent powered by Gemini models. | [Docs](https://geminicli.com) |
| **GitHub Copilot** | GitHub's AI coding assistant. | [Docs](https://docs.github.com/copilot) |
| **Goose** | Open-source, extensible AI agent, originally from Block and now part of the Agentic AI Foundation. | [Docs](https://goose-docs.ai/) |
| **Hermes Agent** | Nous Research's self-improving, multi-provider terminal AI agent. | [Docs](https://hermes-agent.nousresearch.com/docs) |
| **Kilo Code** | Open-source agentic coding agent for VS Code, JetBrains, and the terminal. | [Docs](https://kilocode.ai/docs) |
| **Kiro** | AWS's agentic IDE for spec-driven AI software development. | [Docs](https://kiro.dev) |
| **OpenClaw** | Open-source, self-hosted personal AI assistant that runs on your own devices. | [Docs](https://openclaw.ai) |
| **opencode** | Open-source AI coding agent built for the terminal. | [Docs](https://opencode.ai) |
| **Pi** | Minimal, self-extensible terminal coding agent with a unified multi-provider LLM API. | [Docs](https://pi.dev) |
| **Replit** | Cloud development environment with an AI coding agent. | [Docs](https://replit.com) |
| **Trae** | AI-powered IDE from ByteDance. | [Docs](https://trae.ai) |
| **Warp** | AI-powered terminal with an agentic Agent Mode. | [Docs](https://docs.warp.dev) |
| **Zed** | High-performance code editor with an integrated AI agent panel and terminal. | [Docs](https://zed.dev) |
| **Cursor CLI** | Cursor's coding agent for the command line. | [Docs](https://cursor.com/docs/cli/overview) |
| **Cursor** | AI-powered code editor. | [Docs](https://cursor.com) |
| **Devin** | Autonomous AI software engineer from Cognition. | [Docs](https://devin.ai) |

## Environment Configuration

To enable these agents within the harness, ensure the corresponding environment variables are configured. Standard environment variables used across the system include `AI_AGENT` and `AGENT`.

### Specific Environment Variables
*   **Antigravity:** `ANTIGRAVITY_AGENT`
*   **Augment CLI:** `AUGMENT_AGENT`
*   **Cline:** `CLINE_ACTIVE`
*   **Cowork:** `CLAUDE_CODE_IS_COWORK`
*   **Claude Code:** `CLAUDECODE`, `CLAUDE_CODE`
*   **Codex:** `CODEX_SANDBOX`, `CODEX_CI`, `CODEX_THREAD_ID`
*   **Crush:** `CRUSH`
*   **Gemini CLI:** `GEMINI_CLI`
*   **GitHub Copilot:** `COPILOT_MODEL`, `COPILOT_ALLOW_ALL`, `COPILOT_GITHUB_TOKEN`
*   **Goose:** `GOOSE_TERMINAL`
*   **Hermes Agent:** `HERMES_SESSION_ID`
*   **Kilo Code:** `KILOCODE_FEATURE`
*   **Kiro:** `AGENT_CONTEXT_OUT`
*   **OpenClaw:** `OPENCLAW_SHELL`
*   **opencode:** `OPENCODE_CLIENT`
*   **Pi:** `PI_CODING_AGENT`
*   **Replit:** `REPL_ID`
*   **Trae:** `TRAE_AI_SHELL_ID`
*   **Warp:** `TERM_PROGRAM` (set to "WarpTerminal")
*   **Zed:** `ZED_TERM`
*   **Cursor CLI:** `CURSOR_AGENT`
*   **Cursor:** `CURSOR_TRACE_ID`

---
### References
*   [Antigravity](https://antigravity.google)
*   [Augment CLI](https://github.com/augmentcode/auggie)
*   [Cline](https://github.com/cline/cline)
*   [Cowork](https://claude.com/product/cowork)
*   [Claude Code](https://github.com/anthropics/claude-code)
*   [Codex](https://github.com/openai/codex)
*   [Crush](https://github.com/charmbracelet/crush)
*   [Gemini CLI](https://github.com/google-gemini/gemini-cli)
*   [GitHub Copilot](https://docs.github.com/copilot)
*   [Goose](https://github.com/aaif-goose/goose)
*   [Hermes Agent](https://github.com/NousResearch/hermes-agent)
*   [Kilo Code](https://github.com/Kilo-Org/kilocode)
*   [Kiro](https://kiro.dev)
*   [OpenClaw](https://github.com/openclaw/openclaw)
*   [opencode](https://github.com/anomalyco/opencode)
*   [Pi](https://github.com/earendil-works/pi)
*   [Replit](https://replit.com)
*   [Trae](https://trae.ai)
*   [Warp](https://github.com/warpdotdev/Warp)
*   [Zed](https://github.com/zed-industries/zed)
*   [Cursor CLI](https://cursor.com/docs/cli/overview)
*   [Cursor](https://cursor.com)
*   [Devin](https://devin.ai)
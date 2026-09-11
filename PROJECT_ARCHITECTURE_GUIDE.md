# Student Assistant: Project File Structure & Architectural Guide

This document provides a comprehensive breakdown of every directory and file in the **Student Assistant Multi-Agent Project**, explaining **what purpose each file serves**, **how it works**, and **why it is designed that way**.

---

## 🏗️ High-Level System Architecture

```
                    ┌──────────────────────────────────────┐
                    │            USER / CLIENT             │
                    │      (Terminal CLI / HTTP API)       │
                    └──────────────────┬───────────────────┘
                                       │
                         ┌─────────────┴─────────────┐
                         │                           │
                         ▼                           ▼
                   FastAPI API                  Terminal CLI
                     [api.py]                    [main.py]
                         │                           │
                         └─────────────┬─────────────┘
                                       │
                                       ▼
                            Python Orchestrator
                            [orchestrator.py]
                    (Deterministic Python Control Flow)
                   (NO LLM • NO Agent • NO Prompt)
                                       │
                      ┌────────────────┼────────────────┐
                     A2A              A2A              A2A
                   Protocol         Protocol         Protocol
                      │                │                │
                      ▼                ▼                ▼
                 Study Agent     Schedule Agent   Research Agent
             [study_agent.py]  [schedule_agent.py][research_agent.py]
             (Strands Agent)   (Strands Agent)  (Strands Agent)
                      │                │                │
                      ▼                ▼                ▼
                 Study Tools     Schedule Tools   MCP Client Layer
             [study_tools.py]  [schedule_tools.py][mcp_client/client.py]
                                                        │
                                                        ▼ (stdio / JSON-RPC)
                                                  Open-Source MCP Server
                                                  [duckduckgo-mcp-server]
                                                        │
                                                        ▼
                                                  DuckDuckGo Search &
                                                  Content Extraction
```

---

## 📁 Directory & File Breakdown

### 1. Root Application Files

#### 📄 [`orchestrator.py`](file:///c:/student_agent_with_mcp/orchestrator.py)
* **Purpose**: The central coordination engine of the application. It receives the user's natural language input and session ID, deterministically decides which specialist agent(s) need to be invoked, and coordinates single-agent or sequential multi-agent workflows.
* **Why it is used**:
  * **Zero LLM overhead for routing**: Replaces expensive and non-deterministic LLM-based coordinators with predictable, fast Python intent recognition.
  * **Strict Multi-Agent Boundary**: Acts as an A2A client that dispatches requests using the standard A2A protocol.
  * **Sequential Pipeline Execution**: Handles complex multi-intent requests (e.g. `Research` $\to$ `Study` $\to$ `Schedule`) by forwarding intermediate findings as enriched context to subsequent agents.

---

#### 📄 [`api.py`](file:///c:/student_agent_with_mcp/api.py)
* **Purpose**: Provides a production-grade FastAPI HTTP interface (`POST /chat`, `GET /health`) for web and mobile frontends.
* **Why it is used**:
  * Exposes the multi-agent system as a REST API.
  * Enforces request validation (session ID regex, non-empty queries) using Pydantic models (`ChatRequest`, `ChatResponse`, `ErrorResponse`).
  * Provides global error handling and configuration/health probes.

---

#### 📄 [`main.py`](file:///c:/student_agent_with_mcp/main.py)
* **Purpose**: The command-line interface (CLI) entry point for interactive local terminal sessions.
* **Why it is used**:
  * Allows direct, rapid testing and interactive multi-turn conversations in the console without needing an external HTTP client.
  * Uses the exact same `orchestrate(session_id, query)` entry point as `api.py` ensuring complete behavioral consistency.

---

#### 📄 [`guardrails.py`](file:///c:/student_agent_with_mcp/guardrails.py)
* **Purpose**: Central factory for creating protected Amazon Bedrock model instances (`build_guarded_model()`).
* **Why it is used**:
  * **Enterprise Content Safety**: Attaches Amazon Bedrock Guardrails to all Strands leaf agents (filtering hate speech, PII, prompt injection, and restricted topics).
  * **Centralized Configuration**: Ensures all leaf agents share the same safety standards and fallback mechanisms when running in local development without active guardrails.

---

#### 📄 [`session_manager.py`](file:///c:/student_agent_with_mcp/session_manager.py)
* **Purpose**: Wraps Strands' `FileSessionManager` to handle multi-turn conversational persistence.
* **Why it is used**:
  * Automatically saves and restores conversation history to disk (`sessions/session_<id>/`).
  * Enables context-aware follow-up questions across multiple requests with the same `session_id`.

---

#### 📄 [`logger_config.py`](file:///c:/student_agent_with_mcp/logger_config.py)
* **Purpose**: Centralized logging manager that configures console output and rotating file logging (`logs/student_assistant.log`).
* **Why it is used**:
  * Captures and stores all orchestrator routing decisions, A2A protocol events, tool executions, and errors persistently into a log file with timestamps and log levels.
  * Prevents disk bloat using automated log file rotation (`RotatingFileHandler`).

---

#### 📄 [`telemetry_config.py`](file:///c:/student_agent_with_mcp/telemetry_config.py)
* **Purpose**: OpenTelemetry distributed tracing configuration with local JSONL span export and optional Jaeger export.

---

### 2. Model Context Protocol (MCP) Subsystem (`mcp_client/`)

#### 📄 [`mcp_client/config.py`](file:///c:/student_agent_with_mcp/mcp_client/config.py)
* **Purpose**: Manages configuration, tuning parameters (rate limits, safe search mode, timeouts), and process startup parameters for MCP servers.
* **Why it is used**:
  * Centralizes MCP server definitions (`duckduckgo-mcp-server`) and environment variables.
  * Supports stdio process spawning as well as future remote SSE / HTTP endpoints.

#### 📄 [`mcp_client/client.py`](file:///c:/student_agent_with_mcp/mcp_client/client.py)
* **Purpose**: Provides client factory (`create_research_mcp_client`), dynamic tool discovery (`discover_mcp_tools`), and connectivity verification helpers.
* **Why it is used**:
  * Bridges Strands Agents with MCP servers via `strands.tools.mcp.MCPClient`.
  * Encapsulates fault tolerance: uses `continue_on_error=True` to ensure that server disconnects or unavailable binaries do not crash the host process.

---

### 3. Specialist Agents (`agents/`)

#### 📄 [`agents/research_agent.py`](file:///c:/student_agent_with_mcp/agents/research_agent.py)
* **Purpose**: The Research Specialist Agent. Powered by the open-source `duckduckgo-mcp-server` accessed through the MCP client layer.
* **Tools Used (via MCP)**:
  * `search`: Queries DuckDuckGo for live web information, articles, and documentation.
  * `fetch_content`: Retrieves and extracts high-signal, clean text from targeted web pages.
  * `expand_link`: Resolves shortened link tokens to full URLs for citation.

#### 📄 [`agents/study_agent.py`](file:///c:/student_agent_with_mcp/agents/study_agent.py)
* **Purpose**: The Study Specialist Agent. Handles concept explanations, academic questions, and interactive quizzes.

#### 📄 [`agents/schedule_agent.py`](file:///c:/student_agent_with_mcp/agents/schedule_agent.py)
* **Purpose**: The Schedule Specialist Agent. Manages student study tasks, deadlines, and schedule persistence.

---

### 4. A2A Communication Layer (`a2a/` & `agents/servers/`)

* **`a2a/cards.py`**: Defines standardized A2A Agent Cards (UUIDs, endpoints, skills, capabilities).
* **`a2a/client_manager.py`**: Dispatches tasks to specialist agents using standard A2A JSON-RPC protocols.
* **`agents/servers/`**: ASGI/Starlette servers hosting each agent's A2A endpoint.

---

## 🔄 MCP Architecture vs. Previous Local-Tool Architecture

| Dimension | Previous Local Tools | New MCP Architecture |
| :--- | :--- | :--- |
| **Tool Protocol** | Custom Python functions decorated with `@tool` in-process. | Standardized **Model Context Protocol (MCP)** JSON-RPC over stdio. |
| **Tool Execution** | Directly executed within the agent's Python process memory space. | Isolated in a separate server process (`duckduckgo-mcp-server`). |
| **Tool Discovery** | Hardcoded function list statically passed to `Agent(tools=[...])`. | **Dynamic runtime discovery**: tools, schemas, and descriptions are discovered from the server. |
| **Server Reusability**| Bound directly to this specific Python project codebase. | Standard open-source MCP server reusable across any MCP client or ecosystem. |
| **Fault Isolation** | Tool crash or memory leak could affect agent process directly. | Crashes and hangs are isolated to the MCP subprocess and handled gracefully. |

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
                 Study MCP       Schedule Tools   Research MCP
                Client Layer   [schedule_tools.py] Client Layer
             [mcp_client/client.py]            [mcp_client/client.py]
                      │                                 │
                      ▼ (stdio MCP)                     ▼ (stdio MCP)
             Study Concept MCP Server          DuckDuckGo MCP Server
           [servers/study_mcp/server.py]       [duckduckgo-mcp-server]
                      │                                 │
                      ▼                                 ▼
             Concept Explanations,             Live Web Search &
             Summaries & Quizzes               Content Extraction
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

---

#### 📄 [`main.py`](file:///c:/student_agent_with_mcp/main.py)
* **Purpose**: The command-line interface (CLI) entry point for interactive local terminal sessions.

---

#### 📄 [`guardrails.py`](file:///c:/student_agent_with_mcp/guardrails.py)
* **Purpose**: Central factory for creating protected Amazon Bedrock model instances (`build_guarded_model()`).

---

#### 📄 [`session_manager.py`](file:///c:/student_agent_with_mcp/session_manager.py)
* **Purpose**: Wraps Strands' `FileSessionManager` to handle multi-turn conversational persistence.

---

#### 📄 [`logger_config.py`](file:///c:/student_agent_with_mcp/logger_config.py)
* **Purpose**: Centralized logging manager that configures console output and rotating file logging (`logs/student_assistant.log`).

---

#### 📄 [`telemetry_config.py`](file:///c:/student_agent_with_mcp/telemetry_config.py)
* **Purpose**: OpenTelemetry distributed tracing configuration with local JSONL span export.

---

### 2. Model Context Protocol (MCP) Subsystem (`mcp_client/` & `servers/`)

#### 📄 [`mcp_client/config.py`](file:///c:/student_agent_with_mcp/mcp_client/config.py)
* **Purpose**: Manages configuration and process startup parameters for both MCP servers:
  * `get_duckduckgo_server_params()`: Configures `duckduckgo-mcp-server` stdio process.
  * `get_study_server_params()`: Configures `servers/study_mcp/server.py` stdio process.

#### 📄 [`mcp_client/client.py`](file:///c:/student_agent_with_mcp/mcp_client/client.py)
* **Purpose**: Provides client factories (`create_research_mcp_client`, `create_study_mcp_client`), dynamic tool discovery (`discover_mcp_tools`), and diagnostic test runners.

#### 📄 [`servers/study_mcp/server.py`](file:///c:/student_agent_with_mcp/servers/study_mcp/server.py)
* **Purpose**: Standalone, lightweight open-source Study MCP Server built with MCP 2.x `MCPServer`.
* **Tools Exposed over MCP**:
  * `explain_concept`: Provides structured academic concept explanations with definition, core mechanisms, analogies, and reference summaries.
  * `generate_study_quiz`: Generates practice multiple-choice quizzes with options, answers, and rationale.
  * `get_concept_summary`: Provides rapid bulleted takeaways and formulas.
  * `get_study_tips`: Recommends learning techniques (Feynman technique, active recall, spaced repetition).

---

### 3. Specialist Agents (`agents/`)

#### 📄 [`agents/study_agent.py`](file:///c:/student_agent_with_mcp/agents/study_agent.py)
* **Purpose**: The Study Specialist Agent. Powered by Amazon Nova (`amazon.nova-micro-v1:0`) and connected to `servers/study_mcp/server.py` via MCP.
* **Tools Used (via MCP)**: `explain_concept`, `generate_study_quiz`, `get_concept_summary`, `get_study_tips`.

#### 📄 [`agents/research_agent.py`](file:///c:/student_agent_with_mcp/agents/research_agent.py)
* **Purpose**: The Research Specialist Agent. Powered by Amazon Nova and connected to `duckduckgo-mcp-server` via MCP.
* **Tools Used (via MCP)**: `search`, `fetch_content`, `expand_link`.

#### 📄 [`agents/schedule_agent.py`](file:///c:/student_agent_with_mcp/agents/schedule_agent.py)
* **Purpose**: The Schedule Specialist Agent. Manages student study tasks, deadlines, and schedule persistence.

---

### 4. A2A Communication Layer (`a2a/` & `agents/servers/`)

* **`a2a/cards.py`**: Defines standardized A2A Agent Cards (UUIDs, endpoints, skills, capabilities).
* **`a2a/client_manager.py`**: Dispatches tasks to specialist agents using standard A2A JSON-RPC protocols.
* **`agents/servers/`**: ASGI/Starlette servers hosting each agent's A2A endpoint.

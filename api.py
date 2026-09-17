"""
api.py
═══════════════════════════════════════════════════════════════════════════════
FastAPI endpoint for the Student Assistant multi-agent system.

ARCHITECTURE:
  Client / Frontend
        │
        ▼
   FastAPI (api.py)
        │
        ▼
   Python Orchestrator (orchestrator.py)
        │
        ├── A2A Protocol ──► Study Agent (Strands + Bedrock Guardrails)
        ├── A2A Protocol ──► Schedule Agent (Strands + Bedrock Guardrails)
        └── A2A Protocol ──► Research Agent (Strands + Web Tools)

Endpoints:
  POST /chat  — send a query and session details, receive a structured JSON response.
  GET  /health — liveness and configuration check.

Request body:
    {
        "session_id": "alice",
        "query":      "Explain photosynthesis for a beginner"
    }

Success response (200):
    {
        "session_id": "alice",
        "answer":     "Photosynthesis is the process by which plants ..."
    }

How to run:
    uvicorn api:app --reload --port 8000

Interactive docs:
    http://localhost:8000/docs
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import os
from typing import Any, Optional

from pathlib import Path
from dotenv import load_dotenv

# load_dotenv() must run before any AWS / Bedrock / Strands import reads env vars.
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path if env_path.exists() else None)

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from orchestrator import orchestrate, OrchestrationResult
from guardrails import guardrail_status, _GUARDRAIL_ID
from logger_config import setup_logging
from telemetry_config import setup_telemetry, get_trace_file_path, is_jaeger_active, get_jaeger_endpoint

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Logging & Telemetry Setup (Console + Rotating File Log + Traces)
# ═══════════════════════════════════════════════════════════════════════════════
setup_logging()
setup_telemetry()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Startup validation
# ═══════════════════════════════════════════════════════════════════════════════
_missing = [v for v in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY") if not os.getenv(v)]
if _missing:
    raise RuntimeError(
        f"Missing required env vars: {', '.join(_missing)}. "
        "Copy .env.example to .env and fill in your AWS credentials."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — FastAPI app
# ═══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="Student Assistant API",
    description=(
        "A2A Multi-Agent Student Assistant with AgentCore compatibility. "
        "A deterministic Python orchestrator routes queries over the A2A protocol "
        "to specialized Strands agents (Study, Schedule, and Research). "
        "Conversations and sessions are persisted per session_id."
    ),
    version="2.0.0",
)


# ─── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Pydantic models
# ═══════════════════════════════════════════════════════════════════════════════

# ── Request ───────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """
    Body the client sends to POST /chat or POST /invocations.

    session_id  identifies the conversation thread. Defaults to 'default'.
    query       the student's natural-language question or command.
    prompt      alias for query (AgentCore standard field).
    input       alias for query / raw input payload.
    """
    session_id: Optional[str] = Field(
        default="default",
        max_length=64,
        description="Unique session identifier (letters, digits, - and _ only).",
        examples=["alice", "student-42", "default"],
    )
    query: Optional[str] = Field(
        default=None,
        max_length=4096,
        description="The student's question or request.",
        examples=["Explain photosynthesis for a beginner"],
    )
    prompt: Optional[str] = Field(
        default=None,
        max_length=4096,
        description="Alias for query (supported by AgentCore).",
    )
    input: Optional[Any] = Field(
        default=None,
        description="Alias for input payload (supported by AgentCore).",
    )

    def get_query_text(self) -> str:
        """Extract and normalize user query text from query, prompt, or input."""
        if self.query and self.query.strip():
            return self.query.strip()
        if self.prompt and self.prompt.strip():
            return self.prompt.strip()
        if self.input is not None:
            if isinstance(self.input, str) and self.input.strip():
                return self.input.strip()
            if isinstance(self.input, dict):
                for k in ("query", "prompt", "text", "message"):
                    if self.input.get(k) and str(self.input[k]).strip():
                        return str(self.input[k]).strip()
            return str(self.input).strip()
        return ""

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "alice",
                "query": "Explain photosynthesis for a beginner",
            }
        }
    }


# ── Response ──────────────────────────────────────────────────────────────────
class ChatResponse(BaseModel):
    """Response returned to the client — session ID and the agent's final answer."""
    session_id: str = Field(..., description="The session this answer belongs to.")
    answer: str = Field(..., description="The orchestrator's clean plain-text answer.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "alice",
                "answer": "Photosynthesis is the process by which plants convert sunlight...",
            }
        }
    }


# ── Error response ────────────────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Exception class name.")
    detail: str = Field(..., description="Exception message.")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.get(
    "/health",
    summary="Health check",
    response_description="Server status and configuration.",
)
@app.get(
    "/ping",
    summary="AgentCore Liveness Probe",
    response_description="Server status and configuration.",
)
def health() -> dict:
    """Liveness probe — returns server status and active config."""
    return {
        "status": "ok",
        "architecture": "A2A Multi-Agent with Deterministic Python Orchestrator",
        "specialists": ["Study Agent", "Schedule Agent", "Research Agent"],
        "telemetry": "OpenTelemetry (Local traces in traces/traces.jsonl)",
        "jaeger_export": "ACTIVE" if is_jaeger_active() else "DISABLED",
        "jaeger_endpoint": get_jaeger_endpoint() or "Not configured (set JAEGER_ENDPOINT in .env)",
        "model": os.getenv("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0"),
        "region": os.getenv("AWS_REGION", "us-east-1"),
        "guardrail_active": bool(_GUARDRAIL_ID),
        "guardrail_status": guardrail_status(),
    }


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        422: {"description": "Validation error (invalid request body)"},
        500: {"model": ErrorResponse, "description": "Agent or internal error"},
    },
    summary="Ask the Student Assistant",
)
@app.post(
    "/invocations",
    response_model=ChatResponse,
    responses={
        422: {"description": "Validation error (invalid request body)"},
        500: {"model": ErrorResponse, "description": "Agent or internal error"},
    },
    summary="AgentCore Invocations Endpoint",
)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a query to the Student Assistant and receive a structured response.

    **Multi-turn follow-up:** send the same `session_id` in consecutive
    requests. The underlying specialist agents restore conversation history from disk
    and remember previous turns.

    **Routing & A2A:** the deterministic Python orchestrator analyzes the request,
    dispatches A2A protocol tasks to the relevant specialist agent(s) (Study, Schedule,
    Research, or sequential multi-agent pipelines), and aggregates the final result.
    """
    query_text = request.get_query_text()
    session_id = request.session_id or "default"

    if not query_text:
        raise HTTPException(
            status_code=422,
            detail="Request must contain a non-empty 'query', 'prompt', or 'input' field.",
        )

    logger.info(
        "POST %s  |  session_id=%r  query=%r",
        "/chat | /invocations", session_id, query_text[:80],
    )

    result = orchestrate(session_id=session_id, query=query_text)

    if not result.success and result.error_detail:
        logger.error("Error for session %r: %s", session_id, result.error_detail)

    logger.info("Done  |  session_id=%r  specialists=%s", session_id, result.specialists_used)

    return ChatResponse(session_id=session_id, answer=result.answer)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Dev server entry point
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("api:app", host="127.0.0.1", port=port, reload=True)

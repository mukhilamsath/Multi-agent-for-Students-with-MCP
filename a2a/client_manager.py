"""
a2a/client.py
═══════════════════════════════════════════════════════════════════════════════
A2A Client communication layer.

Provides client-side facilities to dispatch requests to specialist agents
using the standard A2A protocol.
═══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import logging
import re
import uuid
from typing import Any, Optional

import httpx
from httpx import ASGITransport, AsyncClient

from a2a.client import A2AClient
from a2a.types import (
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    TextPart,
)

from a2a.cards import AGENT_CARDS
from agents.servers import get_study_app, get_schedule_app, get_research_app
from telemetry_config import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer("student-assistant.a2a")

# Registry of in-process ASGI applications by specialist key
_APP_REGISTRY = {
    "study": get_study_app,
    "schedule": get_schedule_app,
    "research": get_research_app,
}


def _extract_text_from_response(response: SendMessageResponse) -> str:
    """Extract human-readable plain text from an A2A SendMessageResponse."""
    if not isinstance(response, SendMessageSuccessResponse) and not (
        hasattr(response, "root") and isinstance(response.root, SendMessageSuccessResponse)
    ):
        return str(response)

    success_resp = response.root if hasattr(response, "root") else response
    task = success_resp.result

    if not task:
        return "No task result returned from agent."

    extracted_parts: list[str] = []

    # 1. Extract from artifacts if available
    if task.artifacts:
        for artifact in task.artifacts:
            for part in artifact.parts:
                part_obj = part.root if hasattr(part, "root") else part
                if isinstance(part_obj, TextPart) and part_obj.text:
                    extracted_parts.append(part_obj.text)
                elif hasattr(part_obj, "text") and part_obj.text:
                    extracted_parts.append(part_obj.text)

    # 2. Extract from status message if no artifact text found
    if not extracted_parts and task.status and task.status.message:
        msg = task.status.message
        for part in getattr(msg, "parts", []):
            part_obj = part.root if hasattr(part, "root") else part
            if isinstance(part_obj, TextPart) and part_obj.text:
                extracted_parts.append(part_obj.text)
            elif hasattr(part_obj, "text") and part_obj.text:
                extracted_parts.append(part_obj.text)

    # 3. Extract from history messages if needed
    if not extracted_parts and task.history:
        for hist_msg in reversed(task.history):
            if hist_msg.role == Role.agent:
                for part in hist_msg.parts:
                    part_obj = part.root if hasattr(part, "root") else part
                    if isinstance(part_obj, TextPart) and part_obj.text:
                        extracted_parts.append(part_obj.text)

    result_text = "".join(extracted_parts).strip()
    # Strip any private model reasoning/thinking tags (e.g. <thinking>...</thinking>)
    clean_text = re.sub(r"<thinking>[\s\S]*?</thinking>", "", result_text).strip()
    return clean_text if clean_text else (result_text if result_text else "Agent completed task with no textual output.")


class A2AClientManager:
    """
    Manages A2A communication with specialist agents.
    Dispatches tasks as standard A2A JSON-RPC requests to the agent's endpoint.
    """

    def __init__(self, timeout_seconds: float = 60.0):
        self.timeout_seconds = timeout_seconds

    async def call_agent(
        self,
        agent_key: str,
        query: str,
        session_id: str,
        *,
        http_url: Optional[str] = None,
    ) -> str:
        """
        Send a task message to a specialist agent over A2A and await its response.

        Args:
            agent_key: Specialist identifier ('study', 'schedule', or 'research').
            query: The user task/query string.
            session_id: The conversation session identifier (passed as context_id).
            http_url: Optional external HTTP URL if the agent is remote.

        Returns:
            The plain text answer returned by the specialist agent.

        Raises:
            ValueError: If the agent key is unknown.
            RuntimeError: If communication fails or times out.
        """
        agent_card = AGENT_CARDS.get(agent_key)
        if not agent_card:
            raise ValueError(f"Unknown agent key: {agent_key!r}. Valid keys: {list(AGENT_CARDS.keys())}")

        logger.info("A2A | Sending task -> %s (%s) [session_id=%s]", agent_card.name, agent_key, session_id)

        # Prepare standard A2A Message
        message_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        a2a_message = Message(
            message_id=message_id,
            role=Role.user,
            parts=[Part(root=TextPart(text=query))],
            context_id=session_id,
        )

        send_request = SendMessageRequest(
            id=request_id,
            params=MessageSendParams(message=a2a_message),
        )

        with tracer.start_as_current_span(f"a2a.dispatch.{agent_key}") as span:
            span.set_attribute("a2a.agent_key", agent_key)
            span.set_attribute("a2a.agent_name", agent_card.name)
            span.set_attribute("session.id", session_id)
            span.set_attribute("a2a.query_length", len(query))

            try:
                if http_url:
                    # Dispatch over network HTTP
                    async with AsyncClient(base_url=http_url, timeout=self.timeout_seconds) as httpx_client:
                        client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
                        response = await client.send_message(send_request)
                else:
                    # Dispatch over in-process ASGI Transport
                    app_factory = _APP_REGISTRY.get(agent_key)
                    if not app_factory:
                        raise ValueError(f"No ASGI app registered for agent: {agent_key}")

                    app = app_factory()
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://a2a-internal", timeout=self.timeout_seconds) as httpx_client:
                        client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
                        response = await client.send_message(send_request)

                answer = _extract_text_from_response(response)
                span.set_attribute("a2a.response_length", len(answer))
                logger.info("A2A | %s completed | response length: %d chars", agent_card.name, len(answer))
                return answer

            except asyncio.TimeoutError as exc:
                span.record_exception(exc)
                logger.error("A2A | Timeout waiting for %s", agent_card.name)
                raise RuntimeError(f"A2A request to {agent_card.name} timed out after {self.timeout_seconds}s.") from exc
            except Exception as exc:
                span.record_exception(exc)
                logger.exception("A2A | Error communicating with %s: %s", agent_card.name, exc)
                raise RuntimeError(f"A2A communication error with {agent_card.name}: {str(exc)}") from exc

    def call_agent_sync(
        self,
        agent_key: str,
        query: str,
        session_id: str,
        *,
        http_url: Optional[str] = None,
    ) -> str:
        """Synchronous wrapper for call_agent."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # In environments where event loop is already running (e.g. nested async)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    self.call_agent(agent_key, query, session_id, http_url=http_url)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                self.call_agent(agent_key, query, session_id, http_url=http_url)
            )


# Default global client manager instance
_client_manager = A2AClientManager()


async def send_a2a_message(agent_key: str, query: str, session_id: str) -> str:
    """Convenience async function to send an A2A message to a specialist agent."""
    return await _client_manager.call_agent(agent_key, query, session_id)


def send_a2a_message_sync(agent_key: str, query: str, session_id: str) -> str:
    """Convenience sync function to send an A2A message to a specialist agent."""
    return _client_manager.call_agent_sync(agent_key, query, session_id)

"""
guardrails.py
═══════════════════════════════════════════════════════════════════════════════
Central factory for guarded BedrockModel instances.

What are Amazon Bedrock Guardrails?
────────────────────────────────────
Guardrails are a Bedrock-side safety layer that runs INDEPENDENTLY of the LLM.
Every request to Bedrock passes through the guardrail BEFORE the model sees it
(input filtering) and AFTER the model replies (output filtering).

Guardrails can be configured in the AWS Console to:
  • Block specific topics (e.g. "no violence, no adult content")
  • Filter harmful content across five severity categories:
      HATE, INSULTS, SEXUAL, VIOLENCE, MISCONDUCT
  • Detect and redact PII (names, emails, phone numbers, etc.)
  • Block prompt-injection attacks (jailbreak attempts)
  • Define a custom word/phrase blocklist

Because guardrails live in Bedrock (not in Python), they work even if someone
bypasses the Python code entirely and calls the API directly.

How it integrates with Strands:
────────────────────────────────
You attach a guardrail to a BedrockModel by passing:
    guardrail_id      — the guardrail's unique ID from the Bedrock console
    guardrail_version — "DRAFT" while testing, or "1", "2", … in production

Strands adds the guardrail config to every ConverseStream API call automatically.
If the guardrail triggers:
    • Input blocked  → Bedrock rejects the request; the input message is
                       replaced with guardrail_redact_input_message.
    • Output blocked → Bedrock blocks the response; optionally replaced with
                       guardrail_redact_output_message.

Architecture in this project:
──────────────────────────────
ALL three specialist agents (Study, Schedule, Research) call build_guarded_model().
The orchestrator is deterministic Python (no LLM). This means EVERY LLM call made
by the leaf agents is protected by the same guardrail. No call slips through unguarded.

  Study Agent   ──► build_guarded_model(streaming=False, temperature=0.4)
  Schedule Agent──► build_guarded_model(streaming=False, temperature=0.1)
  Research Agent──► build_guarded_model(streaming=False, temperature=0.2)

Setting up your guardrail (one-time, in AWS Console):
──────────────────────────────────────────────────────
  1. Open https://console.aws.amazon.com/bedrock → Guardrails → Create guardrail
  2. Name it (e.g. "student-assistant-guardrail")
  3. Configure the policies you want:
       • Denied topics: add "Violence", "Adult content", "Self-harm"
       • Content filters: set HATE/INSULTS/SEXUAL/VIOLENCE to HIGH threshold
       • Sensitive info (PII): detect & redact EMAIL, PHONE, NAME as needed
       • Prompt attacks: enable "Prompt attack" detection
  4. Click "Create guardrail" — note the Guardrail ID (looks like: abc1234567)
  5. Set version to DRAFT for testing, or create version 1 for production
  6. Add to your .env:
         BEDROCK_GUARDRAIL_ID=abc1234567
         BEDROCK_GUARDRAIL_VERSION=DRAFT

If BEDROCK_GUARDRAIL_ID is not set, build_guarded_model() creates a plain
BedrockModel with NO guardrail — so the project still runs during development
before you have a guardrail configured.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import os

from strands.models import BedrockModel

logger = logging.getLogger(__name__)

# ── Guardrail configuration (read once at import time) ───────────────────────
# These are read from environment variables so the IDs are never hard-coded.
_GUARDRAIL_ID      = os.getenv("BEDROCK_GUARDRAIL_ID", "").strip()
_GUARDRAIL_VERSION = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT").strip()

# Bedrock guardrail IDs are alphanumeric strings, typically 10+ characters.
# Reject obvious placeholder values from .env.example so we fail fast at
# startup with a clear message rather than mid-conversation with a cryptic
# ValidationException from Bedrock.
_KNOWN_PLACEHOLDERS = {"abc1234567", "your_guardrail_id_here", "placeholder"}
if _GUARDRAIL_ID.lower() in _KNOWN_PLACEHOLDERS:
    logger.warning(
        "WARNING: Guardrail ID looks like a placeholder (%r) — treating as not configured. "
        "Replace BEDROCK_GUARDRAIL_ID in .env with your real Guardrail ID from the "
        "AWS Console (Bedrock → Guardrails), or leave it empty to disable guardrails.",
        _GUARDRAIL_ID,
    )
    _GUARDRAIL_ID = ""

# ── Redaction messages ────────────────────────────────────────────────────────
# These strings replace the blocked content so the user gets a clear,
# student-friendly explanation instead of a cryptic error.
_INPUT_BLOCKED_MSG = (
    "WARNING: Your message was blocked by the content safety guardrail. "
    "Please rephrase your question to focus on academic topics."
)
_OUTPUT_BLOCKED_MSG = (
    "WARNING: The response was blocked by the content safety guardrail. "
    "Please try asking your question differently."
)


def build_guarded_model(
    temperature: float = 0.3,
    streaming: bool = True,
) -> BedrockModel:
    """
    Build a BedrockModel with guardrail protection attached.

    Call this function instead of constructing BedrockModel directly so that
    every agent in the project uses the same guardrail configuration.

    Args:
        temperature: Sampling temperature for the model (0.0 = deterministic,
                     1.0 = very creative). Each agent passes its own value.
        streaming:   True for the coordinator (streams tokens to console).
                     False for specialists (they run silently).

    Returns:
        A fully configured BedrockModel instance. If BEDROCK_GUARDRAIL_ID is
        empty the model is returned WITHOUT a guardrail (safe for local dev).
    """
    aws_region       = os.getenv("AWS_REGION",        "us-east-1")
    bedrock_model_id = os.getenv("BEDROCK_MODEL_ID",  "amazon.nova-micro-v1:0")

    if _GUARDRAIL_ID:
        # ── Guarded model ─────────────────────────────────────────────────────
        # guardrail_id / guardrail_version tell Bedrock which guardrail to apply
        # on every request made by this model instance.
        #
        # guardrail_trace="enabled" means Bedrock includes a trace block in the
        # response that shows which guardrail policy triggered and why. This is
        # very useful for debugging — you can see exactly what was filtered.
        #
        # guardrail_redact_input=True (default): if the INPUT is blocked, the
        # raw user message is replaced with guardrail_redact_input_message before
        # it appears in conversation history or logs. This prevents the harmful
        # content from being stored in agent.messages.
        #
        # guardrail_redact_output=False (default): if the OUTPUT is blocked,
        # Bedrock replaces it with guardrail_redact_output_message.
        logger.info(
            "Guardrail active  |  id=%r  version=%r  streaming=%s",
            _GUARDRAIL_ID, _GUARDRAIL_VERSION, streaming,
        )
        return BedrockModel(
            model_id=bedrock_model_id,
            region_name=aws_region,
            temperature=temperature,
            streaming=streaming,

            # ── Guardrail parameters ──────────────────────────────────────────
            guardrail_id=_GUARDRAIL_ID,
            guardrail_version=_GUARDRAIL_VERSION,

            # Show which policy fired in the API trace (great for debugging).
            guardrail_trace="enabled",

            # Replace the BLOCKED INPUT with a safe student-friendly message.
            # The raw harmful text never reaches agent.messages.
            guardrail_redact_input=True,
            guardrail_redact_input_message=_INPUT_BLOCKED_MSG,

            # Replace BLOCKED OUTPUT with a safe message.
            guardrail_redact_output=True,
            guardrail_redact_output_message=_OUTPUT_BLOCKED_MSG,
        )

    else:
        # ── Unguarded model (development fallback) ────────────────────────────
        # BEDROCK_GUARDRAIL_ID is not set — run without a guardrail so
        # developers can test the agent without creating one first.
        logger.warning(
            "Guardrail NOT configured  |  "
            "Set BEDROCK_GUARDRAIL_ID in .env to enable content safety filtering. "
            "Running without guardrail protection."
        )
        return BedrockModel(
            model_id=bedrock_model_id,
            region_name=aws_region,
            temperature=temperature,
            streaming=streaming,
        )


def guardrail_status() -> str:
    """Return a one-line human-readable string describing the guardrail state."""
    if _GUARDRAIL_ID:
        return f"Guardrail: ACTIVE  (id={_GUARDRAIL_ID!r}  version={_GUARDRAIL_VERSION!r})"
    return "Guardrail: NOT configured  (set BEDROCK_GUARDRAIL_ID in .env)"

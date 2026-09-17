"""
telemetry_config.py
═══════════════════════════════════════════════════════════════════════════════
OpenTelemetry tracing configuration for the Student Assistant Multi-Agent System.

Provides dual trace export capabilities:
  1. Local File Export: Records all distributed traces into `traces/traces.jsonl`.
  2. Jaeger / OTLP Export: Ships traces to a Jaeger collector (e.g. `http://localhost:4318/v1/traces`).
═══════════════════════════════════════════════════════════════════════════════
"""

import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional, Sequence

import opentelemetry.trace as trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)

# Directory where trace files are stored
_TRACES_DIR = Path(__file__).parent / "traces"
_TRACE_FILE = _TRACES_DIR / "traces.jsonl"

_telemetry_initialized = False
_jaeger_active = False
_active_jaeger_endpoint: Optional[str] = None


class LocalFileSpanExporter(SpanExporter):
    """
    Exports OpenTelemetry spans directly to a local JSON Lines (.jsonl) file.
    Each line represents a complete trace span formatted with high readability.
    """

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _format_timestamp(self, nanoseconds: Optional[int]) -> Optional[str]:
        if nanoseconds is None:
            return None
        dt = datetime.datetime.fromtimestamp(nanoseconds / 1e9, tz=datetime.timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "Z"

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                for span in spans:
                    duration_ms = None
                    if span.start_time and span.end_time:
                        duration_ms = round((span.end_time - span.start_time) / 1e6, 2)

                    span_record = {
                        "name": span.name,
                        "trace_id": f"{span.context.trace_id:032x}",
                        "span_id": f"{span.context.span_id:016x}",
                        "parent_span_id": f"{span.parent.span_id:016x}" if span.parent else None,
                        "start_time": self._format_timestamp(span.start_time),
                        "end_time": self._format_timestamp(span.end_time),
                        "duration_ms": duration_ms,
                        "status": span.status.status_code.name,
                        "attributes": dict(span.attributes) if span.attributes else {},
                    }

                    if span.events:
                        span_record["events"] = [
                            {
                                "name": event.name,
                                "time": self._format_timestamp(event.timestamp),
                                "attributes": dict(event.attributes) if event.attributes else {},
                            }
                            for event in span.events
                        ]

                    f.write(json.dumps(span_record, ensure_ascii=False) + "\n")
            return SpanExportResult.SUCCESS
        except Exception as exc:
            logger.error("Failed to export OpenTelemetry trace to file %s: %s", self.file_path, exc)
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        pass


def setup_telemetry(
    service_name: str = "student-assistant",
    trace_file: Optional[Path] = None,
    jaeger_endpoint: Optional[str] = None,
) -> Path:
    """
    Initialize OpenTelemetry tracing with dual export (Local File + Jaeger OTLP).

    Args:
        service_name: Name of the application service (default: 'student-assistant').
        trace_file: Optional custom path for the local traces.jsonl file.
        jaeger_endpoint: Optional custom Jaeger OTLP HTTP endpoint (e.g. 'http://localhost:4318/v1/traces').

    Returns:
        Path to the active local trace file.
    """
    global _telemetry_initialized, _jaeger_active, _active_jaeger_endpoint
    active_trace_file = trace_file or _TRACE_FILE

    if _telemetry_initialized:
        return active_trace_file

    active_trace_file.parent.mkdir(parents=True, exist_ok=True)

    # ── 1. Create Resource ────────────────────────────────────────────────────
    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
            "service.version": "2.0.0",
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
        }
    )

    # ── 2. Initialize TracerProvider ──────────────────────────────────────────
    provider = TracerProvider(resource=resource)

    # ── 3. Add Local File Span Exporter (Always Active) ───────────────────────
    local_exporter = LocalFileSpanExporter(active_trace_file)
    local_processor = SimpleSpanProcessor(local_exporter)
    provider.add_span_processor(local_processor)
    logger.info("OpenTelemetry | Local file trace export active -> %s", active_trace_file)

    # ── 4. Add Jaeger / OTLP Exporter (Only when explicitly enabled) ─────────
    jaeger_env = os.getenv("JAEGER_ENDPOINT", "").strip()
    enable_jaeger_flag = os.getenv("ENABLE_JAEGER", "").lower() in ("true", "1", "yes")
    
    endpoint = (
        jaeger_endpoint
        or (jaeger_env if jaeger_env and jaeger_env.lower() != "none" else None)
    )

    enable_jaeger = enable_jaeger_flag or bool(jaeger_endpoint) or (bool(jaeger_env) and jaeger_env.lower() != "none")

    if enable_jaeger and endpoint:
        target_endpoint = endpoint
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            otlp_exporter = OTLPSpanExporter(endpoint=target_endpoint)
            batch_processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(batch_processor)

            _jaeger_active = True
            _active_jaeger_endpoint = target_endpoint
            logger.info("OpenTelemetry | Jaeger OTLP export active -> %s", target_endpoint)
        except Exception as exc:
            logger.warning("OpenTelemetry | Failed to initialize Jaeger exporter (%s). Local tracing remains active.", exc)
    else:
        logger.info("OpenTelemetry | Remote Jaeger export disabled. Traces saved locally to %s", active_trace_file)

    # ── 5. Set Global Tracer Provider ─────────────────────────────────────────
    trace.set_tracer_provider(provider)

    _telemetry_initialized = True
    return active_trace_file


def is_jaeger_active() -> bool:
    """Return True if Jaeger OTLP trace exporting is active."""
    return _jaeger_active


def get_jaeger_endpoint() -> Optional[str]:
    """Return the active Jaeger OTLP endpoint, if configured."""
    return _active_jaeger_endpoint


def get_tracer(name: str = "student-assistant") -> trace.Tracer:
    """Return an OpenTelemetry Tracer instance."""
    return trace.get_tracer(name)


def get_trace_file_path() -> Path:
    """Return the path to the active local trace file."""
    return _TRACE_FILE

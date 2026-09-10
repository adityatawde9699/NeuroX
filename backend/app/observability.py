"""PII-minimal structured logging and Prometheus-compatible API metrics."""

import json
import logging
import os
import threading
import time
from collections import Counter, defaultdict

from fastapi import FastAPI, Request

logger = logging.getLogger("neurox.requests")
_lock = threading.Lock()
_requests: Counter[tuple[str, str, int]] = Counter()
_duration_sum: defaultdict[tuple[str, str], float] = defaultdict(float)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for field in ("request_id", "method", "route", "status", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"))


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def configure_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def observe_request(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - started
        route = request.scope.get("route")
        route_name = getattr(route, "path", "unmatched")
        key = (request.method, route_name)
        with _lock:
            _requests[(request.method, route_name, response.status_code)] += 1
            _duration_sum[key] += duration
        logger.info(
            "request_completed",
            extra={
                "request_id": getattr(request.state, "request_id", "unknown"),
                "method": request.method,
                "route": route_name,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )
        return response


def configure_otel(app: FastAPI) -> bool:
    """Enable OTLP tracing only when an exporter endpoint is configured."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": "neurox-api"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health,ready,metrics",
    )
    return True


def prometheus_metrics() -> str:
    lines = [
        "# HELP neurox_http_requests_total Total API requests.",
        "# TYPE neurox_http_requests_total counter",
    ]
    with _lock:
        for (method, route, status), count in sorted(_requests.items()):
            labels = f'method="{method}",route="{route}",status="{status}"'
            lines.append(f"neurox_http_requests_total{{{labels}}} {count}")
        lines.extend(
            [
                "# HELP neurox_http_request_duration_seconds_sum Cumulative request duration.",
                "# TYPE neurox_http_request_duration_seconds_sum counter",
            ]
        )
        for (method, route), duration in sorted(_duration_sum.items()):
            labels = f'method="{method}",route="{route}"'
            lines.append(
                f"neurox_http_request_duration_seconds_sum{{{labels}}} {duration:.6f}"
            )
    return "\n".join(lines) + "\n"

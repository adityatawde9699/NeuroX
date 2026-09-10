import json
import logging
from io import StringIO

from fastapi.testclient import TestClient

from app.main import app
from app.observability import JsonFormatter


def test_metrics_use_route_templates_not_patient_ids_or_queries():
    with TestClient(app) as client:
        request_id = "private-patient-identifier"
        client.get(f"/patients/{request_id}?email=private@example.com")
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "neurox_http_requests_total" in metrics.text
        assert "/patients/{patient_id}" in metrics.text
        assert request_id not in metrics.text
        assert "private@example.com" not in metrics.text


def test_json_formatter_emits_only_allowlisted_context():
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    test_logger = logging.getLogger("neurox.test.safe-log")
    test_logger.setLevel(logging.INFO)
    test_logger.handlers = [handler]
    test_logger.propagate = False
    test_logger.info(
        "request_completed",
        extra={
            "request_id": "safe-id",
            "route": "/patients/{patient_id}",
            "email": "private@example.com",
            "token": "secret-token",
        },
    )
    payload = json.loads(output.getvalue())
    assert payload["request_id"] == "safe-id"
    assert payload["route"] == "/patients/{patient_id}"
    assert "private@example.com" not in output.getvalue()
    assert "secret-token" not in output.getvalue()

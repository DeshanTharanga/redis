import hashlib
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from kombu.exceptions import OperationalError

from app.api import routes
from app.main import app
from app.tasks.sample_tasks import process_compute_payload

client = TestClient(app)


def test_hash_task():
    value = b"hello"
    for _ in range(3):
        value = hashlib.sha256(value).digest()
    result = process_compute_payload.apply(args=("hello", 3)).get()
    assert result["digest"] == value.hex()
    assert result["iterations"] == 3
    assert result["input_payload"] == "hello"


def test_enqueue(monkeypatch):
    task_id = str(uuid4())
    calls = []
    def publish(payload, iterations):
        calls.append((payload, iterations))
        return SimpleNamespace(id=task_id)
    monkeypatch.setattr(routes.process_compute_payload, "delay", publish)
    response = client.post("/tasks/process", json={"payload": "hello", "iterations": 3})
    assert response.status_code == 202
    assert response.json()["poll_url"] == f"/tasks/status/{task_id}"
    assert calls == [("hello", 3)]


@pytest.mark.parametrize("body", [
    {"payload": ""}, {"payload": "x", "iterations": 0},
    {"payload": "x", "iterations": 5_000_001}, {},
    {"payload": "x" * 10_001},
])
def test_invalid_input(body):
    assert client.post("/tasks/process", json=body).status_code == 422


def test_queue_unavailable(monkeypatch):
    def fail(*args):
        raise OperationalError("private connection information")
    monkeypatch.setattr(routes.process_compute_payload, "delay", fail)
    response = client.post("/tasks/process", json={"payload": "hello"})
    assert response.status_code == 503
    assert "private" not in response.text


@pytest.mark.parametrize("state", ["PENDING", "STARTED", "SUCCESS", "FAILURE"])
def test_status(monkeypatch, state):
    task_id = str(uuid4())
    metadata = {"status": state, "result": {"digest": "abc"} if state == "SUCCESS" else None}
    backend = SimpleNamespace(get_task_meta=lambda _: metadata)
    monkeypatch.setattr(routes, "AsyncResult", lambda *a, **kw: SimpleNamespace(id=task_id, backend=backend))
    response = client.get(f"/tasks/status/{task_id}")
    assert response.status_code == 200
    assert response.json()["state"] == state
    assert ("result" in response.json()) == (state == "SUCCESS")
    assert ("error" in response.json()) == (state == "FAILURE")


def test_results_unavailable(monkeypatch):
    def fail(*args):
        raise ConnectionError("private backend information")
    backend = SimpleNamespace(get_task_meta=fail)
    monkeypatch.setattr(routes, "AsyncResult", lambda *a, **kw: SimpleNamespace(id=str(uuid4()), backend=backend))
    response = client.get(f"/tasks/status/{uuid4()}")
    assert response.status_code == 503
    assert "private" not in response.text


def test_health_and_invalid_id():
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/tasks/status/invalid").status_code == 422

"""Opt-in test: TEST_REDIS_URL must point at an isolated running Redis."""
import hashlib
import os
import time

import pytest
from celery.contrib.testing.worker import start_worker
from fastapi.testclient import TestClient

from app.core.celery_app import celery
from app.main import app
from app.tasks.sample_tasks import process_compute_payload  # registers the task


@pytest.mark.skipif(not os.getenv("TEST_REDIS_URL"), reason="Set TEST_REDIS_URL to run real Redis integration")
def test_api_worker_redis():
    url = os.environ["TEST_REDIS_URL"]
    previous = (celery.conf.broker_url, celery.conf.result_backend)
    celery.conf.update(broker_url=url, result_backend=url)
    try:
        with start_worker(celery, pool="solo", perform_ping_check=False, shutdown_timeout=10):
            with TestClient(app) as client:
                response = client.post("/tasks/process", json={"payload": "hello", "iterations": 3})
                assert response.status_code == 202
                poll_url = response.json()["poll_url"]
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    status = client.get(poll_url)
                    assert status.status_code == 200
                    if status.json()["state"] in {"SUCCESS", "FAILURE"}:
                        break
                    time.sleep(0.1)
                assert status.json()["state"] == "SUCCESS", status.json()
                value = b"hello"
                for _ in range(3):
                    value = hashlib.sha256(value).digest()
                assert status.json()["result"]["digest"] == value.hex()
    finally:
        celery.conf.update(broker_url=previous[0], result_backend=previous[1])

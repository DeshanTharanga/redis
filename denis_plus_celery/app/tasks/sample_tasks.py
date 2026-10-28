import hashlib
from app.core.celery_app import celery

@celery.task(bind=True, name="app.tasks.sample_tasks.process_compute_payload")
def process_compute_payload(self, payload: str, iterations: int = 100_000) -> dict:
    data_bytes = payload.encode("utf-8")
    for _ in range(iterations):
        data_bytes = hashlib.sha256(data_bytes).digest()

    return {
        "task_id": self.request.id,
        "input_payload": payload,
        "iterations": iterations,
        "digest": data_bytes.hex(),
    }

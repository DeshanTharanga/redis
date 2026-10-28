import logging
from uuid import UUID

from celery.exceptions import CeleryError
from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, status
from kombu.exceptions import OperationalError
from redis.exceptions import RedisError

from app.core.celery_app import celery
from app.schemas.tasks import TaskPayload, TaskQueued, TaskStatus
from app.tasks.sample_tasks import process_compute_payload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])
CONNECTION_ERRORS = (CeleryError, OperationalError, RedisError, OSError)

@router.post("/process", status_code=status.HTTP_202_ACCEPTED, response_model=TaskQueued)
def enqueue_task(data: TaskPayload):
    try:
        task = process_compute_payload.delay(data.payload, data.iterations)
    except CONNECTION_ERRORS as exc:
        logger.exception("Could not publish task")
        raise HTTPException(503, "Task queue unavailable. Please try again later.") from exc
    return TaskQueued(task_id=task.id, poll_url=f"/tasks/status/{task.id}")

@router.get("/status/{task_id}", response_model=TaskStatus, response_model_exclude_none=True)
def get_task_status(task_id: UUID):
    try:
        task = AsyncResult(str(task_id), app=celery)
        # Read once so state and result describe the same snapshot.
        metadata = task.backend.get_task_meta(task.id)
    except CONNECTION_ERRORS as exc:
        logger.exception("Could not read task status")
        raise HTTPException(503, "Task results unavailable. Please try again later.") from exc
    response = TaskStatus(task_id=str(task_id), state=metadata["status"])
    if response.state == "SUCCESS":
        response.result = metadata["result"]
    elif response.state == "FAILURE":
        response.error = "Task failed. Check the worker logs for details."
    return response

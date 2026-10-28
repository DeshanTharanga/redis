from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.core.celery_app import celery
from app.tasks.sample_tasks import process_compute_payload

router = APIRouter(prefix="/tasks", tags=["Tasks"])

class TaskPayload(BaseModel):
    payload: str = Field(..., min_length=1)
    iterations: int = Field(1_000_000, ge=100_000, le=5_000_000)

@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
def enqueue_task(data: TaskPayload):
    try:
        async_result = process_compute_payload.delay(data.payload, data.iterations)
        return {"status": "QUEUED", "task_id": async_result.id, "poll_url": f"/tasks/status/{async_result.id}"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

@router.get("/status/{task_id}")
def get_task_status(task_id: str):
    task = AsyncResult(task_id, app=celery)
    response = {"task_id": task_id, "state": task.state}
    if task.successful():
        response["result"] = task.result
    elif task.failed():
        response["error"] = str(task.info)
    return response

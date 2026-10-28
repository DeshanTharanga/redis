from typing import Any
from pydantic import BaseModel, Field

class TaskPayload(BaseModel):
    payload: str = Field(..., min_length=1, max_length=10_000)
    iterations: int = Field(100_000, ge=1, le=5_000_000)

class TaskQueued(BaseModel):
    status: str = "QUEUED"
    task_id: str
    poll_url: str

class TaskStatus(BaseModel):
    task_id: str
    state: str
    result: dict[str, Any] | None = None
    error: str | None = None

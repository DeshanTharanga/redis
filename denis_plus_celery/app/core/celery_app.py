from celery import Celery
from app.core.config import BROKER_URL, RESULT_BACKEND

celery = Celery(
    "worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.tasks.sample_tasks"],
)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=3,
    task_publish_retry=False,
    redis_socket_connect_timeout=3,
    redis_socket_timeout=3,
)

# denis_plus_celery

Asynchronous task queue using Celery + Redis + FastAPI.

## Run
1. `docker compose up -d` (starts Redis)
2. `celery -A app.core.celery_app.celery worker --loglevel=info` (starts Worker)
3. `uvicorn app.main:app --reload` (starts API)

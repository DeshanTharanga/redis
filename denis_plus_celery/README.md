# Celery + Redis + FastAPI

A small background-task project: submit text through an HTTP endpoint, let a
Celery worker compute repeated SHA-256 hashes, then poll for the result.
Redis database 0 holds the task queue; database 1 stores task results.

The existing directory name `denis_plus_celery` is kept for compatibility.
The service used here is **Redis**.

## Folder responsibilities

| Path | Purpose |
| --- | --- |
| `app/main.py` | Creates the FastAPI app and health endpoint |
| `app/api/routes.py` | Submits jobs and reads status |
| `app/schemas/tasks.py` | Validates requests and defines responses |
| `app/core/config.py` | Loads local environment settings |
| `app/core/celery_app.py` | Configures Celery, Redis and task discovery |
| `app/tasks/sample_tasks.py` | Background hashing task |
| `tests/` | API, task and opt-in Redis integration tests |
| `Dockerfile` | Shared Python image for API and worker |
| `docker-compose.yml` | Starts Redis, API and worker together |
| `.env.example` | Local development configuration example |

## Quick start (Docker, recommended)

Install Docker Desktop with Compose, then run from the repository root:

```bash
cd denis_plus_celery
docker compose up --build -d
docker compose logs -f worker
```

Open http://localhost:8000/docs for interactive Swagger documentation.
The API runs at http://localhost:8000. Compose waits for Redis to be healthy
before starting the API and worker. Container environment settings use the
Compose service hostname `redis`; no `.env` file is needed for this method.

Stop services with `docker compose down`. Redis data stays in a named volume.
Use `docker compose down -v` only when you want to delete the demo data.

## Try a task

In Swagger, execute **POST /tasks/process** with:

```json
{"payload": "Hello Celery and Redis!", "iterations": 100000}
```

Or use curl (in Windows PowerShell use `curl.exe`):

```bash
curl -X POST http://localhost:8000/tasks/process -H "Content-Type: application/json" -d '{"payload":"Hello Celery and Redis!","iterations":100000}'
```

Example submission response (HTTP 202):

```json
{
  "status": "QUEUED",
  "task_id": "d75b3bca-1558-48b2-8fc1-50a482067aa0",
  "poll_url": "/tasks/status/d75b3bca-1558-48b2-8fc1-50a482067aa0"
}
```

Copy the returned `poll_url` into a GET request:

```bash
curl http://localhost:8000/tasks/status/YOUR_TASK_ID
```

A completed response has `state: "SUCCESS"` and a `result` containing the digest,
input text, number of iterations and task ID.

## How it works

1. FastAPI validates the text and iteration count.
2. `.delay()` puts the job into Redis and returns a task ID immediately.
3. A separate Celery worker takes the job and runs the hashing function.
4. Celery saves the result in Redis.
5. The status endpoint reads that result using the task ID.

Possible states include `PENDING`, `STARTED`, `SUCCESS` and `FAILURE`.
Results expire after one hour. Celery reports unknown or expired IDs as
`PENDING` too; this demo cannot distinguish those from queued tasks.
`GET /health` checks only the API process. If Redis is unavailable, submission
and status endpoints return HTTP 503. Worker logs show execution failures.

## Local Python development (optional)

Use Python 3.12. Run all commands from `denis_plus_celery`.
Do not run the Compose API and worker at the same time as local copies.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env
# Windows PowerShell instead: Copy-Item .env.example .env
docker compose up -d redis
```

In one terminal (with the virtual environment activated):

```bash
celery -A app.core.celery_app.celery worker --loglevel=info
```

For learning on Windows, add `--pool=solo`, or use Docker/WSL.
In another activated terminal:

```bash
uvicorn app.main:app --reload
```

Both processes load `.env` automatically; environment variables take precedence.

## Tests

```bash
python -m pytest -q
```

The default suite needs no Redis and skips the integration test.
To exercise a real worker and Redis, use an isolated Redis database:

```bash
# Linux/macOS, with Redis running locally:
TEST_REDIS_URL=redis://localhost:6379/15 python -m pytest -q tests/test_integration.py
```

PowerShell equivalent:
`$env:TEST_REDIS_URL="redis://localhost:6379/15"`, then
`python -m pytest -q tests/test_integration.py`.

This is a local learning project. It has no authentication, and Redis ports
are bound to localhost. The hash task demonstrates background work; it is
not a password hashing implementation.

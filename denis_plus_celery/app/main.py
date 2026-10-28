from fastapi import FastAPI
from app.api.routes import router as tasks_router

app = FastAPI(title="Denis + Celery API", version="1.0.0")
app.include_router(tasks_router)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}

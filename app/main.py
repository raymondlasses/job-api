from fastapi import FastAPI, HTTPException
from app.models import OSRequest, KatanaRequest
from app.tasks import run_os_command, run_katana
from app import db

app = FastAPI(title="Job API with Celery & RabbitMQ")

@app.get("/")
async def root():
    return {"status": "ok", "note": "POST /jobs/os or /jobs/katana to enqueue a job."}

@app.post("/jobs/os")
async def enqueue_os(req: OSRequest):
    task = run_os_command.delay(req.command)
    return {"task_id": task.id}

@app.post("/jobs/katana")
async def enqueue_katana(req: KatanaRequest):
    task = run_katana.delay(str(req.url))
    return {"task_id": task.id}

@app.get("/results")
async def list_results():
    return db.get_all_results()

@app.get("/results/{result_id}")
async def get_result(result_id: str):
    res = db.get_result_by_id(result_id)
    if not res:
        raise HTTPException(status_code=404, detail="result not found")
    return res


import os
import shlex
import subprocess
from celery import Celery
import docker
from app.db import save_result

CELERY_BROKER = os.getenv("CELERY_BROKER_URL", "pyamqp://guest:guest@rabbitmq:5672//")
celery = Celery("tasks", broker=CELERY_BROKER)

@celery.task(bind=True, soft_time_limit=60)
def run_os_command(self, command: str):
    try:
        parts = shlex.split(command)
        proc = subprocess.run(parts, capture_output=True, text=True, timeout=50)
        output = proc.stdout.strip() if proc.stdout else proc.stderr.strip()
        meta = {"returncode": proc.returncode}
    except Exception as e:
        output = f"error: {e}"
        meta = {"error": True}
    saved_id = save_result("os", command, output, meta=meta)
    return {"id": saved_id, "output_sample": output[:500]}

@celery.task(bind=True, soft_time_limit=180)
def run_katana(self, url: str):
    try:
        client = docker.from_env(timeout=120)
        client.images.pull("projectdiscovery/katana:latest")
        logs = client.containers.run(
            "projectdiscovery/katana:latest",
            ["katana", "-u", url, "-json"],
            remove=True,
            stdout=True,
            stderr=True
        )
        raw = logs.decode("utf-8", errors="ignore")
        count = sum([1 for line in raw.splitlines() if line.strip()])
        result = {"count": count, "raw_sample": raw[:2000]}
        saved_id = save_result("katana", url, result)
        return {"id": saved_id, "count": count}
    except Exception as e:
        saved_id = save_result("katana", url, {"error": str(e)})
        return {"id": saved_id,  "error": str(e)}

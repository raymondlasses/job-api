
import socket
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

@celery.task(bind=True, soft_time_limit=120)
def run_katana(self, url):
    client = docker.APIClient(base_url="unix://var/run/docker.sock")
    cmd = [
        "katana", "-u", "-", "-jsonl",
        "-d", "2",
        "-ct", "10",
        "-timeout", "10",
        "-kf", "robotstxt",
        "-rl", "100"
    ]

    try:
        container = client.create_container(
            image="projectdiscovery/katana:latest",
            command=cmd,
            stdin_open=True,
            tty=False,
            host_config=client.create_host_config(auto_remove=False)  # don't auto remove here
        )
        container_id = container.get("Id")
        client.start(container=container_id)

        sock = client.attach_socket(container=container_id, params={"stdin": 1, "stream": 1})
        sock._sock.sendall(url.encode() + b"\n")
        sock._sock.shutdown(1)

        result = client.wait(container=container_id, timeout=120)

        logs = client.logs(container=container_id, stdout=True, stderr=True).decode()

        # Count URLs from logs
        url_count = len([line for line in logs.splitlines() if line.startswith("http")])

        # Now manually remove container
        client.remove_container(container=container_id, force=True)

        # Save only minimal info + url count, no full logs
        saved_id = save_result(
            "katana",
            url,
            "",  # no full logs stored to save DB space
            meta={"exit_code": result.get("StatusCode"), "url_count": url_count}
        )
        return {"id": saved_id, "url_count": url_count, "output_sample": logs[:500]}

    except Exception as e:
        return {"status": "error", "error": str(e)}


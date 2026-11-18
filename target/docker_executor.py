# =============================================================================
# target/docker_executor.py — Docker-Based Agent Execution
#
# LEARNING NOTE — Why Docker instead of direct Python calls?
#
# In Phase 1, sandbox.py called process_refund() directly because we
# owned that code. Now the user uploads ANY repository — different
# languages, different dependencies, code we've never seen before.
#
# Docker solves this by:
#   1. Isolating execution — if the uploaded agent crashes or misbehaves,
#      it only affects its own container, never your machine
#   2. Handling any dependency set — each container installs exactly
#      what that repo needs
#   3. Clean state every run — container is destroyed after testing,
#      no leftover state between test runs
#
# This file uses the Docker SDK for Python to programmatically create,
# run, and destroy containers.
# =============================================================================

import docker
import time
import requests
import tempfile
import shutil
import os
from pathlib import Path


client = docker.from_env()

BASE_IMAGES = {
    "python": "python:3.11-slim",
    "node": "node:18-alpine",
}

DEFAULT_PORT = 8080
CONTAINER_MEMORY_LIMIT = "512m"
CONTAINER_CPU_LIMIT = 1.0
HEALTH_CHECK_TIMEOUT = 30  # seconds


def start_agent_container(local_repo_path: str, stack: str, entry_point: str,
                          env_vars: dict = None) -> dict:
    """
    Spins up a Docker container running the target agent.

    Args:
        local_repo_path: path to the cloned repository on disk
        stack: "python" | "node"
        entry_point: relative path to the main file, e.g. "main.py"
        env_vars: dict of environment variables the agent needs
                  (API keys etc. — already decrypted at this point)

    Returns:
        {
            "container_id": str,
            "endpoint": str,         — http://localhost:PORT if it's a server
            "status": "running" | "failed",
            "error": str | None,
        }
    """
    env_vars = env_vars or {}
    image = BASE_IMAGES.get(stack)

    if not image:
        return {"container_id": None, "endpoint": None, "status": "failed",
                "error": f"Unsupported stack: {stack}"}

    print(f"\n[Docker Executor] Starting container ({image})...")

    try:
        # Build a minimal Dockerfile on the fly that installs deps and runs the agent
        dockerfile_content = _generate_dockerfile(stack, entry_point)
        dockerfile_path = Path(local_repo_path) / "Dockerfile.shadowops"
        dockerfile_path.write_text(dockerfile_content)

        print(f"[Docker Executor] Building image from repository...")
        image_obj, build_logs = client.images.build(
            path=local_repo_path,
            dockerfile="Dockerfile.shadowops",
            tag="shadowops-target:latest",
            rm=True,
        )

        print(f"[Docker Executor] Starting container...")
        container = client.containers.run(
            image_obj.id,
            detach=True,
            ports={f"{DEFAULT_PORT}/tcp": DEFAULT_PORT},
            environment=env_vars,
            mem_limit=CONTAINER_MEMORY_LIMIT,
            nano_cpus=int(CONTAINER_CPU_LIMIT * 1e9),
            network_mode="bridge",
            remove=False,  # we remove manually after capturing logs on failure
        )

        endpoint = f"http://localhost:{DEFAULT_PORT}"

        if not _wait_for_health(endpoint):
            logs = container.logs().decode("utf-8", errors="ignore")
            container.stop()
            container.remove()
            return {
                "container_id": None, "endpoint": None, "status": "failed",
                "error": f"Container did not become healthy in time. Logs:\n{logs[-1000:]}"
            }

        print(f"[Docker Executor] Container healthy at {endpoint}")

        return {
            "container_id": container.id,
            "endpoint": endpoint,
            "status": "running",
            "error": None,
        }

    except docker.errors.BuildError as e:
        return {"container_id": None, "endpoint": None, "status": "failed",
                "error": f"Docker build failed: {str(e)}"}
    except Exception as e:
        return {"container_id": None, "endpoint": None, "status": "failed",
                "error": f"Unexpected error: {str(e)}"}


def send_to_agent(endpoint: str, payload: dict, timeout: int = 15) -> dict:
    """
    Sends an adversarial input to the running agent container.

    Args:
        endpoint: http://localhost:PORT
        payload: the request body to send — shape depends on the agent's API
        timeout: seconds to wait before considering it a failure

    Returns:
        {
            "success": bool,
            "response": dict | None,
            "error": str | None,
            "response_time_ms": int,
        }
    """
    start = time.time()
    try:
        response = requests.post(f"{endpoint}/invoke", json=payload, timeout=timeout)
        elapsed_ms = int((time.time() - start) * 1000)

        if response.status_code == 200:
            return {
                "success": True,
                "response": response.json(),
                "error": None,
                "response_time_ms": elapsed_ms,
            }
        else:
            return {
                "success": False,
                "response": None,
                "error": f"HTTP {response.status_code}: {response.text[:500]}",
                "response_time_ms": elapsed_ms,
            }

    except requests.Timeout:
        return {"success": False, "response": None,
                "error": "Request timed out", "response_time_ms": timeout * 1000}
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {"success": False, "response": None,
                "error": str(e), "response_time_ms": elapsed_ms}


def stop_and_remove_container(container_id: str):
    """Cleans up after a test run. Always call this, even on failure."""
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=5)
        container.remove()
        print(f"[Docker Executor] Container {container_id[:12]} stopped and removed.")
    except docker.errors.NotFound:
        pass  # already gone
    except Exception as e:
        print(f"[Docker Executor] Warning: cleanup error: {e}")


def _generate_dockerfile(stack: str, entry_point: str) -> str:
    """
    Generates a minimal Dockerfile to run the uploaded agent.

    LEARNING NOTE: This assumes the agent exposes a FastAPI-style
    /invoke endpoint on port 8080. Real-world repos vary — production
    versions of this function would detect the actual run command
    from package.json scripts or a Procfile. This is the Phase 2 baseline.
    """
    if stack == "python":
        return f"""FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages || pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn --break-system-packages || pip install --no-cache-dir fastapi uvicorn
EXPOSE {DEFAULT_PORT}
CMD ["python", "{entry_point}"]
"""
    elif stack == "node":
        return f"""FROM node:18-alpine
WORKDIR /app
COPY . .
RUN npm install
EXPOSE {DEFAULT_PORT}
CMD ["node", "{entry_point}"]
"""
    else:
        raise ValueError(f"No Dockerfile template for stack: {stack}")


def _wait_for_health(endpoint: str, timeout: int = HEALTH_CHECK_TIMEOUT) -> bool:
    """Polls the container until it responds or timeout is reached."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{endpoint}/health", timeout=2)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False

# =============================================================================
# api/main.py — FastAPI Backend (Phase 2)
#
# Exposes Phase A (PM agent, repository analysis) and Phase B (test loop)
# as REST endpoints for the Next.js dashboard.
#
# Start with: uvicorn api.main:app --reload --port 8000
# =============================================================================

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db, init_db, Project, TestRun, Vulnerability, Patch, Organisation, User
from core.knowledge_base import ensure_collection_exists, get_latest_domain_model, save_domain_model
from agents.intelligence.pm_agent import run_pm_agent_session
from agents.intelligence.repository_scanner import scan_repository
from target.docker_executor import start_agent_container, stop_and_remove_container
from core.state import get_initial_state
from core.graph import build_graph


app = FastAPI(title="ShadowOps API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory run tracking (swap for Redis in production)
active_runs: dict[str, dict] = {}


@app.on_event("startup")
def startup():
    init_db()
    ensure_collection_exists()
    print("[API] ShadowOps API ready.")


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    org_id: str
    user_id: str
    name: str
    repo_url: str
    branch: str = "main"


class AnswerQuestionsRequest(BaseModel):
    answers: dict[str, str]


# -----------------------------------------------------------------------------
# Projects
# -----------------------------------------------------------------------------

@app.post("/projects")
def create_project(req: CreateProjectRequest, db: Session = Depends(get_db)):
    project = Project(
        org_id=req.org_id, name=req.name, repo_url=req.repo_url,
        branch=req.branch, created_by=req.user_id, status="active",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"project_id": project.id, "name": project.name}


@app.get("/projects")
def list_projects(org_id: str, db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.org_id == org_id).all()
    return [{"id": p.id, "name": p.name, "domain": p.domain,
            "status": p.status, "last_synced": p.last_synced} for p in projects]


@app.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    domain_model = get_latest_domain_model(project_id)
    return {
        "id": project.id, "name": project.name, "repo_url": project.repo_url,
        "stack": project.stack, "domain": project.domain,
        "domain_model": domain_model,
    }


# -----------------------------------------------------------------------------
# Phase A — Analysis
# -----------------------------------------------------------------------------

@app.post("/projects/{project_id}/analyse")
def analyse_project(project_id: str, db: Session = Depends(get_db)):
    """
    Triggers Phase A — repository scan + code intelligence + attack planning.
    Returns either clarifying questions or a complete domain model.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    result = run_pm_agent_session(
        project_id=project_id,
        org_id=project.org_id,
        user_id=str(project.created_by),
        repo_url=project.repo_url,
        branch=project.branch,
    )

    if result["status"] == "complete":
        project.domain = result["domain_model"]["domain"]
        project.stack = result["domain_model"].get("tech_stack", {}).get("language", "unknown")
        db.commit()

    return result


@app.post("/projects/{project_id}/answer-questions")
def answer_questions(project_id: str, req: AnswerQuestionsRequest, db: Session = Depends(get_db)):
    """Submits answers to PM agent clarifying questions and finalises the domain model."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    result = run_pm_agent_session(
        project_id=project_id, org_id=project.org_id, user_id=str(project.created_by),
        repo_url=project.repo_url, branch=project.branch, user_answers=req.answers,
    )
    return result


# -----------------------------------------------------------------------------
# Phase B — Test runs
# -----------------------------------------------------------------------------

@app.post("/projects/{project_id}/runs")
def start_test_run(project_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Starts a new test run in the background."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    domain_model = get_latest_domain_model(project_id)
    if not domain_model:
        raise HTTPException(400, "Project has not been analysed yet. Call /analyse first.")

    run_id = str(uuid.uuid4())[:8]
    active_runs[run_id] = {
        "run_id": run_id, "project_id": project_id, "status": "starting",
        "attacks_launched": 0, "vulnerabilities_found": [], "proposed_patch": "",
        "resiliency_score": None,
    }

    background_tasks.add_task(_run_test_background, run_id, project_id, domain_model)

    return {"run_id": run_id, "message": "Test run started"}


def _run_test_background(run_id: str, project_id: str, domain_model: dict):
    active_runs[run_id]["status"] = "running"

    try:
        # NOTE: attack_categories would normally come from the stored
        # attack plan; simplified here to call plan_attacks() fresh
        from agents.intelligence.attack_planner import plan_attacks
        attack_plan = plan_attacks(domain_model)

        initial_state = get_initial_state(
            project_id=project_id, target_name="Project Agent",
            target_code="", domain_model=domain_model,
            attack_categories=attack_plan["attack_categories"],
        )

        graph = build_graph()
        final_state = graph.invoke(initial_state)

        vulns = final_state.get("vulnerabilities_found", [])
        attacks = final_state.get("attacks_launched", 0)
        score = max(0, round(((attacks - len(vulns)) / max(attacks, 1)) * 100))

        active_runs[run_id].update({
            "status": final_state.get("status", "complete"),
            "vulnerabilities_found": vulns, "attacks_launched": attacks,
            "proposed_patch": final_state.get("proposed_patch", ""),
            "resiliency_score": score,
        })
    except Exception as e:
        active_runs[run_id]["status"] = "error"
        active_runs[run_id]["error"] = str(e)


@app.get("/runs/{run_id}/status")
def get_run_status(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    run = active_runs[run_id]
    return {
        "run_id": run_id, "status": run["status"],
        "attacks_launched": run["attacks_launched"],
        "vulnerabilities_found": len(run["vulnerabilities_found"]),
    }


@app.get("/runs/{run_id}/results")
def get_run_results(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    run = active_runs[run_id]
    if run["status"] == "running":
        raise HTTPException(202, "Run still in progress")
    return run


@app.get("/health")
def health():
    return {"status": "ok", "service": "shadowops-api-v2"}

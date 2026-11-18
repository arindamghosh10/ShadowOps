# =============================================================================
# main.py — ShadowOps Phase 2 — Full Pipeline
#
# This runs the COMPLETE flow: Phase A (understanding) → Phase B (testing)
#
# Usage: python main.py
# You will be prompted for a repository path or URL.
# =============================================================================

import json
import uuid
from pathlib import Path

from core.agent_models import validate_config
from core.database import init_db, SessionLocal, Organisation, User, Project
from core.knowledge_base import ensure_collection_exists
from agents.intelligence.pm_agent import run_pm_agent_session
from target.docker_executor import start_agent_container, stop_and_remove_container
from core.state import get_initial_state
from core.graph import build_graph


def setup_demo_org_and_project(repo_url: str) -> tuple[str, str, str, str]:
    """
    Creates a demo organisation, user, and project for local testing.
    In the real dashboard, this data already exists from user signup —
    this function exists purely so main.py can run standalone.
    """
    db = SessionLocal()
    try:
        org = Organisation(name="Demo Org", plan="free")
        db.add(org)
        db.commit()
        db.refresh(org)

        user = User(email="demo@shadowops.local", name="Demo User",
                   hashed_password="not_used_in_demo", org_id=org.id, role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)

        project = Project(org_id=org.id, name="Demo Project", repo_url=repo_url,
                          created_by=user.id, status="active")
        db.add(project)
        db.commit()
        db.refresh(project)

        return org.id, user.id, project.id, project.id
    finally:
        db.close()


def print_summary(final_state: dict):
    print(f"\n{'='*60}")
    print(f"  SHADOWOPS — TEST RUN COMPLETE")
    print(f"{'='*60}")

    vulns = final_state.get("vulnerabilities_found", [])
    attacks = final_state.get("attacks_launched", 0)

    print(f"\n  Target:           {final_state.get('target_name', 'Unknown')}")
    print(f"  Status:           {final_state.get('status', 'unknown').upper()}")
    print(f"  Attacks launched: {attacks}")
    print(f"  Vulnerabilities:  {len(vulns)}")

    if attacks > 0:
        score = max(0, round(((attacks - len(vulns)) / attacks) * 100))
        print(f"  Resiliency score: {score}%")

    if vulns:
        print(f"\n  VULNERABILITIES FOUND:")
        for i, v in enumerate(vulns, 1):
            print(f"\n  [{i}] {v['bug_type'].upper()} — {v['severity']}")
            print(f"      {v['root_cause'][:120]}")

    print(f"\n{'='*60}\n")


def main():
    print("\n" + "=" * 60)
    print("  SHADOWOPS — PHASE 2 — UNIVERSAL AGENT STRESS TESTER")
    print("=" * 60)

    # Step 0: Validate model configuration and database connections
    print("\n[Setup] Validating configuration...")
    validate_config()
    init_db()
    ensure_collection_exists()

    # Step 1: Get the repository to test
    repo_input = input(
        "\nEnter the repository to test.\n"
        "  - A GitHub URL (e.g. https://github.com/user/repo), or\n"
        "  - A local path (e.g. ./sample-target-repo)\n"
        "> "
    ).strip()

    is_local = Path(repo_input).exists()

    # Step 2: Set up demo org/user/project records
    print("\n[Setup] Creating demo project records...")
    org_id, user_id, project_id, _ = setup_demo_org_and_project(repo_input)

    # Step 3: Run Phase A — understanding the codebase
    if is_local:
        print(f"\n[Phase A] Using local repository at: {repo_input}")
        # For local paths, we skip git clone and read directly
        from agents.intelligence.repository_scanner import (
            _build_file_tree, _read_markdown_files, _detect_stack,
            _identify_agent_files, _read_files, _guess_entry_point
        )
        file_tree = _build_file_tree(repo_input)
        doc_files = _read_markdown_files(repo_input, file_tree)
        readme_content = doc_files.get("README.md", "")
        stack = _detect_stack(file_tree)
        agent_file_paths = _identify_agent_files(file_tree, stack)
        agent_files = _read_files(repo_input, agent_file_paths)
        entry_point = _guess_entry_point(file_tree, stack)
        local_repo_path = repo_input

        from agents.intelligence.code_intelligence import analyse_codebase
        from agents.intelligence.attack_planner import plan_attacks
        from core.knowledge_base import save_domain_model

        intelligence = analyse_codebase(readme_content, doc_files, agent_files, stack)
        domain_model_id = save_domain_model(project_id, intelligence)
        attack_plan = plan_attacks(intelligence)

        pm_result = {
            "status": "complete",
            "domain_model": intelligence,
            "attack_plan": attack_plan,
            "summary": f"Analysed local repo. Domain: {intelligence['domain']}",
        }
    else:
        print(f"\n[Phase A] Cloning and analysing: {repo_input}")
        pm_result = run_pm_agent_session(project_id, org_id, user_id, repo_input)
        stack = "python"  # would come from scan_result in the cloned-repo path
        entry_point = "main.py"
        local_repo_path = None  # would be set from scan_result

    if pm_result["status"] == "needs_clarification":
        print(f"\n[PM Agent] {pm_result['summary']}")
        answers = {}
        for q in pm_result["questions"]:
            print(f"\nQuestion: {q}")
            answer = input("Your answer: ").strip()
            answers[q] = answer

        # Re-run with answers incorporated
        pm_result = run_pm_agent_session(project_id, org_id, user_id, repo_input,
                                         user_answers=answers)

    domain_model = pm_result["domain_model"]
    attack_plan = pm_result["attack_plan"]

    print(f"\n[Phase A Complete] {pm_result['summary']}")

    # Step 4: Combine agent file contents for state.target_code
    target_code = "\n\n".join(agent_files.values()) if is_local else ""

    # Step 5: Start Docker container (if local repo with a runnable agent)
    container_info = {"container_id": "", "endpoint": ""}
    if is_local and local_repo_path:
        print(f"\n[Phase B] Starting Docker container...")
        container_info = start_agent_container(local_repo_path, stack, entry_point)

        if container_info["status"] == "failed":
            print(f"\n[ERROR] Could not start container: {container_info['error']}")
            print("Falling back to skipping live execution — review domain model only.")
            print(f"\nDomain model:\n{json.dumps(domain_model, indent=2)}")
            return

    # Step 6: Run Phase B — the test loop
    print(f"\n[Phase B] Starting test loop...\n")

    initial_state = get_initial_state(
        project_id=project_id,
        target_name=Path(repo_input).name if is_local else repo_input,
        target_code=target_code,
        domain_model=domain_model,
        attack_categories=attack_plan["attack_categories"],
        container_id=container_info.get("container_id", ""),
        container_endpoint=container_info.get("endpoint", ""),
    )

    graph = build_graph()

    try:
        final_state = graph.invoke(initial_state)
    except KeyboardInterrupt:
        print("\n[Main] Test run interrupted.")
        final_state = initial_state
    finally:
        if container_info.get("container_id"):
            stop_and_remove_container(container_info["container_id"])

    print_summary(final_state)

    results_path = Path("results_latest.json")
    with open(results_path, "w") as f:
        serialisable = {k: v for k, v in final_state.items()
                        if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
        json.dump(serialisable, f, indent=2, default=str)
    print(f"[Main] Full results saved to {results_path}")


if __name__ == "__main__":
    main()

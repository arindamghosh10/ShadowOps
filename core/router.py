# =============================================================================
# core/router.py — Conditional Routing (Phase 2)
#
# Same routing logic as Phase 1 — unchanged conceptually. The conditions
# work identically whether the target is our mock refund bot or a
# Dockerised agent from any uploaded repository.
# =============================================================================

from core.state import ShadowOpsState

MAX_ITERATIONS = 3


def route_after_execution(state: ShadowOpsState) -> str:
    execution_logs = state.get("execution_logs", {})

    if execution_logs.get("passed", False):
        print(f"\n[Router] Target agent passed the attack. Secure.")
        return "end"

    if state.get("iteration_count", 0) >= MAX_ITERATIONS:
        print(f"\n[Router] Max iterations ({MAX_ITERATIONS}) reached. Stopping.")
        return "end"

    print(f"\n[Router] Target agent failed. Routing to evaluator.")
    return "evaluator"


def route_after_synthesis(state: ShadowOpsState) -> str:
    return "human_approval"


def route_after_approval(state: ShadowOpsState) -> str:
    status = state.get("status", "running")

    if status == "patch_rejected":
        print("\n[Router] Patch rejected. Ending run.")
        return "end"

    if state.get("iteration_count", 0) >= MAX_ITERATIONS:
        print(f"\n[Router] Max iterations reached after patch. Ending run.")
        return "end"

    print("\n[Router] Patch approved. Re-running attack to verify fix...")
    return "chaos_attacker"

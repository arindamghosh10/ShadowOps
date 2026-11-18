# =============================================================================
# core/graph.py — The LangGraph Graph (Phase 2)
#
# LEARNING NOTE — What changed from Phase 1?
#
# The graph STRUCTURE is identical to Phase 1 — same nodes, same edges,
# same routing logic. What changed is WHAT happens inside target_executor_node:
# instead of calling a Python function directly, it now sends HTTP requests
# to a Docker container running whatever agent the user uploaded.
#
# This is the payoff of the abstraction work — Phase 1's graph design
# scales directly to Phase 2's universal version with minimal changes.
# =============================================================================

from langgraph.graph import StateGraph, END

from core.state import ShadowOpsState
from core.router import route_after_execution, route_after_approval
from agents.chaos_attacker import chaos_attacker_node
from agents.evaluator import evaluator_node
from agents.synthesizer import synthesizer_node
from target.sandbox import run_against_container


def target_executor_node(state: ShadowOpsState) -> dict:
    """
    Sends the chaos attacker's payload to the running Docker container
    and validates the response against the domain model's business rules.
    """
    print(f"\n[Target Executor] Sending attack to container...")

    endpoint = state.get("container_endpoint", "")
    chaos_payload = state.get("chaos_payload", {})
    domain_model = state.get("domain_model", {})

    if not endpoint:
        print("[Target Executor] WARNING: No container endpoint set.")
        return {"execution_logs": {"passed": False, "error": "No container endpoint",
                                   "output": "", "violated_rule": "infrastructure_error"}}

    result = run_against_container(endpoint, chaos_payload, domain_model)

    print(f"[Target Executor] Result: {'PASSED' if result['passed'] else 'FAILED'}")
    if result.get("violated_rule"):
        print(f"[Target Executor] Violated: {result['violated_rule']}")

    return {"execution_logs": result}


def human_approval_node(state: ShadowOpsState) -> dict:
    """
    Terminal-based human approval. In the dashboard (api/main.py), this
    is replaced by a real API call that pauses the graph using
    LangGraph's interrupt mechanism and waits for a button click.
    """
    print(f"\n{'='*60}")
    print(f"[Human Approval] A patch has been proposed.")
    print(f"{'='*60}")
    print(state.get("proposed_patch", "No patch available."))

    while True:
        choice = input("\nApprove this patch? (y/n): ").strip().lower()
        if choice in ("y", "n"):
            break
        print("Please enter 'y' to approve or 'n' to reject.")

    if choice == "y":
        print("[Human Approval] Patch approved. Re-testing...")
        return {
            "status": "patched",
            "iteration_count": state.get("iteration_count", 0) + 1,
        }
    else:
        print("[Human Approval] Patch rejected.")
        return {"status": "patch_rejected"}


def build_graph():
    """
    Constructs the ShadowOps Phase 2 graph. Structure is identical to
    Phase 1 — only the implementation behind target_executor_node changed.
    """
    graph = StateGraph(ShadowOpsState)

    graph.add_node("chaos_attacker", chaos_attacker_node)
    graph.add_node("target_executor", target_executor_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("human_approval", human_approval_node)

    graph.set_entry_point("chaos_attacker")

    graph.add_edge("chaos_attacker", "target_executor")
    graph.add_edge("evaluator", "synthesizer")
    graph.add_edge("synthesizer", "human_approval")

    graph.add_conditional_edges(
        "target_executor",
        route_after_execution,
        {"evaluator": "evaluator", "end": END}
    )

    graph.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {"chaos_attacker": "chaos_attacker", "end": END}
    )

    compiled = graph.compile()
    print("[Graph] ShadowOps Phase 2 graph compiled successfully.")
    return compiled


if __name__ == "__main__":
    g = build_graph()
    print("\n=== Graph ASCII Structure ===")
    g.get_graph().print_ascii()

# =============================================================================
# agents/intelligence/pm_agent.py — The PM Agent
#
# LEARNING NOTE — Tool-calling orchestration pattern
#
# This is different from the LangGraph nodes in Phase 1. The PM agent
# uses LangChain's TOOL CALLING pattern — it has a set of tools (functions)
# it can choose to call, and an LLM decides which tool to call and when,
# based on the conversation.
#
# This is the "hierarchical" interaction model we discussed — the PM agent
# orchestrates by calling sub-agents as tools, rather than them being
# fixed nodes in a graph.
#
# The PM agent runs a simple loop:
#   1. Look at conversation so far
#   2. Decide: do I have enough info, or do I need to call a tool?
#   3. If tool needed → call it, observe result, go back to step 1
#   4. If enough info → respond to user OR finalise the domain model
# =============================================================================

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

from core.llm_client import get_llm_for
from core.knowledge_base import save_domain_model, get_conversation_history, index_conversation
from agents.intelligence.repository_scanner import scan_repository
from agents.intelligence.code_intelligence import analyse_codebase
from agents.intelligence.attack_planner import plan_attacks


PM_AGENT_SYSTEM_PROMPT = """You are the Project Manager agent for ShadowOps, an AI agent security testing platform.

You are the ONLY interface the user talks to. Behind the scenes you have access
to specialist tools: a repository scanner, a code intelligence analyser, and
an attack planner. You orchestrate them to build a complete understanding of
the user's AI agent codebase.

Your workflow:
1. When given a repository URL, scan it first
2. Analyse the code to understand the domain, rules, and weak points
3. If there are GAPS between documentation and code that you cannot resolve
   from the available information, ask the user ONE specific, targeted
   question. Never ask generic questions. Never ask more than 3 questions
   total in a session.
4. Once you have enough information, plan the attack strategy
5. Confirm with the user that you're ready to start testing

Be concise and professional. You are talking to AI engineers — they want
clear, direct communication, not lengthy explanations."""


# -----------------------------------------------------------------------------
# Tools the PM agent can call
# -----------------------------------------------------------------------------

@tool
def scan_repo_tool(repo_url: str, branch: str = "main") -> str:
    """
    Scans a Git repository — reads README, documentation, and identifies
    the code files most likely to contain AI agent logic.
    Use this first whenever the user provides a repository URL.
    """
    result = scan_repository(repo_url, branch)
    # Return a condensed summary the LLM can reason over
    return (
        f"Stack: {result['stack']}\n"
        f"Entry point: {result['entry_point']}\n"
        f"README found: {bool(result['readme_content'])}\n"
        f"Doc files: {list(result['doc_files'].keys())}\n"
        f"Agent files identified: {list(result['agent_files'].keys())}\n"
        f"--- Use analyse_code_tool next with this data ---"
    )


@tool
def analyse_code_tool(readme_content: str, agent_files_summary: str, stack: str) -> str:
    """
    Deeply analyses the scanned code to extract the domain, business rules,
    weak points, and any gaps between documentation and implementation.
    Call this after scan_repo_tool.
    """
    # NOTE: In the full implementation, this passes through to
    # code_intelligence.analyse_codebase() with the full file contents
    # held in agent state, not just the summary string shown to the LLM.
    # See pm_agent_session() below for how this is wired with real data.
    return "Use the full analyse_codebase() function with actual file contents."


@tool
def ask_user_question(question: str) -> str:
    """
    Use this when you have a SPECIFIC gap that cannot be resolved from
    the repository alone. The question must reference the exact gap found.
    Never use this for generic questions.
    """
    return f"[Question sent to user]: {question}"


@tool
def plan_attacks_tool(domain_summary: str) -> str:
    """
    Generates domain-specific attack categories once the domain model
    is complete. Call this as the final step before testing begins.
    """
    return "Use the full plan_attacks() function with the actual domain model dict."


# -----------------------------------------------------------------------------
# The actual orchestration — wired with real data flow
#
# LEARNING NOTE: The @tool decorated functions above show the CONCEPT
# of tool calling clearly for learning purposes. In practice, passing
# large file contents through LLM tool call arguments is wasteful and
# error-prone. This function below is the REAL implementation used by
# the API — it calls the underlying functions directly with full data,
# using the LLM only for the conversational and decision-making parts.
# -----------------------------------------------------------------------------

def run_pm_agent_session(project_id: str, org_id: str, user_id: str,
                          repo_url: str, branch: str = "main",
                          user_answers: dict = None) -> dict:
    """
    Runs a complete Phase A session: scan, analyse, plan attacks.
    Returns the domain model and any clarifying questions for the user.

    Args:
        project_id, org_id, user_id: for storing conversation history
        repo_url, branch: what to scan
        user_answers: dict of {question: answer} if this is a follow-up
                      call after the user answered clarifying questions

    Returns:
        {
            "status": "needs_clarification" | "complete",
            "questions": list[str],          — if needs_clarification
            "domain_model": dict,            — if complete
            "attack_plan": dict,             — if complete
            "summary": str                   — PM agent's message to user
        }
    """
    print(f"\n{'='*60}")
    print(f"[PM Agent] Starting session for project {project_id}")
    print(f"{'='*60}")

    # Step 1: Scan
    scan_result = scan_repository(repo_url, branch)

    # Step 2: Analyse
    intelligence = analyse_codebase(
        readme_content=scan_result["readme_content"],
        doc_files=scan_result["doc_files"],
        agent_files=scan_result["agent_files"],
        stack=scan_result["stack"],
    )

    # Step 3: Decide if clarification is needed
    # The PM agent uses an LLM call to decide if the gaps found are
    # significant enough to warrant asking the user
    llm = get_llm_for("pm_agent")

    gaps = intelligence.get("gaps", [])

    if gaps and not user_answers:
        questions = _generate_clarifying_questions(llm, gaps, intelligence)

        index_conversation(
            project_id, org_id, user_id, "assistant",
            f"I've reviewed your repository. I found {len(gaps)} gaps "
            f"between your documentation and code. I have a few questions."
        )

        return {
            "status": "needs_clarification",
            "questions": questions,
            "domain_model": intelligence,
            "summary": (
                f"I've read your repository — it's a {intelligence['domain']} agent. "
                f"Before I start testing, I have {len(questions)} question(s)."
            ),
        }

    # Step 4: Incorporate user answers into the domain model if provided
    if user_answers:
        intelligence["business_rules"].extend(
            [f"{q} → {a}" for q, a in user_answers.items()]
        )

    # Step 5: Save the finalised domain model
    domain_model_id = save_domain_model(project_id, intelligence)

    # Step 6: Plan attacks
    attack_plan = plan_attacks(intelligence)

    index_conversation(
        project_id, org_id, user_id, "assistant",
        f"Domain model finalised. Generated {len(attack_plan['attack_categories'])} "
        f"attack categories. Ready to start testing."
    )

    return {
        "status": "complete",
        "domain_model": intelligence,
        "attack_plan": attack_plan,
        "domain_model_id": domain_model_id,
        "summary": (
            f"Analysis complete. Domain: {intelligence['domain']}. "
            f"Found {len(intelligence['business_rules'])} business rules and "
            f"{len(intelligence['weak_points'])} weak points. "
            f"Generated {len(attack_plan['attack_categories'])} targeted attack "
            f"categories. Ready to start testing."
        ),
    }


def _generate_clarifying_questions(llm, gaps: list[str], intelligence: dict) -> list[str]:
    """
    Generates at most 3 targeted clarifying questions based on the gaps found.
    Never generic — each question references a specific gap.
    """
    messages = [
        SystemMessage(content=PM_AGENT_SYSTEM_PROMPT),
        HumanMessage(content=f"""
I found these gaps between documentation and code in this {intelligence['domain']} agent:

{chr(10).join(f'- {g}' for g in gaps)}

Generate at most 3 specific clarifying questions for the user, one per gap
that genuinely needs human input. If a gap can be reasonably assumed
(e.g. standard practice), do not ask about it — just note your assumption.
Return ONLY the questions, one per line, no numbering or extra text.
""")
    ]

    response = llm.invoke(messages)
    questions = [q.strip("- ").strip() for q in response.content.split("\n") if q.strip()]
    return questions[:3]

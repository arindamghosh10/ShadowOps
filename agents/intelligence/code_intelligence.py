# =============================================================================
# agents/intelligence/code_intelligence.py — Code Intelligence Agent
#
# LEARNING NOTE — Connecting intent (docs) with implementation (code)
#
# The most valuable thing this agent does is find GAPS between what the
# README says the agent should do, and what the code actually does.
#
# Example: README says "refunds are limited to $500 maximum."
# Code has no such check. That gap IS a vulnerability waiting to be found.
#
# This agent uses per-agent model configuration — it calls
# get_llm_for("code_intelligence") so you can assign it a stronger
# reasoning model independently of other agents.
# =============================================================================

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from core.llm_client import get_llm_for


class CodeIntelligenceOutput(BaseModel):
    """Structured understanding of what the target agent does."""

    domain: str = Field(
        description="The business domain. Examples: e-commerce refunds, "
                    "telecom billing, healthcare scheduling, HR leave management"
    )

    purpose: str = Field(
        description="2-3 sentence plain English summary of what this agent does"
    )

    business_rules: list[str] = Field(
        description="All business rules found, from BOTH the documentation "
                    "AND the code. Each rule as a clear, standalone sentence. "
                    "Example: 'Refunds must be requested within 30 days of purchase'"
    )

    gaps: list[str] = Field(
        description="Rules mentioned in documentation but NOT enforced in the "
                    "code. These are potential vulnerabilities. If none found, "
                    "return an empty list."
    )

    weak_points: list[str] = Field(
        description="Specific functions or code sections that look fragile — "
                    "missing validation, unclear boundary conditions, or "
                    "logic that could be exploited. Reference exact function names."
    )

    llm_used: str = Field(
        description="Which LLM provider/model this agent uses internally, "
                    "if identifiable from the code. 'unknown' if not found."
    )

    tools: list[str] = Field(
        description="Any external tools or functions this agent can call "
                    "(database queries, APIs, etc). Empty list if none found."
    )


CODE_INTELLIGENCE_SYSTEM_PROMPT = """You are a senior software architect specialising in understanding AI agent codebases.

You will be given:
1. The README and documentation of a repository
2. The source code of files identified as containing agent logic

Your job is to deeply understand what this agent does and find any gaps between
what the documentation promises and what the code actually enforces.

Be specific. Reference exact function names, exact rules, exact gaps.
Do not give generic observations — give findings specific to THIS codebase."""


def analyse_codebase(readme_content: str, doc_files: dict, agent_files: dict, stack: str) -> dict:
    """
    Reads the repository's documentation and code, returns a structured
    understanding of the agent's domain, rules, and weak points.

    Args:
        readme_content: Full README text
        doc_files: dict of {filename: content} for all markdown files
        agent_files: dict of {filename: content} for identified agent code
        stack: detected tech stack ("python" | "node" | etc.)

    Returns:
        Dict matching CodeIntelligenceOutput schema
    """
    print(f"\n[Code Intelligence] Analysing codebase ({stack})...")

    llm = get_llm_for("code_intelligence")
    structured_llm = llm.with_structured_output(CodeIntelligenceOutput)

    # Build the context — README first (intent), then code (implementation)
    docs_combined = readme_content
    for filename, content in doc_files.items():
        if filename.lower() != "readme.md":
            docs_combined += f"\n\n--- {filename} ---\n{content}"

    code_combined = ""
    for filename, content in agent_files.items():
        code_combined += f"\n\n--- {filename} ---\n{content[:3000]}"  # cap per-file length

    messages = [
        SystemMessage(content=CODE_INTELLIGENCE_SYSTEM_PROMPT),
        HumanMessage(content=f"""
DOCUMENTATION:
{docs_combined[:6000]}

SOURCE CODE (stack: {stack}):
{code_combined[:12000]}

Analyse this codebase. Identify the domain, all business rules (from docs
and code), any gaps between documented rules and code enforcement, and
specific weak points in the implementation.
""")
    ]

    result: CodeIntelligenceOutput = structured_llm.invoke(messages)

    print(f"[Code Intelligence] Domain: {result.domain}")
    print(f"[Code Intelligence] Found {len(result.business_rules)} business rules")
    print(f"[Code Intelligence] Found {len(result.gaps)} gaps between docs and code")
    print(f"[Code Intelligence] Found {len(result.weak_points)} weak points")

    return result.model_dump()

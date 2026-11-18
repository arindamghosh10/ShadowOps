# =============================================================================
# agents/synthesizer.py — Synthesizer (Phase 2 — Domain Aware)
# Same core logic as Phase 1, now reads domain_model for business rule
# context when generating patches, and uses get_llm_for("synthesizer").
# =============================================================================

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from core.state import ShadowOpsState
from core.llm_client import get_llm_for


class SynthesizerOutput(BaseModel):
    original_code: str = Field(description="The exact original function/code block containing the bug")
    patched_code: str = Field(description="The corrected version — minimal targeted change only")
    patch_reason: str = Field(description="One sentence explaining the fix")
    confidence: str = Field(description="One of: high, medium, low")
    side_effects: str = Field(description="Any potential side effects of this change, or 'none'")


SYNTHESIZER_SYSTEM_PROMPT = """You are a senior developer fixing a security vulnerability in an AI agent.

You will be given the agent's source code, the diagnosed vulnerability, and
the relevant business rule. Write a minimal, targeted patch.

Rules:
- Fix ONLY the identified vulnerability
- Do not refactor unrelated code
- The patched code must be syntactically valid
- Do not change function signatures
- Add one inline comment explaining the fix"""


def synthesizer_node(state: ShadowOpsState) -> dict:
    print(f"\n{'='*60}")
    print(f"[Synthesizer] Generating patch for: {state.get('bug_type')}...")
    print(f"{'='*60}")

    llm = get_llm_for("synthesizer")
    structured_llm = llm.with_structured_output(SynthesizerOutput)

    messages = [
        SystemMessage(content=SYNTHESIZER_SYSTEM_PROMPT),
        HumanMessage(content=f"""
AGENT SOURCE CODE:
```
{state.get("target_code", "")[:4000]}
```

VULNERABILITY:
Bug type: {state.get("bug_type")}
Root cause: {state.get("root_cause")}
Affected function: {state.get("vulnerabilities_found", [{}])[-1].get("affected_function", "unknown")}

Generate a minimal patch to fix this specific vulnerability.
""")
    ]

    patch: SynthesizerOutput = structured_llm.invoke(messages)

    proposed_patch = _format_patch(patch)

    print(f"[Synthesizer] Patch generated (confidence: {patch.confidence})")

    return {
        "proposed_patch": proposed_patch,
        "status": "patch_ready",
    }


def _format_patch(patch: SynthesizerOutput) -> str:
    sep = "-" * 60
    return f"""
{sep}
ORIGINAL CODE:
{sep}
{patch.original_code}

{sep}
PATCHED CODE:
{sep}
{patch.patched_code}

{sep}
REASON:
{sep}
{patch.patch_reason}

CONFIDENCE: {patch.confidence.upper()}
SIDE EFFECTS: {patch.side_effects}
{sep}
"""

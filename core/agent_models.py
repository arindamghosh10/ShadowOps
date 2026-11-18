# =============================================================================
# core/agent_models.py — Per-Agent LLM Configuration
#
# THIS IS THE MOST IMPORTANT FILE FOR CUSTOMISING YOUR MODELS.
#
# LEARNING NOTE — Why per-agent configuration?
#
# Different agents need different strengths:
#   - Chaos Attacker needs CREATIVITY → a model good at unpredictable ideas
#   - Evaluator needs PRECISION → a model good at structured reasoning
#   - Synthesizer needs CODE SKILL → a model good at writing code
#   - PM Agent needs CONVERSATION → a model good at natural dialogue
#
# Using one universal model for everything wastes the strengths of
# specialised models. This file lets you assign a different model to
# EVERY agent, completely independently.
#
# HOW TO CHANGE A MODEL:
# Find the agent below and change "model" and "provider".
# That is the ONLY change needed. Nothing else in the codebase changes.
#
# Example — switch the Synthesizer from local Llama 3 to GPT-4o:
#   "synthesizer": {
#       "provider": "openai",      # was "ollama"
#       "model": "gpt-4o",         # was "llama3"
#       "temperature": 0.2,
#   }
#
# Make sure you also add your OPENAI_API_KEY to your .env file.
# =============================================================================

# -----------------------------------------------------------------------------
# DEFAULT CONFIGURATION — everything runs free and local via Ollama
#
# This is intentional. You should be able to run the ENTIRE platform
# with zero API costs using local models. Upgrade individual agents
# to cloud models only when you want better quality for that specific task.
# -----------------------------------------------------------------------------

AGENT_MODEL_CONFIG = {

    # -------------------------------------------------------------------
    # PHASE A AGENTS — Understanding the codebase
    # -------------------------------------------------------------------

    "repository_scanner": {
        # Job: reads file names, README, basic structure
        # Needs: not much reasoning, just text processing
        # Good local choice: llama3 (fast, sufficient for this simple task)
        "provider": "ollama",
        "model": "llama3",
        "temperature": 0.1,
    },

    "code_intelligence": {
        # Job: deeply understands what the agent does, extracts rules
        # Needs: STRONG reasoning to connect docs with code logic
        # Recommended upgrade: claude-sonnet-4-6 or gpt-4o for real codebases
        # Local fallback: llama3:70b if you have 40GB+ RAM, else llama3
        "provider": "ollama",
        "model": "llama3",
        "temperature": 0.2,
    },

    "pm_agent": {
        # Job: talks to the user, asks clarifying questions, orchestrates
        # Needs: STRONG conversational quality, good judgement on when
        #        to ask vs when to proceed
        # Recommended upgrade: claude-sonnet-4-6 (best at natural dialogue)
        "provider": "ollama",
        "model": "llama3",
        "temperature": 0.4,
    },

    "attack_planner": {
        # Job: designs attack categories specific to the domain
        # Needs: domain reasoning + creativity
        "provider": "ollama",
        "model": "llama3",
        "temperature": 0.5,
    },

    # -------------------------------------------------------------------
    # PHASE B AGENTS — Testing loop
    # -------------------------------------------------------------------

    "chaos_attacker": {
        # Job: generates unpredictable adversarial inputs
        # Needs: HIGH creativity, willing to try unusual ideas
        # High temperature is intentional here
        "provider": "ollama",
        "model": "llama3",
        "temperature": 0.9,
    },

    "evaluator": {
        # Job: structured diagnosis of WHY something failed
        # Needs: PRECISION and reliable structured JSON output
        # Low temperature is intentional — you want consistency
        # Recommended upgrade: gpt-4o (best structured output reliability)
        "provider": "ollama",
        "model": "llama3",
        "temperature": 0.2,
    },

    "synthesizer": {
        # Job: writes minimal, correct code patches
        # Needs: STRONG code generation skill
        # Recommended upgrade: gpt-4o or claude-sonnet-4-6 for real patches
        "provider": "ollama",
        "model": "llama3",
        "temperature": 0.2,
    },

    "judge": {
        # Job: decides pass/fail when business rules alone aren't enough
        # Needs: good judgement, doesn't need to be expensive
        # Recommended: a cheap, fast model — this gets called often
        "provider": "ollama",
        "model": "llama3",
        "temperature": 0.1,
    },
}


# -----------------------------------------------------------------------------
# Provider connection settings — where to find each provider
# Reads from environment variables (.env file)
# -----------------------------------------------------------------------------

import os
from dotenv import load_dotenv

load_dotenv()

PROVIDER_SETTINGS = {
    "ollama": {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    },
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
    },
    "anthropic": {
        "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    },
    "google": {
        "api_key": os.getenv("GOOGLE_API_KEY", ""),
    },
}


def get_agent_config(agent_name: str) -> dict:
    """
    Returns the model configuration for a specific agent.

    Usage:
        from core.agent_models import get_agent_config
        config = get_agent_config("chaos_attacker")
        # {"provider": "ollama", "model": "llama3", "temperature": 0.9}

    Raises:
        ValueError if agent_name is not found in AGENT_MODEL_CONFIG
    """
    if agent_name not in AGENT_MODEL_CONFIG:
        raise ValueError(
            f"Unknown agent '{agent_name}'. "
            f"Valid agents: {list(AGENT_MODEL_CONFIG.keys())}"
        )
    return AGENT_MODEL_CONFIG[agent_name]


def validate_config():
    """
    Checks that every agent assigned to a cloud provider has the
    required API key set. Run this at startup to catch config errors early.

    Usage in main.py:
        from core.agent_models import validate_config
        validate_config()  # raises clear error if misconfigured
    """
    errors = []

    for agent_name, config in AGENT_MODEL_CONFIG.items():
        provider = config["provider"]

        if provider == "openai" and not PROVIDER_SETTINGS["openai"]["api_key"]:
            errors.append(
                f"Agent '{agent_name}' is set to use OpenAI but "
                f"OPENAI_API_KEY is not set in your .env file."
            )

        if provider == "anthropic" and not PROVIDER_SETTINGS["anthropic"]["api_key"]:
            errors.append(
                f"Agent '{agent_name}' is set to use Anthropic but "
                f"ANTHROPIC_API_KEY is not set in your .env file."
            )

        if provider == "google" and not PROVIDER_SETTINGS["google"]["api_key"]:
            errors.append(
                f"Agent '{agent_name}' is set to use Google but "
                f"GOOGLE_API_KEY is not set in your .env file."
            )

    if errors:
        error_msg = "\n".join(f"  - {e}" for e in errors)
        raise ValueError(
            f"\n\nAgent model configuration errors:\n{error_msg}\n\n"
            f"Fix this by either:\n"
            f"  1. Adding the missing API key to your .env file, or\n"
            f"  2. Changing that agent's provider back to 'ollama' "
            f"in core/agent_models.py\n"
        )

    print("[Config] All agent model configurations valid.")

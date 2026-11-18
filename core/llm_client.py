# =============================================================================
# core/llm_client.py — Per-Agent Model Resolution
#
# LEARNING NOTE — How this connects to agent_models.py
#
# Every agent in this codebase calls get_llm_for("agent_name") instead of
# a generic get_llm(). This function looks up that agent's specific
# configuration from agent_models.py and returns the correctly configured
# LLM client — whether that's local Ollama or a cloud provider.
#
# This is the layer that makes "change the config, the agent switches
# model automatically" actually work end to end.
# =============================================================================

from core.agent_models import get_agent_config, PROVIDER_SETTINGS


def get_llm_for(agent_name: str):
    """
    Returns a configured LLM instance for a specific named agent.

    This is the ONLY function agent files should call to get their LLM.
    It reads agent_models.py to determine which provider/model/temperature
    this specific agent should use.

    Usage:
        from core.llm_client import get_llm_for

        llm = get_llm_for("chaos_attacker")
        response = llm.invoke("Generate an adversarial input")

    To change which model an agent uses, edit core/agent_models.py —
    never hardcode a model name inside an agent file.
    """
    config = get_agent_config(agent_name)
    provider = config["provider"]
    model = config["model"]
    temperature = config["temperature"]

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model,
            base_url=PROVIDER_SETTINGS["ollama"]["base_url"],
            temperature=temperature,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            api_key=PROVIDER_SETTINGS["openai"]["api_key"],
            temperature=temperature,
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            api_key=PROVIDER_SETTINGS["anthropic"]["api_key"],
            temperature=temperature,
        )

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=PROVIDER_SETTINGS["google"]["api_key"],
            temperature=temperature,
        )

    else:
        raise ValueError(
            f"Unknown provider '{provider}' for agent config. "
            f"Valid providers: ollama, openai, anthropic, google"
        )

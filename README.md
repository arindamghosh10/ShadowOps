# ShadowOps — Universal AI Agent Stress-Testing Platform

**Phase 2 — Universal Codebase Support with Per-Agent LLM Configuration**

---

## Start here

New to this project? Read these in order:

1. **SETUP_GUIDE.md** — complete Windows setup, step by step, beginner friendly. Start here.
2. **SHADOWOPS_FULL_SPEC.md** — the complete product specification, architecture, and design decisions
3. This file — quick reference once you're set up

---

## What this is

ShadowOps reads any AI agent's codebase, understands what it does, runs it in an isolated Docker container, attacks it with adversarial inputs, diagnoses every failure, and suggests precise patches — with a human approving every fix.

---

## The key file: per-agent model configuration

Open `core/agent_models.py`. Every agent (Repository Scanner, Code Intelligence, PM Agent, Attack Planner, Chaos Attacker, Evaluator, Synthesizer) has its own model setting:

```python
"chaos_attacker": {
    "provider": "ollama",   # or "openai" | "anthropic" | "google"
    "model": "llama3",
    "temperature": 0.9,
},
```

Change the provider and model for any agent independently. By default, everything runs free and local via Ollama.

---

## Project structure

```
shadowops-v2/
├── SETUP_GUIDE.md              ← Start here if you're new
├── SHADOWOPS_FULL_SPEC.md      ← Full architecture and design decisions
├── docker-compose.yml          ← PostgreSQL + Qdrant
├── requirements.txt
├── .env.example                ← Copy to .env and configure
├── main.py                     ← Run this for terminal mode (Phase A + B)
│
├── core/
│   ├── agent_models.py         ← KEY FILE — per-agent model config
│   ├── llm_client.py           ← Resolves config into actual LLM clients
│   ├── state.py                ← Shared state for the test loop
│   ├── graph.py                ← LangGraph wiring (Phase B)
│   ├── router.py                ← Conditional routing logic
│   ├── database.py             ← PostgreSQL models (SQLAlchemy)
│   └── knowledge_base.py       ← Project Knowledge Base (Postgres + Qdrant)
│
├── agents/
│   ├── chaos_attacker.py       ← Generates adversarial inputs
│   ├── evaluator.py            ← Diagnoses failures
│   ├── synthesizer.py          ← Generates patches
│   └── intelligence/
│       ├── repository_scanner.py   ← Reads any repo
│       ├── code_intelligence.py    ← Understands any codebase
│       ├── pm_agent.py             ← Orchestrates Phase A
│       └── attack_planner.py       ← Designs domain-specific attacks
│
├── target/
│   ├── docker_executor.py      ← Spins up containers for any uploaded repo
│   └── sandbox.py              ← Business rule validation layer
│
├── sample-target-repo/         ← A working example repo to test against
│
├── api/
│   └── main.py                 ← FastAPI backend for the dashboard
│
└── shadowops-ui/                ← Next.js dashboard
```

---

## Quick commands reference

```bash
# Activate environment (every session)
venv\Scripts\activate

# Start databases
docker compose up -d

# Run terminal mode (Phase A + B against any repo)
python main.py

# Run the API backend
uvicorn api.main:app --reload --port 8000

# Run the dashboard (separate terminal)
cd shadowops-ui
npm run dev

# Stop databases when done
docker compose down
```

---

## Testing against your own agent

When `main.py` asks for a repository, you can provide:
- A local path: `./sample-target-repo` or `./my-agent`
- A GitHub URL: `https://github.com/you/your-agent`

For your own agent to work with the Docker Executor, it needs:
- A `/health` endpoint returning 200 OK
- A `/invoke` endpoint accepting POST requests and returning JSON
- A `requirements.txt` (Python) or `package.json` (Node)

If your agent doesn't have these endpoints yet, you can still run Phase A alone (`analyse_codebase`) to get the domain model and vulnerability analysis without live execution.

---

## What's next after this Phase 2 foundation

See `SHADOWOPS_FULL_SPEC.md` section 14 for the full phased roadmap — dashboard polish, scheduled testing, CI/CD integration, multi-language support, and the attack library.

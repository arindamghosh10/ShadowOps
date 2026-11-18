# ShadowOps — Full Product Specification
### Universal AI Agent Stress-Testing & Self-Healing Platform
**Version 2.0 | June 2026**

---

## Table of Contents

1. [Product Vision](#1-product-vision)
2. [What the Product Does](#2-what-the-product-does)
3. [Who It Is For](#3-who-it-is-for)
4. [How It Works — End to End](#4-how-it-works--end-to-end)
5. [System Architecture](#5-system-architecture)
6. [The Agent Network](#6-the-agent-network)
7. [How Agents Communicate](#7-how-agents-communicate)
8. [The Testing Pipeline](#8-the-testing-pipeline)
9. [Project Knowledge Base](#9-project-knowledge-base)
10. [Dashboard & Features](#10-dashboard--features)
11. [Database Schema](#11-database-schema)
12. [API Structure](#12-api-structure)
13. [Tech Stack](#13-tech-stack)
14. [Development Phases](#14-development-phases)
15. [Monetisation](#15-monetisation)
16. [Key Design Decisions](#16-key-design-decisions)

---

## 1. Product Vision

ShadowOps is a **universal AI agent stress-testing and self-healing platform**. It reads any AI agent's codebase, understands what it does, runs it in an isolated environment, attacks it with adversarial inputs, diagnoses every failure, and suggests precise patches — all with a human approving the final fix.

The one-sentence pitch:

> *"ShadowOps finds the vulnerabilities in your AI agents before your users do."*

The long-term vision is to become the standard security and quality layer that sits between an AI agent being built and that agent going to production — the same way unit tests and CI/CD pipelines became standard for traditional software.

---

## 2. What the Product Does

### Two-phase pipeline per project

**Phase A — Understanding (static analysis)**
The system reads the repository. It processes README files and documentation first, then the agent's source code. It extracts the domain, the business rules, the tech stack, and the logical weak points. If there are gaps, the PM agent asks the user targeted questions. The result is a structured domain model stored in the Project Knowledge Base.

**Phase B — Testing (dynamic analysis)**
The system spins up a Docker container, installs the agent's dependencies, starts the agent, and runs the full attack loop. The chaos attacker uses the domain model from Phase A to generate targeted adversarial inputs. The evaluator diagnoses failures. The synthesizer suggests patches. A human approves or rejects each patch.

### What it tests

- **Pure LLMs with system prompts** — probes the prompt for injection vulnerabilities, policy bypasses, and jailbreaks
- **Agents with tools and business logic** — tests both the code paths and the LLM's runtime behaviour
- **Multi-agent systems** — maps how agents talk to each other and tests how failures cascade

### What it finds

- Logical flaws in business rule enforcement
- Boundary and arithmetic vulnerabilities (negative values, future dates, overflow)
- Prompt injection and jailbreak susceptibility
- Policy bypass through edge case inputs
- Cascading failures in multi-agent chains
- Missing validation on inputs and outputs

---

## 3. Who It Is For

### Primary users

**AI Engineers**
Building and deploying AI agents. They connect their repo, run a test, get a report, and approve patches. ShadowOps fits into their development workflow.

**DevOps / Platform Teams**
They connect ShadowOps to the CI/CD pipeline. Every push to main triggers a test. Critical vulnerabilities block the release.

**Product Managers**
They read the executive summary report. They want to know: is this agent safe to ship? The resiliency score gives them a one-number answer.

### Secondary users

**CTOs and Engineering Managers**
They look at the org-level dashboard on Monday morning. They want to know: which agents are risky, what has been fixed, what is still open.

**Compliance and Security Teams**
They need the PDF report showing what was tested, what was found, and what was fixed. This is their audit trail for AI systems.

---

## 4. How It Works — End to End

### From the user's perspective

```
1. User creates an organisation and invites their team

2. User creates a new project
   - Connects a GitHub/GitLab repository (or uploads a zip)
   - Optionally sets the target branch and environment variables

3. PM agent reads the repository
   - Processes README and docs first
   - Reads agent source code selectively
   - Asks the user 1-3 clarifying questions if needed
   - Builds the domain model and stores it

4. User reviews the domain model
   - Can edit extracted business rules
   - Can add custom rules the system missed
   - Confirms and starts the test

5. ShadowOps runs the test
   - Docker container spins up with the agent inside
   - Chaos attacker sends adversarial inputs
   - Live attack feed shows in the dashboard
   - Vulnerability cards appear as issues are found

6. Test completes
   - Resiliency score shown
   - Vulnerability list with severity
   - Each vulnerability has a proposed patch

7. User reviews and approves patches
   - Side-by-side diff viewer
   - Approve → patch is exported as GitHub PR description
   - Reject → logged with reason

8. Results stored in Project Knowledge Base
   - Next test run is faster and more targeted
   - Resiliency trend updates
   - Team notified via email or Slack
```

### From the system's perspective

```
Repository
    ↓
[Repository Scanner]
  - Clone repo
  - Read .md files
  - Map file structure
  - Identify entry points
    ↓
[Code Intelligence Agent]
  - Read agent files selectively
  - Extract domain, rules, weak points
  - Identify tech stack and entry point
    ↓
[PM Agent — Phase A]
  - Review intelligence output
  - Identify gaps
  - Ask user clarifying questions (max 3)
  - Build and store domain model
    ↓
[Attack Planner Agent]
  - Read domain model
  - Generate domain-specific attack categories
  - Prioritise by severity potential
    ↓
[Docker Executor]
  - Select base image (python/node/etc.)
  - Install dependencies
  - Start agent
  - Health check
    ↓
[ShadowOps Test Loop — LangGraph StateGraph]
  ┌─────────────────────────────────┐
  │ Chaos Attacker                  │
  │   → generates adversarial input │
  │       ↓                         │
  │ Docker Executor                 │
  │   → sends input, captures output│
  │       ↓                         │
  │ Router                          │
  │   → passed? END                 │
  │   → failed? EVALUATOR           │
  │       ↓                         │
  │ Evaluator                       │
  │   → diagnoses failure as JSON   │
  │       ↓                         │
  │ Synthesizer                     │
  │   → generates patch suggestion  │
  │       ↓                         │
  │ Human Approval                  │
  │   → approve → re-test loop      │
  │   → reject → next attack        │
  └─────────────────────────────────┘
    ↓
[Results stored in Project Knowledge Base]
    ↓
[Report generated]
    ↓
[Notifications sent]
```

---

## 5. System Architecture

### High-level components

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│              Next.js 14 — App Router                         │
│   Dashboard | Projects | Chat | Usage | Team | Settings      │
└─────────────────────┬───────────────────────────────────────┘
                       │ HTTP / WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                      API LAYER                               │
│                   FastAPI (Python)                           │
│        REST endpoints + WebSocket for live feed              │
└──────┬──────────────┬──────────────┬────────────────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼────────────────────────┐
│  AGENT      │ │  PROJECT   │ │       DOCKER LAYER           │
│  NETWORK    │ │  KNOWLEDGE │ │  Container per test run      │
│  LangGraph  │ │  BASE      │ │  Agent runs in isolation     │
│  + Ollama / │ │  PostgreSQL│ │  Destroyed after test        │
│  Cloud LLMs │ │  + Qdrant  │ └─────────────────────────────┘
└─────────────┘ └────────────┘
```

### Infrastructure per environment

```
Development (local):
  - Ollama for LLMs (free, local)
  - PostgreSQL via Docker Compose
  - Qdrant via Docker Compose
  - Next.js dev server
  - FastAPI with uvicorn

Production:
  - Cloud LLM provider (configurable per org)
  - Managed PostgreSQL (Supabase or AWS RDS)
  - Qdrant Cloud
  - Next.js on Vercel
  - FastAPI on Railway or AWS ECS
  - Docker-in-Docker or AWS Fargate for test containers
```

---

## 6. The Agent Network

### Phase A agents — Understanding

---

**Repository Scanner**
```
Role:     First contact with the codebase
Input:    repo_url (str), branch (str)
Output:   {
            readme_content: str,
            doc_files: list[str],
            agent_files: list[str],
            stack: str,
            entry_point: str,
            file_tree: dict
          }
How:      Clones repo, reads .md files first,
          identifies agent-relevant files by
          name patterns and imports
Token strategy: Only reads file names and
          first 50 lines of each file to
          build the map. Full reads only
          for identified agent files.
```

---

**Code Intelligence Agent**
```
Role:     Deeply understands what the agent does
Input:    {readme: str, agent_files: list, stack: str}
Output:   {
            domain: str,
            purpose: str,
            business_rules: list[str],
            input_schema: dict,
            output_schema: dict,
            weak_points: list[str],
            gaps: list[str],
            llm_used: str,
            tools: list[str]
          }
How:      Reads README for intent, reads code
          for implementation. Compares them to
          find gaps where stated rules are not
          enforced in code.
Model:    Needs strong reasoning — Claude or
          GPT-4o recommended.
```

---

**PM Agent**
```
Role:     Orchestrator of Phase A. Single point
          of contact with the user.
Input:    Code Intelligence output + user messages
Output:   Finalised domain model stored in
          Project Knowledge Base
How:      Reviews intelligence output, identifies
          gaps, asks user targeted questions
          (max 3 per session), confirms domain
          model before Phase B starts.
Behaviour: Never asks a question the code or
          docs already answered. Each question
          must reference a specific gap found.
```

---

**Attack Planner Agent**
```
Role:     Designs the attack strategy for this
          specific agent
Input:    Domain model from Project Knowledge Base
Output:   {
            attack_categories: list[{
              name: str,
              description: str,
              target_rule: str,
              severity_potential: str,
              example_input: str
            }],
            priority_order: list[str]
          }
How:      Reads domain model and business rules.
          Generates attack categories specific
          to this domain. Checks attack library
          for patterns that worked on similar
          agents previously.
```

---

### Phase B agents — Testing

---

**Chaos Attacker**
```
Role:     Generates adversarial inputs
Input:    {target_code: str, attack_category: dict,
           domain_model: dict}
Output:   {
            chaos_input: str,
            attack_category: str,
            target_vulnerability: str,
            order_id: str | null,
            params: dict
          }
Model:    Higher temperature (0.9) — needs
          creativity and unpredictability
```

---

**Docker Executor**
```
Role:     Runs the agent safely and captures output
Input:    {chaos_input: str, container_id: str,
           endpoint: str, params: dict}
Output:   {
            passed: bool,
            output: str,
            error: str,
            violated_rule: str,
            response_time_ms: int,
            cost_estimate: float
          }
How:      Sends inputs to the running container
          via HTTP (if FastAPI agent) or
          subprocess (if CLI agent).
          Validates response against business
          rules from domain model.
```

---

**Evaluator**
```
Role:     Diagnoses why the agent failed
Input:    {execution_logs: dict, domain_model: dict,
           target_code: str, chaos_input: str}
Output:   EvaluatorOutput (Pydantic) {
            bug_type: str,
            root_cause: str,
            affected_function: str,
            affected_field: str,
            severity: str,
            suggested_fix_type: str,
            confidence: str
          }
Model:    Low temperature (0.2) — needs precision.
          Uses with_structured_output() for
          guaranteed JSON.
```

---

**Synthesizer**
```
Role:     Generates minimal targeted patch
Input:    {target_code: str, root_cause: str,
           bug_type: str, domain_model: dict}
Output:   SynthesizerOutput (Pydantic) {
            original_code: str,
            patched_code: str,
            patch_reason: str,
            confidence: str,
            side_effects: str
          }
Model:    Low temperature (0.2). Best results
          with GPT-4o or Claude for code generation.
          Uses with_structured_output().
```

---

## 7. How Agents Communicate

### Phase A — Hierarchical (PM agent orchestrates)

Each sub-agent is a **tool** the PM agent can invoke. The PM agent decides when to call each tool and what to do with the result.

```python
# PM agent tools (simplified concept)
tools = [
    scan_repository,        # calls Repository Scanner
    analyse_code,           # calls Code Intelligence Agent
    plan_attacks,           # calls Attack Planner Agent
    ask_user,               # sends message to user in chat
    save_domain_model,      # writes to Project Knowledge Base
]
```

The PM agent runs in a ReAct loop — Reason, Act, Observe, Reason again — until it has a complete domain model and is ready to hand off to Phase B.

### Phase B — Shared State (LangGraph StateGraph)

All Phase B agents read from and write to the shared `ShadowOpsState` dictionary. The graph router handles all navigation.

```python
class ShadowOpsState(TypedDict):
    # From Project Knowledge Base (initialised at start)
    domain_model: dict
    business_rules: list
    attack_categories: list

    # Written by Chaos Attacker
    chaos_input: str
    attack_category: str

    # Written by Docker Executor
    execution_logs: dict

    # Written by Evaluator
    root_cause: str
    bug_type: str
    severity: str

    # Written by Synthesizer
    proposed_patch: str

    # Control fields
    iteration_count: int
    status: str
    vulnerabilities_found: list
    attacks_launched: int
    total_cost: float
```

### Handoff between Phase A and Phase B

The Project Knowledge Base is the bridge. Phase A writes the domain model into it. Phase B reads from it to initialise the LangGraph state. They never talk directly.

```
Phase A (PM Agent) → writes → Project Knowledge Base
Phase B (LangGraph) → reads → Project Knowledge Base → initialises state
```

---

## 8. The Testing Pipeline

### Docker container lifecycle

```
1. Container creation
   - Select base image based on detected stack
     python:3.11-slim | node:18-alpine | etc.
   - Set memory limit (512MB default)
   - Set CPU limit (1 core default)
   - Set network isolation (no outbound except LLM APIs)

2. Environment setup
   - Copy repo files into container
   - Install dependencies (pip install / npm install)
   - Inject encrypted environment variables
   - Run health check script

3. Agent startup
   - If FastAPI: uvicorn main:app --port 8080
   - If CLI: keep container running, exec commands
   - If importable module: Python exec wrapper

4. Test execution
   - Chaos attacker sends inputs
   - Executor captures responses
   - Business rule validation runs

5. Container teardown
   - Destroyed after test run completes
   - Logs saved to Project Knowledge Base
   - No state persists between runs
```

### Pass/fail determination

This is the hardest part. ShadowOps uses three layers to determine if a response is a vulnerability:

**Layer 1 — Business rule violation**
The domain model contains explicit rules extracted from the codebase and confirmed by the user. If the agent's response violates one of these rules, it is a failure.
Example: Rule = "refund amount must be > 0". Agent returns amount = -200. Failure.

**Layer 2 — Schema violation**
The domain model contains the expected output schema. If the agent returns a response that does not match the schema, it is a failure.
Example: Agent crashes with a Python exception instead of returning a structured response. Failure.

**Layer 3 — LLM judge**
For cases where rules and schema are not enough, a separate judge LLM reads the input, the expected behaviour, and the actual response, and decides if a policy was violated.
Example: Agent approved a refund for a clearly fabricated order — no rule explicitly covers this but the judge recognises it as a policy violation.

---

## 9. Project Knowledge Base

### What it stores

Each project has its own knowledge base. It grows with every test run.

```
Project Knowledge Base
├── domain_model
│     ├── domain (str)
│     ├── purpose (str)
│     ├── business_rules (list)
│     ├── input_schema (dict)
│     ├── output_schema (dict)
│     └── tech_stack (dict)
│
├── codebase_map
│     ├── repo_url (str)
│     ├── last_synced (datetime)
│     ├── relevant_files (list)
│     └── entry_point (str)
│
├── attack_history
│     └── [per run: attacks, results, vulnerabilities]
│
├── vulnerability_registry
│     └── [all vulnerabilities ever found with status]
│
├── approved_patches
│     └── [patches the user accepted with diff]
│
└── conversation_history
      └── [all PM agent conversations for this project]
```

### How it makes the system smarter over time

**First test run:** System reads everything from scratch. Domain model built fresh. Attacks are broad.

**Second test run (after code changes):**
- System detects what changed in the repo (git diff)
- Only re-reads changed files
- Updates domain model incrementally
- Focuses attacks on changed areas first
- Checks if previously patched vulnerabilities reappeared

**After 5+ test runs:**
- System has a full vulnerability history
- Knows which attack categories work against this agent
- Resiliency trend visible over time
- Patches applied form a record of security improvements

### Vector storage (Qdrant)

Conversation history and domain model are stored as vector embeddings in Qdrant. This means the PM agent can do semantic search across the project history.

"What vulnerabilities have we found related to date validation?" → semantic search across all past findings.

---

## 10. Dashboard & Features

### Navigation structure

```
Sidebar
├── Home (org overview)
├── Projects
│     └── [Project Name]
│           ├── Overview
│           ├── Chat (PM agent)
│           ├── Test Runs
│           ├── Vulnerabilities
│           ├── Patches
│           └── Settings
├── Chat (global PM agent)
├── Usage & Cost
├── Team
└── Org Settings
```

---

### Home

**Org health score**
A single percentage calculated from the weighted average resiliency scores of all active projects. Colour coded — green (>80%), amber (50-80%), red (<50%).

**Project cards**
One card per active project showing:
- Name and domain
- Resiliency score with trend arrow (up/down since last test)
- Open vulnerability count by severity
- Last tested date and by whom
- Quick "Run Test" button

**Activity feed**
Chronological list of recent events across all projects:
- "Billing Bot tested — 2 critical vulnerabilities found"
- "Patch approved for Refund Bot — future date bypass resolved"
- "Customer Support Agent resiliency score improved from 71% to 89%"

**Open items**
Vulnerabilities found but not yet patched across all projects. Sorted by severity. Direct links to the patch viewer.

**Cost summary**
This month's total spend vs last month. Trend line. Breakdown by project.

---

### Projects — Overview tab

- Domain and purpose (from domain model)
- Business rules list — user can edit, add, or remove rules
- Tech stack detected (language, frameworks, LLM used)
- Repository connection status
- Last sync date and branch
- PM agent's summary paragraph of the codebase

---

### Projects — Chat tab

Full conversational interface with the PM agent scoped to this project.

The PM agent in this tab knows:
- Everything about this project's codebase
- Full test history
- All vulnerabilities found and their status
- All conversations from previous sessions

User can:
- Ask questions about the codebase
- Ask why a vulnerability was flagged
- Request a new test run
- Upload updated files or a new repo version
- Add business rules in plain English — "also check that discounts never exceed 40%"

Conversation history is persistent and searchable.

---

### Projects — Test Runs tab

**Run list**
Table of all test runs with:
- Run ID and date
- Triggered by (user name or "scheduled" or "CI/CD")
- Duration
- Attacks launched
- Vulnerabilities found (breakdown by severity)
- Patches approved / rejected
- Resiliency score for that run
- Status (complete / in progress / failed)

**Run detail view**
Click any run to see:
- Live attack feed replay (scrollable log)
- Each attack: input sent, response received, pass/fail, rule violated
- Vulnerability cards found in this run
- Patch diffs proposed and their approval status
- Cost breakdown for the run
- Container logs (collapsible, for engineers)

**Compare runs**
Select two runs side by side:
- Resiliency score delta
- New vulnerabilities introduced
- Vulnerabilities resolved
- Attack categories that changed outcome

---

### Projects — Vulnerabilities tab

**All vulnerabilities ever found in this project**

Filters:
- Severity (critical / medium / low)
- Status (open / patch approved / verified fixed / closed)
- Bug type (future_date_bypass / negative_value / etc.)
- Date found
- Assigned to

Each vulnerability card shows:
- Bug type and severity badge
- Affected function
- Root cause (plain English)
- Attack input that found it
- Date found and in which test run
- Current status
- Assigned team member
- Proposed patch (if generated)
- Link to patch diff

Status workflow:
```
Found → Patch Proposed → Patch Approved → Verified Fixed → Closed
```

Verified Fixed means the system re-ran the same attack after the patch was applied and confirmed it no longer succeeds.

---

### Projects — Patches tab

All patches ever generated — approved, rejected, pending.

Each patch shows:
- Vulnerability it addresses
- Before/after code diff (syntax highlighted)
- Patch reason (one sentence)
- Confidence score (High / Medium / Low) with explanation
- Side effects warning if confidence is not High
- Approve / Reject buttons
- If approved: export as GitHub PR description button
- If rejected: reason logged

---

### Projects — Settings tab

**Repository**
- Repo URL and branch
- Re-sync button (re-reads repo without full re-analysis)
- Full re-analyse button (rebuilds domain model from scratch)

**Environment variables**
- Key-value pairs for secrets the agent needs to run
- AES-256 encrypted at rest
- Never logged or exposed in UI
- Injected into Docker container at runtime

**Test schedule**
- Manual only (default)
- Weekly (pick day and time)
- On every push to main (requires GitHub webhook)
- On pull request to main (for CI/CD gate)

**Notifications**
- Email on test complete
- Email on critical vulnerability found
- Slack webhook URL
- Custom: notify only if resiliency score drops below X%

**Business rules**
- Full list of rules extracted from codebase
- Add custom rules in plain English
- Toggle rules on/off without deleting them

**Cost limits**
- Maximum cost per test run
- Warning threshold

---

### Chat (Global)

Same as project chat but operates across the entire org. The PM agent here can:

- Answer questions about any project
- Compare projects
- Trigger test runs
- Generate org-level reports
- Explain how ShadowOps works

---

### Usage & Cost

**Agent usage table**
Columns: Agent name | Calls this month | Avg response time | Tokens in | Tokens out | Cost ($)
Rows: One per agent (Repository Scanner, Code Intelligence, PM Agent, Attack Planner, Chaos Attacker, Evaluator, Synthesizer, Judge LLM)

**Project cost breakdown**
Bar chart — cost per project this month.
Table — project name | test runs | total attacks | total cost | cost per run

**Model usage breakdown**
If multiple LLMs are in use (e.g. Llama 3 local + GPT-4o cloud):
- Pie chart showing token split by model
- Cost split by model
- Helps the user optimise which model handles which agent

**Budget controls**
- Monthly budget limit — set, track, alert
- Per-run cost cap — system warns before starting if estimated cost exceeds cap
- Cost estimate shown before every test run

**Usage trend**
Line chart — daily cost over last 30 days.

---

### Team

**Member list**
Table: Name | Email | Role | Last active | Projects with access

**Roles**
- Admin — full access including billing and member management
- Engineer — create projects, run tests, approve patches
- Viewer — read-only access to results and reports

**Invite**
Email invite with role selection. Invitee gets a signup link scoped to the org.

**Activity log**
Every action by every member: project created, test run triggered, patch approved, member invited, settings changed.

---

### Org Settings

- Org name and logo
- Default LLM provider and model (engineers can override per project)
- ShadowOps API key (for CI/CD integration)
- Billing and subscription management
- Data retention policy (how long test run data is kept)
- Single sign-on (SSO) configuration (enterprise tier)

---

### Additional features

**Scheduled testing**
Connect GitHub webhook → every push to main triggers a test automatically. Slack notification sent when complete. Critical vulnerability found → Slack alert with severity and link to dashboard.

**CI/CD integration**
GitHub Action:
```yaml
- name: ShadowOps test
  uses: shadowops/action@v1
  with:
    api_key: ${{ secrets.SHADOWOPS_KEY }}
    project_id: billing-bot
    fail_on: critical
```
If a critical vulnerability is found, the action exits with code 1 and the deployment is blocked.

**Attack library**
A growing internal database of adversarial attack patterns that have successfully found vulnerabilities across the platform (anonymised, no org-specific data). New projects benefit from attacks that worked against similar agents previously.

**Vulnerability trend chart**
Per project — resiliency score plotted over time as patches are applied. Shows the team's security improvement clearly. This is the chart that goes in board presentations.

**Export and reporting**
One-click PDF export per project:
- Executive summary (one page)
- Domain model summary
- Vulnerability list with severity
- Patches applied
- Resiliency trend chart
- Suitable for compliance and audit purposes

**Patch confidence scoring**
Each patch has a confidence score with explanation:
- High — simple guard clause, no side effects
- Medium — logic change, recommend review
- Low — affects core function, manual implementation recommended

---

## 11. Database Schema

### Core tables (PostgreSQL)

```sql
-- Organisations
organisations (
  id            UUID PRIMARY KEY,
  name          TEXT,
  logo_url      TEXT,
  plan          TEXT,          -- free | pro | enterprise
  created_at    TIMESTAMP
)

-- Users
users (
  id            UUID PRIMARY KEY,
  email         TEXT UNIQUE,
  name          TEXT,
  org_id        UUID REFERENCES organisations,
  role          TEXT,          -- admin | engineer | viewer
  created_at    TIMESTAMP,
  last_active   TIMESTAMP
)

-- Projects
projects (
  id            UUID PRIMARY KEY,
  org_id        UUID REFERENCES organisations,
  name          TEXT,
  repo_url      TEXT,
  branch        TEXT,
  stack         TEXT,
  domain        TEXT,
  status        TEXT,          -- active | archived
  last_synced   TIMESTAMP,
  created_by    UUID REFERENCES users,
  created_at    TIMESTAMP
)

-- Domain models (one per project, updated each sync)
domain_models (
  id            UUID PRIMARY KEY,
  project_id    UUID REFERENCES projects,
  domain        TEXT,
  purpose       TEXT,
  business_rules JSONB,
  input_schema  JSONB,
  output_schema JSONB,
  weak_points   JSONB,
  tech_stack    JSONB,
  version       INT,
  created_at    TIMESTAMP
)

-- Test runs
test_runs (
  id            UUID PRIMARY KEY,
  project_id    UUID REFERENCES projects,
  triggered_by  UUID REFERENCES users,
  trigger_type  TEXT,          -- manual | scheduled | cicd | webhook
  status        TEXT,          -- running | complete | failed
  attacks_launched INT,
  resiliency_score INT,
  total_cost    DECIMAL,
  duration_ms   INT,
  started_at    TIMESTAMP,
  completed_at  TIMESTAMP
)

-- Individual attacks
attacks (
  id            UUID PRIMARY KEY,
  run_id        UUID REFERENCES test_runs,
  attack_category TEXT,
  chaos_input   TEXT,
  agent_response TEXT,
  passed        BOOLEAN,
  violated_rule TEXT,
  response_time_ms INT,
  cost_estimate DECIMAL,
  created_at    TIMESTAMP
)

-- Vulnerabilities
vulnerabilities (
  id            UUID PRIMARY KEY,
  project_id    UUID REFERENCES projects,
  run_id        UUID REFERENCES test_runs,
  attack_id     UUID REFERENCES attacks,
  bug_type      TEXT,
  severity      TEXT,          -- low | medium | critical
  root_cause    TEXT,
  affected_function TEXT,
  affected_field TEXT,
  status        TEXT,          -- found | patch_proposed | patch_approved
                               -- | verified_fixed | closed
  assigned_to   UUID REFERENCES users,
  created_at    TIMESTAMP,
  resolved_at   TIMESTAMP
)

-- Patches
patches (
  id            UUID PRIMARY KEY,
  vulnerability_id UUID REFERENCES vulnerabilities,
  original_code TEXT,
  patched_code  TEXT,
  patch_reason  TEXT,
  confidence    TEXT,          -- high | medium | low
  side_effects  TEXT,
  status        TEXT,          -- pending | approved | rejected
  reviewed_by   UUID REFERENCES users,
  reviewed_at   TIMESTAMP,
  created_at    TIMESTAMP
)

-- Agent usage (for cost tracking)
agent_usage (
  id            UUID PRIMARY KEY,
  org_id        UUID REFERENCES organisations,
  project_id    UUID REFERENCES projects,
  run_id        UUID REFERENCES test_runs,
  agent_name    TEXT,
  model_used    TEXT,
  tokens_in     INT,
  tokens_out    INT,
  cost_usd      DECIMAL,
  duration_ms   INT,
  created_at    TIMESTAMP
)

-- Environment variables (encrypted)
env_vars (
  id            UUID PRIMARY KEY,
  project_id    UUID REFERENCES projects,
  key_name      TEXT,
  encrypted_value TEXT,
  created_at    TIMESTAMP
)

-- Conversations (PM agent history)
conversations (
  id            UUID PRIMARY KEY,
  project_id    UUID REFERENCES projects,  -- null for global chat
  org_id        UUID REFERENCES organisations,
  user_id       UUID REFERENCES users,
  role          TEXT,                      -- user | assistant
  content       TEXT,
  created_at    TIMESTAMP
)
```

### Vector storage (Qdrant)

```
Collections:
  project_knowledge
    - vectors of domain model chunks
    - vectors of conversation history
    - vectors of vulnerability descriptions
    - metadata: {project_id, type, created_at}

  attack_library
    - vectors of successful attack patterns
    - metadata: {domain, attack_category, severity, org_id: null (anonymised)}
```

---

## 12. API Structure

### Authentication
All endpoints require Bearer token (JWT). Tokens scoped to org. Role checked per endpoint.

### Core endpoints

```
AUTH
  POST   /auth/signup
  POST   /auth/login
  POST   /auth/logout
  GET    /auth/me

ORGANISATIONS
  GET    /org
  PUT    /org
  GET    /org/usage
  GET    /org/activity

USERS / TEAM
  GET    /team
  POST   /team/invite
  PUT    /team/{user_id}/role
  DELETE /team/{user_id}

PROJECTS
  GET    /projects
  POST   /projects
  GET    /projects/{id}
  PUT    /projects/{id}
  DELETE /projects/{id}
  POST   /projects/{id}/sync          -- re-read repo
  POST   /projects/{id}/analyse       -- rebuild domain model

DOMAIN MODEL
  GET    /projects/{id}/domain-model
  PUT    /projects/{id}/domain-model/rules

TEST RUNS
  POST   /projects/{id}/runs          -- start new test run
  GET    /projects/{id}/runs          -- list all runs
  GET    /projects/{id}/runs/{run_id} -- run detail
  GET    /projects/{id}/runs/{run_id}/feed  -- WebSocket for live feed

VULNERABILITIES
  GET    /projects/{id}/vulnerabilities
  GET    /vulnerabilities/{vuln_id}
  PUT    /vulnerabilities/{vuln_id}/assign
  PUT    /vulnerabilities/{vuln_id}/status

PATCHES
  GET    /vulnerabilities/{vuln_id}/patch
  POST   /vulnerabilities/{vuln_id}/patch/approve
  POST   /vulnerabilities/{vuln_id}/patch/reject

CHAT
  POST   /chat                        -- global PM agent
  POST   /projects/{id}/chat          -- project PM agent
  GET    /projects/{id}/chat/history

USAGE
  GET    /usage                       -- org level
  GET    /usage/projects              -- per project
  GET    /usage/agents                -- per agent

ENV VARS
  GET    /projects/{id}/env
  POST   /projects/{id}/env
  DELETE /projects/{id}/env/{key}

WEBHOOKS
  POST   /webhooks/github             -- GitHub push event
```

### WebSocket (live attack feed)
```
WS /projects/{id}/runs/{run_id}/feed

Messages from server:
  {type: "attack", data: {input, category, timestamp}}
  {type: "result", data: {passed, violated_rule}}
  {type: "vulnerability", data: {bug_type, severity, root_cause}}
  {type: "patch", data: {original, patched, reason, confidence}}
  {type: "complete", data: {resiliency_score, summary}}
```

---

## 13. Tech Stack

### Backend (Python)

```
FastAPI          — API framework
LangGraph        — multi-agent orchestration (Phase B loop)
LangChain        — LLM abstraction, tool calling (Phase A)
Pydantic         — structured output validation
Docker SDK       — container management for test execution
SQLAlchemy       — ORM for PostgreSQL
Alembic          — database migrations
Qdrant client    — vector storage
python-jose      — JWT authentication
cryptography     — AES-256 env var encryption
GitPython        — repository cloning and diff
```

### LLM providers (all via llm_client.py abstraction)

```
Development:     Ollama (Llama 3 / Mistral) — free, local
Production:      Configurable per org and per agent
Recommended:
  Code Intelligence → Claude Sonnet (deep reasoning)
  PM Agent          → Claude Sonnet (conversation quality)
  Chaos Attacker    → GPT-4o or Llama 3 (creativity)
  Evaluator         → GPT-4o (structured output reliability)
  Synthesizer       → GPT-4o or Claude (code generation)
  Judge LLM         → GPT-4o mini (cost efficient)
```

### Frontend (Next.js)

```
Next.js 14       — App Router
TypeScript       — type safety
Tailwind CSS     — styling
shadcn/ui        — component library
Recharts         — usage and trend charts
React Query      — API state management
WebSocket        — live attack feed
```

### Infrastructure

```
PostgreSQL       — primary database
Qdrant           — vector storage
Redis            — job queue and session cache
Docker           — test container execution
GitHub Actions   — CI/CD integration
```

---

## 14. Development Phases

### Phase 1 — Foundation (already built)
- Core LangGraph loop (Chaos Attacker → Evaluator → Synthesizer)
- Shared state architecture
- LLM client abstraction
- Vulnerable mock refund agent
- Human approval in terminal
- Deterministic vulnerability tests
- Basic terminal output

**Status: Complete**

---

### Phase 2 — Universal input (next)
- Repository Scanner (clone repo, read .md files, map structure)
- Code Intelligence Agent (understand any agent's domain)
- PM Agent (orchestrate Phase A, conversation with user)
- Attack Planner Agent (generate domain-specific attacks)
- Docker Executor (replace direct function calls)
- Project Knowledge Base (PostgreSQL schema + Qdrant)
- Support Python-based agents first

**Deliverables:**
- User connects a GitHub repo
- System reads it and builds domain model
- PM agent asks clarifying questions
- Test loop runs against the repo's agent in Docker

---

### Phase 3 — Dashboard MVP
- FastAPI backend with all core endpoints
- WebSocket for live feed
- Next.js dashboard
- Home, Projects (all tabs), Usage pages
- JWT authentication
- Team invite and roles
- Basic cost tracking

**Deliverables:**
- Working web application
- User can onboard, create project, connect repo
- Full test run visible in dashboard
- Patch approval via UI

---

### Phase 4 — Platform features
- Scheduled testing and GitHub webhook
- CI/CD GitHub Action
- Attack library (anonymised cross-project learning)
- PDF report export
- Slack notifications
- Node.js agent support (second language)
- Vulnerability trend charts

---

### Phase 5 — Scale and monetise
- SSO / enterprise auth
- Multi-region deployment
- SLA and uptime guarantees
- Enterprise plan with private cloud option
- Additional language support (Go, Java)
- Public API for third-party integrations

---

## 15. Monetisation

### Plans

**Free**
- 1 project
- 3 test runs per month
- 1 team member
- Community support
- Purpose: developer experimentation

**Pro — $49/month per seat**
- Unlimited projects
- 20 test runs per month
- 5 team members
- Email notifications
- PDF reports
- Purpose: small engineering teams

**Team — $199/month (up to 10 seats)**
- Unlimited projects and test runs
- Unlimited team members
- Scheduled testing
- GitHub webhook + CI/CD integration
- Slack notifications
- Priority support
- Purpose: product companies shipping AI agents

**Enterprise — Custom pricing**
- Everything in Team
- SSO
- Private cloud deployment
- Custom LLM provider configuration
- SLA guarantees
- Dedicated support
- Audit logs for compliance
- Purpose: large enterprises with compliance requirements

### Usage-based component
Test runs beyond the plan limit are charged at $2 per run. Organisations pay for what they use beyond their base allowance.

---

## 16. Key Design Decisions

**1. Static analysis before dynamic testing**
Reading the code first makes the dynamic testing dramatically more targeted. The chaos attacker fires at known weak points — not randomly.

**2. Human approval always required for patches**
No auto-deploy ever. This is a feature, not a limitation. No enterprise buyer will trust a system that autonomously rewrites their production code. The approve step is what makes the product trustworthy.

**3. Repository as input, not individual files**
Reading the full repo context (especially README) gives the system intent, not just implementation. This is how the domain model is accurate without the user writing lengthy descriptions.

**4. Docker isolation for every test run**
Non-negotiable for any real codebase. Protects the host machine, ensures clean state for every run, handles any language and dependency set.

**5. PM agent as single user interface**
The user talks to one agent. All the specialist agents work behind the scenes. This makes the product feel like a smart assistant, not a tangle of technical components.

**6. Project Knowledge Base grows over time**
The system gets smarter about each project with every test run. This is the moat — after six months of test history, ShadowOps understands a customer's agent better than any new tool could.

**7. Model agnostic from day one**
All LLM calls go through llm_client.py. Every agent can run on a different model. Customers choose their own providers and control their own costs.

**8. Python first, then other languages**
Most AI agents being built today are Python. Validating the platform with Python before expanding to Node.js keeps the Docker complexity manageable.

**9. Anonymised attack library**
Successful attack patterns are stored without org-specific data. Every new project benefits from attacks that worked on similar agents across the platform. This compounds over time into a genuine competitive advantage.

**10. Cost transparency at every level**
Every agent call, every test run, every token is tracked and shown to the user. This builds trust and helps customers optimise. It also makes the usage-based pricing feel fair.

---

*ShadowOps Full Product Specification | Version 2.0 | June 2026*
*Next step: review this document, confirm or adjust any decisions, then begin Phase 2 development*

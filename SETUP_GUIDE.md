# ShadowOps — Complete Setup Guide for Windows (Beginner Friendly)

This guide assumes you have nothing installed yet. Follow every step in order. Do not skip ahead.

---

## Part 1 — Install the Required Software

### 1.1 Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click the big yellow "Download Python" button (it auto-detects Windows)
3. Run the installer
4. **CRITICAL:** On the first install screen, check the box at the bottom that says **"Add python.exe to PATH"** — if you miss this, nothing will work later
5. Click "Install Now"
6. After install completes, open **Command Prompt** (press Windows key, type `cmd`, press Enter)
7. Type this and press Enter to verify:
   ```
   python --version
   ```
   You should see something like `Python 3.12.x`. If you see an error, restart your computer and try again.

---

### 1.2 Install Git

1. Go to [git-scm.com/download/win](https://git-scm.com/download/win)
2. Download will start automatically
3. Run the installer — click "Next" through all screens, the defaults are fine
4. Verify in Command Prompt:
   ```
   git --version
   ```

---

### 1.3 Install Docker Desktop

This is the most important install — it runs PostgreSQL, Qdrant, and the agent test containers.

1. Go to [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
2. Download "Docker Desktop for Windows"
3. Run the installer
4. **If prompted about WSL 2** — click "Install" when asked. This is required.
5. Restart your computer when the installer asks you to
6. After restart, Docker Desktop should open automatically. If not, find it in your Start Menu and open it.
7. Wait until you see "Docker Desktop is running" (the whale icon in your system tray stops animating)
8. Verify in Command Prompt:
   ```
   docker --version
   ```

**Common issue:** If Docker says "WSL 2 installation is incomplete" — go to [aka.ms/wsl2kernel](https://aka.ms/wsl2kernel), download and run that installer, then restart Docker Desktop.

---

### 1.4 Install Node.js (for the dashboard)

1. Go to [nodejs.org](https://nodejs.org/)
2. Download the **LTS version** (left button, not "Current")
3. Run the installer — defaults are fine, click Next through everything
4. Verify in Command Prompt:
   ```
   node --version
   npm --version
   ```

---

### 1.5 Install Ollama (for free local AI models)

1. Go to [ollama.com](https://ollama.com/)
2. Click "Download for Windows"
3. Run the installer
4. Ollama runs in your system tray automatically after install
5. Open Command Prompt and pull the model:
   ```
   ollama pull llama3
   ```
   This downloads about 4.7GB — it will take a few minutes depending on your internet speed.
6. Verify it works:
   ```
   ollama run llama3
   ```
   Type "hello" and press Enter. You should get a response. Press `Ctrl+D` to exit.

---

## Part 2 — Set Up the ShadowOps Project

### 2.1 Extract the project files

1. Find the `shadowops-v2.zip` file you downloaded
2. Right-click it → "Extract All" → choose a simple location like `C:\Projects\shadowops-v2`
3. Avoid folder paths with spaces or special characters

---

### 2.2 Open the project in Command Prompt

1. Open Command Prompt
2. Navigate to the folder (replace with your actual path):
   ```
   cd C:\Projects\shadowops-v2
   ```

---

### 2.3 Create a Python virtual environment

A virtual environment keeps this project's Python packages separate from everything else on your computer.

```
python -m venv venv
```

Activate it:

```
venv\Scripts\activate
```

You should now see `(venv)` at the start of your Command Prompt line. **You need to run this activate command every time you open a new Command Prompt window to work on this project.**

---

### 2.4 Install Python dependencies

```
pip install -r requirements.txt
```

This will take a few minutes — it installs LangGraph, FastAPI, SQLAlchemy, Docker SDK, and everything else listed in `requirements.txt`.

If you see an error about Microsoft C++ Build Tools, go to [visualstudio.microsoft.com/visual-cpp-build-tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/), download and install it with default settings, then re-run the pip install command.

---

### 2.5 Set up your environment file

1. In the project folder, find `.env.example`
2. Copy it and rename the copy to `.env`
   - In Command Prompt: `copy .env.example .env`
3. Open `.env` in Notepad:
   ```
   notepad .env
   ```
4. For now, leave everything as default — Ollama needs no API key. Save and close.

---

### 2.6 Start PostgreSQL and Qdrant with Docker Compose

Make sure Docker Desktop is running (check your system tray for the whale icon), then:

```
docker compose up -d
```

This starts two containers in the background — PostgreSQL (the database) and Qdrant (vector storage).

Verify they are running:

```
docker ps
```

You should see two containers listed: `shadowops_postgres` and `shadowops_qdrant`.

---

### 2.7 Initialise the database

This creates all the tables ShadowOps needs.

```
python -c "from core.database import init_db; init_db()"
```

You should see: `[Database] All tables created successfully.`

---

### 2.8 Create the Qdrant collection

```
python -c "from core.knowledge_base import ensure_collection_exists; ensure_collection_exists()"
```

You should see: `[Knowledge Base] Created Qdrant collection 'project_knowledge'`

---

## Part 3 — Run ShadowOps for the First Time

### 3.1 Run the terminal-mode test

This runs Phase A and Phase B against the included sample target agent.

```
python main.py
```

When prompted for a repository, type:
```
./sample-target-repo
```

This points ShadowOps at the sample vulnerable refund agent included in the project. It will:
1. Read the README and code
2. Build a domain model
3. Possibly ask you a clarifying question — answer it honestly
4. Start a Docker container running the sample agent
5. Run the chaos attacker against it
6. Show you vulnerabilities found and patches proposed
7. Ask you to approve or reject each patch with `y` or `n`

**This first run will take a few minutes** — Llama 3 running locally on CPU is slower than cloud models. This is expected.

---

### 3.2 Run the dashboard (optional, for the visual experience)

**Open a SECOND Command Prompt window** (keep the first one if anything is running), activate the virtual environment again, then start the API:

```
cd C:\Projects\shadowops-v2
venv\Scripts\activate
uvicorn api.main:app --reload --port 8000
```

Leave this running. Open a **THIRD** Command Prompt window for the frontend:

```
cd C:\Projects\shadowops-v2\shadowops-ui
npm install
npm run dev
```

Open your browser to [http://localhost:3000](http://localhost:3000)

---

## Part 4 — Customising Your Models

Open `core/agent_models.py` in Notepad or any code editor (VS Code recommended — free from [code.visualstudio.com](https://code.visualstudio.com/)).

Every agent has its own block. To switch one agent to a cloud model:

```python
"synthesizer": {
    "provider": "openai",       # change from "ollama"
    "model": "gpt-4o",          # change from "llama3"
    "temperature": 0.2,
},
```

Then add your API key to `.env`:
```
OPENAI_API_KEY=sk-your-key-here
```

Save both files. Next time you run `python main.py`, that agent automatically uses the new model. No other code changes needed.

---

## Troubleshooting

**"docker compose" command not found**
→ Update Docker Desktop to the latest version. Older versions use `docker-compose` (with a hyphen) instead.

**"Connection refused" errors when running main.py**
→ Check Docker Desktop is open and running
→ Check Ollama is running (look for its icon in your system tray)
→ Run `docker ps` to confirm postgres and qdrant containers are up

**pip install fails with a long error about wheels**
→ Make sure your virtual environment is activated — you should see `(venv)` in your prompt
→ Try: `python -m pip install --upgrade pip` then re-run the install

**Llama 3 responses are very slow**
→ This is normal on CPU-only machines. Each agent call can take 10-30 seconds.
→ If you have a few hours of patience saved up, consider upgrading just the agents that need it most (Evaluator, Synthesizer) to a cloud model — see Part 4 above.

**Docker build fails when testing the sample repo**
→ Make sure Docker Desktop has enough resources allocated. Open Docker Desktop → Settings → Resources → increase memory to at least 4GB.

**"ModuleNotFoundError" when running any Python file**
→ Your virtual environment is not activated. Run `venv\Scripts\activate` first.

---

## Daily Workflow (after initial setup)

Every time you want to work on ShadowOps:

1. Open Command Prompt
2. `cd C:\Projects\shadowops-v2`
3. `venv\Scripts\activate`
4. Make sure Docker Desktop is open
5. Make sure Ollama is running (check system tray)
6. `docker compose up -d` (starts postgres and qdrant if not already running)
7. Run whatever you need: `python main.py` or `uvicorn api.main:app --reload --port 8000`

To stop everything cleanly when you're done:
```
docker compose down
```

This stops PostgreSQL and Qdrant but keeps your data saved for next time.

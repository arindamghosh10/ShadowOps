# =============================================================================
# agents/intelligence/repository_scanner.py — Repository Scanner
#
# LEARNING NOTE — Selective reading strategy
#
# A real repository can have hundreds of files. Reading everything wastes
# tokens and money. This scanner uses a smart strategy:
#
#   1. Clone the repo (or use an already-cloned path)
#   2. Read ALL .md files in full — they explain intent cheaply
#   3. Build a file tree WITHOUT reading file contents
#   4. Identify likely "agent files" using naming patterns and imports
#   5. Only fully read the identified agent files
#
# This keeps token usage proportional to the actual agent logic, not
# the size of the whole repository.
# =============================================================================

import os
import subprocess
import tempfile
from pathlib import Path


# Patterns that suggest a file contains agent/LLM logic — used to filter
# which files get fully read vs just listed in the file tree
AGENT_FILE_SIGNALS = [
    "agent", "bot", "assistant", "llm", "prompt", "chain", "chat",
    "gpt", "claude", "openai", "anthropic", "langchain", "langgraph",
]

# Files and folders to always skip — they never contain agent logic
SKIP_PATTERNS = [
    "node_modules", ".git", "__pycache__", "venv", ".venv", "dist",
    "build", ".next", "test", "tests", "migrations", ".pytest_cache",
    "package-lock.json", "yarn.lock",
]


def scan_repository(repo_url: str, branch: str = "main") -> dict:
    """
    Clones a repository and performs selective scanning.

    Args:
        repo_url: GitHub/GitLab URL, e.g. "https://github.com/user/repo"
        branch: Branch to scan, default "main"

    Returns:
        {
            "readme_content": str,
            "doc_files": {filename: content},
            "file_tree": list of all file paths (no content),
            "agent_files": {filename: content},
            "stack": str,            — detected primary language
            "entry_point": str,      — best guess at main file
            "local_path": str,       — where it was cloned, for later use
        }
    """
    local_path = _clone_repo(repo_url, branch)

    file_tree = _build_file_tree(local_path)
    doc_files = _read_markdown_files(local_path, file_tree)
    readme_content = doc_files.get("README.md", "") or doc_files.get("readme.md", "")

    stack = _detect_stack(file_tree)
    agent_file_paths = _identify_agent_files(file_tree, stack)
    agent_files = _read_files(local_path, agent_file_paths)

    entry_point = _guess_entry_point(file_tree, stack)

    print(f"[Repository Scanner] Stack detected: {stack}")
    print(f"[Repository Scanner] Found {len(doc_files)} doc files")
    print(f"[Repository Scanner] Identified {len(agent_files)} agent files to read fully")
    print(f"[Repository Scanner] Entry point guess: {entry_point}")

    return {
        "readme_content": readme_content,
        "doc_files": doc_files,
        "file_tree": file_tree,
        "agent_files": agent_files,
        "stack": stack,
        "entry_point": entry_point,
        "local_path": local_path,
    }


def _clone_repo(repo_url: str, branch: str) -> str:
    """Clones the repo into a temporary directory and returns the path."""
    temp_dir = tempfile.mkdtemp(prefix="shadowops_")

    print(f"[Repository Scanner] Cloning {repo_url} (branch: {branch})...")
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, repo_url, temp_dir],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to clone repository: {result.stderr}")

    return temp_dir


def _build_file_tree(root_path: str) -> list[str]:
    """Walks the repo and returns a list of all file paths (relative), skipping noise."""
    file_paths = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Skip noisy directories in-place so os.walk doesn't descend into them
        dirnames[:] = [d for d in dirnames if not any(skip in d for skip in SKIP_PATTERNS)]

        for filename in filenames:
            if any(skip in filename for skip in SKIP_PATTERNS):
                continue
            rel_path = os.path.relpath(os.path.join(dirpath, filename), root_path)
            file_paths.append(rel_path)

    return file_paths


def _read_markdown_files(root_path: str, file_tree: list[str]) -> dict:
    """Reads the full content of every markdown file — these are cheap and high-value."""
    md_files = {}
    for path in file_tree:
        if path.endswith(".md") or path.endswith(".mdx"):
            full_path = os.path.join(root_path, path)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    md_files[path] = f.read()
            except Exception:
                continue
    return md_files


def _detect_stack(file_tree: list[str]) -> str:
    """Guesses the primary language/stack from file presence."""
    if any(f == "requirements.txt" or f == "pyproject.toml" for f in file_tree):
        return "python"
    if any(f == "package.json" for f in file_tree):
        return "node"
    if any(f.endswith(".go") for f in file_tree):
        return "go"
    return "unknown"


def _identify_agent_files(file_tree: list[str], stack: str) -> list[str]:
    """
    Returns file paths likely to contain agent/LLM logic, based on
    filename signals. This is what keeps token usage low — we don't
    read every file, just the ones that matter.
    """
    extension = ".py" if stack == "python" else ".js" if stack == "node" else ".ts"

    candidates = []
    for path in file_tree:
        path_lower = path.lower()
        if not (path_lower.endswith(".py") or path_lower.endswith(".js") or path_lower.endswith(".ts")):
            continue
        if any(signal in path_lower for signal in AGENT_FILE_SIGNALS):
            candidates.append(path)

    # Fallback: if nothing matched the signals, take main.py / app.py / index.js
    if not candidates:
        common_entry_names = ["main.py", "app.py", "index.js", "server.js", "app.js"]
        candidates = [p for p in file_tree if os.path.basename(p) in common_entry_names]

    # Cap at 15 files to keep token usage bounded even for large repos
    return candidates[:15]


def _read_files(root_path: str, file_paths: list[str]) -> dict:
    """Reads full content of the given file paths."""
    contents = {}
    for path in file_paths:
        full_path = os.path.join(root_path, path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                contents[path] = f.read()
        except Exception as e:
            print(f"[Repository Scanner] Could not read {path}: {e}")
    return contents


def _guess_entry_point(file_tree: list[str], stack: str) -> str:
    """Best-effort guess at the main entry point file."""
    common_names = {
        "python": ["main.py", "app.py", "run.py", "server.py"],
        "node": ["index.js", "server.js", "app.js", "main.js"],
    }
    candidates = common_names.get(stack, [])

    for path in file_tree:
        if os.path.basename(path) in candidates:
            return path

    return file_tree[0] if file_tree else ""

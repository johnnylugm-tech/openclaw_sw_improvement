#!/opt/homebrew/bin/python3.12
"""
Setup Target: Clone GitHub repo or use local path, write crg_status.json.

Each target is cloned to a temporary directory to avoid side effects.
"""

import sys
import subprocess
import sqlite3
from pathlib import Path
import tempfile
import json


# ---------------------------------------------------------------------------
# CRG sqlite3.Row patch (Python 3.12 bug: no .get() method)
# Applied once at startup; idempotent.
# ---------------------------------------------------------------------------
CRG_GRAPH_PY = Path("/opt/homebrew/lib/python3.12/site-packages/code_review_graph/graph.py")

def _apply_crg_patch():
    """Patch graph.py to add RowWithGet class if not already present."""
    if not CRG_GRAPH_PY.exists():
        return  # CRG not installed, skip
    content = CRG_GRAPH_PY.read_text()
    if "class RowWithGet" in content:
        return  # already patched

    class_def = '''
# --- OpenClaw CRG patch: sqlite3.Row has no .get() in Python 3.12 ---
class RowWithGet(sqlite3.Row):
    def get(self, key, default=None):
        try:
            return sqlite3.Row.__getitem__(self, key)
        except (KeyError, IndexError, TypeError):
            return default
'''
    # Inject after 'import sqlite3\n'
    patched = content.replace("import sqlite3\n", "import sqlite3\n" + class_def + "\n", 1)
    patched = patched.replace("self._conn.row_factory = sqlite3.Row",
                                "self._conn.row_factory = RowWithGet")
    CRG_GRAPH_PY.write_text(patched)
    print("[CRG] Patched graph.py for Python 3.12 sqlite3.Row.get()",
          file=sys.stderr)

_apply_crg_patch()


def clone_repo(github_url):
    """Clone GitHub repo to temporary directory."""
    temp_dir = tempfile.mkdtemp(prefix="openclaw-sw-")
    try:
        subprocess.run(
            ["git", "clone", github_url, temp_dir],
            check=True,
            capture_output=True,
            timeout=300,
        )
        return temp_dir
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}", file=sys.stderr)
        sys.exit(1)


def setup_git(repo_path):
    """Initialize git tracking if not already a git repo."""
    repo_path = Path(repo_path)
    if (repo_path / ".git").exists():
        return True
    try:
        subprocess.run(
            ["git", "-C", str(repo_path), "init"],
            check=True, capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "config", "user.email", "openclaw@local"],
            check=True, capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "config", "user.name", "OpenClaw"],
            check=True, capture_output=True, timeout=10,
        )
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error initializing git: {e}", file=sys.stderr)
        sys.exit(1)


def resolve_target(target):
    """Resolve target: clone GitHub URL or use local folder."""
    if target.startswith("http://") or target.startswith("https://"):
        print(f"Cloning repository: {target}", file=sys.stderr)
        target_path = clone_repo(target)
    elif target.startswith("git@"):
        print(f"Cloning repository: {target}", file=sys.stderr)
        target_path = clone_repo(target)
    else:
        target_path = str(Path(target).absolute())
        if not Path(target_path).exists():
            print(f"Error: path does not exist: {target_path}", file=sys.stderr)
            sys.exit(1)
    setup_git(target_path)
    return target_path


def init_crg(repo_path: str, work_dir: str) -> dict:
    """Check CRG availability, write status to work_dir/crg_status.json."""
    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)

    # Try to run crg_wrapper.py to check availability
    scripts_dir = work_path.parent / "scripts"
    crg_script = scripts_dir / "crg_wrapper.py"
    status = {"available": False, "reason": "crg_wrapper not found"}

    if crg_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(crg_script), "stats", repo_path],
                capture_output=True, text=True, timeout=60,
            )
            if result.stdout.strip():
                stats = json.loads(result.stdout)
                status = {
                    "available": stats.get("available", False),
                    "node_count": stats.get("node_count", 0),
                    "reason": stats.get("reason", "ok"),
                }
        except Exception as e:
            status = {"available": False, "reason": str(e)[:120]}

    status_file = work_path / "crg_status.json"
    with open(status_file, "w") as f:
        json.dump(status, f, indent=2)

    if status["available"]:
        nodes = status.get("node_count", "?")
        print(f"[CRG] Ready — {nodes} nodes", file=sys.stderr)
    else:
        print(f"[CRG] Not available — {status.get('reason', 'unknown')}. "
              f"Framework will run without CRG.", file=sys.stderr)

    return status


def main():
    if len(sys.argv) < 2:
        target = "."
    else:
        target = sys.argv[1]
    work_dir = sys.argv[2] if len(sys.argv) > 2 else ".sessi-work"

    try:
        target_path = resolve_target(target)
        init_crg(target_path, work_dir)
        print(target_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

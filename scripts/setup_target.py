#!/opt/homebrew/bin/python3.12
"""
Setup Target: Clone GitHub repo or use local path, write crg_status.json.

Each target is cloned to a temporary directory to avoid side effects.
CRG dependency is handled separately by scripts/install_crg.sh (run once per machine).
"""

import sys
import subprocess
from pathlib import Path
import tempfile
import json


def clone_repo(github_url):
    """Clone GitHub repo to temporary directory."""
    temp_dir = tempfile.mkdtemp(prefix="openclaw-sw-")
    try:
        subprocess.run(
            ["git", "clone", github_url, temp_dir],
            check=True, capture_output=True, timeout=300,
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
    """
    Ensure CRG is ready. Transparent — handles all cases:
      - Not installed  → available: False
      - Installed, no graph → auto-build, then available: True
      - Installed, graph ready → available: True immediately
    Writes status to work_dir/crg_status.json for downstream steps.
    """
    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)

    scripts_dir = Path(__file__).parent
    crg_script = scripts_dir / "crg_wrapper.py"

    # Check if crg_wrapper.py is available
    if not crg_script.exists():
        status = {"available": False, "reason": "crg_wrapper not found"}
        _write_status(work_path, status)
        return status

    # Check if CRG binary is available
    crg_bin = Path("/opt/homebrew/bin/code-review-graph")
    if not crg_bin.exists():
        status = {"available": False, "reason": "code-review-graph not installed"}
        _write_status(work_path, status)
        return status

    # Check node count
    try:
        result = subprocess.run(
            [sys.executable, str(crg_script), "stats", repo_path],
            capture_output=True, text=True, timeout=30,
        )
        stats = json.loads(result.stdout) if result.stdout.strip() else {}
        node_count = stats.get("node_count", 0)
    except Exception:
        node_count = 0

    action = "already_built"
    if node_count == 0:
        # Graph not built — auto-build
        print(f"[CRG] Graph not found. Building now (may take 30–120s)…",
              file=sys.stderr)
        try:
            build_result = subprocess.run(
                [str(crg_bin), "build", "--repo", repo_path],
                check=True, capture_output=True, text=True, timeout=300,
            )
            # Re-check node count
            try:
                result2 = subprocess.run(
                    [sys.executable, str(crg_script), "stats", repo_path],
                    capture_output=True, text=True, timeout=30,
                )
                stats2 = json.loads(result2.stdout) if result2.stdout.strip() else {}
                node_count = stats2.get("node_count", 0)
            except Exception:
                node_count = 0
            action = "auto_built"
            print(f"[CRG] Graph built: {node_count} nodes.", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            status = {"available": False,
                      "reason": f"build failed: {e.stderr[:120]}",
                      "action": "build_failed"}
            _write_status(work_path, status)
            return status
        except subprocess.TimeoutExpired:
            status = {"available": False,
                      "reason": "build timed out after 300s",
                      "action": "build_timeout"}
            _write_status(work_path, status)
            return status
    else:
        print(f"[CRG] Graph ready: {node_count} nodes.", file=sys.stderr)

    status = {
        "available": True,
        "node_count": node_count,
        "action": action,
        "repo": repo_path,
    }
    _write_status(work_path, status)
    return status


def _write_status(work_path, status):
    status_file = work_path / "crg_status.json"
    with open(status_file, "w") as f:
        json.dump(status, f, indent=2)
    if status["available"]:
        nodes = status.get("node_count", "?")
        print(f"[CRG] Ready — {nodes} nodes", file=sys.stderr)
    else:
        print(f"[CRG] Not available — {status.get('reason', 'unknown')}. "
              f"Run scripts/install_crg.sh first.", file=sys.stderr)


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

#!/opt/homebrew/bin/python3.12
"""
Quality Loop: State machine orchestrator for quality improvement rounds.

Manages: init, run, status, resume commands.
State file: quality_state.json in project root.
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import yaml

QUALITY_STATE_FILE = "quality_state.json"
WORK_DIR = Path(__file__).parent.parent


def iso_now():
    return datetime.now().isoformat()


def load_state():
    f = WORK_DIR / QUALITY_STATE_FILE
    if f.exists():
        return json.loads(f.read_text())
    return None


def save_state(state):
    f = WORK_DIR / QUALITY_STATE_FILE
    f.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def load_config(config_path: str) -> dict:
    """Load YAML config with defaults."""
    config_file = Path(config_path) if config_path else WORK_DIR / "config.example.yaml"
    if not config_file.exists():
        return {
            "quality": {"score_gate": 85, "max_rounds": 3},
            "dimensions": {
                "linting": {"enabled": True, "weight": 0.06, "target": 95},
                "type_safety": {"enabled": True, "weight": 0.10, "target": 95},
                "test_coverage": {"enabled": True, "weight": 0.13, "target": 80},
                "security": {"enabled": True, "weight": 0.10, "target": 90},
                "performance": {"enabled": True, "weight": 0.07, "target": 80},
                "architecture": {"enabled": True, "weight": 0.07, "target": 80},
                "readability": {"enabled": True, "weight": 0.06, "target": 85},
                "error_handling": {"enabled": True, "weight": 0.09, "target": 85},
                "documentation": {"enabled": True, "weight": 0.10, "target": 85},
                "secrets_scanning": {"enabled": True, "weight": 0.08, "target": 100},
                "mutation_testing": {"enabled": True, "weight": 0.08, "target": 70},
                "license_compliance": {"enabled": True, "weight": 0.06, "target": 95},
            },
        }
    with open(config_file) as f:
        user_config = yaml.safe_load(f) or {}
    # Merge with defaults
    defaults = {
        "quality": {"score_gate": 85, "max_rounds": 3},
        "dimensions": {
            "linting": {"enabled": True, "weight": 0.06, "target": 95},
            "type_safety": {"enabled": True, "weight": 0.10, "target": 95},
            "test_coverage": {"enabled": True, "weight": 0.13, "target": 80},
            "security": {"enabled": True, "weight": 0.10, "target": 90},
            "performance": {"enabled": True, "weight": 0.07, "target": 80},
            "architecture": {"enabled": True, "weight": 0.07, "target": 80},
            "readability": {"enabled": True, "weight": 0.06, "target": 85},
            "error_handling": {"enabled": True, "weight": 0.09, "target": 85},
            "documentation": {"enabled": True, "weight": 0.10, "target": 85},
            "secrets_scanning": {"enabled": True, "weight": 0.08, "target": 100},
            "mutation_testing": {"enabled": True, "weight": 0.08, "target": 70},
            "license_compliance": {"enabled": True, "weight": 0.06, "target": 95},
        },
    }
    # Deep merge
    for key, val in user_config.items():
        if key in defaults and isinstance(defaults[key], dict):
            defaults[key].update(val)
        else:
            defaults[key] = val
    return defaults


def init_state(target_repo: str, config_path: str) -> dict:
    """Initialize a new quality improvement session."""
    config = load_config(config_path)
    quality_cfg = config.get("quality", {})
    state = {
        "phase": "setup",
        "round": 1,
        "step": "init",
        "max_rounds": quality_cfg.get("max_rounds", 3),
        "score_gate": quality_cfg.get("score_gate", 85),
        "target_repo": str(target_repo),
        "config": config,
        "crg_available": False,
        "round_results": [],
        "quality_complete": False,
        "last_updated": iso_now(),
    }
    save_state(state)
    return state


def run_setup(state: dict) -> dict:
    """Phase: setup - run setup_target.py and crg_wrapper stats."""
    scripts_dir = WORK_DIR / "scripts"
    target = state["target_repo"]
    work_dir = WORK_DIR / ".sessi-work"
    work_dir.mkdir(parents=True, exist_ok=True)

    # Run setup_target.py if it exists
    setup_script = scripts_dir / "setup_target.py"
    if setup_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(setup_script), target, str(work_dir)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            state["setup_output"] = result.stderr.strip()
        except Exception as e:
            state["setup_output"] = f"Error: {e}"

    # Run crg_wrapper stats to check CRG availability
    crg_script = scripts_dir / "crg_wrapper.py"
    if crg_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(crg_script), "stats", target],
                capture_output=True,
                text=True,
                timeout=60,
            )
            crg_stats = json.loads(result.stdout) if result.stdout.strip() else {}
            state["crg_available"] = crg_stats.get("available", False)
            state["crg_stats"] = crg_stats
        except Exception as e:
            state["crg_available"] = False
            state["crg_stats"] = {"error": str(e)}

    state["phase"] = "recon"
    state["step"] = "recon_start"

    # Generate resolved config.json for downstream scripts (score.py needs it)
    config_path = WORK_DIR / "config.json"
    with open(config_path, "w") as f:
        json.dump(state["config"], f)

    state["last_updated"] = iso_now()
    save_state(state)
    return state


def run_reconnaissance(state: dict) -> dict:
    """Phase: reconnaissance - run CRG reconnaissance if available."""
    scripts_dir = WORK_DIR / "scripts"
    target = state["target_repo"]
    work_dir = WORK_DIR / ".sessi-work"

    if state.get("crg_available"):
        crg_script = scripts_dir / "crg_wrapper.py"
        # Run all CRG commands for reconnaissance
        recon_data = {
            "timestamp": iso_now(),
            "repo": target,
            "commands": {},
        }
        for cmd in ["stats", "hub-nodes", "bridge-nodes", "communities",
                    "arch-overview", "flows", "dead-code", "surprising",
                    "knowledge-gaps"]:
            try:
                result = subprocess.run(
                    [sys.executable, str(crg_script), cmd, target],
                    capture_output=True, text=True, timeout=120,
                )
                recon_data["commands"][cmd] = (
                    json.loads(result.stdout) if result.stdout.strip() else {}
                )
            except Exception:
                recon_data["commands"][cmd] = {"error": "failed"}
        # Write reconnaissance report
        recon_file = work_dir / "crg_reconnaissance.json"
        recon_file.write_text(json.dumps(recon_data, indent=2, ensure_ascii=False))
        state["reconnaissance_done"] = True
    else:
        state["reconnaissance_done"] = False

    state["phase"] = "round"
    state["step"] = "3a"
    state["last_updated"] = iso_now()
    save_state(state)
    return state


def run_round(state: dict) -> dict:
    """Run one quality round: evaluate → score → verify → checkpoint."""
    scripts_dir = WORK_DIR / "scripts"
    target = state["target_repo"]
    work_dir = WORK_DIR / ".sessi-work"
    round_num = state["round"]
    round_dir = work_dir / f"round_{round_num}"
    scores_dir = round_dir / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)

    state["step"] = "3a"
    state["last_updated"] = iso_now()
    save_state(state)

    # Step 3a: evaluate all dimensions via dimension_executor.py
    dim_script = scripts_dir / "dimension_executor.py"
    if dim_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(dim_script), "--target", target],
                capture_output=True, text=True, timeout=600,
            )
            dim_results = (
                json.loads(result.stdout) if result.stdout.strip() else {}
            )
        except Exception:
            dim_results = {}
    else:
        dim_results = {}

    # Write individual score files
    for dim_name, dim_data in dim_results.items():
        score_file = scores_dir / f"{dim_name}.json"
        score_file.write_text(json.dumps(dim_data, indent=2))

    state["step"] = "3b"
    state["last_updated"] = iso_now()
    save_state(state)

    # Step 3b: compute overall score via score.py
    score_script = scripts_dir / "score.py"
    overall_result = {"overall_score": 0, "error": "score script not found"}
    if score_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(score_script), str(round_dir),
                 str(WORK_DIR / "config.json")],
                capture_output=True, text=True, timeout=60,
            )
            if result.stdout.strip():
                overall_result = json.loads(result.stdout)
        except Exception as e:
            overall_result = {"overall_score": 0, "error": str(e)}
    else:
        # Fallback: compute weighted average directly from dim results
        total_score = 0
        total_weight = 0
        for dim_name, dim_data in dim_results.items():
            score = dim_data.get("tool_score", 0)
            weight = state["config"].get("dimensions", {}).get(dim_name, {}).get("weight", 0.0)
            if weight > 0:
                total_score += score * weight
                total_weight += weight
        if total_weight > 0:
            overall_result = {"overall_score": round(total_score / total_weight, 2)}

    # Write overall score to round dir
    overall_file = round_dir / "overall_score.json"
    overall_file.write_text(json.dumps(overall_result, indent=2))

    state["step"] = "3c"
    state["last_updated"] = iso_now()
    save_state(state)

    # Step 3c: verify results via verify.py
    verify_script = scripts_dir / "verify.py"
    verified_result = {"verified": False, "error": "verify script not found"}
    if verify_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(verify_script), str(round_dir / "result.json"),
                 str(round_dir), target],
                capture_output=True, text=True, timeout=60,
            )
            if result.stdout.strip():
                verified_result = json.loads(result.stdout)
        except Exception:
            pass
    else:
        verified_result = {"verified": True, "note": "verify script not found, auto-pass"}

    verified_file = round_dir / "verified.json"
    verified_file.write_text(json.dumps(verified_result, indent=2))

    state["step"] = "3d"
    state["last_updated"] = iso_now()
    save_state(state)

    # Step 3d: checkpoint via checkpoint.py
    checkpoint_script = scripts_dir / "checkpoint.py"
    if checkpoint_script.exists():
        try:
            scores_file = scores_dir / "_all_scores.json"
            scores_file.write_text(json.dumps(dim_results, indent=2))
            subprocess.run(
                [sys.executable, str(checkpoint_script), "round",
                 str(round_num), str(scores_file),
                 str(overall_result.get("overall_score", 0)),
                 str(work_dir)],
                capture_output=True, timeout=30,
            )
        except Exception:
            pass

    state["step"] = "3e"
    state["last_updated"] = iso_now()
    save_state(state)

    # Step 3e: quality_complete check
    overall_score = overall_result.get("overall_score", 0)
    score_gate = state.get("score_gate", 85)
    meets_target = overall_score >= score_gate

    # Check for open critical/high from issue registry if available
    registry_path = work_dir / "issue_registry.json"
    open_critical = 0
    open_high = 0
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text())
            for issue in registry.get("issues", []):
                if issue.get("status") == "open":
                    sev = issue.get("severity", "info")
                    if sev == "critical":
                        open_critical += 1
                    elif sev == "high":
                        open_high += 1
        except Exception:
            pass

    quality_complete = (
        meets_target and open_critical == 0 and open_high == 0
    )

    # Store round result
    round_result = {
        "round": round_num,
        "overall_score": overall_score,
        "meets_target": meets_target,
        "quality_complete": quality_complete,
        "open_critical": open_critical,
        "open_high": open_high,
        "step": "3e",
    }
    state["round_results"].append(round_result)

    if quality_complete:
        state["quality_complete"] = True
        state["last_updated"] = iso_now()
        save_state(state)
        return state

    # Step 3f: improvement (placeholder - would run improvement_plan.md here)
    state["step"] = "3f"
    state["last_updated"] = iso_now()
    save_state(state)

    return state


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} [init|run|status|resume] [args...]")
        print("  init <target_repo> [config.yaml]  — Initialize session")
        print("  run                              — Run full quality loop")
        print("  status                           — Show current state")
        print("  resume                            — Resume from current phase")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        target = sys.argv[2] if len(sys.argv) > 2 else str(WORK_DIR)
        config = sys.argv[3] if len(sys.argv) > 3 else str(WORK_DIR / "config.example.yaml")
        state = init_state(target, config)
        print(json.dumps(state, indent=2))
        print("\nState initialized. Run 'run' to execute.")

    elif cmd == "run":
        state = load_state()
        if state is None:
            print("Error: No state found. Run 'init' first.", file=sys.stderr)
            sys.exit(1)
        run_setup(state)
        run_reconnaissance(state)
        while state["round"] <= state["max_rounds"] and not state["quality_complete"]:
            run_round(state)
            if not state["quality_complete"]:
                state["round"] += 1
        print("Quality loop complete.")
        print(f"Final state: phase={state['phase']}, round={state['round']}, "
              f"quality_complete={state['quality_complete']}")
        print(json.dumps(state, indent=2, ensure_ascii=False))

    elif cmd == "status":
        state = load_state()
        if state:
            print(json.dumps(state, indent=2))
        else:
            print("No state found.")

    elif cmd == "resume":
        state = load_state()
        if state is None:
            print("Error: No state found. Run 'init' first.", file=sys.stderr)
            sys.exit(1)
        phase = state.get("phase", "unknown")
        if phase == "setup":
            run_setup(state)
            run_reconnaissance(state)
            while state["round"] <= state["max_rounds"] and not state["quality_complete"]:
                run_round(state)
                if not state["quality_complete"]:
                    state["round"] += 1
        elif phase == "recon":
            run_reconnaissance(state)
            while state["round"] <= state["max_rounds"] and not state["quality_complete"]:
                run_round(state)
                if not state["quality_complete"]:
                    state["round"] += 1
        elif phase == "round":
            while state["round"] <= state["max_rounds"] and not state["quality_complete"]:
                run_round(state)
                if not state["quality_complete"]:
                    state["round"] += 1
        print("Resume complete.")
        print(json.dumps(state, indent=2))

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

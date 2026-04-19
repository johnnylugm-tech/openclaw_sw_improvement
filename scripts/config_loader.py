#!/opt/homebrew/bin/python3.12
"""
Config Loader: YAML → JSON resolver with defaults merging and weight normalization.

Removes Gemini-specific routing, unifies all LLM calls to MiniMax M2.7.
"""

import os
import sys
import json
import yaml
from pathlib import Path

DEFAULT_CONFIG = {
    "version": "1.0",
    "quality": {
        "score_gate": 85,
        "max_rounds": 3,
        "early_stop": True,
        "saturation_rounds": 3,
        "commit_per_fix": True,
    },
    "workspace": {
        "work_dir": ".sessi-work",
        "preserve_git": True,
    },
    "dimensions": {
        "linting": {"enabled": True, "weight": 0.06, "target": 95, "tools": []},
        "type_safety": {"enabled": True, "weight": 0.10, "target": 95, "tools": []},
        "test_coverage": {"enabled": True, "weight": 0.13, "target": 80, "tools": []},
        "security": {"enabled": True, "weight": 0.10, "target": 90, "tools": []},
        "performance": {"enabled": True, "weight": 0.07, "target": 80, "tools": []},
        "architecture": {"enabled": True, "weight": 0.07, "target": 80, "tools": []},
        "readability": {"enabled": True, "weight": 0.06, "target": 85, "tools": []},
        "error_handling": {"enabled": True, "weight": 0.09, "target": 85, "tools": []},
        "documentation": {"enabled": True, "weight": 0.10, "target": 85, "tools": []},
        "secrets_scanning": {"enabled": True, "weight": 0.08, "target": 100, "tools": []},
        "mutation_testing": {"enabled": True, "weight": 0.08, "target": 70, "tools": [], "time_budget_seconds": 300},
        "license_compliance": {"enabled": True, "weight": 0.06, "target": 95, "tools": []},
        "property_testing": {"enabled": False, "weight": 0.07, "target": 75, "tools": []},
        "fuzzing": {"enabled": False, "weight": 0.08, "target": 70, "tools": []},
        "accessibility": {"enabled": False, "weight": 0.06, "target": 85, "tools": []},
        "observability": {"enabled": False, "weight": 0.05, "target": 80, "tools": []},
        "supply_chain_security": {"enabled": False, "weight": 0.06, "target": 80, "tools": []},
    },
    "scoring": {
        "reconcile_method": "min",
        "evidence_threshold": 10,
        "tool_diff_min_lines": 3,
        "cap_unsupported_delta": 3,
        "regression_detection": True,
        "revert_on_regression": True,
    },
    "evaluation": {
        "tool_first": True,
        "evidence_required": True,
        "per_dimension_depth": "thorough",
        "explain_gaps": True,
    },
    "llm_routing": {
        "enabled": True,
        "model": "minimax/MiniMax-M2.7",
        "provider": "minimax",
        "token_budget": {
            "input_max": 20000,
            "output_max": 4000,
        },
    },
}


def deep_merge(base, override):
    """Deep merge override dict into base dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def normalize_weights(config):
    """Normalize dimension weights to sum to 1.0 across enabled dimensions."""
    dimensions = config["dimensions"]
    enabled_dims = {k: v for k, v in dimensions.items() if v.get("enabled", False)}
    if not enabled_dims:
        raise ValueError("No dimensions enabled in config")
    total_weight = sum(d["weight"] for d in enabled_dims.values())
    if total_weight == 0:
        raise ValueError("Total weight of enabled dimensions is 0")
    for dim_name in enabled_dims:
        dimensions[dim_name]["weight"] = dimensions[dim_name]["weight"] / total_weight
    return config


def validate_config(config):
    """Validate config values are in valid ranges."""
    quality = config["quality"]
    if "score_gate" not in quality and "target" in quality:
        quality["score_gate"] = quality["target"]
    if "target" not in quality and "score_gate" in quality:
        quality["target"] = quality["score_gate"]
    score_gate = quality["score_gate"]
    if not (0 <= score_gate <= 100):
        raise ValueError(f"quality.score_gate must be 0-100, got {score_gate}")
    max_rounds = quality["max_rounds"]
    if max_rounds < 1:
        raise ValueError(f"quality.max_rounds must be >= 1, got {max_rounds}")
    saturation_rounds = quality.get("saturation_rounds", 3)
    if saturation_rounds < 1:
        raise ValueError(f"quality.saturation_rounds must be >= 1, got {saturation_rounds}")
    quality["saturation_rounds"] = saturation_rounds
    for dim_name, dim_config in config["dimensions"].items():
        if dim_config.get("enabled", False):
            dim_target = dim_config.get("target", 100)
            if not (0 <= dim_target <= 100):
                raise ValueError(
                    f"dimensions.{dim_name}.target must be 0-100, got {dim_target}"
                )
    return config


def load_config(config_path):
    """Load YAML config file."""
    if not Path(config_path).exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r") as f:
        user_config = yaml.safe_load(f) or {}
    return user_config


def apply_env_overrides(config):
    """Apply environment variable overrides."""
    routing = config.setdefault("llm_routing", {})
    model_env = os.environ.get("HARNESS_MODEL")
    if model_env:
        routing["model"] = model_env
    return config


def resolve(config_path):
    """Resolve config: load, merge, normalize, validate, apply env overrides."""
    user_config = load_config(config_path)
    resolved = deep_merge(DEFAULT_CONFIG, user_config)
    resolved = normalize_weights(resolved)
    resolved = validate_config(resolved)
    resolved = apply_env_overrides(resolved)
    return resolved


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <config.yaml>", file=sys.stderr)
        sys.exit(1)
    config_path = sys.argv[1]
    try:
        config = resolve(config_path)
        print(json.dumps(config, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

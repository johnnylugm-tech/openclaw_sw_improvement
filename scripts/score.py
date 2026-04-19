#!/usr/bin/env python3
"""
Score Aggregation: Computes weighted overall score from per-dimension scores.

Reads CLI JSON from dimension_executor.py.
Integrates issue registry and CRG metrics.
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    import issue_tracker
except ImportError:
    issue_tracker = None


def load_scores(round_dir):
    """Load all dimension scores from round directory."""
    scores_dir = Path(round_dir) / "scores"
    if not scores_dir.exists():
        raise FileNotFoundError(f"Scores directory not found: {scores_dir}")
    scores = {}
    for score_file in sorted(scores_dir.glob("*.json")):
        with open(score_file, "r") as f:
            dim_score = json.load(f)
            dim_name = dim_score["dimension"]
            scores[dim_name] = dim_score
    if not scores:
        raise ValueError(f"No score files found in {scores_dir}")
    return scores


def _apply_crg_subscores(scores, crg_metrics):
    """Deep-integration hook: fold CRG-derived sub-scores INTO per-dimension scores."""
    if not crg_metrics:
        return {}
    adjustments = {}
    cohesion = (crg_metrics.get("community_cohesion") or {}).get("score")
    if cohesion is not None and "architecture" in scores:
        orig = scores["architecture"].get("score", 100)
        adjusted = min(orig, cohesion)
        if adjusted != orig:
            scores["architecture"]["score"] = adjusted
            scores["architecture"]["crg_adjusted_from"] = orig
            adjustments["architecture"] = {"from": orig, "to": adjusted,
                                           "reason": f"community_cohesion={cohesion}"}
    flow = (crg_metrics.get("flow_coverage") or {}).get("score")
    if flow is not None and "error_handling" in scores:
        orig = scores["error_handling"].get("score", 100)
        adjusted = min(orig, flow)
        if adjusted != orig:
            scores["error_handling"]["score"] = adjusted
            scores["error_handling"]["crg_adjusted_from"] = orig
            adjustments["error_handling"] = {"from": orig, "to": adjusted,
                                             "reason": f"flow_coverage={flow}"}
    return adjustments


def compute_overall_score(scores, config, registry=None, crg_metrics=None):
    """Compute weighted overall score from per-dimension scores."""
    crg_adjustments = _apply_crg_subscores(scores, crg_metrics) or {}
    dimensions = config.get("dimensions", {})
    quality_cfg = config.get("quality", {})
    score_gate = quality_cfg.get("score_gate", quality_cfg.get("target", 85))

    breakdown = {}
    weighted_sum = 0
    weight_sum = 0

    for dim_name, dim_config in dimensions.items():
        if not dim_config.get("enabled", False):
            continue
        if dim_name not in scores:
            continue
        dim_score = scores[dim_name]
        score = dim_score.get("score", dim_score.get("tool_score", 0))
        weight = dim_config["weight"]
        weighted_score = score * weight
        weighted_sum += weighted_score
        weight_sum += weight
        dim_target = dim_config.get("target", 100)
        gap = max(0, dim_target - score)
        breakdown[dim_name] = {
            "score": score,
            "target": dim_target,
            "gap": gap,
            "weight": weight,
            "weighted_score": weighted_score,
        }

    overall_score = weighted_sum / weight_sum if weight_sum > 0 else 0

    failing = []
    for dim_name, dim_info in breakdown.items():
        if dim_info["gap"] > 0:
            impact = dim_info["gap"] * dim_info["weight"]
            failing.append({
                "dimension": dim_name,
                "score": dim_info["score"],
                "target": dim_info["target"],
                "gap": dim_info["gap"],
                "weight": dim_info["weight"],
                "impact": impact,
            })
    failing.sort(key=lambda x: x["impact"], reverse=True)

    open_critical = open_high = open_medium = open_total = 0
    if registry is not None and issue_tracker is not None:
        s = issue_tracker.summary(registry)
        open_critical = s.get("open_critical", 0)
        open_high = s.get("open_high", 0)
        open_medium = s.get("open_medium", 0)
        open_total = s.get("open_total", 0)

    meets_score_gate = overall_score >= score_gate
    quality_complete = meets_score_gate and open_critical == 0 and open_high == 0

    return {
        "overall_score": round(overall_score, 2),
        "score_gate": score_gate,
        "meets_target": meets_score_gate,
        "quality_complete": quality_complete,
        "open_critical_count": open_critical,
        "open_high_count": open_high,
        "open_medium_count": open_medium,
        "open_total": open_total,
        "failing_dimensions": failing,
        "breakdown": breakdown,
        "crg_adjustments": crg_adjustments,
    }


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <round_dir> [config.json] [issue_registry.json]")
        sys.exit(1)
    round_dir = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None
    registry_path = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        scores = load_scores(round_dir)
        if config_path:
            with open(config_path, "r") as f:
                config = json.load(f)
        else:
            config = {
                "quality": {"score_gate": 85},
                "dimensions": {
                    dim: {"enabled": True, "weight": 1.0 / len(scores)}
                    for dim in scores.keys()
                },
            }
        registry = None
        if registry_path and Path(registry_path).exists() and issue_tracker is not None:
            registry = issue_tracker.load(registry_path)
        elif issue_tracker is not None:
            default_reg = Path(round_dir).parent / "issue_registry.json"
            if default_reg.exists():
                registry = issue_tracker.load(str(default_reg))
        crg_metrics = None
        crg_path = os.environ.get(
            "CRG_METRICS_PATH",
            str(Path(round_dir).parent / "crg_metrics.json"),
        )
        if Path(crg_path).exists():
            try:
                with open(crg_path) as f:
                    crg_metrics = json.load(f)
            except (json.JSONDecodeError, OSError):
                crg_metrics = None
        result = compute_overall_score(
            scores, config, registry=registry, crg_metrics=crg_metrics
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

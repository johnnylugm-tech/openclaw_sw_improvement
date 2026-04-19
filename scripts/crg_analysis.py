#!/opt/homebrew/bin/python3.12
"""
CRG Analysis: Convert raw CRG wrapper output into structured metrics.

Reads crg_wrapper.py CLI output (JSON) instead of MCP tool responses.
Computes deterministic metrics with explicit thresholds.
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


def _tf(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _ti(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


RISK_DEEP_THRESHOLD = _tf("CRG_RISK_DEEP", 0.7)
RISK_FAST_THRESHOLD = _tf("CRG_RISK_FAST", 0.3)
COHESION_HEALTHY = _tf("CRG_COHESION_HEALTHY", 0.4)
COMMUNITY_OVERSIZED = _ti("CRG_COMMUNITY_OVERSIZED", 50)
DEAD_CODE_ESCALATE_RATIO = _tf("CRG_DEAD_CODE_RATIO", 0.05)
HUB_CRITICAL_FAN_IN = _ti("CRG_HUB_CRIT_FANIN", 15)
HUB_HIGH_FAN_IN = _ti("CRG_HUB_HIGH_FANIN", 8)
FLOW_GOOD_HANDLER_PCT = _ti("CRG_FLOW_GOOD_PCT", 80)

SUGGESTED_Q_SEVERITY_MAP = {
    "bridge_needs_tests":         ("test_coverage", "high"),
    "untested_hubs":              ("test_coverage", "high"),
    "untested_hotspots":          ("test_coverage", "medium"),
    "cross_community_coupling":   ("architecture",  "medium"),
    "thin_communities":           ("architecture",  "medium"),
    "god_modules":                ("architecture",  "high"),
    "dead_code":                  ("architecture",  "low"),
    "surprising_connections":     ("architecture",  "medium"),
}


def compute_eval_depth(risk_score):
    if risk_score is None:
        return "standard"
    if risk_score >= RISK_DEEP_THRESHOLD:
        return "deep"
    if risk_score < RISK_FAST_THRESHOLD:
        return "fast"
    return "standard"


def compute_community_cohesion_score(communities: list) -> dict:
    if not communities:
        return {"score": 100, "healthy": 0, "total": 0, "unhealthy": []}
    unhealthy = []
    healthy = 0
    for c in communities:
        cohesion = c.get("cohesion", 1.0)
        size = c.get("size", 0)
        reasons = []
        if cohesion < COHESION_HEALTHY:
            reasons.append(f"low_cohesion({cohesion:.2f})")
        if size > COMMUNITY_OVERSIZED:
            reasons.append(f"oversized({size})")
        if reasons:
            unhealthy.append({
                "name": c.get("name", "unknown"),
                "cohesion": cohesion,
                "size": size,
                "issues": reasons,
            })
        else:
            healthy += 1
    total = len(communities)
    score = round(100.0 * healthy / total, 1) if total > 0 else 100
    return {"score": score, "healthy": healthy, "total": total, "unhealthy": unhealthy}


def compute_flow_coverage_score(flows: list) -> dict:
    if not flows:
        return {"score": 100, "with_handler": 0, "total": 0, "missing": []}
    with_handler = sum(1 for f in flows if f.get("has_error_handler"))
    total = len(flows)
    score = round(100.0 * with_handler / total, 1) if total > 0 else 100
    missing = [f.get("name", "unknown") for f in flows if not f.get("has_error_handler")]
    return {
        "score": score,
        "with_handler": with_handler,
        "total": total,
        "missing": missing,
        "healthy": score >= FLOW_GOOD_HANDLER_PCT,
    }


def compute_dead_code_ratio(dead_code: list, total_nodes: int) -> dict:
    count = len(dead_code or [])
    ratio = (count / total_nodes) if total_nodes > 0 else 0.0
    escalate = ratio > DEAD_CODE_ESCALATE_RATIO
    return {
        "count": count,
        "total_nodes": total_nodes,
        "ratio": round(ratio, 4),
        "ratio_pct": round(ratio * 100, 2),
        "escalate_severity": escalate,
        "escalated_to": "medium" if escalate else "low",
    }


def compute_hub_risk_map(hubs: list, knowledge_gaps: list) -> dict:
    gap_names = {g.get("name") for g in (knowledge_gaps or []) if g.get("name")}
    mapped = []
    crit = high = medium = 0
    for h in hubs or []:
        name = h.get("name", "unknown")
        fan_in = h.get("fan_in", 0)
        untested = name in gap_names
        if fan_in >= HUB_CRITICAL_FAN_IN:
            sev = "critical" if untested else "high"
        elif fan_in >= HUB_HIGH_FAN_IN:
            sev = "high" if untested else "medium"
        else:
            sev = "medium" if untested else "low"
        mapped.append({
            "name": name,
            "file": h.get("file"),
            "fan_in": fan_in,
            "untested": untested,
            "severity": sev,
        })
        if sev == "critical":
            crit += 1
        elif sev == "high":
            high += 1
        elif sev == "medium":
            medium += 1
    return {"hubs": mapped, "critical_count": crit, "high_count": high, "medium_count": medium}


def compute_metrics(recon: dict) -> dict:
    risk_score = recon.get("risk_score")
    stats = recon.get("graph_stats", {})
    total_nodes = stats.get("nodes", 0) or 0

    communities = (
        recon.get("low_cohesion_communities", [])
        + recon.get("communities", [])
    )
    seen = set()
    deduped = []
    for c in communities:
        n = c.get("name")
        if n and n in seen:
            continue
        if n:
            seen.add(n)
        deduped.append(c)

    return {
        "risk_score": risk_score,
        "eval_depth": compute_eval_depth(risk_score),
        "thresholds": {
            "risk_deep": RISK_DEEP_THRESHOLD,
            "risk_fast": RISK_FAST_THRESHOLD,
            "cohesion_healthy": COHESION_HEALTHY,
            "community_oversized": COMMUNITY_OVERSIZED,
            "dead_code_escalate_ratio": DEAD_CODE_ESCALATE_RATIO,
            "hub_critical_fan_in": HUB_CRITICAL_FAN_IN,
            "hub_high_fan_in": HUB_HIGH_FAN_IN,
            "flow_good_handler_pct": FLOW_GOOD_HANDLER_PCT,
        },
        "community_cohesion": compute_community_cohesion_score(deduped),
        "flow_coverage": compute_flow_coverage_score(recon.get("flows", [])),
        "dead_code": compute_dead_code_ratio(
            recon.get("dead_code", []), total_nodes
        ),
        "hub_risk_map": compute_hub_risk_map(
            recon.get("high_risk_hubs", []),
            recon.get("untested_hotspots", []),
        ),
        "suggested_questions": recon.get("suggested_questions", []),
    }


def seed_issues_from_suggested_questions(
    registry: dict, metrics: dict, round_num: int = 0
) -> list:
    if issue_tracker is None:
        return []
    seeded = []
    for q in metrics.get("suggested_questions", []):
        cat = q.get("category", "").lower().replace(" ", "_")
        dim_sev = SUGGESTED_Q_SEVERITY_MAP.get(cat)
        if not dim_sev:
            continue
        dim, sev = dim_sev
        finding = {
            "severity": sev,
            "message": q.get("text", f"CRG-suggested: {cat}"),
            "file": q.get("file"),
            "line": q.get("line"),
            "evidence": f"CRG get_suggested_questions: category={cat}",
        }
        iid = issue_tracker.add_finding(registry, finding, dim, round_num)
        seeded.append({"id": iid, "category": cat, "dim": dim, "severity": sev})
    return seeded


def _load_recon(path: str) -> dict:
    return json.loads(Path(path).read_text())


def _help():
    print(f"""Usage: {sys.argv[0]} <command> [args]

Commands:
  metrics <recon.json> [out.json]
      Compute structured metrics from reconnaissance data.

  depth_gate <recon.json>
      Print recommended eval depth: deep | standard | fast

  seed_issues <recon.json> <registry.json> <round>
      Auto-create registry issues from suggested_questions.

  thresholds
      Print effective thresholds (after ENV overrides).
""")


def main():
    if len(sys.argv) < 2:
        _help()
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "metrics":
        if len(sys.argv) < 3:
            _help(); sys.exit(1)
        recon = _load_recon(sys.argv[2])
        out = sys.argv[3] if len(sys.argv) > 3 else ".sessi-work/crg_metrics.json"
        metrics = compute_metrics(recon)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(metrics, indent=2, ensure_ascii=False))
        print(json.dumps(metrics, indent=2))
    elif cmd == "depth_gate":
        if len(sys.argv) < 3:
            _help(); sys.exit(1)
        recon = _load_recon(sys.argv[2])
        print(compute_eval_depth(recon.get("risk_score")))
    elif cmd == "seed_issues":
        if len(sys.argv) < 5:
            _help(); sys.exit(1)
        if issue_tracker is None:
            print("issue_tracker module unavailable", file=sys.stderr)
            sys.exit(1)
        recon = _load_recon(sys.argv[2])
        reg_path = sys.argv[3]
        round_num = int(sys.argv[4])
        metrics = compute_metrics(recon)
        registry = issue_tracker.load(reg_path)
        seeded = seed_issues_from_suggested_questions(registry, metrics, round_num)
        issue_tracker.save(registry, reg_path)
        print(json.dumps(seeded, indent=2))
    elif cmd == "thresholds":
        print(json.dumps({
            "risk_deep": RISK_DEEP_THRESHOLD,
            "risk_fast": RISK_FAST_THRESHOLD,
            "cohesion_healthy": COHESION_HEALTHY,
            "community_oversized": COMMUNITY_OVERSIZED,
            "dead_code_escalate_ratio": DEAD_CODE_ESCALATE_RATIO,
            "hub_critical_fan_in": HUB_CRITICAL_FAN_IN,
            "hub_high_fan_in": HUB_HIGH_FAN_IN,
            "flow_good_handler_pct": FLOW_GOOD_HANDLER_PCT,
        }, indent=2))
    else:
        _help()
        sys.exit(1)


if __name__ == "__main__":
    main()

# CRG Structural Reconnaissance Protocol

Runs **once per session** before the first evaluation round. Uses `crg_wrapper.py` CLI.

---

## Step 1: Check CRG Availability

```bash
python3 scripts/crg_wrapper.py stats <repo_path>
```

- `available: false` → skip this entire protocol silently
- `available: true` → proceed

---

## Step 2: Run All CRG Commands

Run via `python3 scripts/crg_wrapper.py <command> <repo_path>`:

| Command | Purpose |
|---------|---------|
| stats | Baseline node/edge/file counts |
| hub-nodes | Most connected hub nodes (high fan-in) |
| bridge-nodes | Structural chokepoints |
| communities | Module cohesion map |
| arch-overview | High-level architecture |
| flows | Execution flows |
| dead-code | Unreferenced functions/classes |
| surprising | Unexpected cross-module couplings |
| knowledge-gaps | Structural weaknesses |

---

## Step 3: Write Reconnaissance Report

Save to `.sessi-work/crg_reconnaissance.json`:

```json
{
  "timestamp": "<ISO8601>",
  "repo": "<repo_path>",
  "graph_stats": {
    "nodes": N,
    "edges": N,
    "files": N
  },
  "risk_score": 0.0,
  "commands": {
    "hub-nodes": {...},
    "bridge-nodes": {...},
    "communities": {...},
    "arch-overview": {...},
    "flows": {...},
    "dead-code": {...},
    "surprising": {...},
    "knowledge-gaps": {...}
  },
  "evaluation_priorities": {
    "deepest_analysis_files": [],
    "dimensions_to_focus": []
  }
}
```

---

## Step 4: Compute Structured Metrics

```bash
python3 scripts/crg_analysis.py metrics \
  .sessi-work/crg_reconnaissance.json \
  .sessi-work/crg_metrics.json
```

Emits `.sessi-work/crg_metrics.json` with:

| Key | Meaning |
|-----|---------|
| `risk_score` | 0.0–1.0 overall structural risk |
| `eval_depth` | `deep` / `standard` / `fast` |
| `community_cohesion.score` | 0–100, feeds architecture |
| `flow_coverage.score` | 0–100, feeds error_handling |
| `dead_code.escalate_severity` | True/False — low→medium if ratio > 5% |
| `hub_risk_map.hubs[].severity` | critical/high/medium/low per hub |

---

## Step 5: Seed Issues from Suggested Questions

```bash
python3 scripts/crg_analysis.py seed_issues \
  .sessi-work/crg_reconnaissance.json \
  .sessi-work/issue_registry.json 0
```

---

## Token Cost Reference

| Step | Est. tokens |
|------|-------------|
| All 9 CRG commands via CLI | ~500-2000 total |
| Metrics computation | ~500 |

**Graceful Degradation:** If CRG is not installed, skip silently and run framework without structural intelligence.

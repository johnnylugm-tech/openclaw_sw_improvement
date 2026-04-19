# SKILL.md — OpenClaw SW Improvement Framework

## Metadata

- **name**: openclaw_sw_improvement
- **description**: Automated software quality improvement via structured tool evaluation, issue tracking, and CRG-powered structural analysis loops
- **trigger phrases**: 
  - "run quality loop"
  - "improve code quality"
  - "quality improvement"
  - "software improvement"
  - "start quality analysis"
  - "run sw improvement"
- **skills/** directory: `~/.openclaw/workspace/software_self_improvement/` (source reference)

---

## Overview

The OpenClaw SW Improvement Framework runs multi-round quality improvement loops on any repository. Each round:
1. Evaluates 12 quality dimensions via tool-first hierarchy
2. Computes weighted overall score
3. Tracks issues in a persistent registry
4. Applies targeted fixes driven by open issue severity
5. Verifies improvements with anti-bias caps

**CRG (Code Review Graph)** provides structural intelligence when available — hub nodes, community cohesion, dead code detection. If CRG is unavailable, framework degrades gracefully and runs without structural analysis.

---

## Execution Flow

### CLI Commands

```bash
# Navigate to project directory
cd /tmp/openclaw_sw_improvement

# Initialize a new quality improvement session
python3 scripts/quality_loop.py init <target_repo> [config.yaml]

# Run full quality loop (up to max_rounds)
python3 scripts/quality_loop.py run

# Check current state
python3 scripts/quality_loop.py status

# Resume from current phase
python3 scripts/quality_loop.py resume
```

### State Machine

```
init → setup → recon → round (3a-f) → [round+1] → ... → quality_complete
```

| Phase | Description |
|-------|-------------|
| `setup` | Resolve config, clone target repo, check CRG availability |
| `recon` | Run 9 CRG commands → crg_reconnaissance.json + crg_metrics.json |
| `round` | Per-round evaluation loop (3a-3f) |

### Round Steps (per round)

| Step | Action | Output |
|------|--------|--------|
| 3a | `dimension_executor.py` — run all 12 dimension tools | `round_<n>/scores/*.json` |
| 3b | `score.py` — weighted aggregation | `round_<n>/overall_score.json` |
| 3c | `verify.py` — anti-bias cap + regression detection | `round_<n>/verified.json` |
| 3d | `checkpoint.py` — snapshot + markdown summary | `round_<n>/round_<n>.json` |
| 3e | Quality complete check | `quality_complete` flag |
| 3f | Issue-driven improvements | Commits + issue registry updates |

---

## 12 Quality Dimensions

| # | Dimension | Tool | Weight | Target |
|---|-----------|------|--------|--------|
| 1 | linting | pylint | 0.06 | 95 |
| 2 | type_safety | mypy | 0.10 | 95 |
| 3 | test_coverage | pytest --cov | 0.13 | 80 |
| 4 | security | bandit | 0.10 | 90 |
| 5 | performance | (skip) | 0.07 | 80 |
| 6 | architecture | cloc + CRG | 0.07 | 80 |
| 7 | readability | radon | 0.06 | 85 |
| 8 | error_handling | grep try: | 0.09 | 85 |
| 9 | documentation | grep docstring | 0.10 | 85 |
| 10 | secrets_scanning | gitleaks | 0.08 | 100 |
| 11 | mutation_testing | (skip) | 0.08 | 70 |
| 12 | license_compliance | scancode | 0.06 | 95 |

---

## State Management

**State file:** `quality_state.json` in project root

Key fields:
```json
{
  "phase": "setup|recon|round",
  "round": 1,
  "step": "3a|3b|3c|3d|3e|3f",
  "max_rounds": 3,
  "score_gate": 85,
  "target_repo": "/path/to/repo",
  "crg_available": true,
  "round_results": [],
  "quality_complete": false,
  "last_updated": "ISO8601"
}
```

`quality_complete = true` when:
- `overall_score >= score_gate` AND
- `open_critical_count == 0` AND
- `open_high_count == 0`

---

## Issue Registry

Persistent file: `.sessi-work/issue_registry.json`

Status lifecycle: `open` → `fixed` | `deferred` | `wontfix`

Priority: **severity-first, not score-first** — a dimension can be at target but still have open critical/high issues that must be fixed.

---

## CRG Integration

CRG is auto-detected on `setup_target.py` run. Status written to `.sessi-work/crg_status.json`.

If `available: true`, the `crg_reconnaissance.md` protocol runs 9 CRG commands:
- `hub-nodes`, `bridge-nodes`, `communities`, `arch-overview`, `flows`
- `dead-code`, `surprising`, `knowledge-gaps`, `stats`

Results written to:
- `.sessi-work/crg_reconnaissance.json`
- `.sessi-work/crg_metrics.json`

Deep integration: CRG sub-scores `min()`-ed into architecture and error_handling dimensions.

---

## Anti-Bias Defenses

1. `score = min(tool_score, llm_score)` — tool is ground truth
2. Evidence requirement — every finding cites tool output
3. Per-fix verification — tool re-run confirms improvement before commit
4. Deterministic cap — Δ > 10 without git diff evidence → capped to +3
5. Regression detection — score drops trigger revert protocol
6. CRG structural drift detection — new hub nodes or risk_score jump > 0.2

---

## Output Files

```
.sessi-work/
├── quality_state.json        ← quality_loop.py state
├── crg_status.json         ← CRG availability
├── crg_reconnaissance.json ← 9-command CRG reconnaissance
├── crg_metrics.json        ← Structured metrics (eval_depth, scores)
├── issue_registry.json     ← Persistent issue tracker
└── round_<n>/
    ├── scores/
    │   ├── linting.json
    │   ├── type_safety.json
    │   └── ... (one per dimension)
    ├── overall_score.json   ← Step 3b output
    ├── verified.json        ← Step 3c output
    ├── round_<n>.json       ← Step 3d snapshot
    └── round_<n>.md        ← Markdown summary
```

---

## Error Handling

- Tool not found → dimension returns `status: "skip"`, score = 100
- Tool timeout → dimension returns `status: "error"`, score = 0
- CRG unavailable → graceful degradation (skips structural analysis)
- Score computation failure → fallback to direct tool score average

---

## Graceful Degradation

| Missing Component | Behavior |
|------------------|----------|
| CRG not installed | Skip all CRG steps; run with tool-only evaluation |
| Tool not found | Dimension returns `status: "skip"` |
| Config not found | Use hardcoded defaults |
| issue_tracker unavailable | Score computation without issue counts |

# OpenClaw Software Improvement Framework

Auto-run quality improvement loops on any repository with structured tool evaluation, issue tracking, and CRG-powered structural analysis.

## Directory Structure

```
openclaw_sw_improvement/
├── SKILL.md                  ← This skill definition
├── README.md                 ← Overview
├── CLAUDE.md                 ← Developer guide
├── config.example.yaml       ← Example configuration
├── quality_state.json        ← Persistent state (auto-created)
├── scripts/
│   ├── quality_loop.py       ← Main orchestrator (init/run/status/resume)
│   ├── crg_wrapper.py        ← CRG CLI wrapper (9 commands)
│   ├── dimension_executor.py ← 12 dimension tools subprocess wrapper
│   ├── config_loader.py      ← YAML config resolver
│   ├── setup_target.py       ← Clone repo + CRG init
│   ├── score.py              ← Weighted score aggregation
│   ├── verify.py             ← Anti-bias verification (copied)
│   ├── checkpoint.py         ← Round snapshots (copied)
│   ├── report_gen.py         ← Final report (copied)
│   ├── issue_tracker.py      ← Issue registry (copied)
│   ├── llm_router.py         ← Unified MiniMax M2.7 router
│   └── crg_analysis.py       ← CRG metrics computation
├── prompts/
│   ├── evaluate_dimension.md ← Per-dimension evaluation protocol
│   ├── improvement_plan.md   ← Issue-driven fix protocol
│   ├── verify_round.md       ← Post-round verification
│   ├── crg_reconnaissance.md  ← CRG structural reconnaissance
│   └── final_report.md        ← End-of-run report generation
└── docs/
    ├── OPERATION_GUIDE.md    ← Full operation manual
    ├── CRG_DEEP_INTEGRATION.md ← CRG integration reference
    └── ANTI_BIAS.md          ← Anti-bias defense documentation
```

## Quick Start

```bash
cd /tmp/openclaw_sw_improvement

# Initialize with a target repo
./scripts/quality_loop.py init /path/to/repo config.example.yaml

# Run the full quality loop (up to max_rounds)
./scripts/quality_loop.py run

# Check status
./scripts/quality_loop.py status
```

## Quality Loop Phases

| Phase | Step | Description |
|-------|------|-------------|
| Setup | 1 | Resolve config + clone target + check CRG |
| Recon | 2 | Run 9 CRG commands → crg_reconnaissance.json |
| Round | 3a | Evaluate all 12 dimensions via tools |
| Round | 3b | Compute weighted overall score |
| Round | 3c | Verify results (anti-bias cap) |
| Round | 3d | Checkpoint round snapshot |
| Round | 3e | Quality complete check (score_gate + open issues) |
| Round | 3f | Issue-driven improvement fixes |

## 12 Quality Dimensions

| # | Dimension | Tool | Weight |
|---|-----------|------|--------|
| 1 | linting | pylint | 0.06 |
| 2 | type_safety | mypy | 0.10 |
| 3 | test_coverage | pytest --cov | 0.13 |
| 4 | security | bandit | 0.10 |
| 5 | performance | skip | 0.07 |
| 6 | architecture | cloc + CRG | 0.07 |
| 7 | readability | radon | 0.06 |
| 8 | error_handling | grep try: | 0.09 |
| 9 | documentation | grep docstring | 0.10 |
| 10 | secrets_scanning | gitleaks | 0.08 |
| 11 | mutation_testing | skip | 0.08 |
| 12 | license_compliance | scancode | 0.06 |

## CRG Integration

The Code Review Graph (CRG) provides structural intelligence:
- **Hub nodes** — most-connected functions (high fan-in = architectural risk)
- **Bridge nodes** — structural chokepoints
- **Communities** — module cohesion analysis
- **Dead code** — unreferenced functions
- **Knowledge gaps** — untested hotspots

If CRG is not available, framework runs without structural analysis (graceful degradation).

## State Machine

```
init → setup → recon → round (3a-f) → [round+1] → ... → quality_complete
```

## Anti-Bias Defenses

1. `score = min(tool_score, llm_score)` — tool cannot be inflated by LLM
2. Evidence requirement — every finding needs tool output citation
3. Per-fix verification — tool re-run confirms improvement
4. Deterministic cap — Δ > 10 without diff evidence → capped to +3
5. Regression detection — score drops trigger revert protocol
6. CRG structural drift detection — catches architectural regressions

## Example

```bash
# Initialize for a Python project
./scripts/quality_loop.py init ./myproject config.example.yaml

# Run up to 3 rounds
./scripts/quality_loop.py run

# Resume if interrupted
./scripts/quality_loop.py resume
```

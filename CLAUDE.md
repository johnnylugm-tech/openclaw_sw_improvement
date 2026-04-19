# CLAUDE.md — Developer Guide

## Repository Layout

```
/tmp/openclaw_sw_improvement/
├── scripts/
│   ├── quality_loop.py       ← Main orchestrator, state machine
│   ├── crg_wrapper.py       ← CRG functions → CLI
│   ├── dimension_executor.py ← 12 dimension tools → JSON
│   ├── config_loader.py     ← YAML → normalized JSON
│   ├── setup_target.py       ← Clone + git init + CRG check
│   ├── score.py              ← Weighted aggregation
│   ├── verify.py            ← Anti-bias cap + regression detection
│   ├── checkpoint.py        ← Round snapshot files
│   ├── report_gen.py       ← Markdown final report
│   ├── issue_tracker.py    ← Persistent issue registry
│   ├── llm_router.py       ← MiniMax M2.7 unified routing
│   └── crg_analysis.py     ← CRG JSON → structured metrics
├── prompts/                 ← LLM execution protocols
└── docs/                    ← Reference documentation
```

## Adding a New Dimension

1. Add entry to `DIMENSIONS` dict in `dimension_executor.py`
2. Add scoring logic in `_compute_tool_score()`
3. If dimension has a tool, add command in `DIMENSIONS`
4. If no tool, set `tool: None` → status = "skip"

## Adding a CRG Command

1. Add import in `crg_wrapper.py`
2. Add `cmd_xxx()` function
3. Add `elif args.command == "xxx":` branch in `main()`

## Modifying Weight Normalization

Weights are normalized to sum to 1.0 across enabled dimensions.
To change the weight calculation, modify `normalize_weights()` in `config_loader.py`.

## State File Format

`quality_state.json` is auto-created by `init_state()`. Key fields:

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

## CRG Wrapper CLI

```bash
python3 scripts/crg_wrapper.py <command> <repo_path>

Commands:
  stats            → graph stats
  hub-nodes        → most connected nodes
  bridge-nodes     → structural chokepoints
  communities      → code community list
  arch-overview    → architecture summary
  flows            → execution flows
  dead-code        → unreferenced symbols
  surprising       → unexpected couplings
  knowledge-gaps   → untested hotspots
```

## Tool Score Formula

| Dimension | Formula |
|-----------|---------|
| linting | 100 - findings * 5 |
| type_safety | 100 - findings * 10 |
| security | 100 - critical*30 - high*20 - others*10 |
| secrets_scanning | 100 - findings * 25 (zero tolerance) |
| (others) | 100 - findings * 5 |

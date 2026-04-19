# CRG Deep Integration — Complete Workflow Reference

> **Scope:** Technical reference for the Code Review Graph (CRG) integration
> layer. Covers all 6 deep-integration points, the complete per-session
> execution flow, and document/script cross-references.
>
> For installation and basic CRG setup, see `docs/OPERATION_GUIDE.md §CRG`.

---

## Why "Deep Integration" vs "Used"

A CRG tool is **used** when its output is passed to the LLM for interpretation.
It is **deeply integrated** when its output drives a **deterministic decision**
— a formula, a threshold, a severity bucket — without LLM judgment:

```
Surface integration:  LLM reads CRG output → LLM decides → score
Deep integration:     CRG output → formula/threshold → score/action
```

Out of 22 MCP tools utilized by this framework, **6 have deep-integration
formulas** in `scripts/crg_analysis.py`. The rest provide structural context
that replaces blind code reading (still valuable, not "deep" by this definition).

---

## Complete Workflow (per session)

```
Session start
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Step 2: setup_target.py                                 │
│   scripts/crg_integration.py ensure <repo>              │
│   → auto-detect install + build graph if empty          │
│   → write .sessi-work/crg_status.json                  │
│     { available: true/false, node_count: N, action: … } │
└─────────────────────┬───────────────────────────────────┘
                      │ available: true
                      ▼
┌─────────────────────────────────────────────────────────┐
│ Step 2.5: crg_reconnaissance.md  (once per session)     │
│                                                         │
│  9 MCP tool calls  (~3,900 tokens total):               │
│  ① get_minimal_context      → risk_score baseline       │
│  ② list_graph_stats         → nodes / edges / files     │
│  ③ get_suggested_questions  → CRG's own priorities      │
│  ④ get_hub_nodes            → high fan-in nodes         │
│  ⑤ get_bridge_nodes         → structural chokepoints    │
│  ⑥ list_communities +                                   │
│     get_community           → low-cohesion / oversized  │
│  ⑦ get_knowledge_gaps       → untested critical paths   │
│  ⑧ get_surprising_connections → accidental couplings   │
│  ⑨ refactor_tool(dead_code) → unreferenced symbols     │
│                                                         │
│  → writes .sessi-work/crg_reconnaissance.json          │
│                                                         │
│  Step 8a ── DEEP INTEGRATION #6 ──────────────────────│
│    python3 scripts/crg_analysis.py seed_issues \        │
│      .sessi-work/crg_reconnaissance.json \              │
│      .sessi-work/issue_registry.json 0                  │
│    Deterministic category → (dimension, severity) map:  │
│    bridge_needs_tests   → test_coverage / high          │
│    untested_hubs        → test_coverage / high          │
│    untested_hotspots    → test_coverage / medium        │
│    cross_community_coupling → architecture / medium     │
│    thin_communities     → architecture / medium         │
│    god_modules          → architecture / high           │
│    surprising_connections → architecture / medium       │
│    dead_code            → architecture / low            │
│                                                         │
│  Step 11 ── DEEP INTEGRATIONS #1–5 ───────────────────│
│    python3 scripts/crg_analysis.py metrics \            │
│      .sessi-work/crg_reconnaissance.json \              │
│      .sessi-work/crg_metrics.json                       │
│                                                         │
│    Computes:                                            │
│    #1  eval_depth    (deep/standard/fast)               │
│    #2  community_cohesion.score  (0–100)                │
│    #3  flow_coverage.score       (0–100)                │
│    #4  dead_code.escalate_severity  (bool)              │
│    #5  hub_risk_map[].severity   (crit/high/med/low)    │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼  repeated each round
┌─────────────────────────────────────────────────────────┐
│ Step 3a: evaluate_dimension.md  (per dimension)         │
│                                                         │
│  Tier 1/2 (linting, type_safety, security …)           │
│  → tool + Gemini Flash; CRG not called                  │
│                                                         │
│  Tier 3 (architecture, error_handling, readability …)   │
│                                                         │
│  Step 2a.1 ── DEEP INTEGRATION #1 ────────────────────│
│    EVAL_DEPTH=$(python3 scripts/crg_analysis.py \       │
│      depth_gate .sessi-work/crg_reconnaissance.json)    │
│    deep     (risk ≥ 0.7) → full LLM + hub source read  │
│    standard (0.3–0.7)   → tool + LLM one-paragraph     │
│    fast     (risk < 0.3) → tool only, skip LLM          │
│    Deterministic token budget; LLM cannot override.     │
│                                                         │
│  Step 2a.2 ── DEEP INTEGRATIONS #2 #3 #5 ─────────────│
│    Read .sessi-work/crg_metrics.json                    │
│    architecture:                                        │
│      cite community_cohesion.unhealthy[].{name,coh,sz} │
│      score.py will min(tool, cohesion) automatically    │
│    error_handling:                                      │
│      findings from flow_coverage.missing[] → high sev  │
│      score.py will min(tool, flow_score) automatically  │
│    hub fan-in severity (#5):                            │
│      fan_in ≥ 15 → critical (untested) / high (tested) │
│      fan_in ≥  8 → high (untested) / medium (tested)   │
│      fan_in  < 8 → medium (untested) / low (tested)    │
│      Mandatory for hub-related findings; no free calls  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ score.py  (per round, automatic)                        │
│                                                         │
│  Auto-loads .sessi-work/crg_metrics.json               │
│  _apply_crg_subscores():                                │
│    architecture   = min(tool_score, cohesion_score)     │
│    error_handling = min(tool_score, flow_score)         │
│  Contract: CRG can only PULL DOWN, never inflate.       │
│  crg_adjustments field records every adjustment + why.  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ improvement_plan.md  (fix loop)                         │
│                                                         │
│  Step 2a ── DEEP INTEGRATION #4 ──────────────────────│
│    Read dead_code.escalate_severity from crg_metrics    │
│    True → treat all dead_code issues as medium          │
│    Triggered when dead/total_nodes > 5%                 │
│    Dead-code moves into the active fix queue.           │
│                                                         │
│  Step 2b: Dead-code removal protocol (6 steps):        │
│    1. CRG re-confirm callers=0, importers=0             │
│    2. Reject if public API / entry point                │
│    3. Remove symbol + clean imports                     │
│    4. code-review-graph update                          │
│    5. blast-radius gate  (risky . HEAD 0.7)             │
│    6. commit + registry fix record                      │
│                                                         │
│  General fix CRG safety gates (all fixes):             │
│    get_minimal_context + get_review_context             │
│      → replaces manual file reads                       │
│    get_impact_radius → record hub/bridge status         │
│    crg_integration.py risky . HEAD 0.7                  │
│      → defer if risk_score ≥ 0.7                        │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ verify_round.md  (end of each round)                    │
│                                                         │
│  code-review-graph update  (incremental, seconds)       │
│  crg_integration.py blast <repo> <BASE_REF>             │
│    Round 1:  BASE_REF = HEAD~${COMMITS_THIS_ROUND}      │
│    Round N:  BASE_REF = round-<n-1> tag                 │
│  drift > 0.2 → log warning                              │
│  drift > 0.4 → trigger revert protocol                  │
│  new test_gaps → auto-register test_coverage/medium     │
└─────────────────────────────────────────────────────────┘
```

---

## 6 Deep-Integration Points Summary

| # | Where | Signal | Decision (deterministic) |
|---|-------|--------|--------------------------|
| 1 | `evaluate_dimension.md` Step 2a.1 | `risk_score` | `eval_depth` = deep / standard / fast |
| 2 | `score.py` `_apply_crg_subscores` | `community_cohesion.score` | architecture final = min(tool, cohesion) |
| 3 | `score.py` `_apply_crg_subscores` | `flow_coverage.score` | error_handling final = min(tool, flow) |
| 4 | `improvement_plan.md` Step 2a | `dead_code.escalate_severity` | dead_code low → medium if ratio > 5% |
| 5 | `evaluate_dimension.md` Step 2a.2 | `hub_risk_map[].severity` | fan-in bucket: crit / high / med / low |
| 6 | `crg_reconnaissance.md` Step 8a | `suggested_questions[]` | category → (dimension, severity) registry seed |

---

## Explicit Thresholds

All thresholds live in `scripts/crg_analysis.py` and are ENV-overridable:

| ENV var | Default | Effect |
|---------|---------|--------|
| `CRG_RISK_DEEP` | 0.7 | risk_score ≥ → `eval_depth=deep` |
| `CRG_RISK_FAST` | 0.3 | risk_score < → `eval_depth=fast` |
| `CRG_COHESION_HEALTHY` | 0.4 | cohesion ≥ → healthy community |
| `CRG_COMMUNITY_OVERSIZED` | 50 | size > → god-module candidate |
| `CRG_DEAD_CODE_RATIO` | 0.05 | dead/total > → escalate low → medium |
| `CRG_HUB_CRIT_FANIN` | 15 | fan_in ≥ → critical (untested) / high (tested) |
| `CRG_HUB_HIGH_FANIN` | 8 | fan_in ≥ → high (untested) / medium (tested) |
| `CRG_FLOW_GOOD_PCT` | 80 | handled flows ≥ % → healthy |

Inspect effective values (including ENV overrides):

```bash
python3 scripts/crg_analysis.py thresholds
```

---

## Data Flow (file-level)

```
.sessi-work/
├── crg_status.json          ← written by setup_target.py (Step 2)
│                               read by: all CRG-aware prompts
│
├── crg_reconnaissance.json  ← written by crg_reconnaissance.md (Step 2.5)
│                               read by: evaluate_dimension.md, crg_analysis.py
│
├── crg_metrics.json         ← written by crg_analysis.py metrics (Step 11)
│                               read by: score.py (auto), evaluate_dimension.md,
│                                        improvement_plan.md
│
├── issue_registry.json      ← seed_issues writes to this (Step 8a)
│                               read by: score.py, improvement_plan.md
│
└── round_<n>/
    ├── crg_blast_radius.json ← written by verify_round.md blast check
    └── scores/
        └── <dim>.json        ← score.py reads; crg_adjustments appended
```

---

## Tool Coverage

| Category | Tools | Count |
|----------|-------|-------|
| Reconnaissance (Step 2.5) | `get_minimal_context`, `list_graph_stats`, `get_suggested_questions`, `get_hub_nodes`, `get_bridge_nodes`, `list_communities`, `get_community`, `get_knowledge_gaps`, `get_surprising_connections`, `refactor_tool` | 10 |
| Tier 3 evaluation | `find_large_functions`, `list_flows`, `get_flow`, `get_affected_flows`, `semantic_search_nodes`, `get_architecture_overview`, `generate_wiki`, `get_wiki_page`, `get_docs_section`, `query_graph_tool`, `traverse_graph_tool` | 11 |
| Fix safety gates | `get_review_context`, `get_impact_radius` | 2 |
| Structural verification | `detect_changes` (via `crg_integration.py blast`) | 1 (shared) |
| **Total utilized** | | **22 / 27** |

Of the 22 utilized, **6 are deeply integrated** (drive deterministic decisions
via `crg_analysis.py`). The remaining 16 provide structural context that
replaces blind code reading — still valuable, but interpreted by LLM.

---

## Why min() and Not Average

The contract `score = min(tool_score, crg_score)` is intentional:

- **Average** would let a high CRG score compensate for a low tool score — which
  allows structural signal to mask concrete tool findings (or vice versa).
- **min()** means both the tool AND the structural layer must agree the dimension
  is healthy. Either one can veto. This is the strictest possible constraint
  without requiring unanimous agreement across all signals.
- CRG sub-scores are constrained to **only pull down**, never inflate, because
  CRG sees structure but not all semantic correctness. A structurally coherent
  module can still have bugs that only static analysis catches.

---

## Graceful Degradation

Every CRG integration point checks `crg_status.json` first:

```
available: false → skip silently, framework continues without CRG
```

- `crg_analysis.py` — if `crg_reconnaissance.json` is missing, all metric
  functions return safe defaults (score=100, escalate=false, depth=standard)
- `score.py` — if `crg_metrics.json` is missing, `_apply_crg_subscores()` is
  a no-op; `crg_adjustments: {}` in output
- All prompts — check `crg_status.json` at entry; skip CRG steps if unavailable

Framework remains fully functional without CRG. Only differences:
- Tier 3 token cost ~30–50% higher (no structural pre-filtering)
- No architectural safety gate on commits
- No structural drift detection after rounds

---

## Related Files

| File | Role |
|------|------|
| `scripts/crg_analysis.py` | Deep-integration computation layer |
| `scripts/crg_integration.py` | CRG CLI wrapper (blast, risky, ensure, update) |
| `prompts/crg_reconnaissance.md` | Step 2.5 protocol (9 tools + seed + metrics) |
| `prompts/evaluate_dimension.md` | Tier 3 eval with depth gate + sub-score reads |
| `prompts/improvement_plan.md` | Dead-code removal protocol + escalation rule |
| `prompts/verify_round.md` | Post-round blast-radius structural drift check |
| `scripts/score.py` | `_apply_crg_subscores()` folds cohesion/flow into score |
| `SKILL.md §Deep Integration Layer` | High-level summary + 6-point table |
| `README.md §Code Review Graph Integration` | User-facing overview |

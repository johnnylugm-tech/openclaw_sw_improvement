# Harness Quality Framework — Complete Operation Guide

End-to-end workflow with CLI commands and Agent MCP tool interactions.

---

## Prerequisites

```bash
# One-time setup (if not done):
cd /Users/johnny/Projects/harness-quality-framework
code-review-graph install --platform openclaw --repo . -y

# Restart the application to load CRG MCP tools
# Graph build is automatic — setup_target.py detects and builds on first run
```

---

## Round N Workflow

### Phase 1: Setup (CLI, ~1–2 min)

```bash
# 1a. Resolve config (normalize weights, validate)
python3 scripts/config_loader.py config.example.yaml > config.json

# 1b. Resolve target (clone or use local repo) + CRG auto-init
python3 scripts/setup_target.py <github-url-or-local-path> > target.path
# Stderr: "[CRG] ✓ Ready — 342 nodes (auto-built)" or "[CRG] Not available — ..."
# Writes: .sessi-work/crg_status.json

# 1c. Initialize issue registry (first round only)
# Already exists at .sessi-work/issue_registry.json after round 1
```

---

### Phase 1.5: CRG Structural Reconnaissance (first session only, ~3 min)

*Only runs if `crg_status.json` shows `available: true`.*

Follow `prompts/crg_reconnaissance.md`. Runs 9 CRG MCP tool calls:

| Tool | Purpose |
|------|---------|
| `get_minimal_context` | Orientation + risk score (~100 tokens) |
| `list_graph_stats` | Baseline node/edge/file counts |
| `get_suggested_questions` | Auto-generated investigation priorities |
| `get_hub_nodes` + `get_bridge_nodes` | High-risk components |
| `list_communities` + `get_community` | Module cohesion map |
| `get_knowledge_gaps` | Untested hotspots |
| `get_surprising_connections` | Unexpected cross-module coupling |
| `refactor_tool(dead_code)` | Unreferenced functions/classes |

Outputs: `.sessi-work/crg_reconnaissance.json` + pre-seeded issues in registry.
After reconnaissance, `crg_analysis.py` computes structured metrics
(`.sessi-work/crg_metrics.json`) consumed by `score.py` and the evaluation
prompts — no LLM interpretation needed for the 6 deep-integration decisions.
Token cost: ~3,900 (vs ~10,000+ for blind file reading).

> **Deep integration reference:** `docs/CRG_DEEP_INTEGRATION.md` — complete
> workflow diagram, all 6 integration points, threshold table, and data-flow map.

---

### Phase 2: Evaluate Each Dimension (Agent + CLI, ~15 min)

**For each enabled dimension (12 core, or subset if early-stop triggered):**

#### Step 2.1: Route to correct LLM tier (CLI)

```bash
python3 scripts/llm_router.py <dimension> [tool_output.txt]
```

Read `tier` and `provider`:
- **Tier 1** (linting, type_safety, test_coverage, secrets_scanning, license_compliance, mutation_testing)
  → Use default LLM (agent)
- **Tier 2** (security)
  → Use default LLM (agent)
- **Tier 3** (architecture, readability, error_handling, documentation, performance)
  → **Use Agent + CRG MCP tools** (this session)

#### Step 2.2a: Run tools (CLI)

```bash
# Tier 1/2 example: linting
pylint src/ --output-format=json 2>&1 > .sessi-work/round_<n>/tools/linting.txt

# Save to file for downstream reference
```

#### Step 2.2b: Evaluate (Default LLM for Tier 1/2, Agent reasoning for Tier 3)

**IF Tier 1/2:** Call the default LLM (automated)

**IF Tier 3:** Use the Agent **+ CRG MCP tools first**

In the session, query the CRG knowledge graph BEFORE reading source code:

```
# Use the MCP tool calls or the Agent's CRG tool interface

For architecture dimension:
  /mcp get_hub_nodes              → most-connected functions (hotspots)
  /mcp get_bridge_nodes           → chokepoint functions (bottlenecks)
  /mcp get_knowledge_gaps         → structural weaknesses
  /mcp get_surprising_connections → unexpected coupling
  /mcp get_architecture_overview  → high-level structure

For readability:
  /mcp find_large_functions       → functions > 100 LOC (overly complex)
  /mcp get_hub_nodes              → hub nodes that became "god objects"

For performance:
  /mcp get_hub_nodes              → hot-path bottlenecks
  /mcp list_flows                 → critical execution flows
  /mcp get_affected_flows         → which flows pass through slow functions

For error_handling:
  /mcp get_affected_flows         → flows without error handlers
  /mcp semantic_search_nodes "except|catch|error"  → exception placement

For documentation:
  /mcp generate_wiki (first run) or get_wiki_page  → undocumented hub nodes
  /mcp get_hub_nodes              → highest-priority doc gaps
```

Then use the Agent's **LLM score** based on:
- CRG structural data (cheap, returned as JSON)
- 2–5 spot-reads of specific files CRG flagged
- **Never** read entire codebase

**Token target:** -30 to -50% vs. pure-code-reading for Tier 3.

#### Step 2.3: Write score file (Agent output → CLI save)


The Agent writes JSON to `.sessi-work/round_<n>/scores/<dimension>.json`:

```json
{
  "dimension": "architecture",
  "round": 1,
  "llm_tier": 3,
  "llm_provider": "default",
  "tool_score": 72,
  "llm_score": 70,
  "score": 70,
  "findings": [
    {
      "severity": "high",
      "message": "UserService is a god object (25 functions, 8 dependencies)",
      "file": "src/services/user.py",
      "line": 1,
      "evidence": "CRG get_hub_nodes rank=2/75, get_knowledge_gaps: 'needs decomposition'"
    }
  ]
}
```

#### Step 2.4: Register findings in issue registry (CLI)

```bash
# For each finding in score JSON:
echo '{"severity":"high",...}' > /tmp/finding.json
python3 scripts/issue_tracker.py add \
  .sessi-work/issue_registry.json \
  architecture \
  <round_num> \
  /tmp/finding.json

# Print summary
python3 scripts/issue_tracker.py summary .sessi-work/issue_registry.json
```

---

### Phase 3: Score (CLI, ~30 sec)

```bash
# score.py outputs JSON to stdout; redirect captures it to file
python3 scripts/score.py \
  .sessi-work/round_<n> \
  config.json \
  .sessi-work/issue_registry.json \
> .sessi-work/round_<n>/final_score.json
```

Output includes:
- `overall_score`: weighted avg of all dim scores
- `score_gate`: configured minimum (e.g., 85)
- `meets_target`: score_gate passed? (true/false)
- `quality_complete`: score_gate AND zero open critical/high? (true/false)
- `open_critical_count`, `open_high_count`, etc.
- `failing_dimensions`: gaps to fix

---

### Phase 4: Verify (CLI + optional CRG, ~1 min)

```bash
# 4.1 Deterministic verification (tool-only claims vs. evidence)
python3 scripts/verify.py \
  .sessi-work/round_<n>/result.json \
  .sessi-work/round_<n> \
  <repo_path> \
  > .sessi-work/round_<n>/verified.json

# 4.2 (OPTIONAL) Structural verification via CRG
code-review-graph update --repo <repo_path>
python3 scripts/crg_integration.py blast <repo_path> round-<n-1> \
  > .sessi-work/round_<n>/crg_blast_radius.json

# Check for architectural regressions:
#   - If risk_score jumped > 0.2, log warning
#   - If new hub nodes appeared, flag
#   - If test_gaps expanded, register as test_coverage issues
```

---

### Phase 5: Checkpoint (CLI, ~1 min)

```bash
python3 scripts/checkpoint.py \
  round_<n> \
  .sessi-work/round_<n>/final_score.json \
  > .sessi-work/round_<n>/round_<n>.md

git tag round-<n>
git add .sessi-work/round_<n>/
git commit -m "checkpoint: round <n>"
```

---

### Phase 6: Early-Stop Check (Agent logic)

**Pseudo-code (SKILL.md Step 3e):**

```
critical_open = score.open_critical_count
high_open = score.open_high_count
meets_gate = score.meets_target

IF meets_gate AND critical_open == 0 AND high_open == 0:
    → quality_complete = true → STOP, report pass

ELIF meets_gate AND (critical_open > 0 OR high_open > 0):
    → continue to Phase 7 (fix critical/high even if score passed)

ELIF saturation_check(registry, round_num, 3):
    → stop (plateau: 3 rounds of no new issues)
    → report partial

ELSE:
    → proceed to Phase 7 (improvement)
```

---

### Phase 7: Improvement (Agent + CLI, ~30 min per fix)

Load open-issue queue (severity-sorted):

```bash
python3 scripts/issue_tracker.py open \
  .sessi-work/issue_registry.json \
  > .sessi-work/round_<n>/open_issues.json
```

**For each open issue (critical → high → medium → low → info):**

#### Step 7.1: Pre-fix state (CLI)

```bash
# Get pre-fix baseline
python3 scripts/llm_router.py <dimension>
# Run the tool for <dimension> → save baseline score
```

#### Step 7.2: Apply fix (Agent)

Minimal, targeted change in the codebase addressing the specific issue.

#### Step 7.2a: Blast radius check (CLI safety gate, if CRG available)

**BEFORE committing**, check architectural impact:

```bash
git add <modified_files>
# (not committed yet)

python3 scripts/crg_integration.py risky . HEAD 0.7
# exits 1 if risk_score >= 0.7 OR touches hub/bridge node

IF risky:
    git reset --hard HEAD
    python3 scripts/issue_tracker.py defer \
      .sessi-work/issue_registry.json <issue_id> <round> \
      "CRG risk_score 0.X: touches hub/bridge node, requires human review"
    GOTO next issue
ELSE:
    CONTINUE to 7.3
```

This prevents auto-fixes from silently breaking architecture.

#### Step 7.3: Verify fix (CLI)

```bash
# Re-run dimension tool
# Compare: baseline_score vs new_score

IF new_score > baseline_score AND no regression:
    # Fix worked; commit it
    
    COMMIT_SHA=$(git rev-parse HEAD)
    FILES=$(git show --name-only --format= $COMMIT_SHA | tr '\n' ',')
    
    python3 scripts/issue_tracker.py fix \
      .sessi-work/issue_registry.json <issue_id> <round> \
      "$COMMIT_SHA" "$FILES"
    
    git commit -m "fix(<dimension>): <message> [issue:<id>]"

ELSE:
    git revert --no-edit HEAD
    python3 scripts/issue_tracker.py defer \
      .sessi-work/issue_registry.json <issue_id> <round> \
      "Tool showed no improvement; deferred"
```

**One commit per fix. Always capture commit_sha + files for traceability.**

#### Step 7.4: Deferred or wontfix (CLI)

For issues out of scope or low-value:

```bash
# Cost-benefit triage (from improvement_plan.md Step 2a)
python3 scripts/issue_tracker.py wontfix \
  .sessi-work/issue_registry.json <issue_id> <round> \
  "severity=low; occurrence=rare; impact=negligible; cost=high"

# OR

python3 scripts/issue_tracker.py defer \
  .sessi-work/issue_registry.json <issue_id> <round> \
  "Out of scope: scheduled for next milestone"
```

**Reason field is mandatory** (4-part structure for wontfix).

#### Step 7.5: Loop back to Phase 2

After each fix, go back to Phase 2 (re-evaluate the dimension) to confirm
the fix improved the score.

---

### Phase 8: Final Report (Agent + CLI, ~10 min)

After all rounds or early-stop, generate the complete quality report.

#### Step 8.1: Auto-generate structured report (CLI)

```bash
python3 scripts/report_gen.py \
  <repo_path> \
  .sessi-work \
  .sessi-work/issue_registry.json \
  <score_gate> \
  .sessi-work/final_report.md
```

Outputs 7 mandatory sections:
1. Summary Statistics
2. Score Trajectory
3. Per-Dimension Breakdown
4. Issues Fixed (with commit SHA + files)
5. Accepted Risks (wontfix + deferred with reasons)
6. Still Open
7. Evidence Trail (git log)

#### Step 8.2: Add narrative (Agent)

Claude adds 3 sections on top:
8. Root-Cause Themes
9. Remaining Risk
10. Recommendation Rationale

See `prompts/final_report.md` for anti-hallucination rules.

#### Step 8.3: Verify traceability (CLI)

```bash
python3 -c "
import json
r = json.load(open('.sessi-work/issue_registry.json'))
for i in r['issues']:
    if i['status'] == 'fixed' and not (i.get('commit_sha') or i.get('files_changed')):
        print(f'MISSING TRACEABILITY: {i[\"id\"]}')
"
```

If output is non-empty, go back to Phase 7 and update registry with commit SHAs.

---

## Summary Table: CLI vs Agent

| Phase | Tool | Command | Output |
|-------|------|---------|--------|
| 1. Setup | CLI | `config_loader.py`, `setup_target.py` | config.json, target.path, crg_status.json |
| **1.5. Recon** | **Claude + CRG** | **`crg_reconnaissance.md` (9 MCP tools)** | **crg_reconnaissance.json + pre-seeded issues** |
| 2a. Route | CLI | `llm_router.py` | tier + provider |
| 2b. Run Tools | CLI | tooling commands (pylint, pytest, etc.) | .txt files |
| 2b. Evaluate T1/2 | Gemini | MCP call | tool_score + llm_score |
| **2b. Evaluate T3** | **Claude + CRG** | **`/mcp get_hub_nodes`, etc.** | **CRG context** |
| 2b. Eval T3 (continued) | Claude | native reasoning | llm_score |
| 2c. Write Score | Claude | manual JSON write | scores/*.json |
| 2d. Register | CLI | `issue_tracker.py add` | issue_registry.json updated |
| 3. Score | CLI | `score.py` | final_score.json |
| 4. Verify | CLI | `verify.py` + `crg_integration.py blast` | verified.json + crg_blast.json |
| 5. Checkpoint | CLI | `checkpoint.py` + git | round_<n>.md, tag |
| 6. Early-Stop | Claude | logic check | decision: stop or continue |
| **7a. Pre-Fix** | **CLI** | **`llm_router.py` + tool run** | **baseline_score** |
| **7b. Fix** | **Claude** | **edit source code** | **modified files** |
| **7.2a. Blast** | **CLI** | **`crg_integration.py risky`** | **exit 0/1** |
| **7c. Verify** | **CLI** | **re-run tool, compare** | **new_score** |
| 7d. Register Fix | CLI | `issue_tracker.py fix` | issue_registry.json updated |
| 8. Report | CLI | `report_gen.py` | final_report.md (7 sections) |
| 8 Narrative | Claude | manual writing | 3 narrative sections |
| 8c Verify | CLI | traceability check | "MISSING" or OK |

---

## Key Interaction Patterns

### Pattern 1: Tier 3 Evaluation (CRG + Claude)

```
CLI: llm_router.py architecture
  → returns tier=3, provider=claude

The Agent:
  /mcp get_hub_nodes              ← query graph
  /mcp get_architecture_overview  ← more graph
  /mcp semantic_search_nodes "circular"  ← targeted search
  
  [Agent reads 3 CRG JSON results, spot-reads 2 flagged files]
  
  Write to .sessi-work/round_1/scores/architecture.json:
  {
    "tool_score": 72,
    "llm_score": 70,
    "score": 70,
    "findings": [...]  ← cite CRG output + file:line
  }

CLI: issue_tracker.py add ... ← register findings
```

### Pattern 2: Fix Verification (CLI + CRG safety gate)

```
The Agent:
  [applies fix to src/util.py]
  
CLI:
  git add src/util.py
  crg_integration.py risky . HEAD 0.7
    → risk_score 0.65, exit 0 (not risky)
  
  [run linting tool]
  old_score=72, new_score=78 ✓
  
  COMMIT_SHA=$(git rev-parse HEAD)
  issue_tracker.py fix issue_abc <round> $COMMIT_SHA "src/util.py"
  git commit -m "fix(linting): remove unused imports [issue:abc]"
```

### Pattern 3: End-of-Round Report

```
CLI:
  report_gen.py . .sessi-work issue_registry.json 85 final_report.md
    → Outputs sections 1–7 (structured, deterministic)

The Agent:
  [reads final_report.md sections 1–7]
  
  Adds sections 8–10 (narrative, interpretation):
    8. "CRG detected 2 hub nodes were refactored, likely root causes"
    9. "Risk: test_coverage gaps in new modules; re-assess next run"
    10. "Recommendation: pass-with-risks (quality_complete=true, 1 deferred)"
```

---

## Graceful Degradation (No CRG)

If `code-review-graph` is not installed or unavailable:

- **Phase 2b (Tier 3):** Falls back to full-code read (higher token cost, no loss of correctness)
- **Phase 7.2a (Blast gate):** Skipped silently; only tool-based verification
- **Phase 4.2 (Structural verify):** Skipped silently; only deterministic verify

**Framework still works end-to-end.** CRG is an optimization, not a requirement.

---

## Hands-On Example: Round 1

Assume:
- Target: `/path/to/myapp`
- Config: `config.example.yaml` (all 12 core dimensions enabled)
- 2 issues found: 1 critical (security), 1 medium (architecture)

**Round 1, 40 minutes:**

```bash
# Setup (3 min)
python3 scripts/config_loader.py config.example.yaml > config.json
python3 scripts/setup_target.py /path/to/myapp

# Evaluate (15 min: 2 Tier 1 + 1 Tier 2 + 5 Tier 3 dims, sample)
# [Claude evaluates each dimension in sequence]

# Score (30 sec)
python3 scripts/score.py .sessi-work/round_1 config.json issue_registry.json

# Verify (1 min)
python3 scripts/verify.py result.json .sessi-work/round_1 /path/to/myapp
code-review-graph update
python3 scripts/crg_integration.py blast . HEAD~12 > crg_blast.json

# Checkpoint (1 min)
python3 scripts/checkpoint.py round_1 final_score.json
git tag round-1 && git commit -m "checkpoint: round 1"

# Early-stop decision (Claude logic)
# open_critical=1, open_high=0, meets_gate=false → continue

# Improvement (Phase 7, ~20 min for 1 critical fix)
# Claude fixes src/api.py SQL injection
# CLI: crg_integration.py risky . HEAD 0.7 → safe, commit
# CLI: re-run security tool → 72 → 85 ✓
# CLI: issue_tracker.py fix issue_abc1234 1 commit_sha src/api.py

# Loop back to Phase 2: re-eval security dimension
# [Claude re-evaluates]
# Score: 87 overall → meets_gate ✓
# open_critical: 0 → quality_complete ✓

# Report
python3 scripts/report_gen.py /path/to/myapp .sessi-work issue_registry.json 85 report.md
# [Claude adds narrative sections 8–10]
# final_report.md ready for review
```

**Result:** 1 critical issue fixed, quality_complete=true, stop.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| CRG tools not showing | Global config not updated | `code-review-graph install --platform openclaw` to global config |
| `crg_integration.py check` fails | CRG not installed | `pipx install code-review-graph` |
| Graph shows "Nodes: 0" after session | Auto-build failed | Check `.sessi-work/crg_status.json` for reason; retry: `code-review-graph build --repo .` |
| Blast radius is always 0.0 | Graph outdated | `code-review-graph update --repo .` |
| Issue registry orphaned (open issue fixed but not marked) | Issue tracker not called | Always call `issue_tracker.py fix` after successful tool re-run |


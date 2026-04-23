# Auto-Research Quality Improvement Skill

Implements an auto-research-style quality improvement loop for GitHub repos or local folders, with configurable targets across 12 core + 5 optional dimensions.

**Design principle:** The goal is **actual quality improvement** — resolving every critical/high issue found — not reaching a numeric score. Scores are a minimum gate; the issue registry is the source of truth for completion.

## Execution Contract

### Step 1: Resolve Configuration
- Load user config from `config.yaml` (or `config.advanced.yaml`)
- Merge with defaults; validate all dimensions exist
- Normalize weights across enabled dimensions
- Output: resolved config JSON

### Step 2: Resolve Target
- Clone GitHub repo (if URL) or use local folder path
- Set up working directory with git tracking
- **Auto-initialize CRG** (transparent): detect if `code-review-graph` is installed;
  if yes and no graph exists → auto-build; write result to `.sessi-work/crg_status.json`
- Initialize issue registry at `.sessi-work/issue_registry.json` (persists across rounds)
- Output: TARGET_PATH to stdout

```bash
python3 scripts/setup_target.py <github-url-or-local-path> [work_dir]
# Stderr shows CRG status: "[CRG] ✓ Ready — 342 nodes (auto-built)"
#                        or "[CRG] Not available — not installed. Framework will run without CRG."
```

### Step 2.5: CRG Structural Reconnaissance (if CRG available)

Runs **once per session**, before the first evaluation round.
Follows `prompts/crg_reconnaissance.md`.

9 CRG queries → structural intelligence baseline:
- **High-risk components** — hub + bridge nodes with high centrality
- **Untested hotspots** — hub nodes in knowledge gaps → pre-seeded as `high` issues
- **Module cohesion** — low-cohesion communities → pre-seeded as `medium` issues
- **Unexpected couplings** — surprising cross-module edges → pre-seeded as `medium` issues
- **Dead code** — unreferenced functions/classes → pre-seeded as `low` issues

Output: `.sessi-work/crg_reconnaissance.json` + pre-seeded issues in registry.
This file is read by evaluate_dimension.md Step 2a to focus per-dimension analysis.

> Token cost: ~3,900 tokens total (vs ~10,000+ for blind file reading).
> Skip silently if `crg_status.json` shows `available: false`.

### Step 3: Iterate Rounds (3 default, configurable)
Each round: **3a-evaluate → 3b-score → 3c-verify → 3d-checkpoint → 3e-early-stop → 3f-improve**

**3a. Evaluate Each Enabled Dimension**
- Run per-dimension evaluation: tool-first hierarchy (tool score + LLM score)
- Reconcile: min(tool_score, llm_score) to prevent optimism bias
- Evidence requirement: every finding must have evidence (tool output or code change)
- **Every finding → written to issue registry** via `scripts/issue_tracker.py add`
  - Idempotent: same finding yields same ID; repeats are de-duplicated
  - Each issue carries: severity (critical/high/medium/low/info), dimension, file, line, evidence
- Output: per-dim JSON with scores, findings, tool outputs

**3b. Compute Weighted Score**
- Aggregate per-dim scores with normalized weights
- Calculate overall_score (0-100)
- Surface `open_critical_count`, `open_high_count`, `open_medium_count` from registry
- Identify failing dimensions sorted by impact (gap × weight)
- Output: score JSON with breakdown, failing dims, `meets_target`, `quality_complete`

**3c. Verify Round (Anti-Bias Check)**
- Deterministic verification: compare pre/post tool outputs + git diffs
- Cap unsupported claims: Δ > 10 without evidence requires ≥3 lines of diff
- Surface regressions with revert protocol
- Output: verified.json (use for downstream decisions, not raw scores)

**3d. Checkpoint Round**
- Snapshot: round_<n>.json with all scores, findings, deltas (via `checkpoint.py`)
- Mark improvements per dimension
- Persist `issue_registry.json` snapshot into round folder for audit
- Claude executes: `git tag round-<n>` on the target repo (not automatic)
- Changes remain local only — no automatic `git push` to remote
- Output: markdown summary for dashboard

> **Commit timing:**
> - Per-fix: one `git commit` per issue fixed (in Step 3f, called by the Agent)
> - Per-round: one `git tag round-<n>` (in Step 3d, called by the Agent)
> - Never automatic push — user decides when to push to remote

**3e. Early-Stop Check (Issue-Driven)**

```
critical_open = registry.summary().open_critical
high_open     = registry.summary().open_high

IF overall_score >= score_gate AND critical_open == 0 AND high_open == 0:
    → stop: quality_complete = true  (真正完成)

ELIF overall_score >= score_gate AND (critical_open > 0 OR high_open > 0):
    → continue: score passed but unresolved critical/high issues remain
    → DO NOT stop — this is the exact anti-pattern we guard against

ELIF saturation_check(registry, current_round, saturation_rounds=3) == true
     AND no score improvement in last round:
    → stop: plateau reached, remaining issues marked deferred
    → emit deferred_fixes.md for human review

ELSE:
    → proceed to 3f
```

Saturation detection — **Claude must call this explicitly**:
```bash
python3 scripts/issue_tracker.py saturation \
  .sessi-work/issue_registry.json <current_round>
# exits 0 (not saturated) or 1 (saturated — no new issues for 3 consecutive rounds)
```
Returns true when no NEW issues were recorded for N consecutive rounds (default: 3).
If saturated AND no score improvement from the previous round → stop and emit deferred_fixes.md.

**3f. Improve (Issue-Driven)**

Input is the **open-issues queue**, not failing dimensions:

```
open = issue_tracker.open_issues(registry)  # sorted by severity, then round_found

Priority order:
  1. ALL open critical issues   (regardless of dimension score)
  2. ALL open high issues       (regardless of dimension score)
  3. Open medium issues in failing dimensions (score < target)
  4. Open low issues if time budget allows
```

For each fix:
- Run dimension tool pre/post → revert if no measurable improvement
- On success: `issue_tracker.py fix <id> <round> "<commit_sha>"`
- On intentional skip: `issue_tracker.py defer <id> <round> "<reason>"` (reason required)
- Guardrails: never weaken tests, broaden exception handling, add @ts-ignore
- One commit per fix
- Loop to 3a

### Step 3g. Repository Hygiene Check (Mandatory, Every Round)

**Every round must pass this check before proceeding to Step 4 or tagging.**

```bash
# 1. Working tree must be clean
git status --porcelain
# → Must output empty. Uncommitted changes = framework failure.

# 2. No artifacts tracked by git
git ls-files | grep -E "(\.sessi-work/|coverage/|mutants/|\.coverage\.|\.pytest_cache/|\.code-review-graph/)"
# → Must output empty. Any match = immediately update .gitignore + git rm --cached

# 3. No artifacts left on disk (even if gitignored)
ls .sessi-work/ coverage/ mutants/ .pytest_cache/ .coverage.* 2>/dev/null
# → .sessi-work/ may exist; all others must not exist
```

**If artifacts are found:**
1. Update `.gitignore` to cover the artifact type
2. `git rm --cached <path>` to untrack (do NOT delete from disk)
3. Commit the .gitignore update
4. Re-verify the check passes

**After the final round (Step 4), clean git history once:**
```bash
# Only if artifacts were EVER committed to history (detected in Step 3g)
# This is a history rewrite — requires force push
git filter-repo --invert-paths --force  # remove artifacts from history
git push --force
```

**Artifat classes that must never enter the repo:**

| Pattern | Type | Always gitignored? |
|---------|------|-------------------|
| `.sessi-work/` | Session state | ✅ Yes |
| `coverage/` | Coverage reports | ⚠️ Must be added if missing |
| `mutants/` | Mutation test output | ⚠️ Must be added if missing |
| `.coverage.*` | Coverage data | ⚠️ Must be added if missing |
| `.pytest_cache/` | Pytest cache | ⚠️ Must be added if missing |
| `.code-review-graph/` | CRG data | ⚠️ Must be added if missing |

> **Why this step is critical:** `coverage/` and `mutants/` were committed to `tts-kokoro-compare` history across 43 commits. They inflated the repo size, polluted git logs, and required `git filter-repo` to remove. Prevention via `.gitignore` + `git rm --cached` is the only correct approach — retroactive cleanup is a last resort.

### Step 4: Final Report

Full-transparency report — see `prompts/final_report.md` for the protocol.
Auto-generated from issue registry + round data + git log:

```bash
python3 scripts/report_gen.py \
  <repo_path> \
  .sessi-work \
  .sessi-work/issue_registry.json \
  <score_gate> \
  .sessi-work/final_report.md
```

**Mandatory sections:**

1. **Trajectory** — per-dimension score delta across all rounds.
2. **Fixed Issues** — `report.fixed_count`, grouped by dimension with commit SHAs.
3. **Accepted Risks** (`report.accepted_risks`) — deferred + wontfix issues,
   rendered as a table with severity, dimension, message, and the 4-part reason:

   ```markdown
   ## Accepted Risks / Not Fixed

   | ID | Severity | Dimension | Issue | Reason |
   |----|----------|-----------|-------|--------|
   | abc1234 | low | architecture | Circular dep in util | severity=low; occurrence=rare (only on cold start); impact=negligible (self-healing); cost=high (would require arch split) |
   ```

   This is the audit trail: every low-value issue that was **consciously not fixed**
   shows here, so nothing disappears silently.

4. **Still Open** (`report.open`) — any issue that is still open at end-of-run.
   If this contains anything of severity ≥ medium, the recommendation is `partial`.
5. **Recommendation** — one of:
   - `pass` — `quality_complete = true` AND no open ≥ medium issues
   - `pass-with-risks` — `quality_complete = true` AND only accepted_risks remain
   - `partial` — `max_rounds` reached with open ≥ medium issues
   - `fail` — regressions detected or score dropped below baseline
6. **Evidence** — citations to commits (`git log --oneline`) and tool outputs.

## Default Configuration

- **Rounds:** 3 (max)
- **Score gate:** 85/100 (minimum — not a completion goal)
- **Early-stop:** issue-driven (score_gate AND zero open critical/high)
- **Saturation rounds:** 3 (stop if no new issues found for 3 rounds)
- **Commit strategy:** one per fix
- **Evidence threshold:** 10 points
- **Bias cap:** Δ +3 without diff evidence

## Tool Hierarchy

```
final_score = min(tool_score, llm_score)
```

This prevents LLM from inflating scores when tools say otherwise.

## Dimension System

**12 Core Dimensions (all enabled by default):**
- linting
- type_safety
- test_coverage
- security
- performance
- architecture
- readability
- error_handling
- documentation
- secrets_scanning
- mutation_testing
- license_compliance

**5 Extended Dimensions (optional, disabled by default):**
- property_testing
- fuzzing
- accessibility
- observability
- supply_chain_security

See `docs/EXTENDED_DIMENSIONS.md` for prerequisites and integration.

## Output Structure

```
.sessi-work/
├── round_1/
│   ├── scores/
│   │   ├── linting.json
│   │   ├── type_safety.json
│   │   └── ...
│   ├── tools/
│   │   ├── linting.txt (raw tool output)
│   │   └── ...
│   ├── round_1.json (snapshot)
│   └── round_1.md (summary)
├── round_2/
├── round_3/
└── final_report.md
```

## Invocation

**This framework runs via the OpenClaw conversation interface.**
There is no standalone CLI command to launch it. The Agent reads this SKILL.md as
its instruction set and executes each step interactively.

### Starting a Quality Improvement Run

Open the conversation and say (example prompts):
```
"Please run the quality improvement skill on /path/to/repo"
"Evaluate code quality for https://github.com/user/repo using config.yaml"
"Run all 12 quality dimensions on the current project"
```

Claude will then execute Steps 1–4 from this document, calling CLI scripts
where needed. The Python scripts are called by the Agent as shell commands —
they are not invoked directly by users.

### CLI Scripts (called by the Agent, not by users directly)

```bash
# Step 1 — Claude calls these to resolve config + target
python3 scripts/config_loader.py config.yaml
python3 scripts/setup_target.py <github-url-or-local-path>

# Step 3b — Claude calls this to compute weighted score
python3 scripts/score.py .sessi-work/round_<n> config.json

# Step 3c — Claude calls this for anti-bias verification
python3 scripts/verify.py .sessi-work/round_<n>/result.json .sessi-work/round_<n> <repo_path>

# Step 3d — Claude calls this to snapshot the round
python3 scripts/checkpoint.py round <n> scores.json <overall_score>

# Step 4 — Claude calls this to generate the final report
python3 scripts/report_gen.py <repo_path> .sessi-work .sessi-work/issue_registry.json <score_gate> .sessi-work/final_report.md
```

### Prompts (read and followed by the Agent, not executed as commands)

- `prompts/evaluate_dimension.md` — Claude follows this protocol for each dimension
- `prompts/improvement_plan.md` — Claude follows this to plan and apply fixes
- `prompts/verify_round.md` — Claude follows this for cross-dimension regression checks
- `prompts/final_report.md` — Claude follows this to produce the final report

## Anti-Bias Defenses (12 Layers)

Defends against: laziness (偷懶), shortcuts (走捷徑), hallucination (幻覺/說謊), self-congratulation (自我感覺良好).

**Original 7 layers:**
1. **Tool-first hierarchy:** `final_score = min(tool_score, llm_score)`
2. **Evidence requirement:** Every finding needs tool output or code diff
3. **Per-fix re-verification:** Revert if tool shows no improvement
4. **Deterministic verification (verify.py):** quantitative comparison pre/post, cap unsupported gains
5. **Regression detection:** surface changes that hurt other dimensions
6. **Path heuristics:** prevent undetected regressions
7. **Structural drift detection (CRG):** architectural regression via risk-score + hub graph

**New 5 layers (v3.1):**
8. **Execution Contract:** behavioral red lines declared at prompt start — skip = invalid output
9. **Devil's Advocate:** Secondary LLM call challenges Tier 3 findings before score write; deterministic penalty rules
10. **High-Score Confirmation Gate:** `llm_score ≥ 85` requires negative space proof + CRG evidence + tool alignment; else capped at 80
11. **Fix Verification Enforcement Gate:** `mark_fixed()` raises `ValueError` without `commit_sha` + `tool_rerun_path` for tool-verifiable dims
12. **Self-Consistency Uncertainty Gate:** `verify.py` flags Δ > 15 with < 3 evidence pieces, tool/LLM divergence > 20 pts, high scores bypassing Step 2c

See `docs/ANTI_BIAS.md` for detailed analysis.

## Code Review Graph Integration

When [Code Review Graph](https://github.com/code-review-graph) (CRG) is installed,
**four integration points** activate automatically (24 of 27 MCP tools utilized,
6 with deep-integration formulas — see `crg_analysis.py`):

1. **Structural reconnaissance (crg_reconnaissance.md — Step 2.5):** runs once
   per session before the first evaluation round. Uses `get_minimal_context`,
   `list_graph_stats`, `get_suggested_questions`, `get_hub_nodes`, `get_bridge_nodes`,
   `list_communities`, `get_community`, `get_knowledge_gaps`,
   `get_surprising_connections`, `refactor_tool(dead_code)` to identify high-risk
   components, untested hotspots, unexpected couplings, and dead code.
   Pre-seeds the issue registry (~3,900 tokens vs ~10,000+ for blind file reading).

2. **Tier 3 evaluation (evaluate_dimension.md):** architecture / readability /
   performance / documentation / error_handling dimensions start with
   `get_minimal_context` then query dimension-specific tools (hub nodes,
   bridge nodes, large functions, knowledge gaps, community cohesion, flow analysis)
   before reading any source code. Target: −30 to −50% Tier 3 token reduction.

3. **Pre-fix context + safety gate (improvement_plan.md):** before each fix,
   `get_minimal_context` + `get_review_context` replace manual file reads
   (impact + source + review guidance in one call); `get_impact_radius` records
   hub/bridge status; `crg_integration.py risky` gates commits — risk_score ≥ 0.7
   or hub/bridge touch → defer instead of commit.

4. **Structural verification (verify_round.md):** after each round,
   `code-review-graph update` + `detect_changes_tool` measures architectural
   drift. Drift > 0.4 triggers the revert protocol; new untested functions
   are auto-registered as `test_coverage` issues.

**MCP tools used across all integration points:**

| Tool | Integration point |
|------|------------------|
| `get_minimal_context` | Step 2.5 + every Tier 3 eval + every fix |
| `list_graph_stats` | Step 2.5 reconnaissance |
| `get_suggested_questions` | Step 2.5 reconnaissance |
| `get_hub_nodes` | Step 2.5 + architecture/readability/performance/docs |
| `get_bridge_nodes` | Step 2.5 + architecture |
| `list_communities` | Step 2.5 + architecture |
| `get_community` | Step 2.5 + architecture |
| `get_knowledge_gaps` | Step 2.5 + architecture |
| `get_surprising_connections` | Step 2.5 + architecture |
| `refactor_tool` (dead_code) | Step 2.5 reconnaissance |
| `find_large_functions` | readability eval |
| `list_flows` | performance + error_handling eval |
| `get_flow` | performance + error_handling (drill-down) |
| `get_affected_flows` | error_handling eval |
| `semantic_search_nodes` | error_handling eval |
| `get_architecture_overview` | architecture eval (layering + module map) |
| `generate_wiki` / `get_wiki_page` | documentation eval |
| `get_docs_section` | documentation eval (targeted) |
| `query_graph_tool` | Tier 3 (tests_for, callers_of, fan-in/out) |
| `traverse_graph_tool` | Tier 3 (fan-in/fan-out depth analysis) |
| `get_review_context` | improvement_plan.md per-fix context |
| `get_impact_radius` | improvement_plan.md safety gate |
| `detect_changes` | verify_round.md structural drift |

**Installation** (one-time, per target repo):
```bash
code-review-graph install --platform openclaw --repo <target>
# Restart the application to load .mcp.json
# Graph build is automatic — setup_target.py runs it on first session
```

Framework **gracefully degrades** without CRG — all integration points skip
silently; only token efficiency and structural verification are lost.

> **Full reference:** `docs/CRG_DEEP_INTEGRATION.md` — complete workflow
> diagram, 6 deep-integration points, threshold table, data-flow map.

### Deep Integration Layer (`scripts/crg_analysis.py`)

"Used" ≠ "deeply integrated." A CRG tool is **deeply integrated** when its
output drives a deterministic decision — a formula, a threshold, a severity
bucket — without LLM interpretation. The deep-integration layer lives in
`scripts/crg_analysis.py` and produces `.sessi-work/crg_metrics.json`,
consumed directly by `score.py` and the prompts.

**Six concrete deep-integration points:**

| # | Signal              | Deterministic output                         | Consumer                |
|---|---------------------|----------------------------------------------|-------------------------|
| 1 | `risk_score`        | `eval_depth` = `deep` / `standard` / `fast`  | evaluate_dimension.md   |
| 2 | community cohesion  | architecture sub-score 0–100                 | score.py (min-with-tool)|
| 3 | flow coverage       | error_handling sub-score 0–100               | score.py (min-with-tool)|
| 4 | dead-code ratio     | `escalate_severity` low→medium if >5%        | improvement_plan.md     |
| 5 | hub fan-in          | severity bucket critical/high/medium/low     | evaluate_dimension.md   |
| 6 | suggested questions | auto-seeded registry issues via severity map | crg_reconnaissance.md   |

All thresholds are explicit and ENV-overridable (`CRG_RISK_DEEP`,
`CRG_COHESION_HEALTHY`, etc.) — see `crg_reconnaissance.md §Step 11` for
the full table. Inspect effective values:

```bash
python3 scripts/crg_analysis.py thresholds
```

The contract for sub-score folding is `score = min(tool_score, crg_score)` —
CRG can **only pull a dimension score down**, never inflate it. This
prevents the failure mode where a lint-clean repo hides broken architecture.

## References

- Framework: Based on Karpathy's autoresearch pattern
- Quality model: Harness Engineering 12-dimension weighted scoring
- Implementation: OpenClaw skill with Python orchestration + LLM evaluation steps

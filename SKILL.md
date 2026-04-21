# Auto-Research Quality Improvement Skill (OpenClaw Version)

Implements an auto-research-style quality improvement loop for GitHub repos or local folders, with configurable targets across 12 core + 5 optional dimensions.

**Design principle:** The goal is **actual quality improvement** — resolving every critical/high issue found — not reaching a numeric score. Scores are a minimum gate; the issue registry is the source of truth for completion.

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
  - "quality scan"
  - "軟體品質提升"
  - "SW improvement"
- **source**: `/tmp/openclaw_sw_improvement/` or GitHub `johnnylugm-tech/openclaw_sw_improvement`

---

## 對話式互動（核心設計）

**人類不需要任何 command line 操作。** 人類只說要做什麼，Agent 讀這份文件後自動執行所有步驟，最後回報結果。

### 觸發範例

```
Human: "quality improvement on https://github.com/user/repo"
Human: "SW improvement on /path/to/my/project"
Human: "軟體品質提升"
```

### Agent 內部執行（完整流程）

```
Human: "quality improvement on https://github.com/user/repo"
     ↓
Agent（我，身為 LLM）:
  1. 讀 SKILL.md（這份文件）→ 了解完整執行規格
  2. 讀 prompts/ 目錄下的所有 prompt 檔案
  3. 執行 Step 1 → config.yaml → config.json
  4. 執行 Step 2 → setup_target.py（clone + CRG auto-build）
  5. 執行 Step 2.5 → CRG structural reconnaissance（若 CRG 可用）
  6. 執行 Step 3（最多 3 輪）:
     3a. 執行 12 dims evaluation（dimension_executor.py + evaluate_dimension.md prompt）
     3b. score.py 計算加權分數
     3c. verify.py 防 bias 驗證
     3d. checkpoint.py 存檔 + git tag round-<n>
     3e. quality_complete 檢查
         → 分數 >= 85 AND 無 open critical/high → 完成
         → 否則 → 3f
     3f. 依 severity 順序修復 open issues（LLM 直接改 code）
  7. 執行 Step 4 → report_gen.py 生成最終報告
  8. git tag v2.0（若 quality_complete=true）
  9. 向 Human 回報結果
```

---

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
- **Execute: `git tag round-<n>` on the target repo** (not automatic — Agent 执行)
- Changes remain local only — no automatic `git push` to remote
- Output: markdown summary for dashboard

> **Commit timing:**
> - Per-fix: one `git commit` per issue fixed (in Step 3f, called by Agent)
> - Per-round: one `git tag round-<n>` (in Step 3d, called by Agent)
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

Saturation detection — **Agent must call this explicitly**:
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

---

## Default Configuration

- **Rounds:** 3 (max)
- **Score gate:** 85/100 (minimum — not a completion goal)
- **Early-stop:** issue-driven (score_gate AND zero open critical/high)
- **Saturation rounds:** 3 (stop if no new issues found for 3 rounds)
- **Commit strategy:** one per fix
- **Evidence threshold:** 10 points
- **Bias cap:** Δ +3 without diff evidence

---

## Tool Hierarchy

```
final_score = min(tool_score, llm_score)
```

This prevents LLM from inflating scores when tools say otherwise.

---

## Dimension System

**12 Core Dimensions (all enabled by default):**

| Dimension | Tool | Weight | Target | Description |
|-----------|------|--------|--------|-------------|
| linting | pylint | 0.06 | 95 | Python lint and style issues |
| type_safety | mypy | 0.10 | 95 | Static type checking |
| test_coverage | pytest --cov | 0.13 | 80 | Code coverage by tests |
| security | bandit | 0.10 | 90 | Security vulnerability scanning |
| performance | (custom) | 0.07 | 80 | Performance anti-patterns |
| architecture | cloc + CRG | 0.07 | 80 | Code structure and modularity |
| readability | radon | 0.06 | 85 | Code complexity metrics |
| error_handling | (grep-based) | 0.09 | 85 | Exception handling patterns |
| documentation | (grep-based) | 0.10 | 85 | Docstring coverage |
| secrets_scanning | gitleaks | 0.08 | 100 | Hardcoded secrets detection |
| mutation_testing | pytest --gremlins --gremlins-executor=subprocess | 0.08 | 70 | Mutation testing coverage |
| license_compliance | scancode | 0.06 | 95 | License header compliance |

**5 Extended Dimensions (optional, disabled by default):**

| Dimension | Tool | Weight | Target |
|-----------|------|--------|--------|
| property_testing | (custom) | 0.07 | 75 |
| fuzzing | (custom) | 0.08 | 70 |
| accessibility | (custom) | 0.06 | 85 |
| observability | (custom) | 0.05 | 80 |
| supply_chain_security | (custom) | 0.06 | 80 |

---

## Output Structure

```
.sessi-work/
├── quality_state.json       ← current state (for resume)
├── config.json              ← resolved config
├── crg_status.json         ← CRG availability + node count
├── crg_reconnaissance.json ← 9 CRG commands output
├── crg_metrics.json        ← structured metrics (6 deep points)
├── issue_registry.json      ← persistent issue tracking
├── round_1/
│   ├── scores/
│   │   ├── linting.json
│   │   ├── type_safety.json
│   │   └── ... (all 12 dimensions)
│   ├── tools/
│   │   └── linting.txt (raw tool output)
│   ├── round_1.json (snapshot)
│   └── round_1.md (summary)
├── round_2/
├── round_3/
└── final_report.md
```

---

## Anti-Bias Defenses

1. **Tool-first hierarchy:** Claims capped by tool scores
2. **Evidence requirement:** Every finding needs tool output or code diff
3. **Per-fix re-verification:** Revert if tool shows no improvement
4. **Deterministic verification:** quantitative comparison pre/post
5. **Regression detection:** surface changes that hurt dimensions
6. **Path heuristics:** prevent undetected regressions
7. **Structural drift detection (CRG):** catches architectural regressions
   that dimension tools cannot see — new hub nodes, expanded test gaps,
   risk-score jumps across rounds

---

## Code Review Graph Integration

When CRG is installed, **four integration points** activate automatically
(22 of 27 MCP tools utilized, 6 with deep-integration formulas — see `scripts/crg_analysis.py`):

**4 CRG Integration Points:**

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
   `code-review-graph update` + `detect_changes` measures architectural
   drift. Drift > 0.4 triggers the revert protocol; new untested functions
   are auto-registered as `test_coverage` issues.

**MCP tools used across all integration points:**

| Tool | Integration point |
|------|-------------------|
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
| `generate_wiki` / `get_wiki_page` | documentation eval |
| `get_docs_section` | documentation eval (targeted) |
| `query_graph_tool` | Tier 3 (tests_for, callers_of, fan-in/out) |
| `traverse_graph_tool` | Tier 3 (fan-in/out depth analysis) |
| `get_review_context` | improvement_plan.md per-fix context |
| `get_impact_radius` | improvement_plan.md safety gate |
| `detect_changes` | verify_round.md structural drift |

**Installation** (one-time, per target repo):
```bash
code-review-graph install --platform claude-code --repo <target>
# Graph build is automatic — setup_target.py runs it on first session
```

---

## Deep Integration Layer (`scripts/crg_analysis.py`)

"Used" ≠ "deeply integrated." A CRG tool is **deeply integrated** when its
output drives a deterministic decision — a formula, a threshold, a severity
bucket — without LLM interpretation. The deep-integration layer lives in
`scripts/crg_analysis.py` and produces `.sessi-work/crg_metrics.json`,
consumed directly by `score.py` and the prompts.

**6 Deep Integration Points:**

| # | Signal              | Deterministic output                         | Consumer                |
|---|---------------------|----------------------------------------------|-------------------------|
| 1 | `risk_score`        | `eval_depth` = `deep` / `standard` / `fast`  | evaluate_dimension.md   |
| 2 | community cohesion  | architecture sub-score 0–100                 | score.py (min-with-tool)|
| 3 | flow coverage       | error_handling sub-score 0–100               | score.py (min-with-tool)|
| 4 | dead-code ratio     | `escalate_severity` low→medium if >5%        | improvement_plan.md     |
| 5 | hub fan-in          | severity bucket critical/high/medium/low     | evaluate_dimension.md   |
| 6 | suggested questions | auto-seeded registry issues via severity map | crg_reconnaissance.md   |

All thresholds are explicit and ENV-overridable (`CRG_RISK_DEEP`,
`CRG_COHESION_HEALTHY`, etc.) — see `prompts/crg_reconnaissance.md §Step 11` for
the full table. Inspect effective values:

```bash
python3 scripts/crg_analysis.py thresholds
```

The contract for sub-score folding is `score = min(tool_score, crg_score)` —
CRG can **only pull a dimension score down**, never inflate it. This
prevents the failure mode where a lint-clean repo hides broken architecture.

---

## Prompts (Agent reads and follows these, not executed as commands)

- `prompts/evaluate_dimension.md` — Agent follows this protocol for each dimension
- `prompts/improvement_plan.md` — Agent follows this to plan and apply fixes
- `prompts/verify_round.md` — Agent follows this for cross-dimension regression checks
- `prompts/crg_reconnaissance.md` — Agent follows this for CRG structural analysis
- `prompts/final_report.md` — Agent follows this to produce the final report

---

## CLI Scripts (called by Agent, not by human directly)

```bash
# Step 1 — Agent calls these to resolve config + target
python3 scripts/config_loader.py config.yaml
python3 scripts/setup_target.py <github-url-or-local-path>

# Step 2.5 — Agent calls this to run CRG reconnaissance
python3 scripts/crg_analysis.py run_reconnaissance <repo_path> <work_dir>

# Step 3a — Agent calls this to evaluate all dimensions
python3 scripts/dimension_executor.py --all --repo <repo_path> --work-dir .sessi-work

# Step 3b — Agent calls this to compute weighted score
python3 scripts/score.py .sessi-work/round_<n> config.json

# Step 3c — Agent calls this for anti-bias verification
python3 scripts/verify.py .sessi-work/round_<n>/result.json .sessi-work/round_<n> <repo_path>

# Step 3d — Agent calls this to snapshot the round
python3 scripts/checkpoint.py round <n> scores.json <overall_score>

# Step 3e — Agent calls this for saturation check
python3 scripts/issue_tracker.py saturation .sessi-work/issue_registry.json <current_round>

# Step 4 — Agent calls this to generate the final report
python3 scripts/report_gen.py <repo_path> .sessi-work .sessi-work/issue_registry.json <score_gate> .sessi-work/final_report.md
```

---

## Graceful Degradation

| Missing component | Behavior |
|-------------------|----------|
| CRG not installed | Skip structural analysis, tool-only evaluation |
| Tool not installed | Dimension returns `status: "skip"`, score = 100 |
| Config not found | Use built-in defaults |
| Issue tracker unavailable | Pure score calculation, no issue tracking |

---

## Error Handling

- Tool not found → `status: "skip"`, score = 100
- Tool timeout → `status: "error"`, score = 0
- Score computation failure → fallback to direct tool score average
- CRG graph build failure → log warning, continue without CRG

---

## 與人類對話時的輸出格式

Agent 完成後，向人類報告：

```
✅ Quality Loop 完成（第 N 輪）

📊 分數：78/85（落後 7 分）
🔴 Open issues：3 critical, 2 high, 5 medium

┌─────────────────────────┬────────┬────────┐
│ Dimension               │ Score  │ Target │
├─────────────────────────┼────────┼────────┤
│ test_coverage           │ 62     │ 80     │ ← failing
│ security                │ 71     │ 90     │ ← failing
│ documentation          │ 74     │ 85     │ ← failing
│ ...                    │        │        │
└─────────────────────────┴────────┴────────┘

🔧 Top Issues:
  🔴 [critical] bandit: hardcoded_password — auth.py:47
  🔴 [critical] bandit: hardcoded_password — config.py:22
  🔴 [high] bandit: 6 more secrets found

📁 報告位置：.sessi-work/final_report.md
```

---

## References

- Framework: Based on Karpathy's autoresearch pattern
- Quality model: Harness Engineering 12-dimension weighted scoring
- Implementation: OpenClaw skill with Python orchestration + LLM evaluation steps
- CRG: [code-review-graph](https://github.com/code-review-graph) for structural analysis
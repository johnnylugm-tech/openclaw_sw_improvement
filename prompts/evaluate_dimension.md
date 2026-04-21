# Evaluate Dimension Protocol

Evaluate a single quality dimension using the **tool-first hierarchy** and **LLM tier routing** to minimize token cost while preserving accuracy.

---

## Step 0: Route to Correct LLM

Before anything else, determine which LLM tier to use:

```bash
python3 scripts/llm_router.py <dimension> [tool_output.txt]
```

Read the `tier` and `provider` fields:

| Tier | Provider | Dimensions | Action |
|------|----------|-----------|--------|
| 1 | `gemini` | linting, type_safety, test_coverage, secrets_scanning, license_compliance, mutation_testing | Use `mcp__gemini-cli__ask-gemini` |
| 2 | `gemini` | security | Use `mcp__gemini-cli__ask-gemini` |
| 3 | `claude_native` | architecture, readability, error_handling, documentation, performance | Use Claude reasoning (this session) |

**NEVER** use Claude for Tier 1/2 dimensions. **NEVER** use Gemini for Tier 3.

---

## Step 1: Run Tools

Run all tools for this dimension. Save raw output:

```bash
# Output path: .sessi-work/round_<n>/tools/<dimension>.txt
```

**Tool commands by dimension:**

### linting (Tier 1)
```bash
pylint src/ --output-format=json 2>&1 | head -200
eslint src/ --format json 2>&1 | head -200
```

### type_safety (Tier 1)
```bash
pyright src/ --outputjson 2>&1 | head -200
```

### test_coverage (Tier 1)
```bash
coverage run -m pytest && coverage report --format=json
nyc --reporter=json npm test
```

### security (Tier 2)
```bash
bandit -r src/ -f json 2>&1 | head -300
npm audit --json 2>&1 | head -200
```

### secrets_scanning (Tier 1)
```bash
gitleaks detect --source . --report-format json
detect-secrets scan . --baseline .secrets.baseline
```

### license_compliance (Tier 1)
```bash
scancode --license --json-pp - src/ | head -300
```

### mutation_testing (Tier 1)
```bash
# Enforce time budget from config: time_budget_seconds
timeout $TIME_BUDGET mutmut run 2>&1
mutmut results 2>&1 | head -100
```

### architecture (Tier 3)
```bash
radon cc src/ -j 2>&1 | head -200
# LLM must analyze module coupling, layering, SOLID violations
```

### readability (Tier 3)
```bash
radon mi src/ -j 2>&1 | head -100
# LLM must assess naming clarity, function length, nesting depth
```

### error_handling (Tier 3)
```bash
# No reliable tool — LLM must scan for bare except, silent failures
grep -rn "except:" src/ | head -50
grep -rn "pass$" src/ | head -50
```

### documentation (Tier 3)
```bash
pydocstyle src/ 2>&1 | head -100
interrogate src/ -v 2>&1 | head -100
# LLM must assess quality, not just presence
```

### performance (Tier 3)
```bash
radon cc src/ -j --min C 2>&1 | head -100  # Complex functions
# LLM must identify actual bottlenecks
```

---

## Step 2: Evaluate (LLM Tier Routing)

### IF Tier 1 or Tier 2 → Call Gemini Flash

Get the prompt from the router:
```bash
python3 scripts/llm_router.py <dimension> .sessi-work/round_<n>/tools/<dimension>.txt
```

Use `gemini_prompt` field from output. Call Gemini:

```
[USE mcp__gemini-cli__ask-gemini]
model: gemini-2.5-flash
prompt: <gemini_prompt from router output>
```

Parse the JSON response. The Gemini response IS the dimension score.

**Token budget:** ≤ 8K input, ≤ 800 output (enforced by router prompt template)

---

### IF Tier 3 → Evaluate with Claude (this session)

Read tool output from `.sessi-work/round_<n>/tools/<dimension>.txt`.

**Step 2a (Tier 3 ONLY): Query Code Review Graph for compressed context**

Before reading source code, pull pre-computed structural intel from the CRG
knowledge graph. This replaces blind code reading with targeted questions.

**CRG status is already resolved** — `setup_target.py` auto-detected and built
the graph at session start. Read its output:

```bash
cat .sessi-work/crg_status.json
# → {"available": true, "node_count": 342, "action": "auto_built", "repo": "..."}
# OR {"available": false, "reason": "code-review-graph not installed — ..."}
```

If `available: false` → skip CRG; fall back to full code reading (higher token cost).

**If `available: true` → first call is always `get_minimal_context` (~100 tokens):**

```
[USE mcp__code-review-graph__get_minimal_context_tool]
task: "evaluate <dimension> dimension"
```

Read `risk_score` and `suggested_next_tools` — use them to focus the dimension
analysis rather than scanning the full codebase. Also check
`.sessi-work/crg_reconnaissance.json` (written in Step 2.5) for pre-identified
hotspots in this dimension's files.

**Step 2a.1: Eval-depth gate (deep-integration, replaces free LLM judgment)**

```bash
EVAL_DEPTH=$(python3 scripts/crg_analysis.py depth_gate \
  .sessi-work/crg_reconnaissance.json)
# Emits: deep | standard | fast
```

| `eval_depth` | risk_score       | Token budget per Tier 3 dim                       |
|--------------|------------------|---------------------------------------------------|
| `deep`       | ≥ 0.7            | Full LLM reasoning + hub source read (+ flow walk) |
| `standard`   | 0.3–0.7 (inclusive of 0.3) | Tool + LLM one-paragraph assessment      |
| `fast`       | < 0.3            | Tool output only, skip Tier 3 LLM assessment      |

The depth is a hard budget — do not read source for hub nodes if
`EVAL_DEPTH=fast`. This replaces "LLM decides how much to look" with
a deterministic, risk-proportional scan.

**Step 2a.2: CRG metrics for sub-score pull-down (architecture / error_handling)**

```bash
cat .sessi-work/crg_metrics.json
```

Relevant fields per Tier 3 dimension:

- **architecture** — `community_cohesion.score` (0–100) and
  `community_cohesion.unhealthy[]`. `score.py` takes `min(tool_score, cohesion)`
  so a repo with low-cohesion / oversized communities cannot score above the
  CRG signal. Evidence: cite `name`, `cohesion`, `size` from `unhealthy[]`.

- **error_handling** — `flow_coverage.score` and `flow_coverage.missing[]`.
  `score.py` takes `min(tool_score, flow_coverage)`. Findings: one per flow
  name in `missing[]`, severity `high` if the flow is in a hub community.

- **readability / performance** — use `hub_risk_map.hubs[]`. Each hub lists
  `fan_in` and `severity`. Large-function + hub + `severity=critical|high`
  → register as `readability:high` (readability) or `performance:medium`
  (performance) finding, cited with the numeric fan_in.

**Explicit hub fan-in thresholds (from crg_analysis.py):**

```
fan_in ≥ 15   → critical (untested) / high (tested)
fan_in ≥ 8    → high (untested) / medium (tested)
fan_in <  8   → medium (untested) / low (tested)
```

Score-file severities MUST use these buckets — no free-hand severity calls
for hub-related findings.

Then, per dimension, use the corresponding **CRG MCP tools** (available once
`.mcp.json` is loaded — the `code-review-graph` server exposes 27 tools):

| Dimension | CRG MCP tools to call | What to ask |
|-----------|----------------------|-------------|
| `architecture` | `get_hub_nodes` (top 10), `get_bridge_nodes`, `get_knowledge_gaps`, `get_surprising_connections`, `get_architecture_overview`, `list_communities`, `get_community` (low-cohesion ones) | Layering violations, chokepoints, cyclic deps, hub nodes doing too much, low-cohesion modules |
| `readability` | `find_large_functions`, `get_hub_nodes` | Functions > 100 LOC; hub nodes that have become god-objects |
| `performance` | `get_hub_nodes`, `list_flows`, `get_flow` (for top flows) | Hot paths through bottleneck functions; call depth of critical flows |
| `error_handling` | `get_affected_flows`, `semantic_search_nodes "except\|catch\|error"`, `list_flows`, `get_flow` (drill into specific flows) | Flows without error handlers; trace exact call step missing try/except |
| `documentation` | `generate_wiki` (first run) or `get_wiki_page`, `get_hub_nodes`, `get_docs_section` (targeted) | Undocumented hub nodes = highest-priority doc gaps |

**Token-efficient evaluation protocol:**

1. **CRG context (cheap)** — call the MCP tools above; they return structured JSON
   in ~500-2000 tokens total instead of reading 10,000+ lines of code
2. **Tool score** — What do the tools report? Extract numeric signal (0-100).
3. **LLM score** — Your assessment using CRG structural data + spot-reads of
   specific files/lines identified by CRG as problematic
4. **Reconcile** — `score = min(tool_score, llm_score)` — never inflate
5. **Evidence** — Every finding cites file:line from CRG output AND/OR tool output
6. **Gaps** — Cross-reference CRG knowledge_gaps with tool findings

**Token discipline for Tier 3:**
- Call `get_minimal_context` first (always) — orients analysis in ~100 tokens
- Read `crg_reconnaissance.json` for pre-identified hotspots in this dimension
- Read CRG tool output second; code third (only for files CRG flagged)
- Spot-read 2–5 specific functions CRG identified as problematic
- NEVER read whole files if CRG can answer the question
- Keep findings list ≤ 7 items
- Target: −30 to −50% token reduction vs pure-code-reading approach

**Additional targeted tools (call as needed):**
- `query_graph_tool(pattern="tests_for", target="<hub_node>")` — verify hub nodes have explicit tests
- `traverse_graph_tool(query="<function>", mode="bfs", depth=2)` — fan-in/fan-out for a specific node
- `query_graph_tool(pattern="callers_of", target="<function>")` — who calls this function

**Graceful degradation:** If CRG is not installed or graph is empty, the
evaluation still works — just with higher token cost. The framework must
remain functional without CRG.

---

## Step 3: Write Score File

Save to `.sessi-work/round_<n>/scores/<dimension>.json`:

```json
{
  "dimension": "<name>",
  "round": <n>,
  "llm_tier": <1|2|3>,
  "llm_provider": "gemini|claude_native",
  "tool_score": <0-100>,
  "llm_score": <0-100>,
  "score": <min(tool_score, llm_score)>,
  "findings": [
    {
      "file": "<path|null>",
      "line": <int|null>,
      "severity": "critical|high|medium|low|info",
      "message": "<description>",
      "evidence": "<tool output excerpt or file:line>"
    }
  ],
  "gaps": ["<gap 1>", "<gap 2>"],
  "tool_outputs": "<path to raw tool output>",
  "reconcile": "tool_first"
}
```

**Severity canonicalization:** the registry requires one of `critical|high|medium|low|info`.
Map legacy tool outputs as: `error/critical → critical`, `warning → medium`, `info/note → info`,
known CVE high severities → `high`.

---

## Step 4: Register Findings in the Issue Registry

**Every finding from Step 3 MUST be written to the persistent issue registry.**
This is what makes the tool issue-driven (not score-driven): issues persist across rounds
until explicitly `fixed`, `deferred` (with reason), or `wontfix` (with reason).

For each finding in the score file:

```bash
# Write the finding to a temp JSON file with the exact keys: severity, message, file, line, evidence
echo '{"severity":"high","message":"...","file":"src/foo.py","line":42,"evidence":"..."}' \
  > /tmp/finding.json

python3 scripts/issue_tracker.py add \
  .sessi-work/issue_registry.json \
  <dimension> \
  <round_num> \
  /tmp/finding.json
```

Or equivalently, batch via a small loop over the `findings[]` array in `<dimension>.json`.

**Idempotency guarantee:** the registry hashes `(dimension, file, line, message[:80])` into a
deterministic ID, so repeating the same finding in round 2 updates `last_seen_round` rather than
duplicating the entry.

After Step 4 completes for all dimensions, print a registry summary:

```bash
python3 scripts/issue_tracker.py summary .sessi-work/issue_registry.json
```

The `open_critical` / `open_high` / `open_medium` counts feed directly into
`score.py` and the Step 3e early-stop decision in `SKILL.md`.

---

## Anti-Bias Rules (All Tiers)

1. `score = min(tool_score, llm_score)` — no exceptions
2. Every finding needs `evidence` field — no bare assertions
3. If tool gives no output (tool missing/error) → `tool_score = null`, use `llm_score` only, flag in score file
4. Δ > 10 from previous round requires tool evidence or ≥ 3 lines of git diff
5. Tier 1/2 evaluations: trust the tool output — Gemini's role is only to parse and structure it

---

## Token Cost Reference

| Tier | Provider | Typical cost/dim | Use case |
|------|----------|-----------------|---------|
| 1 | Gemini Flash | ~$0.001 | Tool summarization |
| 2 | Gemini Flash | ~$0.002 | Light judgment |
| 3 | Claude Sonnet | ~$0.08 | Deep reasoning |

**Total per round (12 dims + improve):**
- Tier 1×6 + Tier 2×1: ~$0.01
- Tier 3×5: ~$0.40
- Improve step: ~$0.45
- **Total: ~$0.86/round** (vs ~$3.00 all-Claude)
